#!/usr/bin/env python3
"""task-dashboard.py — Task Dashboard（按 account 分组）

扫描 data/tasks/*.yaml + audit.jsonl，按 account 和 status 分组统计。

用法：
  python3 scripts/control/task-dashboard.py
  python3 scripts/control/task-dashboard.py --format summary
  python3 scripts/control/task-dashboard.py --account surenxuan
"""

import argparse
import json
import os
import yaml
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))


def load_task_yamls() -> list[dict]:
    """从 data/tasks/*.yaml 加载所有任务"""
    tasks_dir = HUB_DIR / "data" / "tasks"
    if not tasks_dir.exists():
        return []

    tasks = []
    for f in sorted(tasks_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text())
            if data and isinstance(data, dict):
                tasks.append(data)
        except Exception:
            continue

    return tasks


def load_recent_audit(days: int = 7) -> list[dict]:
    """从 audit.jsonl 加载最近的任务记录"""
    audit_file = HUB_DIR / "logs" / "audit.jsonl"
    if not audit_file.exists():
        return []

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    records = []

    with open(audit_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("timestamp", "") >= cutoff:
                    records.append(d)
            except json.JSONDecodeError:
                continue

    return records


def build_dashboard(tasks: list, audit: list, account_filter: str = "") -> dict:
    """构建 dashboard"""
    # 按 account 分组
    by_account = defaultdict(lambda: defaultdict(int))
    by_agent = defaultdict(lambda: defaultdict(int))
    total_by_status = defaultdict(int)

    for t in tasks:
        account = t.get("account", "") or "platform"
        status = t.get("status", "unknown")
        agent = t.get("agent", "unknown")

        if account_filter and account != account_filter:
            continue

        by_account[account][status] += 1
        by_agent[agent][status] += 1
        total_by_status[status] += 1

    # 从 audit 补充（可能没有 task yaml 的旧任务）
    audit_agents = defaultdict(lambda: {"completed": 0, "failed": 0, "total_cost": 0})
    for r in audit:
        agent = r.get("agent", "unknown")
        status = r.get("status", "")
        cost = r.get("cost_usd", 0)
        if isinstance(cost, (int, float)):
            audit_agents[agent]["total_cost"] += cost
        if status in ("completed",):
            audit_agents[agent]["completed"] += 1
        elif status in ("failed", "repair_failed"):
            audit_agents[agent]["failed"] += 1

    return {
        "generated_at": datetime.now().isoformat(),
        "task_yaml_count": len(tasks),
        "audit_record_count": len(audit),
        "by_account": {k: dict(v) for k, v in by_account.items()},
        "by_agent": {k: dict(v) for k, v in by_agent.items()},
        "total_by_status": dict(total_by_status),
        "agent_audit_summary": {k: dict(v) for k, v in audit_agents.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="Task Dashboard")
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    parser.add_argument("--account", default="", help="过滤特定 account")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    tasks = load_task_yamls()
    audit = load_recent_audit(args.days)
    dashboard = build_dashboard(tasks, audit, args.account)

    # 保存
    output_file = HUB_DIR / "data" / "control" / "dashboard.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    if args.format == "json":
        print(json.dumps(dashboard, indent=2, ensure_ascii=False))
    else:
        print(f"=== Task Dashboard ({args.days}天) ===")
        print(f"Task YAML: {dashboard['task_yaml_count']} | Audit: {dashboard['audit_record_count']}")
        print(f"\n按 Account:")
        for acc, statuses in dashboard["by_account"].items():
            print(f"  {acc}: {dict(statuses)}")
        print(f"\n按状态:")
        for status, count in dashboard["total_by_status"].items():
            print(f"  {status}: {count}")
        print(f"\n按 Agent (审计):")
        for agent, stats in sorted(dashboard["agent_audit_summary"].items()):
            cost = stats.get("total_cost", 0)
            print(f"  {agent}: {stats.get('completed',0)} done, {stats.get('failed',0)} failed, ${cost:.2f}")


if __name__ == "__main__":
    main()
