#!/usr/bin/env python3
"""
Heartbeat — 系统监督脚本

值班员工：定时读取系统状态 → 调 Anthropic API 判断 → Slack 通知 Mason。
实际执行留给 Mason 的 Max Plan session，这里只做监督和判断。

用法:
  python3 heartbeat.py              # 运行一次监督检查
  python3 heartbeat.py --dry-run    # 只打印 prompt，不调 API
  python3 heartbeat.py --verbose    # 显示完整推理过程

架构:
  MASONHUB.md = 灵魂文件（权限 + 检查清单 + 关键状态）
  SYSTEM_MAP.md = 完整状态（按需读取，heartbeat 只读精简版）

成本:
  每次调用 ~1500 input + ~300 output token ≈ $0.005
  每天 14 次（CST 08-22，每小时）≈ $0.07/天 ≈ $2/月

Cron:
  0 * * * * cd ~/mason-hub && .venv/bin/python3 scripts/heartbeat.py >> logs/heartbeat.log 2>&1
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- 配置 ---

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
MODEL = os.environ.get("HEARTBEAT_MODEL", "claude-sonnet-4-20250514")
MAX_OUTPUT_TOKENS = 800
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
LOG_FILE = HUB_DIR / "logs" / "heartbeat.log"
CST = timezone(timedelta(hours=8))


def in_time_window() -> bool:
    """CST 08:00-22:00 窗口检查"""
    now_cst = datetime.now(CST)
    return 8 <= now_cst.hour < 22


def read_file(path: Path, max_lines: int = 0) -> str:
    """安全读取文件，可限制行数"""
    try:
        text = path.read_text()
        if max_lines > 0:
            lines = text.strip().split("\n")
            return "\n".join(lines[:max_lines])
        return text
    except FileNotFoundError:
        return f"[文件不存在: {path}]"


def collect_context() -> dict:
    """收集系统上下文，控制 token 量"""
    ctx = {}

    # 1. MASONHUB.md — 灵魂文件（权限 + 检查清单 + 关键状态）
    ctx["masonhub"] = read_file(HUB_DIR / "MASONHUB.md")

    # 2. 最近事件（queue.jsonl 最后 10 条）
    queue_file = HUB_DIR / "data" / "events" / "queue.jsonl"
    if queue_file.exists():
        lines = queue_file.read_text().strip().split("\n")
        recent = lines[-10:] if len(lines) > 10 else lines
        ctx["recent_events"] = "\n".join(recent)
    else:
        ctx["recent_events"] = "[无事件记录]"

    # 3. 最近 git log（5 条，~200 token）
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, cwd=HUB_DIR, timeout=5
        )
        ctx["recent_commits"] = result.stdout.strip()
    except Exception:
        ctx["recent_commits"] = "[git log 失败]"

    # 4. 系统健康快照
    health = []
    try:
        result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
        health.append(f"uptime: {result.stdout.strip()}")
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["free", "-h"], capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")[:2]
        health.append("\n".join(lines))
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["df", "-h", "/"], capture_output=True, text=True, timeout=5
        )
        health.append(result.stdout.strip().split("\n")[-1])
    except Exception:
        pass
    ctx["system_health"] = "\n".join(health) if health else "[健康检查失败]"

    # 5. dispatcher 最近日志（最后 5 行）
    dispatcher_log = HUB_DIR / "logs" / "dispatcher.log"
    if dispatcher_log.exists():
        ctx["dispatcher_log"] = read_file(dispatcher_log, max_lines=5)
    else:
        ctx["dispatcher_log"] = "[dispatcher 尚未运行]"

    # 6. 阿里云连通性
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "root@106.14.44.68", "echo ok"],
            capture_output=True, text=True, timeout=8
        )
        ctx["aliyun"] = "✅ 连通" if "ok" in result.stdout else "❌ 不通"
    except Exception:
        ctx["aliyun"] = "❌ 超时"

    return ctx


def build_prompt(ctx: dict) -> str:
    """构建监督 prompt"""
    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")

    prompt = f"""当前时间: {now_cst}

{ctx['masonhub']}

--- 实时数据 ---

最近事件:
{ctx['recent_events']}

最近 commits:
{ctx['recent_commits']}

系统健康:
{ctx['system_health']}
阿里云: {ctx['aliyun']}

Dispatcher 日志:
{ctx['dispatcher_log']}

---

按照 MASONHUB 检查清单逐项检查。
如果一切正常，只回复"✅ 系统正常"。
如果有异常，格式：[级别] 一句话总结 + 详情 + 建议行动。"""

    return prompt


def call_api(prompt: str) -> str:
    """调用 Anthropic API"""
    import anthropic

    client = anthropic.Anthropic()  # 自动读 ANTHROPIC_API_KEY
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def send_slack(message: str):
    """发送 Slack 通知"""
    if not SLACK_WEBHOOK:
        return
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", SLACK_WEBHOOK,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"text": f"🫀 Heartbeat\n{message}"})],
            capture_output=True, timeout=10,
        )
    except Exception as e:
        print(f"Slack 发送失败: {e}")


def log(message: str):
    """追加日志"""
    timestamp = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S CST")
    entry = f"[{timestamp}] {message}"
    print(entry)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    verbose = "--verbose" in args
    force = "--force" in args

    # 时间窗口检查
    if not in_time_window() and not force:
        log("⏰ 窗口外（CST 08-22），跳过")
        return

    log("--- heartbeat 开始 ---")

    # 收集上下文
    ctx = collect_context()
    prompt = build_prompt(ctx)

    if dry_run:
        print("=== PROMPT ===")
        print(prompt)
        print(f"\n=== 预估 token: ~{len(prompt) // 4} input ===")
        return

    if verbose:
        print(f"上下文大小: ~{len(prompt) // 4} token")

    # 调 API
    try:
        result = call_api(prompt)
    except Exception as e:
        error_msg = f"❌ API 调用失败: {e}"
        log(error_msg)
        send_slack(error_msg)
        return

    if verbose:
        print(f"=== API 响应 ===\n{result}")

    log(f"响应: {result[:100]}...")

    # 判断是否需要通知
    is_normal = result.strip().startswith("✅") and len(result.strip()) < 50
    if not is_normal:
        send_slack(result)
        log("📨 已发 Slack")
    else:
        log("✅ 系统正常，不通知")

    log("--- heartbeat 结束 ---")


if __name__ == "__main__":
    main()
