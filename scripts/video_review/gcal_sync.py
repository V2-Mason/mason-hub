#!/usr/bin/env python3
"""
Google Calendar 同步 - 把 reminders 表里的待办推到日历

这个脚本本身不调用 Google Calendar API，而是输出一份 JSON，
由 video-review skill 用 mcp__claude_ai_Google_Calendar__gcal_create_event 来创建。

用法:
  # 列出需要同步到 Calendar 的提醒
  python scripts/video_review/gcal_sync.py list-pending

  # 标记某个 reminder 已同步（保存 gcal event id）
  python scripts/video_review/gcal_sync.py mark-synced --video-id 1 --checkpoint D7 --event-id xxx
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, time
from pathlib import Path

DB_PATH = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/data/video-reviews/reviews.db")


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def cmd_list_pending(args):
    """输出还没同步到 Calendar 的 reminders（即 gcal_event_id 为 NULL）"""
    conn = get_db()
    rows = conn.execute(
        """SELECT r.id as reminder_id, r.video_id, r.checkpoint, r.due_date,
                  v.platform, v.platform_id, v.title
           FROM reminders r
           JOIN videos v ON r.video_id = v.id
           WHERE r.gcal_event_id IS NULL AND r.status='pending'
           ORDER BY r.due_date ASC"""
    ).fetchall()

    events = []
    for r in rows:
        # 默认下午 14:00 提醒
        start_dt = f"{r['due_date']}T14:00:00"
        end_dt = f"{r['due_date']}T14:30:00"
        events.append({
            "reminder_id": r["reminder_id"],
            "video_id": r["video_id"],
            "checkpoint": r["checkpoint"],
            "summary": f"[Video Review {r['checkpoint']}] {r['title'][:40]}",
            "description": (
                f"Platform: {r['platform']}\n"
                f"ID: {r['platform_id']}\n"
                f"Title: {r['title']}\n\n"
                f"Run: /video-review {r['platform_id']} --checkpoint {r['checkpoint']}"
            ),
            "start": start_dt,
            "end": end_dt,
        })

    conn.close()
    print(json.dumps(events, ensure_ascii=False, indent=2))
    return 0


def cmd_mark_synced(args):
    """记录 gcal_event_id（由 skill 调用 calendar API 后回填）"""
    conn = get_db()
    conn.execute(
        "UPDATE reminders SET gcal_event_id=? WHERE video_id=? AND checkpoint=?",
        (args.event_id, args.video_id, args.checkpoint),
    )
    conn.commit()
    conn.close()
    print(f"Marked: video {args.video_id} {args.checkpoint} -> {args.event_id}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p1 = sub.add_parser("list-pending")
    p1.set_defaults(func=cmd_list_pending)

    p2 = sub.add_parser("mark-synced")
    p2.add_argument("--video-id", type=int, required=True)
    p2.add_argument("--checkpoint", required=True)
    p2.add_argument("--event-id", required=True)
    p2.set_defaults(func=cmd_mark_synced)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
