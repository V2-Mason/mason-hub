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
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
TASKS_FILE = HUB_DIR / "data" / "autonomous_tasks.yaml"
BACKLOG_FILE = HUB_DIR / "tasks" / "backlog.md"
SYSTEM_MAP_FILE = HUB_DIR / "SYSTEM_MAP.md"
BACKLOG_SCANNER = HUB_DIR / "scripts" / "backlog-scanner.py"

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

        line_status = get_line_status(system_map_text, line)
        if line_status != "active":
            if mode == "--list":
                print(f"  ⏸️  [{priority}] {tid}: 能力线 {line} = {line_status}")
            continue

        if mode == "--list":
            print(f"  🟢 [{priority}] {tid} → {agent}: {desc[:60]}")

        static_actionable.append(task)

    # --- 动态任务（backlog-scanner）---
    dynamic_tasks = load_backlog_scanner_tasks()
    if mode == "--list" and dynamic_tasks:
        print(f"\n--- Backlog 动态扫描 ({len(dynamic_tasks)} 个) ---")
        for t in dynamic_tasks:
            print(f"  📋 [{t.get('priority', 'P2')}] {t['id']} → {t.get('agent', '?')}: {t.get('description', '')[:60]}")

    # --- 合并 + 排序（静态优先，同优先级静态在前）---
    all_actionable = []
    for t in static_actionable:
        t["_source"] = "static"
        all_actionable.append(t)
    for t in dynamic_tasks:
        t["_source"] = "dynamic"
        all_actionable.append(t)

    all_actionable.sort(key=lambda t: (
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


if __name__ == "__main__":
    main()
