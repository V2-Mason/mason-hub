#!/usr/bin/env python3
"""Top 10 sampler for video_list.tsv.

Selects the top 10 videos by view count for hook analysis (Tier 2/3 accounts).
- Excludes videos < 60s (sub-clips) and > 7200s (livestream replays)
- If fewer than 10 pass the filter, takes all of them
- Writes selected.tsv with schema matching sample_tmb.py output (bucket=top)

Usage:
    python sample_top10.py <slug>
"""
import sys
import csv
from pathlib import Path

BATCH_ROOT = Path(r"c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04")

MIN_DURATION_S = 60
MAX_DURATION_S = 7200
TOP_N = 10


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


def pick_top(videos: list[dict], n: int = TOP_N) -> list[dict]:
    sorted_v = sorted(videos, key=lambda v: v["views"], reverse=True)
    return sorted_v[:n]


def write_selected(slug: str, top: list[dict]) -> Path:
    out = BATCH_ROOT / slug / "selected.tsv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["BV", "title", "duration", "date", "views", "bucket"])
        for v in top:
            w.writerow([v["BV"], v["title"], v["duration"], v["date"], v["views"], "top"])
    return out


def main():
    if len(sys.argv) != 2:
        print("Usage: python sample_top10.py <slug>", file=sys.stderr)
        sys.exit(2)
    slug = sys.argv[1]

    videos = load_videos(slug)
    print(f"[{slug}] Loaded {len(videos)} videos (after duration filter)")

    if not videos:
        print(f"[{slug}] No videos pass filter, aborting", file=sys.stderr)
        sys.exit(1)

    top = pick_top(videos)
    out = write_selected(slug, top)

    lo = top[-1]["views"]
    hi = top[0]["views"]
    print(f"[{slug}] Wrote {out}")
    print(f"[{slug}] Selected {len(top)} (of requested {TOP_N}): views {lo:,} - {hi:,}")


if __name__ == "__main__":
    main()
