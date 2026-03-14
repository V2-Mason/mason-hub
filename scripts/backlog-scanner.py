#!/usr/bin/env python3
"""
backlog-scanner.py — 从 backlog.md 扫描可自主执行的任务

读取 backlog.md + SYSTEM_MAP.md + MASON_AUTHORITY.md
过滤出：L2 范围内、无外部依赖、能力线 active 的未完成项
输出格式：与 autonomous_tasks.yaml 兼容的结构化 JSON

用法:
  python3 scripts/backlog-scanner.py              # 输出可执行任务 JSON
  python3 scripts/backlog-scanner.py --list        # 人类可读列表
  python3 scripts/backlog-scanner.py --count       # 可执行任务数
"""

import json
import os
import re
import sys
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
BACKLOG_FILE = HUB_DIR / "tasks" / "backlog.md"
SYSTEM_MAP_FILE = HUB_DIR / "SYSTEM_MAP.md"
DAILY_COUNTER_FILE = HUB_DIR / "data" / ".backlog_dispatch_today"

# 每天最大自动派发任务数（8 小时工作量，每任务约 1-2 小时）
MAX_DAILY_TASKS = 6

# 外部依赖关键词 — 含这些词的任务不自动执行
EXTERNAL_DEPENDENCY_KEYWORDS = [
    "Mason 手动", "Mason手动", "待 Mason", "待Mason",
    "等 Mason", "等Mason", "Mason 确认", "Mason确认",
    "Mason 提供", "Mason提供", "Mason 审批", "Mason审批",
    "外部依赖", "等清谭", "等清潭", "等平台",
    "需 Mason", "需Mason", "Mason 协调", "Mason协调",
    "Mason 决定", "Mason决定", "Mason 选择", "Mason选择",
    "手动触发", "Mason 操作", "Mason操作",
    "API key", "API Key", "api key", "API_KEY", "api_key",
    "需要.*营业执照", "需要.*手机号",
    "等.*cookie", "等.*授权书",
    "触发条件.*>",
    # 中文等待/依赖模式
    "等.*就绪", "等.*到期", "等.*开放",
    "待.*配置", "待.*部署后",
    "需.*手动", "需.*注册",
    "观察中", "等销售数据积累",
    # 英文模式
    "waiting for", "depends on", "blocked by",
]

# Section 级别的阻塞标记 — 整个 section 下的任务都不执行
BLOCKED_SECTION_KEYWORDS = [
    "Mason 手动验证",
    "Mason 确认分阶段",
    "手动验证通过后",
    "采集稳定后",
    "诊断稳定后",
    "触发条件",
    "月均订单 > 100",
    "开店日激活",
    "Layer 2 稳定后",
    "Layer 3",
]

# 红线关键词 — 含这些词的任务绝对不自动执行
REDLINE_KEYWORDS = [
    "品牌定位", "定价策略", "推广预算",
    "账号操作", "删帖", "小红书.*发布",
    "密钥创建", "密码修改", "credentials.*明文",
    "MASON_AUTHORITY",
    "新建.*Agent", "删除.*Agent",
]

# Agent 匹配：从 backlog 行中提取 (EMP_XXXX) 或 （EMP_XXXX） 标注
AGENT_PATTERN = re.compile(r'[（(]EMP_(\d{4})[）)]')
# 也匹配内联写法如 "EMP_0014 建管道"
AGENT_INLINE_PATTERN = re.compile(r'EMP_(\d{4})')

def _get_agent_config(agent_num: str) -> str:
    """v2 优先 identity.md，fallback config.md"""
    agent_id = f"EMP_{agent_num}"
    identity = f"agents/{agent_id}/identity.md"
    config = f"agents/{agent_id}/config.md"
    hub = os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub"))
    if os.path.exists(os.path.join(hub, identity)):
        return identity
    return config  # fallback

# Agent ID → 配置文件路径（动态检测 v2/v1）
AGENT_CONFIG = {
    num: _get_agent_config(num)
    for num in ["0000", "0001", "0002", "0003", "0004", "0005",
                "0006", "0008", "0009", "0010", "0013", "0014", "0015"]
}

# 能力线关键词映射（backlog section → SYSTEM_MAP 能力线名称）
LINE_MAPPING = {
    "自治闭环": "自治线",
    "Push→Pull": "自治线",
    "Agent 基础设施": "自治线",
    "开发流程强化": "自治线",
    "Scout": "自治线",
    "数据中台": "数据线",
    "MediaCrawler": "数据线",
    "分析管道": "数据线",
    "EMP_0015": "数据线",
    "SocialMesh": "内容生产线",
    "TTS": "内容生产线",
    "小红书对接": "商业运营线",
    "店铺运营": "商业运营线",
    "EMP_0013": "商业运营线",
    "ComfyUI": "内容生产线",
    "Radar": "数据线",
    "china-hub": "数据线",
    "看板": "数据线",
    "Webhook": "商业运营线",
    "Agent 角色": "自治线",
    "agent.log": "审计",
    "system_feedback": "数据线",
    "记忆系统": "自治线",
    "四层声明": "自治线",
}


def get_line_status(system_map_text: str, line_name: str) -> str:
    """从 SYSTEM_MAP 提取能力线状态"""
    pattern = rf"###.*{re.escape(line_name)}.*\n```\n状态:\s*(\w+)"
    match = re.search(pattern, system_map_text)
    return match.group(1) if match else "unknown"


def get_daily_count() -> int:
    """获取今天已派发的任务数"""
    if not DAILY_COUNTER_FILE.exists():
        return 0
    try:
        data = json.loads(DAILY_COUNTER_FILE.read_text())
        from datetime import date
        if data.get("date") == str(date.today()):
            return data.get("count", 0)
    except (json.JSONDecodeError, ValueError):
        pass
    return 0


def increment_daily_count():
    """增加今天的派发计数"""
    from datetime import date
    today = str(date.today())
    count = get_daily_count() + 1
    DAILY_COUNTER_FILE.write_text(json.dumps({"date": today, "count": count}))


def has_external_dependency(line: str) -> bool:
    """检查任务行是否包含外部依赖关键词"""
    for kw in EXTERNAL_DEPENDENCY_KEYWORDS:
        if re.search(kw, line):
            return True
    return False


def hits_redline(line: str) -> bool:
    """检查任务行是否触碰红线"""
    for kw in REDLINE_KEYWORDS:
        if re.search(kw, line):
            return True
    return False


def extract_agent(line: str) -> str | None:
    """从任务行提取 agent ID"""
    # 优先匹配括号标注 (EMP_XXXX) 或 （EMP_XXXX）
    match = AGENT_PATTERN.search(line)
    if match:
        return match.group(1)
    # 其次匹配内联写法 EMP_XXXX
    match = AGENT_INLINE_PATTERN.search(line)
    if match:
        return match.group(1)
    return None


def infer_line(line: str, section_context: str) -> str:
    """推断任务所属能力线"""
    combined = line + " " + section_context
    for keyword, line_name in LINE_MAPPING.items():
        if keyword in combined:
            return line_name
    return "unknown"


def is_section_blocked(section: str) -> bool:
    """检查当前 section 是否整体被阻塞"""
    for kw in BLOCKED_SECTION_KEYWORDS:
        if kw in section:
            return True
    return False


def parse_backlog(backlog_text: str) -> list[dict]:
    """解析 backlog 中所有未完成的 [ ] 任务"""
    tasks = []
    current_section = ""
    # 父级 section（**...**:），子标题切换时保留
    parent_section = ""
    # 累积 section 上下文（包括 > 引用块中的条件信息）
    section_context = ""
    lines = backlog_text.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 跟踪当前 section（用于推断能力线）
        if stripped.startswith("**") and stripped.endswith("**:"):
            current_section = stripped
            parent_section = stripped
            section_context = stripped
        elif stripped.startswith("P") and " — " in stripped[:6] and stripped[:2] in ("P0", "P1", "P2"):
            current_section = stripped
            # 保留父级上下文，子标题追加而非替换
            section_context = parent_section + " " + stripped
        elif re.match(r'^Phase \d', stripped):
            # "Phase N — ..." 也是 section 切换，保留父级上下文
            current_section = stripped
            section_context = parent_section + " " + stripped
        elif stripped.startswith(">"):
            section_context += " " + stripped

        # 跳过已完成和非任务行
        if "[ ]" not in stripped:
            continue

        # 提取任务描述（去掉 "- [ ] " 前缀）
        desc_match = re.match(r'[-*]\s*\[ \]\s*(.*)', stripped)
        if not desc_match:
            continue
        desc = desc_match.group(1)

        # 提取优先级（从 section context）
        priority = "P2"  # 默认
        if "P0" in current_section:
            priority = "P0"
        elif "P1" in current_section:
            priority = "P1"
        elif "P2" in current_section:
            priority = "P2"

        # 提取 agent
        agent_id = extract_agent(stripped)
        agent_path = AGENT_CONFIG.get(agent_id, "") if agent_id else ""

        # 推断能力线（用 section_context 包含父级关键词）
        cap_line = infer_line(stripped, section_context)

        # 生成任务 ID（从描述中取关键词）
        task_id = f"backlog-{i}"

        tasks.append({
            "id": task_id,
            "line_num": i + 1,
            "agent": agent_path,
            "agent_id": agent_id,
            "line": cap_line,
            "description": desc.strip(),
            "priority": priority,
            "section": current_section[:80],
            "section_context": section_context[:200],
            "raw": stripped,
        })

    return tasks


def filter_actionable(tasks: list[dict], system_map_text: str) -> tuple[list[dict], list[dict]]:
    """过滤出可自主执行的任务，返回 (actionable, skipped)"""
    actionable = []
    skipped = []

    for task in tasks:
        skip_reason = None

        # 过滤 1: 红线检查
        if hits_redline(task["raw"]):
            skip_reason = "🔴 触碰红线"

        # 过滤 2: Section 级别阻塞（只检查当前 section 标题，不含父级）
        elif is_section_blocked(task.get("section", "")):
            skip_reason = "⏳ Section 阻塞"

        # 过滤 3: 外部依赖
        elif has_external_dependency(task["raw"]):
            skip_reason = "⏳ 外部依赖"

        # 过滤 4: 没有 agent 标注
        elif not task["agent"]:
            skip_reason = "❓ 无 agent 标注"

        # 过滤 5: 能力线状态
        elif task["line"] == "unknown":
            skip_reason = "❓ 能力线未知"
        else:
            line_status = get_line_status(system_map_text, task["line"])
            if line_status != "active":
                skip_reason = f"⏸️ 能力线 {task['line']}={line_status}"

        if skip_reason:
            task["skip_reason"] = skip_reason
            skipped.append(task)
        else:
            actionable.append(task)

    return actionable, skipped


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else None

    if not BACKLOG_FILE.exists():
        print("backlog.md 不存在", file=sys.stderr)
        if mode == "--count":
            print("0")
        sys.exit(1)

    backlog_text = BACKLOG_FILE.read_text()
    system_map_text = SYSTEM_MAP_FILE.read_text() if SYSTEM_MAP_FILE.exists() else ""

    # 解析所有未完成任务
    all_tasks = parse_backlog(backlog_text)

    # 过滤可执行任务
    actionable, skipped = filter_actionable(all_tasks, system_map_text)

    # 按优先级排序
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    actionable.sort(key=lambda t: priority_order.get(t["priority"], 2))

    # 检查每日上限
    daily_count = get_daily_count()
    remaining = max(0, MAX_DAILY_TASKS - daily_count)

    if mode == "--list":
        print(f"Backlog Scanner — {len(all_tasks)} 个未完成任务\n")
        print(f"可执行 ({len(actionable)} 个, 今日剩余配额 {remaining}/{MAX_DAILY_TASKS}):")
        for t in actionable:
            agent_label = f"EMP_{t['agent_id']}" if t['agent_id'] else "?"
            print(f"  🟢 [{t['priority']}] L{t['line_num']} {agent_label}: {t['description'][:70]}")
        print(f"\n跳过 ({len(skipped)} 个):")
        for t in skipped:
            print(f"  {t['skip_reason']}: {t['description'][:60]}")
        return

    if mode == "--count":
        print(min(len(actionable), remaining))
        return

    if mode == "--increment":
        increment_daily_count()
        return

    # 默认模式: 输出 JSON（供 find-actionable-task.py 合并）
    output = []
    for t in actionable[:remaining]:
        output.append({
            "id": t["id"],
            "agent": t["agent"],
            "line": t["line"],
            "description": t["description"],
            "priority": t["priority"],
            "source": "backlog-scanner",
        })

    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
