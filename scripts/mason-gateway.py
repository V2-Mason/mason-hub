#!/usr/bin/env python3
"""
Mason Gateway — 永驻 daemon，Mason Hub 的值班员工

架构（对标 OpenClaw Gateway，v2: agentic loop + tool_use + 记忆回写）:
  MASONHUB.md       = 灵魂文件（权限 + 检查清单）
  SYSTEM_MAP.md     = 系统状态（Gateway 可读写）
  mason-gateway.py  = Gateway（本文件，永驻 daemon）
  scripts/          = Skills（纯脚本，零成本执行）
  Anthropic API     = 推理引擎（tool_use + agentic loop）

执行模型:
  Agentic loop: 观察 → 思考 → 行动（tool_use）→ 观察结果 → ... 直到完成
  Mason session 活跃 → Gateway 自动让路
  每次 session 结束 → 自动回写记忆到 gateway-memory.jsonl

两层执行:
  Tier 1: 纯脚本（data-sync, health-check）→ 直接 subprocess，零成本
  Tier 2: 需要推理 → agentic loop（tool_use），可读写文件 + 跑命令

安全边界:
  read_file:    只限 HUB_DIR 内
  write_file:   只限白名单路径（SYSTEM_MAP, MASONHUB checklist, gateway-memory）
  run_command:  白名单命令 + 超时 60s + 无 sudo
  max_turns:    10（防止无限循环）

成本:
  heartbeat 每小时 1 次，平均 3-5 轮 tool_use ≈ $0.01-0.03/次
  每天 14 次 ≈ $0.15-0.40/天 ≈ $5-12/月

用法:
  python3 mason-gateway.py                # 前台运行
  python3 mason-gateway.py --once         # 只跑一轮（调试）
  python3 mason-gateway.py --once --force # 忽略 Mason session + 时间窗口
  python3 mason-gateway.py --status       # 查看状态
"""

import json
import os
import signal
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- 配置 ---

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
MODEL_HEAVY = os.environ.get("HEARTBEAT_MODEL", "claude-sonnet-4-20250514")
MODEL_LIGHT = os.environ.get("HEARTBEAT_MODEL_LIGHT", "claude-haiku-4-5-20251001")
MODEL = MODEL_HEAVY  # 默认用重模型，heartbeat 动态切换
MAX_OUTPUT_TOKENS = 1024
MAX_TURNS_HEAVY = 20  # 重巡最大轮次
MAX_TURNS_LIGHT = 8   # 轻量 agentic（Haiku 常规巡检）最大轮次
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

LOG_FILE = HUB_DIR / "logs" / "gateway.log"
LOCK_FILE = HUB_DIR / "data" / "gateway.lock"
QUEUE_FILE = HUB_DIR / "data" / "events" / "queue.jsonl"
MASONHUB_FILE = HUB_DIR / "MASONHUB.md"
KNOWN_STATES_FILE = HUB_DIR / "data" / "gateway-known-states.yaml"
MEMORY_FILE = HUB_DIR / "data" / "gateway-memory.jsonl"

HEARTBEAT_INTERVAL = 3600
QUEUE_CHECK_INTERVAL = 60
LOCK_TIMEOUT = 600

CST = timezone(timedelta(hours=8))

# 可写文件白名单（Gateway 只能写这些）
WRITABLE_PATHS = [
    "SYSTEM_MAP.md",
    "MASONHUB.md",
    "data/gateway-memory.jsonl",
    "data/events/queue.jsonl",
    "data/repair_queue.json",
]

REPAIR_LOCK = Path("/tmp/repair-session.lock")
REPAIR_QUEUE_FILE = HUB_DIR / "data" / "repair_queue.json"

# 可重启/reload 的服务白名单
ALLOWED_SERVICES = [
    "surenxuan-fastapi",
    "ssh-tunnel",
    "mason-gateway",
]

# 可执行命令白名单（前缀匹配）— 这是权限边界，不只是安全防护
ALLOWED_COMMANDS = [
    # 系统监控（只读）
    "uptime",
    "free",
    "df",
    "date",
    "cat ",
    "head ",
    "tail ",
    "wc ",
    "ls ",
    # Git（完整操作权限）
    "git log",
    "git status",
    "git diff",
    "git add",
    "git commit",
    "git push",
    "git pull",
    # 服务管理（限定服务名，见 ALLOWED_SERVICES）
    "systemctl status",
    "systemctl is-active",
    "systemctl restart",
    "systemctl reload",
    # 脚本执行（信任脚本层）
    "bash scripts/",
    "bash data/pipelines/",
    "python3 scripts/",
    f"{sys.executable} scripts/",
    # 部署 + 远程
    "scp ",
    "ssh ",
    # Cron（可读可写）
    "crontab",
    # 文件操作（只读/诊断）
    "find ",
    "grep ",
    "chmod ",
    # 进程 + 网络诊断
    "pgrep",
    "ps ",
    "curl -s",
    "ping ",
    "cd ",
    "timeout ",
    # 技能脚本
    "bash skills/",
]

# 全局状态
running = True
last_heartbeat = 0
task_queue = deque()
queue_file_pos = 0
_last_event_analysis = {}  # {event_type: timestamp} — 同类事件去重
_last_heavy_heartbeat = 0  # 上次重巡时间
_last_light_result = None  # 上次轻巡结果（用于变化检测）
_was_yielding = False  # Mason 让路状态（用于日志去重，启动时从日志恢复）
HEAVY_HEARTBEAT_INTERVAL = 14400  # 4 小时强制一次重巡


# ========================================
# 工具函数
# ========================================

def log(message: str):
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S CST")
    entry = f"[{ts}] {message}"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception:
        print(entry, flush=True)  # 文件写入失败时 fallback 到 stdout


def in_time_window() -> bool:
    return 8 <= datetime.now(CST).hour < 22


def send_slack(message: str, prefix: str = "🫀 Gateway") -> bool:
    if not SLACK_WEBHOOK:
        log("Slack webhook 未配置，跳过")
        return False
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", SLACK_WEBHOOK,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"text": f"{prefix}\n{message}"})],
            capture_output=True, timeout=10,
        )
        return True
    except Exception as e:
        log(f"Slack 发送失败: {e}")
        return False


def mason_session_active() -> bool:
    """检测 Mason 是否活跃：claude 进程存在 + 终端最近 15 分钟有输入"""
    try:
        # 1. claude 进程必须存在
        result = subprocess.run(
            ["pgrep", "-f", "claude"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return False

        # 2. 检查所有终端的 idle 时间（w 命令的 IDLE 列）
        #    如果所有终端都 idle 超过 15 分钟，认为 Mason 不在
        import glob
        now = time.time()
        min_idle = float('inf')
        for pts in glob.glob("/dev/pts/[0-9]*"):
            try:
                mtime = os.path.getmtime(pts)
                idle = now - mtime
                min_idle = min(min_idle, idle)
            except OSError:
                continue

        # 最活跃的终端 idle < 15 分钟 → Mason 在
        return min_idle < 900
    except Exception:
        return False


# ========================================
# P0: Tool Definitions (Anthropic tool_use)
# ========================================

TOOLS = [
    {
        "name": "read_file",
        "description": "读取 mason-hub 内的文件。路径相对于 ~/mason-hub/。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对路径，如 'SYSTEM_MAP.md' 或 'data/events/queue.jsonl'"
                },
                "tail": {
                    "type": "integer",
                    "description": "只读最后 N 行（大文件时用），默认读全文"
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "写入文件（仅限白名单路径：SYSTEM_MAP.md, MASONHUB.md, gateway-memory.jsonl, queue.jsonl）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对路径（必须在白名单内）"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的完整内容"
                },
                "append": {
                    "type": "boolean",
                    "description": "追加模式（默认 false = 覆盖）"
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "执行 shell 命令（仅限白名单命令，超时 60s，无 sudo）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令"
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "send_slack_message",
        "description": "发送 Slack 消息到 #system-alerts。",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "消息内容"
                },
                "level": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                    "description": "消息级别"
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "list_directory",
        "description": "列出目录内容。路径相对于 ~/mason-hub/。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对路径，如 'scripts/' 或 'data/events/'"
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "save_memory",
        "description": "保存发现到持久化记忆（gateway-memory.jsonl）。下次 heartbeat 会优先读取未完结条目（will_retry/pending_mason）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "finding": {
                    "type": "string",
                    "description": "发现的内容（一句话）"
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                    "description": "严重程度"
                },
                "status": {
                    "type": "string",
                    "enum": ["resolved", "pending_mason", "will_retry", "monitoring", "suggestion", "emitted"],
                    "description": "resolved=已解决, pending_mason=等Mason决策, will_retry=下次续接, monitoring=持续关注, suggestion=建议, emitted=已发射给dispatcher"
                },
                "action_taken": {
                    "type": "string",
                    "description": "已采取的行动（如果有）"
                },
                "context": {
                    "type": "object",
                    "description": "续接上下文（will_retry 时建议填写）：file, progress, next_step, blockers"
                },
            },
            "required": ["finding", "severity", "status"],
        },
    },
    {
        "name": "patch_file",
        "description": "增量编辑白名单文件：查找 old_text 并替换为 new_text。比 write_file 更适合更新 SYSTEM_MAP.md 等大文件（不需要传完整内容）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "相对路径（必须在白名单内）"
                },
                "old_text": {
                    "type": "string",
                    "description": "要被替换的原文片段（必须精确匹配）"
                },
                "new_text": {
                    "type": "string",
                    "description": "替换后的新文本"
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
]


# ========================================
# P0: Tool Execution
# ========================================

def execute_tool(name: str, input_data: dict) -> str:
    """执行工具调用，返回结果字符串"""
    try:
        if name == "read_file":
            return _tool_read_file(input_data)
        elif name == "write_file":
            return _tool_write_file(input_data)
        elif name == "run_command":
            return _tool_run_command(input_data)
        elif name == "send_slack_message":
            return _tool_send_slack(input_data)
        elif name == "list_directory":
            return _tool_list_directory(input_data)
        elif name == "save_memory":
            return _tool_save_memory(input_data)
        elif name == "patch_file":
            return _tool_patch_file(input_data)
        else:
            return f"错误: 未知工具 {name}"
    except Exception as e:
        return f"错误: {e}"


def _tool_read_file(input_data: dict) -> str:
    rel_path = input_data["path"]
    full_path = (HUB_DIR / rel_path).resolve()

    # 安全检查：必须在 HUB_DIR 内
    if not str(full_path).startswith(str(HUB_DIR.resolve())):
        return "错误: 路径越界，只能读取 mason-hub 内的文件"

    if not full_path.exists():
        return f"文件不存在: {rel_path}"

    if full_path.is_dir():
        return f"这是目录，请用 list_directory"

    try:
        text = full_path.read_text()
        tail = input_data.get("tail")
        if tail:
            lines = text.strip().split("\n")
            text = "\n".join(lines[-tail:])

        # 限制输出大小（防止塞爆 context）
        if len(text) > 8000:
            text = text[:8000] + f"\n\n... [截断，原文 {len(text)} 字符]"

        return text
    except Exception as e:
        return f"读取失败: {e}"


def _tool_write_file(input_data: dict) -> str:
    rel_path = input_data["path"]
    content = input_data["content"]
    append = input_data.get("append", False)

    # 白名单检查
    if rel_path not in WRITABLE_PATHS:
        return f"错误: 不允许写入 {rel_path}。可写路径: {', '.join(WRITABLE_PATHS)}"

    full_path = HUB_DIR / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        mode = "a" if append else "w"
        with open(full_path, mode) as f:
            f.write(content)
        action = "追加" if append else "写入"
        return f"✅ 已{action} {rel_path} ({len(content)} 字符)"
    except Exception as e:
        return f"写入失败: {e}"


def _tool_patch_file(input_data: dict) -> str:
    rel_path = input_data["path"]
    old_text = input_data["old_text"]
    new_text = input_data["new_text"]

    # 白名单检查
    if rel_path not in WRITABLE_PATHS:
        return f"错误: 不允许写入 {rel_path}。可写路径: {', '.join(WRITABLE_PATHS)}"

    full_path = HUB_DIR / rel_path
    if not full_path.exists():
        return f"错误: 文件不存在: {rel_path}"

    try:
        content = full_path.read_text()
        if old_text not in content:
            return f"错误: 未找到要替换的文本片段（{len(old_text)} 字符）。请用 read_file 确认当前内容"
        if content.count(old_text) > 1:
            return f"错误: 找到 {content.count(old_text)} 处匹配，请提供更精确的片段以避免歧义"
        new_content = content.replace(old_text, new_text, 1)
        full_path.write_text(new_content)
        return f"✅ 已更新 {rel_path}（替换了 {len(old_text)} → {len(new_text)} 字符）"
    except Exception as e:
        return f"编辑失败: {e}"


def _check_command_allowed(cmd: str) -> bool:
    """检查单条命令是否在白名单内（前缀匹配）"""
    cmd = cmd.strip()
    return any(cmd.startswith(prefix) for prefix in ALLOWED_COMMANDS)


def _tool_run_command(input_data: dict) -> str:
    command = input_data["command"]

    # 白名单检查：支持 && / || / ; 组合命令，逐段校验
    import re
    sub_commands = re.split(r'\s*(?:&&|\|\||;)\s*', command)
    all_allowed = all(_check_command_allowed(sub) for sub in sub_commands if sub.strip())

    if not all_allowed:
        failed = [sub.strip() for sub in sub_commands if sub.strip() and not _check_command_allowed(sub)]
        return f"错误: 命令不在白名单内: {failed[0][:60]}... 允许的前缀: {', '.join(ALLOWED_COMMANDS[:10])}..."

    # systemctl restart/reload 限定服务名
    for action in ("systemctl restart", "systemctl reload"):
        if command.startswith(action):
            service = command[len(action):].strip()
            if service not in ALLOWED_SERVICES:
                return f"错误: 不允许操作服务 '{service}'。允许的服务: {', '.join(ALLOWED_SERVICES)}"

    # 安全：禁止危险操作
    dangerous = ["rm ", "rm -", "sudo", "> /", "| sudo", "&& rm", "; rm", "dd if="]
    for d in dangerous:
        if d in command:
            return f"错误: 检测到危险操作 '{d}'，拒绝执行"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(HUB_DIR),
            timeout=120,
        )
        output = ""
        if result.stdout:
            output += result.stdout[-2000:]
        if result.stderr:
            output += f"\n[stderr] {result.stderr[-500:]}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip() if output.strip() else "(无输出)"
    except subprocess.TimeoutExpired:
        return "错误: 命令超时 (120s)"
    except Exception as e:
        return f"执行失败: {e}"


def _tool_send_slack(input_data: dict) -> str:
    message = input_data["message"]
    level = input_data.get("level", "info")

    prefix_map = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}
    prefix = prefix_map.get(level, "🫀")

    ok = send_slack(message, prefix=f"{prefix} Gateway")
    if ok:
        return f"✅ Slack 已发送 ({level})"
    return "❌ Slack 发送失败（webhook 未配置或网络错误）"


def _tool_list_directory(input_data: dict) -> str:
    rel_path = input_data["path"]
    full_path = (HUB_DIR / rel_path).resolve()

    if not str(full_path).startswith(str(HUB_DIR.resolve())):
        return "错误: 路径越界"

    if not full_path.exists():
        return f"目录不存在: {rel_path}"

    if not full_path.is_dir():
        return f"这是文件，不是目录"

    try:
        entries = sorted(full_path.iterdir())
        lines = []
        for e in entries[:50]:  # 最多 50 项
            suffix = "/" if e.is_dir() else f" ({e.stat().st_size}B)"
            lines.append(f"  {e.name}{suffix}")
        result = f"{rel_path} ({len(entries)} 项):\n" + "\n".join(lines)
        if len(entries) > 50:
            result += f"\n  ... 还有 {len(entries) - 50} 项"
        return result
    except Exception as e:
        return f"列目录失败: {e}"


def _tool_save_memory(input_data: dict) -> str:
    finding = input_data["finding"]
    severity = input_data.get("severity", "info")
    status = input_data.get("status", "resolved")
    action_taken = input_data.get("action_taken", "")
    context = input_data.get("context", None)

    entry = {
        "timestamp": datetime.now(CST).isoformat(),
        "finding": finding,
        "severity": severity,
        "status": status,
        "action_taken": action_taken,
    }
    if context:
        entry["context"] = context

    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return f"✅ 记忆已保存 [{status}]: {finding[:50]}..."
    except Exception as e:
        return f"记忆保存失败: {e}"


# ========================================
# P1: Agentic Loop
# ========================================

def load_known_states() -> str:
    """加载 Mason 已确认的已知状态，过滤过期条目，返回纯文本供 prompt 注入"""
    if not KNOWN_STATES_FILE.exists():
        return ""

    try:
        import yaml
        states = yaml.safe_load(KNOWN_STATES_FILE.read_text())
        if not states:
            return ""

        today = datetime.now(CST).strftime("%Y-%m-%d")
        active = []
        for s in states:
            expires = str(s.get("expires", "2099-12-31"))
            if expires >= today:
                active.append(f"- [{s.get('date')}] {s.get('decision')} → {s.get('impact')}")

        if not active:
            return ""

        return "Mason 已确认的已知状态（遇到这些情况直接跳过，不告警）:\n" + "\n".join(active)
    except Exception as e:
        log(f"[KnownStates] 加载失败: {e}")
        return ""


def load_recent_memories(n: int = 5) -> str:
    """加载 Gateway 记忆：先未完结条目（去重），再最近 N 条已完结条目"""
    if not MEMORY_FILE.exists():
        return "[无历史记忆]"

    try:
        lines = MEMORY_FILE.read_text().strip().split("\n")
        all_entries = []
        for line in lines:
            if line.strip():
                try:
                    all_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        if not all_entries:
            return "[无历史记忆]"

        # 第一步：未完结条目（pending_mason / will_retry），按 finding 去重取最新
        unfinished_statuses = {"pending_mason", "will_retry"}
        unfinished_map = {}  # finding -> entry（后出现的覆盖前面的）
        for entry in all_entries:
            if entry.get("status") in unfinished_statuses:
                unfinished_map[entry.get("finding", "")] = entry

        # 第二步：最近 N 条已完结条目（resolved / monitoring / suggestion / emitted / 无 status 的旧条目）
        finished = [e for e in all_entries if e.get("status") not in unfinished_statuses]
        recent_finished = finished[-n:] if len(finished) > n else finished

        def format_entry(entry):
            status = entry.get("status", "?")
            ts = entry.get("timestamp", "?")[:16]
            finding = entry.get("finding", "?")
            action = entry.get("action_taken", "")
            context = entry.get("context", {})
            line = f"  [{status}] {ts}: {finding}"
            if action:
                line += f" → {action}"
            if context and isinstance(context, dict):
                next_step = context.get("next_step", "")
                if next_step:
                    line += f"\n    下一步: {next_step}"
            return line

        result_parts = []
        if unfinished_map:
            result_parts.append("=== 未完结任务 (优先处理) ===")
            for entry in unfinished_map.values():
                result_parts.append(format_entry(entry))
        if recent_finished:
            result_parts.append("=== 近期背景 (参考) ===")
            for entry in recent_finished:
                result_parts.append(format_entry(entry))

        return "\n".join(result_parts) if result_parts else "[无历史记忆]"
    except Exception:
        return "[记忆读取失败]"


def run_agentic_session(system_prompt: str, user_prompt: str, model: str = None, max_turns: int = None) -> str:
    """
    Agentic loop: 多轮 tool_use 直到任务完成。

    流程: prompt → API → (tool_use → 执行 → 结果 → API) × N → 最终文本
    安全: 最多 max_turns 轮，每轮超时 60s
    支持 prompt caching: system prompt 标记为 ephemeral cache，降低 90% 重复 token 成本
    """
    import anthropic

    use_model = model or MODEL
    use_max_turns = max_turns or MAX_TURNS_HEAVY

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": user_prompt}]

    # Prompt caching: 将 system prompt 包装为带 cache_control 的格式
    # Anthropic API 会缓存 5 分钟，后续请求命中缓存降低 90% 输入成本
    system_with_cache = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    total_input_tokens = 0
    total_output_tokens = 0

    for turn in range(use_max_turns):
        try:
            response = client.messages.create(
                model=use_model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_with_cache,
                tools=TOOLS,
                messages=messages,
            )
        except Exception as e:
            log(f"[Agentic] Turn {turn + 1} API 失败: {e}")
            return f"API 错误: {e}"

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # 记录 cache 命中情况（首轮）
        if turn == 0:
            cache_read = getattr(response.usage, 'cache_read_input_tokens', 0) or 0
            cache_write = getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
            if cache_read > 0:
                log(f"[Agentic] Cache hit: {cache_read} tokens cached ({use_model})")
            elif cache_write > 0:
                log(f"[Agentic] Cache write: {cache_write} tokens ({use_model})")

        # 检查是否有 tool_use
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_calls:
            # 没有工具调用 → 任务完成
            final_text = "\n".join(b.text for b in text_blocks)
            log(f"[Agentic] 完成: {turn + 1} 轮, {total_input_tokens}+{total_output_tokens} tokens ({use_model})")
            return final_text

        # 有工具调用 → 执行并继续
        log(f"[Agentic] Turn {turn + 1}: {len(tool_calls)} 个工具调用")

        # 将 assistant 的响应加入消息历史
        messages.append({"role": "assistant", "content": response.content})

        # 执行每个工具并收集结果
        tool_results = []
        for tc in tool_calls:
            log(f"  🔧 {tc.name}({json.dumps(tc.input, ensure_ascii=False)[:80]})")
            result = execute_tool(tc.name, tc.input)
            log(f"  📎 结果: {result[:80]}...")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        # stop_reason == "end_turn" 且有 tool_use → 继续循环
        if response.stop_reason == "end_turn" and not tool_calls:
            break

    log(f"[Agentic] 达到最大轮次 {use_max_turns} ({use_model})")
    return "[达到最大轮次限制]"


# ========================================
# Heartbeat (升级版: agentic loop)
# ========================================

def run_light_heartbeat() -> bool:
    """轻巡：纯脚本检查，零 token。返回 True=正常，False=异常需重巡"""
    global _last_light_result
    log("[Heartbeat] 轻巡开始")
    try:
        # 跑 data_health_check（--no-emit 避免自产自消：Gateway 内部调用不发射事件）
        result = subprocess.run(
            ["bash", str(HUB_DIR / "data/pipelines/data_health_check.sh"), "--no-emit"],
            capture_output=True, text=True, cwd=str(HUB_DIR), timeout=120,
        )
        health_output = result.stdout[-500:] if result.stdout else ""

        # 检查磁盘
        disk = subprocess.run(
            ["df", "-h", "/"], capture_output=True, text=True, timeout=10,
        )
        disk_output = disk.stdout if disk.stdout else ""

        # 检查内存
        mem = subprocess.run(
            ["free", "-m"], capture_output=True, text=True, timeout=10,
        )
        mem_output = mem.stdout if mem.stdout else ""

        # 提取关键指标做变化检测
        current = f"{health_output[:200]}|{disk_output[:100]}|{mem_output[:100]}"
        changed = (_last_light_result is not None and current != _last_light_result)
        _last_light_result = current

        # 判断是否异常（排除 known-states 中已确认的问题）
        has_error = result.returncode != 0 or "❌" in health_output or ":x:" in health_output

        # 如果有已知状态声明"健康检查基线是 10/15"，则部分失败不算异常
        if has_error and KNOWN_STATES_FILE.exists():
            try:
                import yaml
                known = yaml.safe_load(KNOWN_STATES_FILE.read_text()) or []
                today = datetime.now(CST).strftime("%Y-%m-%d")
                suppressed = any(
                    s.get("id") == "health-check-baseline"
                    and str(s.get("expires", "")) >= today
                    for s in known
                )
                if suppressed:
                    # 检查是否比基线更差（新增失败项）
                    fail_count = health_output.count("❌") + health_output.count(":x:")
                    if fail_count <= 5:  # 基线是 10/15 = 5 个已知失败
                        has_error = False
                        log(f"[Heartbeat] 轻巡: {fail_count} 个失败项在已知基线内，不升级")
            except Exception:
                pass  # YAML 解析失败不影响主逻辑
        # 磁盘 >85%
        disk_critical = False
        for line in disk_output.split("\n"):
            if "%" in line:
                try:
                    pct = int(line.split()[-2].replace("%", ""))
                    if pct > 85:
                        disk_critical = True
                except (ValueError, IndexError):
                    pass

        if has_error or disk_critical:
            log(f"[Heartbeat] 轻巡发现异常，升级为重巡")
            return False

        if changed:
            log(f"[Heartbeat] 轻巡发现变化，升级为重巡")
            return False

        log("[Heartbeat] 轻巡 ✅ 正常")
        return True
    except Exception as e:
        log(f"[Heartbeat] 轻巡异常: {e}，升级为重巡")
        return False


def run_heartbeat(force_heavy: bool = False):
    """Heartbeat: 读 MASONHUB → agentic loop → 自主检查 + 修复 + 回写记忆

    force_heavy=True: 每 4 小时或异常时用 Sonnet + 20 轮（深度诊断）
    force_heavy=False: 常规用 Haiku + 8 轮（快速确认，省 token）
    """
    use_model = MODEL_HEAVY if force_heavy else MODEL_LIGHT
    use_turns = MAX_TURNS_HEAVY if force_heavy else MAX_TURNS_LIGHT
    mode_label = "重巡 Sonnet" if force_heavy else "轻量 Haiku"
    log(f"[Heartbeat] 开始 ({mode_label})")

    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    memories = load_recent_memories()
    known_states = load_known_states()

    system_prompt = f"""你是 Mason Hub 的值班工程师。当前时间: {now_cst}

你的完整行为空间定义在 MASONHUB.md 中，每次执行前必须先读取。
简要原则：
- 🟢 不涉及费用的执行类操作（改配置、重启白名单服务、git 操作、清日志）→ 自主做
- 🟡 涉及费用的操作（付费 API、云资源启停、外部服务）→ 记录为 pending_mason，发 Slack，继续其他工作
- 🔴 品牌定位、平台账号操作、推广预算、密钥管理、新建 Agent → 绝不碰，只记录建议

你有以下工具：
- read_file: 读取 mason-hub 内的任何文件
- write_file: 写入白名单文件（整个覆盖，适合小文件）
- patch_file: 增量编辑白名单文件（查找替换，适合 SYSTEM_MAP.md 等大文件）
- run_command: 执行命令（系统检查、脚本执行、git、ssh、服务管理）
- send_slack_message: 发 Slack 通知 Mason
- list_directory: 列目录
- save_memory: 保存发现到持久记忆（带 status 字段：resolved/pending_mason/will_retry/monitoring）

关键文件路径（避免浪费轮次搜索）：
- 记忆: data/gateway-memory.jsonl
- 修复队列: data/repair_queue.json
- 数据健康检查: bash data/pipelines/data_health_check.sh（注意：在 data/pipelines/ 下，不在 scripts/ 下）
- 事件队列: data/events/queue.jsonl
- Dispatcher 日志: logs/dispatcher.log
- SYSTEM_MAP: SYSTEM_MAP.md（更新时用 patch_file，不要用 write_file）
- 阿里云 SSH: ssh -o ConnectTimeout=5 root@106.14.44.68 "命令"

工作节奏:
1. 先检查记忆中 will_retry 的任务 → 有就先续接
2. 检查 data/repair_queue.json 里 status=repair_attempted 的条目 → 重新验证问题是否已修复
   - 已修复 → 运行 python3 scripts/submit-repair.py resolve <id>
   - 未修复 且 attempts<3 → 运行 python3 scripts/submit-repair.py update <id> --status pending（触发再次修复）
   - 未修复 且 attempts>=3 → 运行 python3 scripts/submit-repair.py update <id> --status pending_mason
3. 读 MASONHUB.md 了解完整行为空间和巡逻清单
4. 特别注意 MASONHUB.md 的 "### Mason 已确认" 区块 — 这些是 Mason 明确确认的已知状态，遇到时直接跳过，不升级不重复告警
5. 逐项执行检查，发现问题时走决策树（自主修/排队/等审批/不碰）
6. ≤3 轮 tool use 能修好的 → 立即修，save_memory status=resolved
7. 修不完的 → 提交修复请求: python3 scripts/submit-repair.py submit --issue "描述" --symptom "症状" --location "文件:行号" --severity medium
   然后 save_memory status=emitted，继续巡逻
8. 需要 Mason 的 → save_memory status=pending_mason + send_slack
9. 如果一切正常，直接回复"✅ 系统正常"即可，不需要逐项汇报
10. 如果本次 heartbeat 发现了新的可复用经验（不是一次性修复，而是"下次遇到类似情况也该这么做"的规律），用 patch_file 追加到 MASONHUB.md 的 "## Learned Skills" section。格式：`- **skill_NNN: 标题** — 规则。[来源: 日期]`。编号递增，不要重复已有 skill。"""

    known_states_block = f"\n\n{known_states}" if known_states else ""

    user_prompt = f"""执行 heartbeat 检查。

上次检查的记忆:
{memories}{known_states_block}

请开始：先读 MASONHUB.md 了解检查清单，然后逐项检查。"""

    try:
        result = run_agentic_session(system_prompt, user_prompt, model=use_model, max_turns=use_turns)
        log(f"[Heartbeat] 结果 ({mode_label}): {result[:150]}...")

        # 如果结果不是"正常"，发 Slack
        is_normal = result.strip().startswith("✅") and len(result.strip()) < 100
        if not is_normal and result and not result.startswith("["):
            send_slack(result)
            log("[Heartbeat] 📨 已发 Slack")
        else:
            log("[Heartbeat] ✅ 正常")

    except Exception as e:
        error_msg = f"❌ Heartbeat 失败: {e}"
        log(error_msg)
        send_slack(error_msg)


# ========================================
# 事件分析 (升级版: agentic loop)
# ========================================

def analyze_event(event: dict):
    """分析事件 — L0-1 脚本处理，L2-3 agentic loop（同类事件 1 小时去重）"""
    event_type = event.get("event", "unknown")
    level = event.get("level", 0)

    # Level 0-1: 纯脚本处理
    if level <= 1:
        log(f"[Tier 1] 事件 {event_type} (L{level}): 脚本处理")
        if event_type in ("data-sync-complete", "health-check-all-green", "health-check-failed"):
            _execute_script_task("event-router-process")
        return

    # 同类事件去重：1 小时内不重复做完整 agentic 分析
    now = time.time()
    last_time = _last_event_analysis.get(event_type, 0)
    if now - last_time < 3600:
        elapsed = int(now - last_time)
        log(f"[Agentic] 事件 {event_type} (L{level}): 跳过（{elapsed}s 前已分析，1h 去重）")
        return
    _last_event_analysis[event_type] = now

    # Level 2-3: agentic loop
    log(f"[Agentic] 事件 {event_type} (L{level}): 需要推理")
    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")

    memories = load_recent_memories()

    system_prompt = f"""你是 Mason Hub 的值班监督员。当前时间: {now_cst}

你收到了一个需要分析的系统事件。你有工具可以读取文件、执行命令、发 Slack 通知。

关键文件路径（不要浪费轮次搜索）：
- 数据健康检查: bash data/pipelines/data_health_check.sh（在 data/pipelines/ 下）
- 记忆: data/gateway-memory.jsonl
- SYSTEM_MAP: SYSTEM_MAP.md（更新时用 patch_file，不要用 write_file）

分析步骤:
1. **先读记忆** — 如果同类事件之前已分析过，直接复用结论，不要重复诊断
2. 理解事件含义
3. 读取相关文件获取上下文
4. 能自动处理（≤3 步）→ 执行 + save_memory status=resolved
5. 需要 Mason → send_slack_message + save_memory status=pending_mason
6. 更新 SYSTEM_MAP.md（用 patch_file，如果事件改变了能力线状态）

效率原则：同一类事件连续出现时，不要每次都完整诊断。先读 data/gateway-memory.jsonl 看之前的分析结论，状态没变就只 save_memory 记录时间戳即可。"""

    user_prompt = f"""分析以下事件:

{json.dumps(event, ensure_ascii=False, indent=2)}

上次检查的记忆（先看这里，避免重复诊断）:
{memories}

请开始分析。"""

    try:
        # 事件分析用 Haiku（大部分是重复事件），L3 级用 Sonnet
        event_model = MODEL_HEAVY if level >= 3 else MODEL_LIGHT
        event_turns = MAX_TURNS_HEAVY if level >= 3 else MAX_TURNS_LIGHT
        result = run_agentic_session(system_prompt, user_prompt, model=event_model, max_turns=event_turns)
        log(f"[Agentic] 事件分析完成 ({event_model.split('-')[1]}): {result[:100]}...")

        # L3 必须通知
        if level >= 3 and "slack" not in result.lower():
            send_slack(f"🔴 L3 事件: {event_type}\n{result}", prefix="🫀 Gateway")

    except Exception as e:
        log(f"[Agentic] 事件分析失败: {e}")


# ========================================
# Tier 1: 纯脚本执行
# ========================================

SCRIPT_TASKS = {
    "data-sync": {
        "script": "data/pipelines/data-sync.sh",
        "desc": "数据同步（阿里云→GCP）",
    },
    "health-check": {
        "script": "data/pipelines/data_health_check.sh",
        "desc": "数据健康检查",
    },
    "event-router-process": {
        "script_cmd": [sys.executable, "scripts/event_router.py", "--process-new"],
        "desc": "事件路由处理",
    },
    "dispatcher-scan": {
        "script": "scripts/dispatcher.sh",
        "desc": "Dispatcher 任务扫描",
    },
}


def _execute_script_task(task_id: str) -> dict:
    task_def = SCRIPT_TASKS.get(task_id)
    if not task_def:
        return {"ok": False, "error": f"未知: {task_id}"}

    log(f"[Tier 1] {task_def['desc']}")
    try:
        if "script_cmd" in task_def:
            cmd = task_def["script_cmd"]
        else:
            cmd = ["bash", str(HUB_DIR / task_def["script"])]

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(HUB_DIR), timeout=300,
        )
        ok = result.returncode == 0
        log(f"[Tier 1] {task_def['desc']}: {'✅' if ok else '❌'}")
        return {"ok": ok, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ========================================
# 事件队列扫描
# ========================================

def scan_event_queue():
    global queue_file_pos
    if not QUEUE_FILE.exists():
        return
    try:
        with open(QUEUE_FILE) as f:
            f.seek(queue_file_pos)
            new_lines = f.readlines()
            queue_file_pos = f.tell()
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                task_queue.append({"type": "event", "event": event})
            except json.JSONDecodeError:
                continue
        if new_lines:
            log(f"扫描到 {len(new_lines)} 个新事件")
    except Exception as e:
        log(f"事件队列扫描失败: {e}")


# ========================================
# 锁管理
# ========================================

def acquire_lock() -> bool:
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        if LOCK_FILE.exists():
            try:
                existing = json.loads(LOCK_FILE.read_text())
                pid = existing.get("pid", 0)
                lock_time = existing.get("time", 0)
                try:
                    os.kill(pid, 0)
                    if time.time() - lock_time < LOCK_TIMEOUT:
                        return False
                except ProcessLookupError:
                    pass
            except (json.JSONDecodeError, KeyError):
                pass
        LOCK_FILE.write_text(json.dumps({"pid": os.getpid(), "time": time.time()}))
        return True
    except Exception as e:
        log(f"锁获取失败: {e}")
        return False


def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def refresh_lock():
    try:
        LOCK_FILE.write_text(json.dumps({"pid": os.getpid(), "time": time.time()}))
    except Exception:
        pass


# ========================================
# 主循环
# ========================================

def repair_session_active() -> bool:
    """检查是否有 repair session 在运行"""
    if REPAIR_LOCK.exists():
        try:
            pid = int(REPAIR_LOCK.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError):
            pass
    return False


def process_queue():
    global _was_yielding
    if not task_queue:
        return
    if mason_session_active():
        if not _was_yielding:
            log("🛑 Mason session 活跃，开始让路")
            _was_yielding = True
        return
    if _was_yielding:
        log("✅ Mason session 结束，恢复工作")
        _was_yielding = False
    if repair_session_active():
        log("🔧 Repair session 运行中，heartbeat 跳过")
        return

    task = task_queue.popleft()
    task_type = task.get("type", "unknown")
    try:
        if task_type == "heartbeat":
            global _last_heavy_heartbeat
            now = time.time()
            is_heavy = (now - _last_heavy_heartbeat >= HEAVY_HEARTBEAT_INTERVAL)
            light_ok = run_light_heartbeat()
            if is_heavy or not light_ok:
                # 异常或每 4 小时强制 → agentic heartbeat
                _last_heavy_heartbeat = now
                run_heartbeat(force_heavy=is_heavy)  # 4h 强制用 Sonnet，轻巡异常用 Haiku
            # 轻巡正常 → 什么都不做，省 token
        elif task_type == "event":
            analyze_event(task["event"])
        elif task_type == "script":
            _execute_script_task(task["task_id"])
        else:
            log(f"未知任务: {task_type}")
    except Exception as e:
        log(f"任务异常: {e}")


def schedule_heartbeat():
    global last_heartbeat
    now = time.time()
    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        if in_time_window():
            task_queue.append({"type": "heartbeat"})
            last_heartbeat = now
            log("📅 Heartbeat 已排入队列")
        else:
            last_heartbeat = now


def _recover_yielding_state():
    """从 gateway.log 最后几行恢复让路状态，避免 systemd 重启后状态丢失"""
    global _was_yielding
    try:
        if not LOG_FILE.exists():
            return
        # 读最后 5KB 够了（约 50 行）
        with open(LOG_FILE, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 5000))
            tail = f.read().decode("utf-8", errors="ignore")
        # 找最后一条让路相关的日志
        last_yield_start = tail.rfind("Mason session 活跃，开始让路")
        last_yield_end = tail.rfind("Mason session 结束，恢复工作")
        if last_yield_start > last_yield_end:
            _was_yielding = True
            log("📋 从日志恢复状态: 上次是让路中")
    except Exception:
        pass  # 恢复失败无所谓，默认 False 安全


def main_loop():
    global running
    _recover_yielding_state()
    log("🚀 Mason Gateway v2 启动 (agentic loop + tool_use + 记忆回写)")
    send_slack("🚀 Mason Gateway v2 已启动", prefix="")

    last_check = time.time()
    schedule_heartbeat()

    while running:
        try:
            now = time.time()
            schedule_heartbeat()
            if now - last_check >= QUEUE_CHECK_INTERVAL:
                scan_event_queue()
                last_check = now
            process_queue()
            refresh_lock()
            time.sleep(30)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"主循环异常: {e}")
            time.sleep(60)


# ========================================
# 入口
# ========================================

def show_status():
    print("Mason Gateway v2 状态:")
    if LOCK_FILE.exists():
        try:
            lock = json.loads(LOCK_FILE.read_text())
            pid = lock.get("pid", "?")
            age = time.time() - lock.get("time", 0)
            alive = False
            try:
                os.kill(pid, 0)
                alive = True
            except (ProcessLookupError, TypeError):
                pass
            print(f"  锁: PID {pid} ({'运行中' if alive else '已死'}, {age:.0f}s)")
        except Exception:
            print("  锁: 损坏")
    else:
        print("  锁: 无（未运行）")

    print(f"  Mason session: {'🟢 活跃' if mason_session_active() else '⚪ 不在'}")
    print(f"  时间窗口: {'✅' if in_time_window() else '❌'} CST 08-22")
    print(f"  工具: {len(TOOLS)} 个 (read_file, write_file, patch_file, run_command, send_slack, list_dir, save_memory)")
    print(f"  Agentic loop: 最大 {MAX_TURNS} 轮")

    if MEMORY_FILE.exists():
        lines = MEMORY_FILE.read_text().strip().split("\n")
        print(f"  记忆: {len(lines)} 条")
    else:
        print("  记忆: 无")

    if QUEUE_FILE.exists():
        lines = QUEUE_FILE.read_text().strip().split("\n")
        print(f"  事件队列: {len(lines)} 条")


def handle_signal(signum, frame):
    global running
    log(f"收到信号 {signum}，关闭...")
    running = False


def main():
    args = sys.argv[1:]

    if "--status" in args:
        show_status()
        return

    if "--once" in args:
        force = "--force" in args
        log("--- 单次运行模式 ---")
        scan_event_queue()
        if force or (not mason_session_active() and in_time_window()):
            run_heartbeat()
        else:
            log("跳过 heartbeat（Mason 活跃或窗口外）")
        return

    if not acquire_lock():
        print("Gateway 已在运行")
        sys.exit(1)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        main_loop()
    finally:
        release_lock()
        log("🛑 Mason Gateway v2 已关闭")
        send_slack("🛑 Gateway 已关闭", prefix="")


if __name__ == "__main__":
    main()
