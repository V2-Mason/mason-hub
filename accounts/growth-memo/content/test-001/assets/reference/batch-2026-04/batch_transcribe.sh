#!/usr/bin/env bash
# Whisper Vulkan GPU transcription for 4 Tier 1 accounts
# 221 mp3 files total (56+51+57+57)
set +e
export PYTHONIOENCODING=utf-8

OUT_DIR="c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04"
LOG="$OUT_DIR/batch_transcribe.log"
> "$LOG"

SLUGS=(
  "tier1-programmer-yupi"
  "tier1-ezindie"
  "tier2-xiaolin-shuo"
  "tier2-wushi-finance"
)

cd "C:/Users/hangn/.claude/skills/bilibili-creator-dive" || exit 1

for slug in "${SLUGS[@]}"; do
  echo "[$(date +%H:%M:%S)] Transcribing $slug" | tee -a "$LOG"
  start=$(date +%s)
  python -m scripts.transcribe_whispercpp "$slug" --out "$OUT_DIR" >> "$LOG" 2>&1
  rc=$?
  end=$(date +%s)
  elapsed=$((end-start))
  tr_dir="$OUT_DIR/$slug/transcripts"
  if [ -d "$tr_dir" ]; then
    count=$(find "$tr_dir" -name "*.json" -type f 2>/dev/null | wc -l)
    echo "[$(date +%H:%M:%S)] $slug done: $count json files in ${elapsed}s (rc=$rc)" | tee -a "$LOG"
  else
    echo "[$(date +%H:%M:%S)] $slug FAIL: no transcripts dir (rc=$rc)" | tee -a "$LOG"
  fi
done

echo "[$(date +%H:%M:%S)] BATCH TRANSCRIBE DONE" | tee -a "$LOG"
