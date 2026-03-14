#!/usr/bin/env python3
"""escalation-queue.py — Escalation 队列聚合 + 注意力优先级排序

聚合三个数据源：
1. audit.jsonl (status=failed/escalated)
2. memory_pending.jsonl (需要人判定归属的经验)
3. gateway-known-states.yaml (过期的决策)

输出：data/control/escalation_queue.json（按 urgency × impact 排序）

用法：
  python3 scripts/control/escalation-queue.py
  python3 scripts/control/escalation-queue.py --slack C0AHCMUC057
  python3 scripts/control/escalation-queue.py --format summary
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))


def load_failed_tasks(days: int = 7) -> list[dict]:
    """从 audit.jsonl 提取失败/升级的任务"""
    audit_file = HUB_DIR / "logs" / "audit.jsonl"
    if not audit_file.exists():
        return []

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    items = []

    with open(audit_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                status = d.get("status", "")
                ts = d.get("timestamp", "")
                if status in ("failed", "repair_failed", "escalated") and ts >= cutoff:
                    items.append({
                        "type": "task_failure",
                        "task_id": d.get("task_id", "?"),
                        "agent": d.get("agent", "?"),
                        "status": status,
                        "timestamp": ts,
                        "detail": d.get("root_cause_guess", d.get("task", ""))[:100],
                        "urgency": 3 if status == "escalated" else 2,
                        "impact": 2,
                    })
            except json.JSONDecodeError:
                continue

    return items


def load_memory_pending() -> list[dict]:
    """从 memory_pending.jsonl 提取未分类的经验"""
    pending_file = HUB_DIR / "data" / "memory_pending.jsonl"
    if not pending_file.exists():
        return []

    items = []
    with open(pending_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                items.append({
                    "type": "memory_pending",
                    "content": d.get("content", "")[:80],
                    "source_task": d.get("source_task", ""),
                    "timestamp": d.get("timestamp", datetime.now().isoformat()),
                    "urgency": 1,
                    "impact": 1,
                })
            except json.JSONDecodeError:
                continue

    return items


def load_expired_decisions() -> list[dict]:
    """从 gateway-known-states.yaml 提取过期的决策"""
    states_file = HUB_DIR / "data" / "gateway-known-states.yaml"
    if not states_file.exists():
        return []

    try:
        with open(states_file) as f:
            states = yaml.safe_load(f)
    except Exception:
        return []

    if not states or not isinstance(states, list):
        return []

    items = []
    now = datetime.now().strftime("%Y-%m-%d")
    for s in states:
        expires = str(s.get("expires", ""))
        if expires and expires < now:
            items.append({
                "type": "expired_decision",
                "id": s.get("id", "?"),
                "decision": s.get("decision", "")[:80],
                "expired_on": expires,
                "timestamp": expires,
                "urgency": 1,
                "impact": 1,
            })

    return items


def load_task_yaml_failures() -> list[dict]:
    """从 data/tasks/*.yaml 提取失败任务"""
    tasks_dir = HUB_DIR / "data" / "tasks"
    if not tasks_dir.exists():
        return []

    items = []
    for f in tasks_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text())
            if data.get("status") in ("failed", "escalated"):
                items.append({
                    "type": "task_failure",
                    "task_id": data.get("id", f.stem),
                    "agent": data.get("agent", "?"),
                    "status": data.get("status"),
                    "timestamp": data.get("updated_at", ""),
                    "detail": data.get("error_summary", data.get("description", ""))[:100],
                    "urgency": 3 if data.get("status") == "escalated" else 2,
                    "impact": 2,
                })
        except Exception:
            continue

    return items


def prioritize(items: list[dict]) -> list[dict]:
    """按 urgency × impact × 时间衰减 排序"""
    now = datetime.now()
    for item in items:
        ts = item.get("timestamp", "")
        try:
            age_hours = (now - datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))).total_seconds() / 3600
        except Exception:
            age_hours = 168  # default 1 week

        # 时间衰减：越新越紧急
        recency = max(0.1, 1.0 - (age_hours / 168))  # 1 week decay
        item["priority_score"] = item["urgency"] * item["impact"] * (1 + recency)

    items.sort(key=lambda x: -x["priority_score"])
    return items


def main():
    parser = argparse.ArgumentParser(description="Escalation 队列聚合")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    parser.add_argument("--slack", help="推送到 Slack 频道")
    args = parser.parse_args()

    all_items = []
    all_items.extend(load_failed_tasks(args.days))
    all_items.extend(load_task_yaml_failures())
    all_items.extend(load_memory_pending())
    all_items.extend(load_expired_decisions())

    # 去重（同一 task_id 只保留最新）
    seen = set()
    deduped = []
    for item in all_items:
        key = item.get("task_id", item.get("content", item.get("id", "")))
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    prioritized = prioritize(deduped)

    queue = {
        "generated_at": datetime.now().isoformat(),
        "period_days": args.days,
        "total_items": len(prioritized),
        "by_type": {
            "task_failure": sum(1 for i in prioritized if i["type"] == "task_failure"),
            "memory_pending": sum(1 for i in prioritized if i["type"] == "memory_pending"),
            "expired_decision": sum(1 for i in prioritized if i["type"] == "expired_decision"),
        },
        "items": prioritized,
    }

    # 保存
    output_file = HUB_DIR / "data" / "control" / "escalation_queue.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    if args.format == "json":
        print(json.dumps(queue, indent=2, ensure_ascii=False))
    else:
        print(f"=== Escalation Queue ({args.days}天) ===")
        print(f"总计: {queue['total_items']} 项")
        for k, v in queue["by_type"].items():
            if v > 0:
                print(f"  {k}: {v}")
        print(f"\nTop 5 优先处理:")
        for i, item in enumerate(prioritized[:5], 1):
            print(f"  {i}. [{item['type']}] {item.get('task_id', item.get('content', ''))[:50]} (score: {item['priority_score']:.1f})")


if __name__ == "__main__":
    main()
