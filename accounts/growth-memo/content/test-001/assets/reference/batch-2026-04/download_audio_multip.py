#!/usr/bin/env python3
"""Multi-P aware audio downloader wrapper for Tier 2/3 batch.

Reads <slug>/selected.tsv, downloads each mp3 into <slug>/audio/.
Handles BV_pN suffix by constructing ?p=N URL and forcing explicit filename.

This is a local wrapper that fixes a gap in the upstream skill's download_audio.py
(which uses %(id)s output template and does not understand _pN).

Usage:
    python download_audio_multip.py <slug>
"""
import csv
import subprocess
import sys
from pathlib import Path

BATCH_ROOT = Path(r"c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04")
COOKIES = Path(r"C:/Users/hangn/.claude/skills/bilibili-creator-dive/cookies.txt")
MIN_VALID_MP3_BYTES = 50_000
YTDLP_RETRIES = 3


def bv_to_url(bv: str) -> str:
    if "_p" in bv:
        base, _, part = bv.rpartition("_p")
        try:
            int(part)
            return f"https://www.bilibili.com/video/{base}?p={part}"
        except ValueError:
            pass
    return f"https://www.bilibili.com/video/{bv}"


def should_skip(mp3_path: Path) -> bool:
    return mp3_path.exists() and mp3_path.stat().st_size > MIN_VALID_MP3_BYTES


def run_ytdlp(bv: str, audio_dir: Path) -> tuple[int, str]:
    url = bv_to_url(bv)
    output_template = str(audio_dir / f"{bv}.%(ext)s")
    cmd = [
        "yt-dlp",
        "--cookies", str(COOKIES),
        "-f", "bestaudio",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "--retries", str(YTDLP_RETRIES),
        "-o", output_template,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stderr or ""


def main():
    if len(sys.argv) != 2:
        print("Usage: python download_audio_multip.py <slug>", file=sys.stderr)
        sys.exit(2)
    slug = sys.argv[1]

    if not COOKIES.exists():
        print(f"FATAL: cookies.txt not found at {COOKIES}", file=sys.stderr)
        sys.exit(2)

    cdir = BATCH_ROOT / slug
    selected_path = cdir / "selected.tsv"
    if not selected_path.exists():
        print(f"FATAL: {selected_path} not found", file=sys.stderr)
        sys.exit(2)

    audio_dir = cdir / "audio"
    audio_dir.mkdir(exist_ok=True)
    error_log = cdir / "download_errors.log"

    with open(selected_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    total = len(rows)
    ok = 0
    skipped = 0
    failed = 0

    for i, row in enumerate(rows, 1):
        bv = row["BV"]
        mp3 = audio_dir / f"{bv}.mp3"
        if should_skip(mp3):
            print(f"[{i}/{total}] SKIP {bv} (already downloaded)")
            skipped += 1
            continue

        print(f"[{i}/{total}] downloading {bv}...")
        rc, stderr = run_ytdlp(bv, audio_dir)
        if rc == 0 and should_skip(mp3):
            print(f"[{i}/{total}] OK {bv}")
            ok += 1
            continue

        failed += 1
        msg = (stderr or "").replace("\n", " | ")[:240]
        print(f"[{i}/{total}] FAIL {bv}: rc={rc} {msg}", file=sys.stderr)
        with open(error_log, "a", encoding="utf-8") as logf:
            logf.write(f"{bv}\tdownload_fail\t{msg}\n")

    print(f"Done. {ok} succeeded, {skipped} skipped, {failed} failed of {total}.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
