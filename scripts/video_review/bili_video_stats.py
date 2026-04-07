#!/usr/bin/env python3
"""
B站视频数据采集 - 抓取单条视频的全部公开数据

用法:
  # 注册新视频（首次入库）
  python scripts/video_review/bili_video_stats.py register --bvid BV1xxx \
      --topic AI编程实战 --audience "35+转型者" --hypothesis "..."

  # 抓取数据快照
  python scripts/video_review/bili_video_stats.py snapshot --bvid BV1xxx --checkpoint D7

  # 列出待复盘视频
  python scripts/video_review/bili_video_stats.py pending
"""
import requests
import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/data/video-reviews/reviews.db")
COOKIES_FILE = "c:/Users/hangn/projects/mason-hub/cookies.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}


def load_cookies(session):
    try:
        with open(COOKIES_FILE, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    session.cookies.set(parts[5], parts[6], domain=parts[0])
    except FileNotFoundError:
        pass


def fetch_video_info(bvid):
    """通过 web API 拿视频元数据 + 当前统计"""
    session = requests.Session()
    session.headers.update(HEADERS)
    load_cookies(session)

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    r = session.get(url, timeout=15)
    data = r.json()

    if data.get("code") != 0:
        print(f"API Error: {data.get('message')}", file=sys.stderr)
        return None

    d = data["data"]
    stat = d.get("stat", {})

    return {
        "bvid": d["bvid"],
        "aid": d["aid"],
        "title": d["title"],
        "desc": d.get("desc", ""),
        "duration": d.get("duration", 0),
        "pubdate": datetime.fromtimestamp(d["pubdate"]).date().isoformat(),
        "owner": d.get("owner", {}).get("name", ""),
        "owner_mid": d.get("owner", {}).get("mid", 0),
        "url": f"https://www.bilibili.com/video/{bvid}",
        # 统计数据
        "views": stat.get("view", 0),
        "danmaku": stat.get("danmaku", 0),
        "likes": stat.get("like", 0),
        "coins": stat.get("coin", 0),
        "favorites": stat.get("favorite", 0),
        "shares": stat.get("share", 0),
        "comments_count": stat.get("reply", 0),
    }


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def cmd_register(args):
    """首次注册视频（抓取元数据 + 创建 D0 快照 + 创建 4 个 reminders）"""
    info = fetch_video_info(args.bvid)
    if not info:
        return 1

    conn = get_db()

    # 检查是否已存在
    existing = conn.execute(
        "SELECT id FROM videos WHERE platform=? AND platform_id=?",
        ("bilibili", info["bvid"]),
    ).fetchone()
    if existing:
        print(f"Video already registered (id={existing['id']})")
        conn.close()
        return 0

    # 插入视频主表
    cur = conn.execute(
        """INSERT INTO videos
           (platform, platform_id, title, publish_date, url, duration_sec,
            topic, target_audience, content_pillar, production_hours, hypothesis)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "bilibili",
            info["bvid"],
            info["title"],
            info["pubdate"],
            info["url"],
            info["duration"],
            args.topic,
            args.audience,
            args.pillar,
            args.hours,
            args.hypothesis,
        ),
    )
    video_id = cur.lastrowid

    # 创建 D0 快照
    interaction = (
        info["likes"] + info["coins"] + info["favorites"] + info["shares"] + info["comments_count"]
    )
    rate = interaction / info["views"] if info["views"] > 0 else 0

    conn.execute(
        """INSERT INTO snapshots
           (video_id, checkpoint, snapshot_date, views, likes, coins, favorites,
            shares, comments_count, danmaku, interaction_rate)
           VALUES (?, 'D0', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            video_id,
            date.today().isoformat(),
            info["views"],
            info["likes"],
            info["coins"],
            info["favorites"],
            info["shares"],
            info["comments_count"],
            info["danmaku"],
            rate,
        ),
    )

    # 创建 4 个 reminders
    pub_date = datetime.fromisoformat(info["pubdate"]).date()
    for days, checkpoint in [(7, "D7"), (30, "D30"), (60, "D60"), (90, "D90")]:
        due = pub_date + timedelta(days=days)
        conn.execute(
            """INSERT INTO reminders (video_id, checkpoint, due_date)
               VALUES (?, ?, ?)""",
            (video_id, checkpoint, due.isoformat()),
        )

    conn.commit()
    conn.close()

    print(f"Registered: {info['title'][:60]}")
    print(f"  Video ID: {video_id}")
    print(f"  Reminders created: D7={pub_date + timedelta(days=7)}, D30=..., D60=..., D90=...")
    print(f"\nNext step: gcal_sync to push reminders to Google Calendar")
    return 0


def cmd_snapshot(args):
    """抓取并保存数据快照"""
    info = fetch_video_info(args.bvid)
    if not info:
        return 1

    conn = get_db()

    video = conn.execute(
        "SELECT id FROM videos WHERE platform_id=?", (info["bvid"],)
    ).fetchone()
    if not video:
        print(f"Video not registered. Run 'register' first.", file=sys.stderr)
        conn.close()
        return 1

    video_id = video["id"]
    interaction = (
        info["likes"] + info["coins"] + info["favorites"] + info["shares"] + info["comments_count"]
    )
    rate = interaction / info["views"] if info["views"] > 0 else 0

    # 计算长尾增长（与 D7 对比）
    growth_since_d7 = None
    if args.checkpoint in ("D30", "D60", "D90"):
        d7 = conn.execute(
            "SELECT views FROM snapshots WHERE video_id=? AND checkpoint='D7'",
            (video_id,),
        ).fetchone()
        if d7 and d7["views"]:
            growth_since_d7 = info["views"] - d7["views"]

    conn.execute(
        """INSERT OR REPLACE INTO snapshots
           (video_id, checkpoint, snapshot_date, views, likes, coins, favorites,
            shares, comments_count, danmaku, interaction_rate, growth_since_d7)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            video_id,
            args.checkpoint,
            date.today().isoformat(),
            info["views"],
            info["likes"],
            info["coins"],
            info["favorites"],
            info["shares"],
            info["comments_count"],
            info["danmaku"],
            rate,
            growth_since_d7,
        ),
    )

    # 标记 reminder 为已完成
    conn.execute(
        "UPDATE reminders SET status='completed', completed_at=CURRENT_TIMESTAMP "
        "WHERE video_id=? AND checkpoint=?",
        (video_id, args.checkpoint),
    )

    conn.commit()
    conn.close()

    print(f"Snapshot saved: {args.bvid} @ {args.checkpoint}")
    print(f"  Views: {info['views']:,}")
    print(f"  Interaction rate: {rate*100:.2f}%")
    if growth_since_d7 is not None:
        print(f"  Growth since D7: +{growth_since_d7:,}")
    print(
        f"\nNext step: Manual fill - quality_comment_pct, dm_inquiries, traffic sources"
    )
    return 0


def cmd_pending(args):
    """列出待复盘的视频"""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM pending_reviews WHERE days_until_due <= ?""", (args.days,)
    ).fetchall()
    conn.close()

    if not rows:
        print("No pending reviews")
        return 0

    print(f"Pending reviews (within {args.days} days):\n")
    for r in rows:
        days = int(r["days_until_due"])
        marker = "OVERDUE" if days < 0 else f"in {days}d"
        print(
            f"  [{r['checkpoint']}] {r['platform_id']} | {r['title'][:50]} | due {r['due_date']} ({marker})"
        )
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_reg = sub.add_parser("register", help="Register a new video")
    p_reg.add_argument("--bvid", required=True)
    p_reg.add_argument("--topic", default="")
    p_reg.add_argument("--audience", default="")
    p_reg.add_argument("--pillar", default="")
    p_reg.add_argument("--hours", type=float, default=0)
    p_reg.add_argument("--hypothesis", default="")
    p_reg.set_defaults(func=cmd_register)

    p_snap = sub.add_parser("snapshot", help="Take a data snapshot")
    p_snap.add_argument("--bvid", required=True)
    p_snap.add_argument(
        "--checkpoint",
        required=True,
        choices=["D7", "D30", "D60", "D90", "AD_HOC"],
    )
    p_snap.set_defaults(func=cmd_snapshot)

    p_pending = sub.add_parser("pending", help="List pending reviews")
    p_pending.add_argument("--days", type=int, default=7, help="within N days")
    p_pending.set_defaults(func=cmd_pending)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
