#!/usr/bin/env bash
# Download audio for 4 Tier 1 accounts (57 videos each = 228 total)
set +e
export PYTHONIOENCODING=utf-8

OUT_DIR="c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04"
LOG="$OUT_DIR/batch_download.log"
> "$LOG"

SLUGS=(
  "tier1-programmer-yupi"
  "tier1-ezindie"
  "tier2-xiaolin-shuo"
  "tier2-wushi-finance"
)

cd "C:/Users/hangn/.claude/skills/bilibili-creator-dive" || exit 1

for slug in "${SLUGS[@]}"; do
  echo "[$(date +%H:%M:%S)] Downloading audio for $slug" | tee -a "$LOG"
  start=$(date +%s)
  python -m scripts.download_audio "$slug" --out "$OUT_DIR" >> "$LOG" 2>&1
  rc=$?
  end=$(date +%s)
  elapsed=$((end-start))
  # Count mp3 files in audio/ dir
  audio_dir="$OUT_DIR/$slug/audio"
  if [ -d "$audio_dir" ]; then
    count=$(find "$audio_dir" -name "*.mp3" -type f 2>/dev/null | wc -l)
    echo "[$(date +%H:%M:%S)] $slug done: $count mp3 files in ${elapsed}s (rc=$rc)" | tee -a "$LOG"
  else
    echo "[$(date +%H:%M:%S)] $slug FAIL: no audio dir (rc=$rc)" | tee -a "$LOG"
  fi
done

echo "[$(date +%H:%M:%S)] BATCH DOWNLOAD DONE" | tee -a "$LOG"
