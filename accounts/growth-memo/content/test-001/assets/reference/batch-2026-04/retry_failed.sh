#!/usr/bin/env bash
# Retry the 3 accounts that failed in the first batch run due to bili_api.py
# fail-all bug (single deleted/geo-restricted video aborted whole channel scrape).
# bili_api.py has been patched with --ignore-errors; this re-runs the failed 3.
set +e
export PYTHONIOENCODING=utf-8

OUT_DIR="c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04"
LOG="$OUT_DIR/retry_failed.log"
> "$LOG"

ACCOUNTS=(
  "12890453|tier1-programmer-yupi|程序员鱼皮"
  "395127673|tier1-ezindie|ezindie小产品变现"
  "520819684|tier2-xiaolin-shuo|小Lin说"
)

cd "C:/Users/hangn/.claude/skills/bilibili-creator-dive" || exit 1

i=0
total=${#ACCOUNTS[@]}
for entry in "${ACCOUNTS[@]}"; do
  i=$((i+1))
  IFS='|' read -r uid slug name <<< "$entry"
  echo "[$(date +%H:%M:%S)] [$i/$total] RETRY $name (UID=$uid, slug=$slug)" | tee -a "$LOG"
  start=$(date +%s)
  python -m scripts.probe_channel "https://space.bilibili.com/$uid" "$slug" --out "$OUT_DIR" --refresh >> "$LOG" 2>&1
  rc=$?
  end=$(date +%s)
  elapsed=$((end-start))
  if [ -f "$OUT_DIR/$slug/video_list.tsv" ]; then
    count=$(($(wc -l < "$OUT_DIR/$slug/video_list.tsv") - 1))
    if [ "$count" -gt 0 ]; then
      echo "[$(date +%H:%M:%S)] [$i/$total] OK $name -- $count videos in ${elapsed}s" | tee -a "$LOG"
    else
      echo "[$(date +%H:%M:%S)] [$i/$total] EMPTY $name -- 0 videos in ${elapsed}s" | tee -a "$LOG"
    fi
  else
    echo "[$(date +%H:%M:%S)] [$i/$total] FAIL $name -- exit=$rc, no tsv after ${elapsed}s" | tee -a "$LOG"
  fi
  sleep 5  # longer delay between large channels to be polite to B站
done

echo "[$(date +%H:%M:%S)] RETRY DONE" | tee -a "$LOG"
