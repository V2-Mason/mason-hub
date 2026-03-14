#!/usr/bin/env python3
"""decision-log.py — 决策记录 + 结果追踪 + 质量分析

五维 Gap #4（决策-质量追踪）：做了决策不追踪效果，无法学习哪些决策有效。
无状态工具，数据存 JSONL，多 agent 可用。

用法：
  # 记录新决策
  python3 skills/analytics/decision-log.py log \
    --decision "用悬念式 hook 发 10 条内容" \
    --context "竞品分析显示悬念 hook 效果上升" \
    --expected "互动率提升 20%" \
    --account surenxuan \
    --category content \
    --review-by 2026-03-21

  # 回顾决策（默认最近 30 天）
  python3 skills/analytics/decision-log.py review --days 30
  python3 skills/analytics/decision-log.py review --status pending
  python3 skills/analytics/decision-log.py review --category strategy

  # 记录决策结果
  python3 skills/analytics/decision-log.py outcome \
    --decision-id dec_20260314_010702_f25796 \
    --result "互动率提升 15%，低于预期但正向" \
    --notes "下次设预期时参考历史基线而非竞品"

  # 决策质量统计
  python3 skills/analytics/decision-log.py stats --days 90
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
LOG_FILE = HUB_DIR / "data" / "decision_log.jsonl"

CATEGORIES = ["strategy", "content", "tech", "ops", "other"]
STALE_DAYS = 14  # pending 超过此天数视为过期


def _load_decisions():
    """从 JSONL 加载所有决策记录"""
    if not LOG_FILE.exists():
        return []
    decisions = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                decisions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return decisions


def _save_decisions(decisions):
    """覆盖写入所有决策记录"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def _output(data):
    """统一 JSON 输出"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _parse_date(s):
    """宽松日期解析：支持 YYYY-MM-DD 或 ISO 格式"""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def log_decision(args):
    """记录一条新决策"""
    category = args.category or "other"
    if category not in CATEGORIES:
        _output({"error": f"invalid category '{category}', must be one of {CATEGORIES}"})
        sys.exit(1)

    entry = {
        "id": f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now().isoformat(),
        "decision": args.decision,
        "context": args.context or "",
        "expected_outcome": args.expected or "",
        "category": category,
        "account": args.account or "",
        "decided_by": args.decided_by or "mason",
        "review_by": args.review_by or "",
        "status": "pending",  # pending → tracked → reviewed
        "outcome": None,
        "outcome_date": None,
        "review_notes": None,
    }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    _output(entry)
    return entry


def review_decisions(args):
    """回顾决策 — 支持日期/状态/分类过滤"""
    decisions = _load_decisions()
    if not decisions:
        _output({"status": "no_decisions_logged", "file": str(LOG_FILE)})
        return

    now = datetime.now()

    # 日期过滤（--days）
    if args.days:
        cutoff = now - timedelta(days=args.days)
        decisions = [
            d for d in decisions
            if _parse_date(d.get("timestamp", "")) and _parse_date(d["timestamp"]) >= cutoff
        ]

    # 状态过滤
    if args.status:
        decisions = [d for d in decisions if d.get("status") == args.status]

    # 分类过滤
    if args.category:
        decisions = [d for d in decisions if d.get("category") == args.category]

    # 按时间倒序
    decisions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 条数限制
    if args.limit:
        decisions = decisions[:args.limit]

    # 标记过期决策
    stale = []
    for d in decisions:
        if d.get("status") == "pending":
            ts = _parse_date(d.get("timestamp", ""))
            if ts and (now - ts).days > STALE_DAYS:
                stale.append(d["id"])
            # 检查 review_by 是否过期
            rb = d.get("review_by")
            if rb:
                rb_date = _parse_date(rb)
                if rb_date and now > rb_date and d["id"] not in stale:
                    stale.append(d["id"])

    total_all = len(_load_decisions())  # 全量统计
    report = {
        "total_decisions": total_all,
        "filtered_count": len(decisions),
        "stale_ids": stale,
        "stale_count": len(stale),
        "decisions": decisions,
    }

    _output(report)


def record_outcome(args):
    """给已有决策补录结果"""
    decisions = _load_decisions()
    if not decisions:
        _output({"error": "no decision log found"})
        sys.exit(1)

    updated = False
    target = None
    for d in decisions:
        if d.get("id") == args.decision_id:
            d["outcome"] = args.result
            d["outcome_date"] = datetime.now().isoformat()
            d["status"] = "tracked"
            if args.notes:
                d["review_notes"] = args.notes
            updated = True
            target = d

    if updated:
        _save_decisions(decisions)
        _output(target)
    else:
        _output({"error": f"decision_id '{args.decision_id}' not found"})
        sys.exit(1)


def decision_stats(args):
    """决策质量统计 — Gap #4 核心能力"""
    decisions = _load_decisions()
    if not decisions:
        _output({"status": "no_decisions_logged"})
        return

    now = datetime.now()

    # 日期过滤
    if args.days:
        cutoff = now - timedelta(days=args.days)
        decisions = [
            d for d in decisions
            if _parse_date(d.get("timestamp", "")) and _parse_date(d["timestamp"]) >= cutoff
        ]

    total = len(decisions)
    if total == 0:
        _output({"status": "no_decisions_in_range", "days": args.days})
        return

    # 基础统计
    pending = [d for d in decisions if d.get("status") == "pending"]
    tracked = [d for d in decisions if d.get("status") == "tracked"]
    reviewed = [d for d in decisions if d.get("status") == "reviewed"]

    # 追踪率 = 有结果的 / 总数
    tracking_rate = len(tracked + reviewed) / total if total else 0

    # 按分类统计
    by_category = {}
    for d in decisions:
        cat = d.get("category", "other")
        if cat not in by_category:
            by_category[cat] = {"total": 0, "tracked": 0, "pending": 0}
        by_category[cat]["total"] += 1
        if d.get("status") in ("tracked", "reviewed"):
            by_category[cat]["tracked"] += 1
        else:
            by_category[cat]["pending"] += 1

    # 平均闭环时间（从决策到记录结果的天数）
    closure_days = []
    for d in tracked + reviewed:
        ts = _parse_date(d.get("timestamp", ""))
        ot = _parse_date(d.get("outcome_date", ""))
        if ts and ot:
            closure_days.append((ot - ts).days)
    avg_closure = sum(closure_days) / len(closure_days) if closure_days else None

    # 过期未追踪
    stale = []
    for d in pending:
        ts = _parse_date(d.get("timestamp", ""))
        if ts and (now - ts).days > STALE_DAYS:
            stale.append({
                "id": d["id"],
                "decision": d["decision"][:60],
                "days_ago": (now - ts).days,
            })

    # 按决策人统计
    by_decider = {}
    for d in decisions:
        who = d.get("decided_by", "unknown")
        if who not in by_decider:
            by_decider[who] = 0
        by_decider[who] += 1

    report = {
        "period_days": args.days or "all",
        "total": total,
        "status_breakdown": {
            "pending": len(pending),
            "tracked": len(tracked),
            "reviewed": len(reviewed),
        },
        "tracking_rate": f"{tracking_rate:.0%}",
        "avg_closure_days": avg_closure,
        "by_category": by_category,
        "by_decider": by_decider,
        "stale_decisions": stale,
        "health": "good" if tracking_rate >= 0.6 else "needs_attention" if tracking_rate >= 0.3 else "poor",
    }

    _output(report)


def main():
    parser = argparse.ArgumentParser(description="决策记录 + 结果追踪 + 质量分析")
    subparsers = parser.add_subparsers(dest="command")

    # log 子命令
    log_p = subparsers.add_parser("log", help="记录新决策")
    log_p.add_argument("--decision", required=True, help="决策内容")
    log_p.add_argument("--context", help="决策背景/依据")
    log_p.add_argument("--expected", help="预期结果（可量化最佳）")
    log_p.add_argument("--category", choices=CATEGORIES, default="other",
                       help="分类: strategy/content/tech/ops/other")
    log_p.add_argument("--account", help="关联品牌/账户")
    log_p.add_argument("--decided-by", default="mason", help="决策人")
    log_p.add_argument("--review-by", help="预期回顾日期 (YYYY-MM-DD)")

    # review 子命令
    rev_p = subparsers.add_parser("review", help="回顾决策")
    rev_p.add_argument("--days", type=int, default=30, help="最近 N 天内的决策")
    rev_p.add_argument("--status", choices=["pending", "tracked", "reviewed"],
                       help="按状态过滤")
    rev_p.add_argument("--category", choices=CATEGORIES, help="按分类过滤")
    rev_p.add_argument("--limit", type=int, help="最多显示 N 条")

    # outcome 子命令
    out_p = subparsers.add_parser("outcome", help="记录决策结果")
    out_p.add_argument("--decision-id", required=True, help="决策 ID")
    out_p.add_argument("--result", required=True, help="实际结果")
    out_p.add_argument("--notes", help="反思笔记（经验教训）")

    # stats 子命令
    sta_p = subparsers.add_parser("stats", help="决策质量统计")
    sta_p.add_argument("--days", type=int, default=90, help="统计最近 N 天")

    args = parser.parse_args()

    if args.command == "log":
        log_decision(args)
    elif args.command == "review":
        review_decisions(args)
    elif args.command == "outcome":
        record_outcome(args)
    elif args.command == "stats":
        decision_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
