#!/usr/bin/env python3
"""T19+M19+B19 sampler for video_list.tsv.

Selects 19 Top / 19 Mid / 19 Bottom videos by view count for grid analysis.
- Excludes videos < 60s (sub-clips) and > 7200s (livestream replays)
- Writes selected.tsv with same schema as video_list.tsv (BV, title, duration, date, views)

Usage:
    python sample_tmb.py <slug>
"""
import sys
import csv
from pathlib import Path

BATCH_ROOT = Path(r"c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04")

MIN_DURATION_S = 60
MAX_DURATION_S = 7200


def load_videos(slug: str) -> list[dict]:
    path = BATCH_ROOT / slug / "video_list.tsv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")

    videos = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                duration = int(row["duration"])
                views = int(row["views"])
            except (ValueError, KeyError):
                continue
            if duration < MIN_DURATION_S or duration > MAX_DURATION_S:
                continue
            videos.append({
                "BV": row["BV"],
                "title": row["title"],
                "duration": duration,
                "date": row["date"],
                "views": views,
            })
    return videos


def sample_tmb(videos: list[dict]) -> dict:
    """Select Top 19, Bot 19, Mid 19 by view count."""
    if len(videos) < 57:
        raise ValueError(f"Need >=57 videos after filtering, got {len(videos)}")

    sorted_v = sorted(videos, key=lambda v: v["views"], reverse=True)
    n = len(sorted_v)
    top = sorted_v[:19]  # highest 19
    bot = sorted_v[-19:]  # lowest 19
    # Mid = 19 centered around median
    mid_start = (n - 19) // 2
    mid = sorted_v[mid_start:mid_start + 19]
    return {"top": top, "mid": mid, "bot": bot}


def write_selected(slug: str, samples: dict) -> Path:
    out = BATCH_ROOT / slug / "selected.tsv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["BV", "title", "duration", "date", "views", "bucket"])
        for bucket in ("top", "mid", "bot"):
            for v in samples[bucket]:
                w.writerow([v["BV"], v["title"], v["duration"], v["date"], v["views"], bucket])
    return out


def main():
    if len(sys.argv) != 2:
        print("Usage: python sample_tmb.py <slug>", file=sys.stderr)
        sys.exit(2)
    slug = sys.argv[1]

    videos = load_videos(slug)
    print(f"Loaded {len(videos)} videos (after duration filter)")

    samples = sample_tmb(videos)
    out = write_selected(slug, samples)

    print(f"Wrote {out}")
    print(f"  Top 19: views {samples['top'][-1]['views']:,} - {samples['top'][0]['views']:,}")
    print(f"  Mid 19: views {samples['mid'][-1]['views']:,} - {samples['mid'][0]['views']:,}")
    print(f"  Bot 19: views {samples['bot'][-1]['views']:,} - {samples['bot'][0]['views']:,}")


if __name__ == "__main__":
    main()
