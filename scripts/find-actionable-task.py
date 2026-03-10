#!/usr/bin/env python3
"""
find-actionable-task.py — 从任务注册表中找到下一个可执行任务

读取 data/autonomous_tasks.yaml + tasks/backlog.md + SYSTEM_MAP.md
输出格式: task_id|agent|line|description（供 dispatcher.sh 消费）

用法:
  python3 scripts/find-actionable-task.py           # 输出下一个可执行任务
  python3 scripts/find-actionable-task.py --list     # 列出所有任务状态
  python3 scripts/find-actionable-task.py --count    # 输出可执行任务数
"""

import os
import re
import sys
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
TASKS_FILE = HUB_DIR / "data" / "autonomous_tasks.yaml"
BACKLOG_FILE = HUB_DIR / "tasks" / "backlog.md"
SYSTEM_MAP_FILE = HUB_DIR / "SYSTEM_MAP.md"

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
            if key in ("agent", "line", "backlog_match", "description", "priority"):
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


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else None

    # 读取数据
    tasks = parse_yaml_tasks(TASKS_FILE)
    if not tasks:
        if mode != "--count":
            print("无任务注册表", file=sys.stderr)
        if mode == "--count":
            print("0")
        sys.exit(1)

    backlog_text = BACKLOG_FILE.read_text() if BACKLOG_FILE.exists() else ""
    system_map_text = SYSTEM_MAP_FILE.read_text() if SYSTEM_MAP_FILE.exists() else ""

    # 按优先级排序
    tasks.sort(key=lambda t: PRIORITY_ORDER.get(t.get("priority", "P2"), 2))

    actionable = []

    for task in tasks:
        tid = task.get("id", "?")
        agent = task.get("agent", "")
        line = task.get("line", "")
        match_str = task.get("backlog_match", tid)
        desc = task.get("description", "")
        priority = task.get("priority", "P2")

        # 检查 1: backlog 中是否已完成
        if is_completed_in_backlog(backlog_text, match_str):
            if mode == "--list":
                print(f"  ✅ [{priority}] {tid}: 已完成")
            continue

        # 检查 2: 能力线状态
        line_status = get_line_status(system_map_text, line)
        if line_status != "active":
            if mode == "--list":
                print(f"  ⏸️  [{priority}] {tid}: 能力线 {line} = {line_status}")
            continue

        # 检查 3: backlog 中是否存在该任务（可选，有些任务可能没在 backlog 里）
        # 不强制要求，注册表本身就是授权

        if mode == "--list":
            print(f"  🟢 [{priority}] {tid} → {agent}: {desc[:60]}")

        actionable.append(task)

    if mode == "--list":
        print(f"\n可执行: {len(actionable)} / 总计: {len(tasks)}")
        return

    if mode == "--count":
        print(len(actionable))
        return

    # 默认模式: 输出第一个可执行任务
    if actionable:
        t = actionable[0]
        # 格式: task_id|agent|line|description
        print(f"{t['id']}|{t['agent']}|{t.get('line', '')}|{t.get('description', '')}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
