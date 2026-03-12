#!/usr/bin/env python3
"""
audit-query — 审计日志查询工具

用法:
    # 今日摘要
    python3 scripts/audit-query.py summary

    # 指定日期摘要
    python3 scripts/audit-query.py summary --date 2026-03-11

    # 按 agent 分组统计
    python3 scripts/audit-query.py by-agent

    # 最近 N 条记录
    python3 scripts/audit-query.py tail --n 10

    # 失败记录
    python3 scripts/audit-query.py failures

    # 成本趋势（近 7 天）
    python3 scripts/audit-query.py cost-trend --days 7
"""
import json
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

AUDIT_FILE = os.path.expanduser("~/mason-hub/logs/audit.jsonl")


def load_records(filepath=AUDIT_FILE):
    """Load all audit records, skipping malformed lines."""
    records = []
    if not os.path.exists(filepath):
        return records
    with open(filepath, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def filter_by_date(records, date_str):
    """Filter records matching a date string (YYYY-MM-DD)."""
    return [r for r in records if r.get("timestamp", "").startswith(date_str)]


def fmt_cost(c):
    if c <= 0:
        return "N/A"
    return f"${c:.4f}"


def fmt_tokens(t):
    if t <= 0:
        return "N/A"
    if t >= 1000:
        return f"{t/1000:.1f}K"
    return str(t)


def fmt_duration(d):
    if d <= 0:
        return "N/A"
    m, s = divmod(int(d), 60)
    return f"{m}m{s:02d}s" if m > 0 else f"{s}s"


def cmd_summary(records, date_str):
    """Daily summary."""
    day = filter_by_date(records, date_str)
    if not day:
        print(f"No records for {date_str}")
        return

    total = len(day)
    completed = sum(1 for r in day if r.get("status") == "completed")
    failed = sum(1 for r in day if r.get("status") in ("failed", "repair_failed"))
    total_cost = sum(r.get("cost_usd", 0) for r in day if r.get("cost_usd", 0) > 0)
    total_input = sum(r.get("input_tokens", 0) for r in day if r.get("input_tokens", 0) > 0)
    total_output = sum(r.get("output_tokens", 0) for r in day if r.get("output_tokens", 0) > 0)
    total_dur = sum(r.get("duration", 0) for r in day if r.get("duration", 0) > 0)

    agents = set(r.get("agent", "?") for r in day)

    print(f"📊 审计摘要 | {date_str}")
    print(f"{'─' * 40}")
    print(f"  Sessions:  {total} ({completed} ✅ / {failed} ❌)")
    print(f"  Agents:    {', '.join(sorted(agents))}")
    print(f"  Duration:  {fmt_duration(total_dur)}")
    print(f"  Tokens:    {fmt_tokens(total_input)} in / {fmt_tokens(total_output)} out")
    print(f"  Cost:      {fmt_cost(total_cost)}")

    if failed > 0:
        print(f"\n  ❌ 失败详情:")
        for r in day:
            if r.get("status") in ("failed", "repair_failed"):
                agent = r.get("agent", "?")
                err = r.get("error", r.get("root_cause_guess", "unknown"))
                task = r.get("task", "")[:50]
                print(f"    - {agent}: {task} ({err})")


def cmd_by_agent(records, date_str):
    """Per-agent breakdown."""
    day = filter_by_date(records, date_str) if date_str else records

    stats = defaultdict(lambda: {"count": 0, "completed": 0, "failed": 0,
                                  "cost": 0.0, "input_tokens": 0, "output_tokens": 0,
                                  "duration": 0})
    for r in day:
        a = r.get("agent", "?")
        s = stats[a]
        s["count"] += 1
        if r.get("status") == "completed":
            s["completed"] += 1
        elif r.get("status") in ("failed", "repair_failed"):
            s["failed"] += 1
        s["cost"] += max(r.get("cost_usd", 0), 0)
        s["input_tokens"] += max(r.get("input_tokens", 0), 0)
        s["output_tokens"] += max(r.get("output_tokens", 0), 0)
        s["duration"] += max(r.get("duration", 0), 0)

    label = date_str if date_str else "all time"
    print(f"📊 Agent 分组 | {label}")
    print(f"{'Agent':<12} {'Sessions':>8} {'✅':>4} {'❌':>4} {'Duration':>10} {'Tokens':>12} {'Cost':>8}")
    print(f"{'─' * 62}")
    for agent in sorted(stats.keys()):
        s = stats[agent]
        tok = f"{fmt_tokens(s['input_tokens'])}/{fmt_tokens(s['output_tokens'])}"
        print(f"{agent:<12} {s['count']:>8} {s['completed']:>4} {s['failed']:>4} {fmt_duration(s['duration']):>10} {tok:>12} {fmt_cost(s['cost']):>8}")

    total_cost = sum(s["cost"] for s in stats.values())
    total_count = sum(s["count"] for s in stats.values())
    print(f"{'─' * 62}")
    print(f"{'合计':<12} {total_count:>8} {'':>4} {'':>4} {'':>10} {'':>12} {fmt_cost(total_cost):>8}")


def cmd_tail(records, n):
    """Show last N records."""
    for r in records[-n:]:
        ts = r.get("timestamp", "?")[:19]
        agent = r.get("agent", "?")
        status = r.get("status", "?")
        task = r.get("task", "")[:40]
        dur = fmt_duration(r.get("duration", 0))
        cost = fmt_cost(r.get("cost_usd", 0))
        emoji = "✅" if status == "completed" else "❌"
        print(f"{ts} {emoji} {agent:<10} {dur:>6} {cost:>8}  {task}")


def cmd_failures(records, days):
    """Show failure records from the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    failures = [r for r in records
                if r.get("status") in ("failed", "repair_failed")
                and r.get("timestamp", "") >= cutoff]

    if not failures:
        print(f"No failures in the last {days} days ✅")
        return

    print(f"❌ 失败记录 | 最近 {days} 天 ({len(failures)} 条)")
    print(f"{'─' * 60}")
    for r in failures:
        ts = r.get("timestamp", "?")[:19]
        agent = r.get("agent", "?")
        task = r.get("task", "")[:40]
        err = r.get("error", r.get("root_cause_guess", ""))[:50]
        rounds = r.get("verify_rounds", r.get("verify_round", ""))
        retry = r.get("pm_retry_count", "")
        detail = f"rounds={rounds}" if rounds else ""
        if retry:
            detail += f" retry={retry}"
        print(f"  {ts} {agent:<10} {task}")
        if err:
            print(f"    → {err} {detail}")


def cmd_cost_trend(records, days):
    """Cost trend over last N days."""
    today = datetime.now(timezone.utc).date()
    print(f"💰 成本趋势 | 最近 {days} 天")
    print(f"{'日期':<12} {'Sessions':>8} {'Cost':>10} {'Tokens(in)':>12}")
    print(f"{'─' * 45}")

    total_cost = 0
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        day = filter_by_date(records, d)
        cost = sum(r.get("cost_usd", 0) for r in day if r.get("cost_usd", 0) > 0)
        inp = sum(r.get("input_tokens", 0) for r in day if r.get("input_tokens", 0) > 0)
        total_cost += cost
        bar = "█" * min(int(cost * 20), 40) if cost > 0 else "·"
        print(f"{d:<12} {len(day):>8} {fmt_cost(cost):>10} {fmt_tokens(inp):>12}  {bar}")

    print(f"{'─' * 45}")
    print(f"{'合计':<12} {'':>8} {fmt_cost(total_cost):>10}")
    if days > 0 and total_cost > 0:
        avg = total_cost / days
        monthly = avg * 30
        print(f"{'日均':<12} {'':>8} {fmt_cost(avg):>10}  (≈ ${monthly:.1f}/月)")


def main():
    parser = argparse.ArgumentParser(description="审计日志查询")
    sub = parser.add_subparsers(dest="cmd")

    p_summary = sub.add_parser("summary", help="每日摘要")
    p_summary.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))

    p_agent = sub.add_parser("by-agent", help="按 agent 分组")
    p_agent.add_argument("--date", default="")

    p_tail = sub.add_parser("tail", help="最近 N 条")
    p_tail.add_argument("--n", type=int, default=10)

    p_fail = sub.add_parser("failures", help="失败记录")
    p_fail.add_argument("--days", type=int, default=7)

    p_cost = sub.add_parser("cost-trend", help="成本趋势")
    p_cost.add_argument("--days", type=int, default=7)

    args = parser.parse_args()
    records = load_records()

    if args.cmd == "summary":
        cmd_summary(records, args.date)
    elif args.cmd == "by-agent":
        cmd_by_agent(records, args.date)
    elif args.cmd == "tail":
        cmd_tail(records, args.n)
    elif args.cmd == "failures":
        cmd_failures(records, args.days)
    elif args.cmd == "cost-trend":
        cmd_cost_trend(records, args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
