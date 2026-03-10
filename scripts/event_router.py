#!/usr/bin/env python3
"""
Event Router — 事件驱动的任务触发器

读取 /data/events/queue.jsonl 的新事件，
查路由表决定触发什么动作，检查前置条件后执行。

用法:
  python3 event_router.py --process-new     # 处理 queue.jsonl 中未处理的事件
  python3 event_router.py --process-pending  # 重新检查 pending 事件
  python3 event_router.py --status           # 显示当前状态
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# --- 路径配置 ---
HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
EVENTS_DIR = HUB_DIR / "data" / "events"
QUEUE_FILE = EVENTS_DIR / "queue.jsonl"
PENDING_DIR = EVENTS_DIR / "pending"
ARCHIVE_DIR = EVENTS_DIR / "archive"
REPORTS_DIR = HUB_DIR / "data" / "reports"
SYSTEM_MAP = HUB_DIR / "SYSTEM_MAP.md"
OFFSET_FILE = EVENTS_DIR / ".offset"
LOG_FILE = HUB_DIR / "logs" / "event_router.log"

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

# --- 路由表 ---
# 从 routing_table.yaml 简化为 Python dict，避免额外依赖
ROUTING_TABLE = {
    "data-sync-complete": {
        "preconditions": ["health_check_green"],
        "actions": [
            {"type": "script", "target": "skills/xhs-analyze.sh"},
            {"type": "emit", "event": "data-fresh"},
        ],
    },
    "health-check-all-green": {
        "preconditions": [],
        "actions": [
            {"type": "update_system_map", "line": "数据线", "status": "active"},
            {"type": "check_pending"},
        ],
    },
    "health-check-failed": {
        "preconditions": [],
        "actions": [
            {"type": "update_system_map", "line": "数据线", "status": "blocked"},
            {"type": "slack", "message": "⚠️ data_health_check 出现失败", "level": 2},
        ],
    },
    "scout-complete": {
        "preconditions": ["health_check_green"],
        "actions": [
            {"type": "script", "target": "data/pipelines/scout-normalize.py"},
            {"type": "emit", "event": "intel-fresh"},
        ],
    },
    "intel-fresh": {
        "preconditions": [],
        "actions": [
            {"type": "script", "target": "scripts/optimization-cycle.sh"},
        ],
    },
    "agent-task-complete": {
        "preconditions": [],
        "actions": [
            {"type": "check_downstream"},
            {"type": "slack_if_level", "min_level": 2},
        ],
    },
    "agent-task-failed": {
        "preconditions": [],
        "actions": [
            {"type": "slack", "message": "❌ Agent 任务失败", "level": 2},
        ],
    },
    "blocker-resolved": {
        "preconditions": [],
        "actions": [
            {"type": "check_pending"},
            {"type": "slack", "message": "✅ Blocker 已解除", "level": 2},
        ],
    },
    "content-created": {
        "preconditions": [],
        "actions": [
            {"type": "slack", "message": "📝 新内容就绪，待 EMP_0008 安排发布", "level": 1},
        ],
    },
    "brief-updated": {
        "preconditions": [],
        "actions": [
            {"type": "slack", "message": "📋 品牌 Brief 已更新", "level": 1},
        ],
    },
}


def log(msg: str):
    """写日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def read_offset() -> int:
    """读取上次处理到 queue.jsonl 的第几行"""
    if OFFSET_FILE.exists():
        return int(OFFSET_FILE.read_text().strip())
    return 0


def write_offset(offset: int):
    OFFSET_FILE.write_text(str(offset))


def check_precondition(cond: str) -> bool:
    """检查前置条件是否满足"""
    if cond == "health_check_green":
        # 运行 health check 看是否全绿
        script = HUB_DIR / "data" / "pipelines" / "data_health_check.sh"
        if not script.exists():
            log(f"  前置条件脚本不存在: {script}")
            return False
        try:
            result = subprocess.run(
                ["bash", str(script)],
                capture_output=True, text=True, timeout=60
            )
            # 检查输出是否有 ❌
            return "❌" not in result.stdout
        except (subprocess.TimeoutExpired, Exception) as e:
            log(f"  前置条件检查失败: {e}")
            return False

    log(f"  未知前置条件: {cond}")
    return False


def check_time_window() -> bool:
    """检查是否在允许执行的时间窗口内（CST 08:00-22:00）"""
    from datetime import timedelta
    now_utc = datetime.now(timezone.utc)
    cst = now_utc + timedelta(hours=8)
    return 8 <= cst.hour < 22


def send_slack(message: str):
    """发送 Slack 通知"""
    if not SLACK_WEBHOOK:
        log(f"  Slack webhook 未配置，跳过: {message}")
        return
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", SLACK_WEBHOOK,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"text": message})],
            capture_output=True, timeout=10
        )
    except Exception as e:
        log(f"  Slack 发送失败: {e}")


def run_script(target: str):
    """运行脚本（非阻塞）"""
    script_path = HUB_DIR / target
    if not script_path.exists():
        log(f"  脚本不存在: {script_path}")
        return
    log(f"  启动脚本: {target}")
    subprocess.Popen(
        ["bash", str(script_path)] if str(target).endswith(".sh")
        else ["python3", str(script_path)],
        cwd=str(HUB_DIR),
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
    )


def emit_event(event_type: str, source: str = "event_router"):
    """写入新事件到 queue"""
    event = {
        "event": event_type,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "level": 0,
    }
    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
    log(f"  发射事件: {event_type}")


def save_pending(event: dict, reason: str):
    """前置条件不满足，保存到 pending"""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pending_file = PENDING_DIR / f"{event['event']}_{ts}.json"
    event["_pending_reason"] = reason
    event["_pending_since"] = datetime.now(timezone.utc).isoformat()
    pending_file.write_text(json.dumps(event, indent=2))
    log(f"  保存到 pending: {reason}")


def execute_actions(event: dict, actions: list):
    """执行路由表中的动作"""
    for action in actions:
        action_type = action["type"]

        if action_type == "script":
            run_script(action["target"])

        elif action_type == "emit":
            emit_event(action["event"], source=event.get("source", "unknown"))

        elif action_type == "slack":
            msg = action.get("message", f"事件: {event['event']}")
            event_data = event.get("data", {})
            if event_data:
                msg += f"\n```{json.dumps(event_data, ensure_ascii=False)}```"
            send_slack(msg)

        elif action_type == "slack_if_level":
            min_level = action.get("min_level", 2)
            if event.get("level", 0) >= min_level:
                send_slack(f"[Level {event['level']}] {event.get('event')}: {event.get('data', {}).get('summary', '')}")

        elif action_type == "check_pending":
            process_pending()

        elif action_type == "check_downstream":
            # 检查是否有下游任务因此解锁 — dispatcher 负责
            log(f"  check_downstream: 等待 dispatcher 下次扫描")

        elif action_type == "update_system_map":
            # 标记需要更新，实际更新由 /standup 执行
            log(f"  SYSTEM_MAP 待更新: {action.get('line')} → {action.get('status')}")
            # 写一个标记文件供 /standup 读取
            marker = EVENTS_DIR / "system_map_updates.jsonl"
            with open(marker, "a") as f:
                f.write(json.dumps({
                    "line": action.get("line"),
                    "new_status": action.get("status"),
                    "triggered_by": event["event"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }) + "\n")

        else:
            log(f"  未知动作类型: {action_type}")


def process_event(event: dict):
    """处理单个事件"""
    event_type = event.get("event", "unknown")
    log(f"处理事件: {event_type} (来源: {event.get('source', '?')})")

    route = ROUTING_TABLE.get(event_type)
    if not route:
        log(f"  无匹配路由，跳过")
        return

    # 检查时间窗口
    if not check_time_window():
        save_pending(event, "不在执行时间窗口 (CST 08:00-22:00)")
        return

    # 检查前置条件
    for cond in route.get("preconditions", []):
        if not check_precondition(cond):
            save_pending(event, f"前置条件不满足: {cond}")
            return

    # 执行动作
    execute_actions(event, route["actions"])

    # 归档
    archive_today = ARCHIVE_DIR / datetime.now().strftime("%Y-%m-%d")
    archive_today.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    archive_file = archive_today / f"{event_type}_{ts}.json"
    archive_file.write_text(json.dumps(event, indent=2))


def process_new():
    """处理 queue.jsonl 中的新事件"""
    if not QUEUE_FILE.exists():
        log("queue.jsonl 不存在，无事件")
        return

    offset = read_offset()
    with open(QUEUE_FILE) as f:
        lines = f.readlines()

    new_lines = lines[offset:]
    if not new_lines:
        log("无新事件")
        return

    log(f"发现 {len(new_lines)} 条新事件 (offset={offset})")
    for i, line in enumerate(new_lines):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            process_event(event)
        except json.JSONDecodeError:
            log(f"  JSON 解析失败: {line[:80]}")

    write_offset(len(lines))


def process_pending():
    """重新检查 pending 事件"""
    if not PENDING_DIR.exists():
        return

    pending_files = sorted(PENDING_DIR.glob("*.json"))
    if not pending_files:
        return

    log(f"检查 {len(pending_files)} 条 pending 事件")
    for pf in pending_files:
        try:
            event = json.loads(pf.read_text())
            # 移除 pending 标记
            event.pop("_pending_reason", None)
            event.pop("_pending_since", None)

            event_type = event.get("event", "unknown")
            route = ROUTING_TABLE.get(event_type)
            if not route:
                pf.unlink()
                continue

            # 重新检查前置条件
            all_met = True
            for cond in route.get("preconditions", []):
                if not check_precondition(cond):
                    all_met = False
                    break

            if all_met and check_time_window():
                log(f"  pending 事件条件满足: {event_type}")
                pf.unlink()
                execute_actions(event, route["actions"])
                # 归档
                archive_today = ARCHIVE_DIR / datetime.now().strftime("%Y-%m-%d")
                archive_today.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%H%M%S")
                (archive_today / f"{event_type}_{ts}.json").write_text(
                    json.dumps(event, indent=2)
                )
        except Exception as e:
            log(f"  pending 处理失败: {pf.name}: {e}")


def show_status():
    """显示当前状态"""
    offset = read_offset()
    queue_lines = 0
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE) as f:
            queue_lines = sum(1 for _ in f)

    pending_count = len(list(PENDING_DIR.glob("*.json"))) if PENDING_DIR.exists() else 0

    archive_count = 0
    if ARCHIVE_DIR.exists():
        for d in ARCHIVE_DIR.iterdir():
            if d.is_dir():
                archive_count += len(list(d.glob("*.json")))

    print(f"Event Router 状态:")
    print(f"  队列: {queue_lines} 条 (已处理: {offset}, 待处理: {queue_lines - offset})")
    print(f"  Pending: {pending_count} 条")
    print(f"  已归档: {archive_count} 条")
    print(f"  路由表: {len(ROUTING_TABLE)} 条规则")
    print(f"  时间窗口: {'✅ 在窗口内' if check_time_window() else '❌ 窗口外'}")


if __name__ == "__main__":
    # 确保目录存在
    for d in [EVENTS_DIR, PENDING_DIR, ARCHIVE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) < 2:
        print("用法: event_router.py [--process-new|--process-pending|--status]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "--process-new":
        process_new()
    elif cmd == "--process-pending":
        process_pending()
    elif cmd == "--status":
        show_status()
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
