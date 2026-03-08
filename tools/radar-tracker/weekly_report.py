#!/usr/bin/env python3
"""
weekly_report.py -- 周报脚本，统计每组关键词的关注率。
可手动运行或 cron 调度。

用法:
    python3 weekly_report.py [--weeks N]
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_report(weeks=2):
    if not os.path.exists(DB_PATH):
        print("No tracker.db found -- no data yet.")
        return

    conn = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    print("=" * 60)
    print("  Radar Tracker Weekly Report")
    print("  Generated: " + now.strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 60)

    # Per-week stats
    week_data_list = []
    for w in range(weeks):
        week_end = now - timedelta(weeks=w)
        week_start = week_end - timedelta(weeks=1)
        rows = conn.execute(
            """
            SELECT keyword_group, COUNT(*) as dismissed
            FROM dismissals
            WHERE keyword_group != ''
              AND dismissed_at >= ?
              AND dismissed_at < ?
            GROUP BY keyword_group
            ORDER BY dismissed DESC
            """,
            (week_start.isoformat(), week_end.isoformat()),
        ).fetchall()
        week_data = {r["keyword_group"]: r["dismissed"] for r in rows}
        week_data_list.append(week_data)

        print()
        label = "本周" if w == 0 else str(w) + " 周前"
        print(
            "  [" + label + "] "
            + week_start.strftime("%m/%d")
            + " - "
            + week_end.strftime("%m/%d")
        )
        if not week_data:
            print("    (无标记)")
        for kw, cnt in week_data.items():
            print("    " + kw + ": " + str(cnt) + " 条被标记无用")

    # All-time totals
    all_groups = conn.execute(
        """
        SELECT keyword_group, COUNT(*) as total_dismissed
        FROM dismissals
        WHERE keyword_group != ''
        GROUP BY keyword_group
        ORDER BY total_dismissed DESC
        """
    ).fetchall()

    print()
    print("  [累计]")
    for r in all_groups:
        print("    " + r["keyword_group"] + ": " + str(r["total_dismissed"]) + " 条")

    # Retirement suggestions
    suggest = []
    if len(week_data_list) >= 2:
        w0 = week_data_list[0]
        w1 = week_data_list[1]
        all_kw = set(list(w0.keys()) + list(w1.keys()))
        for kw in sorted(all_kw):
            d0 = w0.get(kw, 0)
            d1 = w1.get(kw, 0)
            if d0 >= 3 and d1 >= 3:
                suggest.append(kw)

    print()
    if suggest:
        print("  [建议淘汰] 以下关键词组连续两周每周被标记 >=3 条无用:")
        for kw in suggest:
            print("    - " + kw)
    else:
        print("  [建议淘汰] 无（数据不足或未达阈值）")

    print()
    print("=" * 60)
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Radar Tracker 周报")
    parser.add_argument("--weeks", type=int, default=2, help="回看周数")
    args = parser.parse_args()
    generate_report(weeks=args.weeks)
