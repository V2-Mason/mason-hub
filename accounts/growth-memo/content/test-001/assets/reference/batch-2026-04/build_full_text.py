#!/usr/bin/env python3
"""Build full_text.txt from transcripts/*.json in the order of selected.tsv.

Format per clip:
    ==========
    <BV> | <YYYY-MM-DD> | <views formatted> | <M:SS>
    <title>
    ==========
    <full_text body>
    <blank line>

Usage:
    python build_full_text.py <slug>
"""
import sys
import csv
import json
from pathlib import Path

BATCH_ROOT = Path(
    r"c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04"
)


def fmt_date(raw: str) -> str:
    # "20250329" -> "2025-03-29"
    raw = str(raw)
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def fmt_duration(seconds) -> str:
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return str(seconds)
    m, sec = divmod(s, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def fmt_views(v) -> str:
    try:
        return f"{int(v):,} views"
    except (TypeError, ValueError):
        return f"{v} views"


def build(slug: str):
    slug_dir = BATCH_ROOT / slug
    selected_tsv = slug_dir / "selected.tsv"
    transcripts_dir = slug_dir / "transcripts"
    out_path = slug_dir / "full_text.txt"

    if not selected_tsv.exists():
        print(f"[{slug}] Missing {selected_tsv}", file=sys.stderr)
        sys.exit(1)
    if not transcripts_dir.exists():
        print(f"[{slug}] Missing {transcripts_dir}", file=sys.stderr)
        sys.exit(1)

    with open(selected_tsv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    lines = []
    used = 0
    missing = []
    for row in rows:
        bv = row["BV"]
        transcript_path = transcripts_dir / f"{bv}.json"
        if not transcript_path.exists():
            missing.append(bv)
            continue
        try:
            data = json.loads(transcript_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[{slug}] Failed to parse {transcript_path}: {e}", file=sys.stderr)
            missing.append(bv)
            continue

        title = row.get("title") or data.get("title", "")
        date = fmt_date(row.get("date") or data.get("date", ""))
        duration = fmt_duration(row.get("duration") or data.get("duration", 0))
        views = fmt_views(row.get("views") or data.get("views", 0))

        header = f"{bv} | {date} | {views} | {duration}"
        body = data.get("full_text", "").rstrip()

        lines.append("==========")
        lines.append(header)
        lines.append(title)
        lines.append("==========")
        lines.append(body)
        lines.append("")  # blank line between clips
        used += 1

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total_lines = out_path.read_text(encoding="utf-8").count("\n")
    print(f"[{slug}] Wrote {out_path}")
    print(f"[{slug}] Clips: {used}/{len(rows)} (missing={len(missing)}) lines={total_lines}")
    if missing:
        print(f"[{slug}] Missing: {missing}", file=sys.stderr)
    return used, len(rows), total_lines


def main():
    if len(sys.argv) != 2:
        print("Usage: python build_full_text.py <slug>", file=sys.stderr)
        sys.exit(2)
    build(sys.argv[1])


if __name__ == "__main__":
    main()
