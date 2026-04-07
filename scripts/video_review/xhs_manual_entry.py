#!/usr/bin/env python3
"""
小红书手动数据录入工具
小红书没有公开 API，Mason 需要手动从创作者后台抄数据填进来。

用法:
  # 注册新笔记
  python scripts/video_review/xhs_manual_entry.py register \
      --note-id 67xxxxxxxx --title "..." --pubdate 2026-04-06

  # 录入数据快照
  python scripts/video_review/xhs_manual_entry.py snapshot \
      --note-id 67xxxxxxxx --checkpoint D7 \
      --views 5230 --likes 89 --collects 45 --comments 12
"""
import argparse
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/data/video-reviews/reviews.db")


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def cmd_register(args):
    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM videos WHERE platform=? AND platform_id=?",
        ("xiaohongshu", args.note_id),
    ).fetchone()
    if existing:
        print(f"Note already registered (id={existing['id']})")
        conn.close()
        return 0

    cur = conn.execute(
        """INSERT INTO videos
           (platform, platform_id, title, publish_date, url, topic, target_audience,
            content_pillar, production_hours, hypothesis)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "xiaohongshu",
            args.note_id,
            args.title,
            args.pubdate,
            f"https://www.xiaohongshu.com/explore/{args.note_id}",
            args.topic,
            args.audience,
            args.pillar,
            args.hours,
            args.hypothesis,
        ),
    )
    video_id = cur.lastrowid

    pub_date = datetime.fromisoformat(args.pubdate).date()
    for days, checkpoint in [(7, "D7"), (30, "D30"), (60, "D60"), (90, "D90")]:
        due = pub_date + timedelta(days=days)
        conn.execute(
            "INSERT INTO reminders (video_id, checkpoint, due_date) VALUES (?, ?, ?)",
            (video_id, checkpoint, due.isoformat()),
        )

    conn.commit()
    conn.close()

    print(f"Registered XHS note: {args.title[:60]}")
    print(f"  Video ID: {video_id}")
    print(f"  Reminders created for D7/D30/D60/D90")
    return 0


def cmd_snapshot(args):
    conn = get_db()

    video = conn.execute(
        "SELECT id FROM videos WHERE platform_id=?", (args.note_id,)
    ).fetchone()
    if not video:
        print(f"Note not registered. Run 'register' first.", file=sys.stderr)
        conn.close()
        return 1

    video_id = video["id"]

    # 小红书的指标映射：
    #   views = 浏览量（不是播放）
    #   likes = 点赞
    #   collects = 收藏
    #   comments = 评论
    #   shares = 分享
    interaction = (args.likes or 0) + (args.collects or 0) + (args.comments or 0) + (args.shares or 0)
    rate = interaction / args.views if args.views and args.views > 0 else 0

    growth_since_d7 = None
    if args.checkpoint in ("D30", "D60", "D90"):
        d7 = conn.execute(
            "SELECT views FROM snapshots WHERE video_id=? AND checkpoint='D7'",
            (video_id,),
        ).fetchone()
        if d7 and d7["views"]:
            growth_since_d7 = (args.views or 0) - d7["views"]

    conn.execute(
        """INSERT OR REPLACE INTO snapshots
           (video_id, checkpoint, snapshot_date, views, likes, favorites,
            shares, comments_count, interaction_rate, growth_since_d7,
            quality_comment_pct, dm_inquiries)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            video_id,
            args.checkpoint,
            date.today().isoformat(),
            args.views,
            args.likes,
            args.collects,
            args.shares,
            args.comments,
            rate,
            growth_since_d7,
            args.quality_pct,
            args.dm,
        ),
    )

    conn.execute(
        "UPDATE reminders SET status='completed', completed_at=CURRENT_TIMESTAMP "
        "WHERE video_id=? AND checkpoint=?",
        (video_id, args.checkpoint),
    )

    conn.commit()
    conn.close()

    print(f"Snapshot saved: {args.note_id} @ {args.checkpoint}")
    print(f"  Views: {args.views}, interaction rate: {rate*100:.2f}%")
    if growth_since_d7 is not None:
        print(f"  Growth since D7: +{growth_since_d7}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_reg = sub.add_parser("register")
    p_reg.add_argument("--note-id", required=True)
    p_reg.add_argument("--title", required=True)
    p_reg.add_argument("--pubdate", required=True, help="YYYY-MM-DD")
    p_reg.add_argument("--topic", default="")
    p_reg.add_argument("--audience", default="")
    p_reg.add_argument("--pillar", default="")
    p_reg.add_argument("--hours", type=float, default=0)
    p_reg.add_argument("--hypothesis", default="")
    p_reg.set_defaults(func=cmd_register)

    p_snap = sub.add_parser("snapshot")
    p_snap.add_argument("--note-id", required=True)
    p_snap.add_argument(
        "--checkpoint", required=True, choices=["D7", "D30", "D60", "D90", "AD_HOC"]
    )
    p_snap.add_argument("--views", type=int, required=True)
    p_snap.add_argument("--likes", type=int, default=0)
    p_snap.add_argument("--collects", type=int, default=0)
    p_snap.add_argument("--comments", type=int, default=0)
    p_snap.add_argument("--shares", type=int, default=0)
    p_snap.add_argument("--quality-pct", type=float, default=None, help="优质评论比 0-1")
    p_snap.add_argument("--dm", type=int, default=0, help="私信咨询数")
    p_snap.set_defaults(func=cmd_snapshot)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
