#!/usr/bin/env python3
"""extract-lessons.py — 从 Task 结果自动提取经验

五维 Gap: Task Engine → Memory 桥梁
输入：task YAML 文件路径
输出：JSON 格式的 Memory Entry 列表 + 自动写入对应 Pipe

用法：
  python3 skills/learning/extract-lessons.py data/tasks/task_EMP_0002_1773xxx.yaml
  python3 skills/learning/extract-lessons.py data/tasks/task_EMP_0002_1773xxx.yaml --dry-run
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))


def load_task(task_path: str) -> dict:
    with open(task_path) as f:
        return yaml.safe_load(f)


def extract_lessons(task: dict) -> list[dict]:
    """从 task 数据中提取结构化经验"""
    lessons = []
    task_id = task.get("id", "unknown")
    agent = task.get("agent", "unknown")
    account = task.get("account", "")
    status = task.get("status", "")
    desc = task.get("description", "")
    result = task.get("result", "")
    error = task.get("error_summary", "")
    criteria = task.get("acceptance_criteria", "")
    rounds = task.get("rounds", 1)

    # 确定 pipe
    if agent and account:
        pipe = 3
    elif agent:
        pipe = 1
    elif account:
        pipe = 2
    else:
        pipe = 4

    if status == "done":
        lesson_text = f"[{datetime.now().strftime('%Y-%m-%d')}] {task_id}: {desc[:80]}"
        if rounds and rounds > 1:
            lesson_text += f" — 经过 {rounds} 轮验证"
        if criteria:
            lesson_text += f" (验收标准: {criteria[:60]})"

        lessons.append({
            "pipe": pipe,
            "agent_scope": agent if pipe in (1, 3) else None,
            "account_scope": account if pipe in (2, 3) else None,
            "source_task": task_id,
            "content": lesson_text,
            "type": "success",
        })

    elif status == "failed":
        lesson_text = f"[{datetime.now().strftime('%Y-%m-%d')}] [FAILED] {task_id}: {desc[:60]}"
        if error:
            lesson_text += f" — 根因: {error[:80]}"
        if rounds:
            lesson_text += f" ({rounds} 轮失败)"

        lessons.append({
            "pipe": pipe,
            "agent_scope": agent if pipe in (1, 3) else None,
            "account_scope": account if pipe in (2, 3) else None,
            "source_task": task_id,
            "content": lesson_text,
            "type": "failure",
        })

        # 失败任务额外提取到 Pipe 1（agent 职能经验）如果有 account
        if account and pipe == 3:
            lessons.append({
                "pipe": 1,
                "agent_scope": agent,
                "account_scope": None,
                "source_task": task_id,
                "content": f"[{datetime.now().strftime('%Y-%m-%d')}] [FAILED] 任务类型: {desc[:40]} — {error[:60] if error else '原因未知'}",
                "type": "failure_generic",
            })

    return lessons


def route_lesson(lesson: dict, dry_run: bool = False) -> str:
    """将 lesson 路由到正确的文件"""
    pipe = lesson["pipe"]
    agent = lesson.get("agent_scope", "")
    account = lesson.get("account_scope", "")

    if pipe == 1 and agent:
        target = HUB_DIR / "agents" / agent / "memory" / "long_term.md"
    elif pipe == 2 and account:
        target = HUB_DIR / "accounts" / account / "shared.md"
    elif pipe == 3 and agent and account:
        target = HUB_DIR / "accounts" / account / "memory" / f"{agent}.md"
    else:
        target = HUB_DIR / "data" / "memory_pending.jsonl"

    if not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)

    content_line = f"- {lesson['content']}\n"

    if dry_run:
        return f"[DRY-RUN] Would write to {target.relative_to(HUB_DIR)}: {content_line.strip()}"

    if target.suffix == ".jsonl":
        # pending queue
        with open(target, "a") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")
    else:
        with open(target, "a") as f:
            f.write(content_line)

    return f"Pipe {pipe} → {target.relative_to(HUB_DIR)}"


def main():
    parser = argparse.ArgumentParser(description="从 Task 结果提取经验")
    parser.add_argument("task_file", help="task YAML 文件路径")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.task_file):
        print(json.dumps({"error": f"file not found: {args.task_file}"}))
        sys.exit(1)

    task = load_task(args.task_file)
    lessons = extract_lessons(task)

    if not lessons:
        print(json.dumps({"status": "no_lessons", "task_id": task.get("id")}))
        return

    results = []
    for lesson in lessons:
        route_result = route_lesson(lesson, dry_run=args.dry_run)
        results.append({"lesson": lesson["content"][:80], "route": route_result})

    # 更新 task YAML 的 lessons_extracted 字段
    if not args.dry_run and lessons:
        task["lessons_extracted"] = [l["content"] for l in lessons]
        task["updated_at"] = datetime.now().isoformat()
        with open(args.task_file, "w") as f:
            yaml.dump(task, f, allow_unicode=True, default_flow_style=False)

    print(json.dumps({"extracted": len(lessons), "results": results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
