#!/usr/bin/env python3
"""decision-log.py — 决策记录 + 结果追踪

五维 Gap #4（决策-质量追踪）：做了决策不追踪效果。
输入：决策描述 或 回顾请求
输出：JSON 决策记录

用法：
  # 记录新决策
  python3 skills/analytics/decision-log.py log \
    --decision "用悬念式 hook 发 10 条内容" \
    --context "竞品分析显示悬念 hook 效果上升" \
    --expected "互动率提升 20%" \
    --account surenxuan

  # 回顾决策结果
  python3 skills/analytics/decision-log.py review --days 30

  # 记录决策结果
  python3 skills/analytics/decision-log.py outcome \
    --decision-id <id> \
    --result "互动率提升 15%，低于预期但正向"
"""

import argparse
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
LOG_FILE = HUB_DIR / "data" / "decision_log.jsonl"


def log_decision(args):
    """记录一条新决策"""
    entry = {
        "id": f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now().isoformat(),
        "decision": args.decision,
        "context": args.context or "",
        "expected_outcome": args.expected or "",
        "account": args.account or "",
        "decided_by": args.decided_by or "mason",
        "status": "pending",  # pending → tracked → reviewed
        "outcome": None,
        "outcome_date": None,
        "review_notes": None,
    }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return entry


def review_decisions(args):
    """回顾最近的决策及其结果"""
    if not LOG_FILE.exists():
        print(json.dumps({"status": "no_decisions_logged", "file": str(LOG_FILE)}))
        return

    decisions = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    decisions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # 按时间倒序
    decisions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 统计
    total = len(decisions)
    pending = sum(1 for d in decisions if d.get("status") == "pending")
    tracked = sum(1 for d in decisions if d.get("outcome") is not None)

    report = {
        "total_decisions": total,
        "pending_review": pending,
        "has_outcome": tracked,
        "decisions": decisions[:args.days] if args.days else decisions,  # limit by count
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


def record_outcome(args):
    """给已有决策补录结果"""
    if not LOG_FILE.exists():
        print(json.dumps({"error": "no decision log found"}))
        return

    decisions = []
    updated = False
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("id") == args.decision_id:
                    d["outcome"] = args.result
                    d["outcome_date"] = datetime.now().isoformat()
                    d["status"] = "tracked"
                    updated = True
                    print(json.dumps(d, indent=2, ensure_ascii=False))
                decisions.append(d)
            except json.JSONDecodeError:
                continue

    if updated:
        with open(LOG_FILE, "w") as f:
            for d in decisions:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    else:
        print(json.dumps({"error": f"decision_id '{args.decision_id}' not found"}))


def main():
    parser = argparse.ArgumentParser(description="决策记录 + 结果追踪")
    subparsers = parser.add_subparsers(dest="command")

    # log 子命令
    log_parser = subparsers.add_parser("log", help="记录新决策")
    log_parser.add_argument("--decision", required=True, help="决策内容")
    log_parser.add_argument("--context", help="决策背景")
    log_parser.add_argument("--expected", help="预期结果")
    log_parser.add_argument("--account", help="关联品牌/账户")
    log_parser.add_argument("--decided-by", default="mason", help="决策人")

    # review 子命令
    review_parser = subparsers.add_parser("review", help="回顾决策")
    review_parser.add_argument("--days", type=int, default=20, help="显示最近 N 条")

    # outcome 子命令
    outcome_parser = subparsers.add_parser("outcome", help="记录决策结果")
    outcome_parser.add_argument("--decision-id", required=True, help="决策 ID")
    outcome_parser.add_argument("--result", required=True, help="实际结果")

    args = parser.parse_args()

    if args.command == "log":
        log_decision(args)
    elif args.command == "review":
        review_decisions(args)
    elif args.command == "outcome":
        record_outcome(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
