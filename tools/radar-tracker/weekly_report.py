#!/usr/bin/env python3
"""
weekly_report.py -- 周报脚本，统计每组关键词的关注率。
可手动运行或 cron 调度。

用法:
    python3 weekly_report.py [--weeks N]
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")
TRENDRADAR_DIR = Path(os.path.expanduser("~/mason-hub/tools/trendradar"))
RETIRE_THRESHOLD = float(os.environ.get("RETIRE_THRESHOLD", "0.5"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _count_weekly_hits(weeks=2):
    """从 TrendRadar 数据统计每组关键词每周的总命中数。"""
    try:
        sys.path.insert(0, str(TRENDRADAR_DIR))
        from trendradar.core.frequency import load_frequency_words, _word_matches

        groups, filter_words, global_filters = load_frequency_words(
            str(TRENDRADAR_DIR / "config" / "frequency_words.txt")
        )

        def match_title(title):
            title_lower = title.lower()
            for gf in global_filters:
                if gf.lower() in title_lower:
                    return None
            for g in groups:
                normal = g.get("normal", [])
                required = g.get("required", [])
                if required:
                    if not all(_word_matches(w, title_lower) for w in required):
                        continue
                if normal:
                    if any(_word_matches(w, title_lower) for w in normal):
                        return g.get("display_name", "?")
                elif required:
                    return g.get("display_name", "?")
            return None

    except Exception as e:
        print(f"  (无法加载 TrendRadar 关键词匹配器: {e})")
        return None

    now = datetime.now()
    weekly_hits = []
    for w in range(weeks):
        week_end = now - timedelta(weeks=w)
        week_start = week_end - timedelta(weeks=1)
        group_counts = {}
        for i in range(7):
            d = week_start + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            # Read news + rss data
            for db_type, table, src_col in [
                ("news", "news_items", "platform_id"),
                ("rss", "rss_items", "feed_id"),
            ]:
                db_path = TRENDRADAR_DIR / f"output/{db_type}/{ds}.db"
                if db_path.exists():
                    c = sqlite3.connect(str(db_path))
                    for (title,) in c.execute(f"SELECT title FROM {table}"):
                        g = match_title(title)
                        if g:
                            group_counts[g] = group_counts.get(g, 0) + 1
                    c.close()
        weekly_hits.append(
            {
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "hits": group_counts,
            }
        )
    return weekly_hits


def generate_report(weeks=2):
    if not os.path.exists(DB_PATH):
        print("No tracker.db found -- no data yet.")
        return

    conn = get_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    print("=" * 60)
    print("  Radar Tracker 关注率周报")
    print("  Generated: " + now.strftime("%Y-%m-%d %H:%M UTC"))
    print("  淘汰阈值: 关注率 < " + f"{RETIRE_THRESHOLD:.0%}")
    print("=" * 60)

    # 每周总命中数
    weekly_hits = _count_weekly_hits(weeks)

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
        hits = weekly_hits[w]["hits"] if weekly_hits and w < len(weekly_hits) else {}

        print()
        label = "本周" if w == 0 else str(w) + " 周前"
        print(
            "  ["
            + label
            + "] "
            + week_start.strftime("%m/%d")
            + " - "
            + week_end.strftime("%m/%d")
        )
        all_kw = sorted(set(list(week_data.keys()) + list(hits.keys())))
        if not all_kw:
            print("    (无数据)")
        for kw in all_kw:
            total = hits.get(kw, 0)
            dismissed = week_data.get(kw, 0)
            if total > 0:
                relevance = 1.0 - dismissed / total
                print(
                    f"    {kw}: {total} 条命中, {dismissed} 条无用, 关注率 {relevance:.0%}"
                )
            elif dismissed > 0:
                print(f"    {kw}: ? 条命中, {dismissed} 条无用, 关注率 0%")

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
    print("  [累计 dismiss]")
    for r in all_groups:
        print("    " + r["keyword_group"] + ": " + str(r["total_dismissed"]) + " 条")

    # Retirement suggestions based on relevance rate
    suggest = []
    if weekly_hits and len(week_data_list) >= 2 and len(weekly_hits) >= 2:
        h0, h1 = weekly_hits[0]["hits"], weekly_hits[1]["hits"]
        d0, d1 = week_data_list[0], week_data_list[1]
        all_kw = set(
            list(h0.keys()) + list(h1.keys()) + list(d0.keys()) + list(d1.keys())
        )
        for kw in sorted(all_kw):
            t0, t1 = h0.get(kw, 0), h1.get(kw, 0)
            dd0, dd1 = d0.get(kw, 0), d1.get(kw, 0)
            rel0 = (1.0 - dd0 / t0) if t0 > 0 else (0.0 if dd0 > 0 else None)
            rel1 = (1.0 - dd1 / t1) if t1 > 0 else (0.0 if dd1 > 0 else None)
            if (
                rel0 is not None
                and rel1 is not None
                and rel0 < RETIRE_THRESHOLD
                and rel1 < RETIRE_THRESHOLD
            ):
                suggest.append((kw, rel0, rel1))

    print()
    if suggest:
        print(
            f"  [建议淘汰] 以下关键词组连续两周关注率 < {RETIRE_THRESHOLD:.0%}:"
        )
        for kw, r0, r1 in suggest:
            print(f"    - {kw} (本周 {r0:.0%}, 上周 {r1:.0%})")
    else:
        print("  [建议淘汰] 无（数据不足或未达阈值）")

    # Seen items stats
    try:
        seen_count = conn.execute("SELECT COUNT(*) FROM seen_items").fetchone()[0]
        seen_dates = conn.execute(
            "SELECT MIN(first_seen_date), MAX(first_seen_date) FROM seen_items"
        ).fetchone()
        print()
        print(
            f"  [去重] 已记录 {seen_count} 个标题 ({seen_dates[0]} ~ {seen_dates[1]})"
        )
    except Exception:
        pass

    print()
    print("=" * 60)
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Radar Tracker 关注率周报")
    parser.add_argument("--weeks", type=int, default=2, help="回看周数")
    args = parser.parse_args()
    generate_report(weeks=args.weeks)
