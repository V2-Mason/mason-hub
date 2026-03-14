#!/usr/bin/env python3
"""content-performance.py — 内容效果追踪

五维 Gap #1（感知-数据回流）：发了内容看不到效果。
输入：平台 + 时间范围
输出：JSON 指标报告

用法：
  python3 skills/analytics/content-performance.py --platform xhs --days 7
  python3 skills/analytics/content-performance.py --platform all --days 30
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
MIRROR_DIR = HUB_DIR / "data" / "mirrors"
ANALYSIS_DIR = HUB_DIR / "data" / "reports"


def get_xhs_performance(days: int) -> dict:
    """从 XHS 采集数据中提取内容表现指标"""
    db_path = MIRROR_DIR / "xhs_notes.db"
    if not db_path.exists():
        # fallback: 从分析 JSON 读取
        return _get_xhs_from_analysis(days)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        rows = conn.execute(
            "SELECT * FROM notes WHERE collected_at >= ? ORDER BY interaction_score DESC",
            (cutoff,)
        ).fetchall()

        if not rows:
            return {"platform": "xhs", "status": "no_data", "days": days}

        total = len(rows)
        metrics = {
            "platform": "xhs",
            "days": days,
            "total_notes": total,
            "avg_likes": sum(r["likes"] for r in rows) / total if total else 0,
            "avg_comments": sum(r["comments"] for r in rows) / total if total else 0,
            "avg_collects": sum(r["collects"] for r in rows) / total if total else 0,
            "top_5": [
                {
                    "title": r["title"][:50],
                    "likes": r["likes"],
                    "comments": r["comments"],
                    "collects": r["collects"],
                    "interaction_score": r.get("interaction_score", 0),
                }
                for r in rows[:5]
            ],
        }
        return metrics
    except Exception as e:
        return {"platform": "xhs", "error": str(e)}
    finally:
        conn.close()


def _get_xhs_from_analysis(days: int) -> dict:
    """从最近的分析 JSON 文件读取（无 DB 时的 fallback）"""
    analysis_dir = Path(os.path.expanduser("~/mason-hub/data/reports"))
    json_files = sorted(analysis_dir.glob("**/xhs_*.json"), reverse=True)

    if not json_files:
        # 尝试阿里云 mirror
        mirror_json = sorted(
            (MIRROR_DIR / "analysis").glob("*.json"), reverse=True
        ) if (MIRROR_DIR / "analysis").exists() else []
        json_files = mirror_json

    if not json_files:
        return {"platform": "xhs", "status": "no_analysis_data", "days": days}

    try:
        with open(json_files[0]) as f:
            data = json.load(f)

        notes = data if isinstance(data, list) else data.get("notes", data.get("results", []))
        total = len(notes)

        return {
            "platform": "xhs",
            "days": days,
            "source": str(json_files[0].name),
            "total_notes": total,
            "avg_likes": sum(n.get("likes", 0) for n in notes) / total if total else 0,
            "avg_comments": sum(n.get("comments", 0) for n in notes) / total if total else 0,
            "top_3": [
                {"title": n.get("title", "")[:50], "likes": n.get("likes", 0)}
                for n in sorted(notes, key=lambda x: x.get("likes", 0), reverse=True)[:3]
            ],
        }
    except Exception as e:
        return {"platform": "xhs", "error": str(e)}


def get_socialmesh_performance(days: int) -> dict:
    """从 SocialMesh DB 读取发布效果"""
    db_path = Path(os.path.expanduser("~/socialmesh/data/socialmesh.db"))
    if not db_path.exists():
        return {"platform": "socialmesh", "status": "db_not_found"}

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        posts = conn.execute(
            "SELECT * FROM platform_posts WHERE created_at >= ?", (cutoff,)
        ).fetchall()

        contents = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM contents WHERE created_at >= ? GROUP BY status",
            (cutoff,)
        ).fetchall()

        conn.close()

        return {
            "platform": "socialmesh",
            "days": days,
            "posts_total": len(posts),
            "posts_success": sum(1 for p in posts if p["status"] == "published"),
            "posts_failed": sum(1 for p in posts if p["status"] == "failed"),
            "content_status": {r["status"]: r["cnt"] for r in contents},
        }
    except Exception as e:
        return {"platform": "socialmesh", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="内容效果追踪")
    parser.add_argument("--platform", default="all", choices=["xhs", "socialmesh", "all"])
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    args = parser.parse_args()

    report = {"generated_at": datetime.now().isoformat(), "period_days": args.days, "platforms": []}

    if args.platform in ("xhs", "all"):
        report["platforms"].append(get_xhs_performance(args.days))

    if args.platform in ("socialmesh", "all"):
        report["platforms"].append(get_socialmesh_performance(args.days))

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== 内容效果报告 ({args.days}天) ===")
        for p in report["platforms"]:
            platform = p.get("platform", "?")
            if "error" in p:
                print(f"\n{platform}: 错误 - {p['error']}")
            elif p.get("status") in ("no_data", "no_analysis_data", "db_not_found"):
                print(f"\n{platform}: 无数据")
            else:
                print(f"\n{platform}:")
                print(f"  总数: {p.get('total_notes', p.get('posts_total', 0))}")
                if "avg_likes" in p:
                    print(f"  平均点赞: {p['avg_likes']:.0f}")
                if "posts_success" in p:
                    print(f"  发布成功: {p['posts_success']}/{p['posts_total']}")


if __name__ == "__main__":
    main()
