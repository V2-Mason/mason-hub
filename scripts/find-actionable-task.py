#!/usr/bin/env python3
"""
find-actionable-task.py — 从任务注册表中找到下一个可执行任务

读取 data/autonomous_tasks.yaml + backlog-scanner 动态任务 + tasks/backlog.md + SYSTEM_MAP.md
输出格式: task_id|agent|line|description（供 dispatcher.sh 消费）

用法:
  python3 scripts/find-actionable-task.py           # 输出下一个可执行任务
  python3 scripts/find-actionable-task.py --list     # 列出所有任务状态
  python3 scripts/find-actionable-task.py --count    # 输出可执行任务数
"""

import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
TASKS_FILE = HUB_DIR / "data" / "autonomous_tasks.yaml"
BACKLOG_FILE = HUB_DIR / "tasks" / "backlog.md"
SYSTEM_MAP_FILE = HUB_DIR / "SYSTEM_MAP.md"
BACKLOG_SCANNER = HUB_DIR / "scripts" / "backlog-scanner.py"
AUDIT_LOG = HUB_DIR / "logs" / "audit.jsonl"
TASK_LOG_DIR = HUB_DIR / "logs" / "tasks"

# 优先级权重
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def parse_yaml_tasks(filepath: Path) -> list[dict]:
    """简单 YAML 解析器（不依赖 PyYAML）"""
    tasks = []
    current = {}

    if not filepath.exists():
        return tasks

    for line in filepath.read_text().splitlines():
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith("#"):
            continue

        # 新任务开始
        if stripped.startswith("- id:"):
            if current:
                tasks.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            continue

        # 任务字段
        if current and ":" in stripped and not stripped.startswith("-"):
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in ("agent", "line", "backlog_match", "description", "priority",
                       "expected_output", "verify_command", "output_path",
                       "max_duration", "depends_on", "context_files", "task_type",
                       "tier", "tier_script", "tier_escalate_on_fail"):
                current[key] = val

    if current:
        tasks.append(current)

    return tasks


def get_line_status(system_map_text: str, line_name: str) -> str:
    """从 SYSTEM_MAP 提取能力线状态"""
    # 找到对应的能力线区块，提取状态字段
    pattern = rf"###.*{re.escape(line_name)}.*\n```\n状态:\s*(\w+)"
    match = re.search(pattern, system_map_text)
    if match:
        return match.group(1)
    return "unknown"


def is_completed_in_backlog(backlog_text: str, match_str: str) -> bool:
    """检查 backlog 中该任务是否已标记完成"""
    # 匹配 [x] 行中包含关键词
    for line in backlog_text.splitlines():
        if "[x]" in line and match_str in line:
            return True
    return False


def is_incomplete_in_backlog(backlog_text: str, match_str: str) -> bool:
    """检查 backlog 中该任务是否存在且未完成"""
    for line in backlog_text.splitlines():
        if "[ ]" in line and match_str in line:
            return True
    return False


def get_today_task_status() -> dict[str, str]:
    """从 audit.jsonl 读取今天的 task 状态，用于去重和失败限流。

    返回 {task_desc_prefix: status}，status 为 completed 或 failed。
    completed 的任务不再派发；failed 的任务当天最多重试 2 次。
    """
    task_status: dict[str, list[str]] = {}  # desc -> [status1, status2, ...]
    today_str = str(date.today())
    if not AUDIT_LOG.exists():
        return {}
    try:
        for line in AUDIT_LOG.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("timestamp", "")
                if today_str in ts:
                    task_desc = entry.get("task", "")
                    status = entry.get("status", "")
                    if task_desc and status:
                        task_status.setdefault(task_desc, []).append(status)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    # 合并：completed → 不再派；failed ≥2 次 → 不再派
    result = {}
    for desc, statuses in task_status.items():
        if "completed" in statuses:
            result[desc] = "completed"
        elif statuses.count("failed") >= 2:
            result[desc] = "failed_max"
        # failed 1 次 → 不加入 result，允许重试
    return result


def get_yesterday_failed_max() -> set[str]:
    """从 audit.jsonl 读取昨天 failed_max 的任务描述前缀。

    这些任务今天应该降优先级（排到最后），让其他任务先跑。
    同时记录到 data/failed_tasks_for_review.jsonl 供 Mason + Meta Manager 决策。
    """
    yesterday_str = str(date.today() - timedelta(days=1))
    failed_descs: set[str] = set()
    task_status: dict[str, list[str]] = {}

    if not AUDIT_LOG.exists():
        return failed_descs

    try:
        for line in AUDIT_LOG.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("timestamp", "")
                if yesterday_str in ts:
                    task_desc = entry.get("task", "")
                    status = entry.get("status", "")
                    if task_desc and status:
                        task_status.setdefault(task_desc, []).append(status)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    for desc, statuses in task_status.items():
        if "completed" not in statuses and statuses.count("failed") >= 2:
            failed_descs.add(desc)

    # 记录到待决策文件
    if failed_descs:
        review_file = HUB_DIR / "data" / "failed_tasks_for_review.jsonl"
        today_str = str(date.today())
        # 检查今天是否已记录过，避免重复
        existing = set()
        if review_file.exists():
            for line in review_file.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get("date") == today_str:
                            existing.add(entry.get("task_desc", ""))
                    except json.JSONDecodeError:
                        pass
        with open(review_file, "a") as f:
            for desc in failed_descs:
                if desc not in existing:
                    f.write(json.dumps({
                        "date": today_str,
                        "failed_date": yesterday_str,
                        "task_desc": desc,
                        "status": "pending_review",
                        "note": "昨日2轮失败，已降优先级，待 Mason + Meta Manager 决策"
                    }, ensure_ascii=False) + "\n")

    return failed_descs


def is_task_running(task_id: str) -> bool:
    """检查任务是否正在运行（通过 summary.json 状态判断）"""
    # 检查今天的 report 日志是否有对应进程还活着
    reports_dir = HUB_DIR / "data" / "reports" / str(date.today())
    if reports_dir.exists():
        for logfile in reports_dir.glob(f"*_{task_id}.log"):
            # 文件存在且最近 30 分钟内有写入 = 可能还在运行
            import time
            if time.time() - logfile.stat().st_mtime < 1800:
                return True
    return False


def load_backlog_scanner_tasks() -> list[dict]:
    """从 backlog-scanner.py 获取动态任务"""
    if not BACKLOG_SCANNER.exists():
        return []
    try:
        result = subprocess.run(
            ["python3", str(BACKLOG_SCANNER)],
            capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return []
        tasks = json.loads(result.stdout)
        return tasks if isinstance(tasks, list) else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return []


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else None

    # 读取静态注册表
    static_tasks = parse_yaml_tasks(TASKS_FILE)

    backlog_text = BACKLOG_FILE.read_text() if BACKLOG_FILE.exists() else ""
    system_map_text = SYSTEM_MAP_FILE.read_text() if SYSTEM_MAP_FILE.exists() else ""
    today_task_status = get_today_task_status()
    yesterday_failed = get_yesterday_failed_max()

    # --- 静态任务过滤 ---
    static_actionable = []
    for task in static_tasks:
        tid = task.get("id", "?")
        agent = task.get("agent", "")
        line = task.get("line", "")
        match_str = task.get("backlog_match", tid)
        desc = task.get("description", "")
        priority = task.get("priority", "P2")

        if is_completed_in_backlog(backlog_text, match_str):
            if mode == "--list":
                print(f"  ✅ [{priority}] {tid}: 已完成")
            continue

        # 检查今天是否已成功执行过或失败超限（audit.jsonl 去重）
        skip_audit = False
        for tc, ts in today_task_status.items():
            if desc[:30] in tc:
                if ts == "completed":
                    if mode == "--list":
                        print(f"  ✅ [{priority}] {tid}: 今日已完成")
                    skip_audit = True
                    break
                elif ts == "failed_max":
                    if mode == "--list":
                        print(f"  ❌ [{priority}] {tid}: 今日失败 ≥2 次，停止重试")
                    skip_audit = True
                    break
        if skip_audit:
            continue

        # 检查是否正在运行
        if is_task_running(tid):
            if mode == "--list":
                print(f"  🔄 [{priority}] {tid}: 正在运行")
            continue

        # 检查依赖是否满足
        depends = task.get("depends_on", "")
        if depends:
            dep_ids = [d.strip() for d in depends.split(",") if d.strip()]
            deps_met = all(
                any(dep_id in tc and ts == "completed" for tc, ts in today_task_status.items())
                or is_completed_in_backlog(backlog_text, dep_id)
                for dep_id in dep_ids
            )
            if not deps_met:
                if mode == "--list":
                    print(f"  ⏳ [{priority}] {tid}: 依赖未满足 ({depends})")
                continue

        line_status = get_line_status(system_map_text, line)
        if line_status != "active":
            if mode == "--list":
                print(f"  ⏸️  [{priority}] {tid}: 能力线 {line} = {line_status}")
            continue

        is_demoted = any(desc[:30] in fd for fd in yesterday_failed)
        if mode == "--list":
            demote_tag = " ⬇️昨日失败降级" if is_demoted else ""
            print(f"  🟢 [{priority}] {tid} → {agent}: {desc[:60]}{demote_tag}")

        static_actionable.append(task)

    # --- 动态任务（backlog-scanner）---
    dynamic_tasks = load_backlog_scanner_tasks()
    if mode == "--list" and dynamic_tasks:
        print(f"\n--- Backlog 动态扫描 ({len(dynamic_tasks)} 个) ---")
        for t in dynamic_tasks:
            print(f"  📋 [{t.get('priority', 'P2')}] {t['id']} → {t.get('agent', '?')}: {t.get('description', '')[:60]}")

    # --- 合并 + 排序（昨日失败降级，优先做别的任务）---
    all_actionable = []
    for t in static_actionable:
        t["_source"] = "static"
        # 标记昨天失败的任务
        desc = t.get("description", "")
        t["_yesterday_failed"] = any(desc[:30] in fd for fd in yesterday_failed)
        all_actionable.append(t)
    for t in dynamic_tasks:
        t["_source"] = "dynamic"
        t["_yesterday_failed"] = False
        all_actionable.append(t)

    all_actionable.sort(key=lambda t: (
        1 if t.get("_yesterday_failed") else 0,  # 昨日失败的排最后
        PRIORITY_ORDER.get(t.get("priority", "P2"), 2),
        0 if t["_source"] == "static" else 1,
    ))

    if mode == "--list":
        static_count = len(static_actionable)
        dynamic_count = len(dynamic_tasks)
        total = static_count + dynamic_count
        print(f"\n总可执行: {total} (静态 {static_count} + 动态 {dynamic_count}) / 静态注册 {len(static_tasks)}")
        return

    if mode == "--count":
        print(len(all_actionable))
        return

    if mode == "--batch":
        # 批量模式: 按 lane 分组，每 lane 取第一个，输出 JSON
        batch_output = get_batch_by_lane(all_actionable)
        json.dump(batch_output, sys.stdout, ensure_ascii=False, indent=2)
        return

    # 默认模式: 输出第一个可执行任务
    if all_actionable:
        t = all_actionable[0]
        # 格式: task_id|agent|line|description
        print(f"{t['id']}|{t['agent']}|{t.get('line', '')}|{t.get('description', '')}")

        # 如果是动态任务，增加每日计数
        if t.get("_source") == "dynamic" or t.get("source") == "backlog-scanner":
            try:
                subprocess.run(
                    ["python3", str(BACKLOG_SCANNER), "--increment"],
                    timeout=5, capture_output=True)
            except Exception:
                pass
    else:
        sys.exit(1)


# Agent ID → Lane 映射（与 lane-lock.sh 保持一致）
AGENT_LANE = {
    "EMP_0001": "ecommerce", "EMP_0003": "ecommerce", "EMP_0005": "ecommerce",
    "EMP_0013": "ecommerce", "EMP_0015": "ecommerce",
    "EMP_0008": "socialmesh", "EMP_0009": "socialmesh", "EMP_0010": "socialmesh",
    "EMP_0002": "platform", "EMP_0004": "platform", "EMP_0014": "platform",
}


def get_agent_lane(agent_path: str) -> str:
    """从 agent 配置路径推断 lane"""
    # v2 目录格式: agents/EMP_0002/ → EMP_0002
    # v1 格式: agents/EMP_0002/config.md → EMP_0002
    # 旧格式: agents/EMP_0002.md → EMP_0002
    agent_path = agent_path.rstrip("/")
    basename = os.path.basename(agent_path)
    if basename == "config.md" or basename == "identity.md":
        agent_id = os.path.basename(os.path.dirname(agent_path))
    elif basename.startswith("EMP_") and os.path.isdir(agent_path):
        agent_id = basename
    else:
        agent_id = basename.replace(".md", "")
    return AGENT_LANE.get(agent_id, "independent")


def get_batch_by_lane(actionable: list[dict]) -> list[dict]:
    """按 lane+agent 分组，同 lane 不同 agent 可并行，同 agent 只取 1 个。

    原逻辑：每 lane 只取 1 个任务 → 5 个 platform 任务只出 1 个。
    新逻辑：同 lane 同 agent 互斥（真正的资源竞争），不同 agent 可并行。
    例如 EMP_0002(platform) 和 EMP_0004(platform) 做不同的事，不应互斥。
    """
    seen_lane_agent = set()  # (lane, agent) 对去重
    batch = []

    for t in actionable:
        lane = get_agent_lane(t.get("agent", ""))
        agent = t.get("agent", "")
        key = (lane, agent)
        if key in seen_lane_agent and lane != "independent":
            continue  # 同 lane 同 agent 只取第一个
        seen_lane_agent.add(key)
        batch.append({
            "id": t.get("id", ""),
            "agent": t.get("agent", ""),
            "lane": lane,
            "line": t.get("line", ""),
            "description": t.get("description", ""),
            "priority": t.get("priority", "P2"),
            "source": t.get("_source", t.get("source", "static")),
            "expected_output": t.get("expected_output", ""),
            "verify_command": t.get("verify_command", ""),
            "output_path": t.get("output_path", ""),
            "max_duration": t.get("max_duration", "0"),
            "context_files": t.get("context_files", ""),
            "task_type": t.get("task_type", "execute"),
            "tier": t.get("tier", ""),
            "tier_script": t.get("tier_script", ""),
            "tier_escalate_on_fail": t.get("tier_escalate_on_fail", ""),
        })

    return batch


if __name__ == "__main__":
    main()
