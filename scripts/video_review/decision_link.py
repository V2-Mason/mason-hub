#!/usr/bin/env python3
"""
mason-decision-system 闭环 - 关联视频和决策记录

工作流：
1. Mason 用 mason-decision-system 做赛道决策 → 写到 ~/vault/decisions/YYYY-MM-DD-xxx.md
2. 发了视频后，用本工具关联：link --video-id 1 --decision-file ...
3. D90 自动验证：validate --video-id 1
4. 验证结果自动写回 ~/vault/decisions/...md 末尾

用法:
  # 关联
  python scripts/video_review/decision_link.py link \
      --video-id 1 --decision-file ~/vault/decisions/2026-04-06-ai-编程实战.md \
      --hypothesis "AI编程实战是冷门高潜赛道"

  # D90 验证
  python scripts/video_review/decision_link.py validate --video-id 1
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/data/video-reviews/reviews.db")


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def cmd_link(args):
    conn = get_db()
    conn.execute(
        """INSERT INTO decision_links
           (video_id, decision_record_path, decision_title, hypothesis, expected_outcome)
           VALUES (?, ?, ?, ?, ?)""",
        (
            args.video_id,
            args.decision_file,
            args.title or "",
            args.hypothesis,
            args.expected or "",
        ),
    )
    # 同时更新 videos 表的冗余字段方便查询
    conn.execute(
        "UPDATE videos SET hypothesis=? WHERE id=?",
        (args.hypothesis, args.video_id),
    )
    conn.commit()
    conn.close()
    print(f"Linked video {args.video_id} to {args.decision_file}")
    return 0


def cmd_validate(args):
    """D90 自动验证决策"""
    conn = get_db()

    # 拿 D90 快照
    snap = conn.execute(
        """SELECT s.*, v.title, v.target_audience
           FROM snapshots s
           JOIN videos v ON s.video_id = v.id
           WHERE s.video_id=? AND s.checkpoint='D90'""",
        (args.video_id,),
    ).fetchone()

    if not snap:
        print(f"No D90 snapshot found for video {args.video_id}", file=sys.stderr)
        conn.close()
        return 1

    # 拿 D7 快照（计算长尾比）
    d7 = conn.execute(
        "SELECT views FROM snapshots WHERE video_id=? AND checkpoint='D7'",
        (args.video_id,),
    ).fetchone()

    # 拿 decision_link
    link = conn.execute(
        "SELECT * FROM decision_links WHERE video_id=?",
        (args.video_id,),
    ).fetchone()

    if not link:
        print(f"No decision link found for video {args.video_id}", file=sys.stderr)
        conn.close()
        return 1

    # === D90 默认验证规则 ===
    quality_pct = (snap["quality_comment_pct"] or 0)
    interaction = (snap["interaction_rate"] or 0)
    fans = (snap["followers_from_video"] or 0)
    long_tail_ratio = (
        (snap["views"] or 0) / d7["views"]
        if d7 and d7["views"]
        else 0
    )

    checks = {
        "quality_comment_pct >= 0.30": quality_pct >= 0.30,
        "long_tail_ratio >= 1.5x": long_tail_ratio >= 1.5,
        "fans_from_video >= 50": fans >= 50,
        "interaction_rate >= 0.05": interaction >= 0.05,
    }

    passed = sum(1 for v in checks.values() if v)

    if passed == 4:
        result = "confirmed"
    elif passed >= 2:
        result = "partial"
    else:
        result = "rejected"

    evidence_lines = [
        f"- 优质评论比: {quality_pct*100:.1f}% ({'PASS' if checks['quality_comment_pct >= 0.30'] else 'FAIL'})",
        f"- 长尾比: {long_tail_ratio:.2f}x ({'PASS' if checks['long_tail_ratio >= 1.5x'] else 'FAIL'})",
        f"- 累计涨粉: {fans} ({'PASS' if checks['fans_from_video >= 50'] else 'FAIL'})",
        f"- 互动率: {interaction*100:.2f}% ({'PASS' if checks['interaction_rate >= 0.05'] else 'FAIL'})",
        f"- **{passed}/4 通过 → {result}**",
    ]
    evidence = "\n".join(evidence_lines)

    # 更新数据库
    conn.execute(
        """UPDATE decision_links
           SET validated_at=CURRENT_TIMESTAMP,
               validation_result=?,
               validation_evidence=?
           WHERE video_id=?""",
        (result, evidence, args.video_id),
    )
    conn.commit()
    conn.close()

    # 输出（skill 会用这个内容写回决策文件）
    print(f"=== Validation Result for video {args.video_id} ===")
    print(f"Hypothesis: {link['hypothesis']}")
    print(f"Result: {result}")
    print(f"\nEvidence:")
    print(evidence)
    print(f"\nDecision file to update: {link['decision_record_path']}")
    print(f"\n--- Markdown to append ---")
    today = datetime.now().date().isoformat()
    print(f"""
## D90 Validation Result ({today}) - by video-review skill

**Hypothesis**: {link['hypothesis']}
**Validation Video**: {snap['title']}
**Result**: **{result}**

### Evidence
{evidence}

### Mason's Notes
（手动补充教训和下一步）
""")
    return 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p1 = sub.add_parser("link")
    p1.add_argument("--video-id", type=int, required=True)
    p1.add_argument("--decision-file", required=True)
    p1.add_argument("--title")
    p1.add_argument("--hypothesis", required=True)
    p1.add_argument("--expected")
    p1.set_defaults(func=cmd_link)

    p2 = sub.add_parser("validate")
    p2.add_argument("--video-id", type=int, required=True)
    p2.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
