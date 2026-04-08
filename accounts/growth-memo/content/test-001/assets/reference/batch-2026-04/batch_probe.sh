#!/usr/bin/env bash
# Batch probe 13 B站 accounts (袁小智 already done)
# Run from skill directory
set +e  # don't abort on individual failures
export PYTHONIOENCODING=utf-8

OUT_DIR="c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04"
LOG="$OUT_DIR/batch_probe.log"
> "$LOG"

# Format: UID|slug|account_name
ACCOUNTS=(
  "12890453|tier1-programmer-yupi|程序员鱼皮"
  "395127673|tier1-ezindie|ezindie小产品变现"
  "163637592|tier2-he-tongxue|老师好我叫何同学"
  "28860626|tier2-yihui-indiedev|Geek4Fun(原熠辉位置)"
  "351969226|tier2-weisheng-ai|未生AI"
  "1815948385|tier2-mark-tech|马克的技术工作坊"
  "520819684|tier2-xiaolin-shuo|小Lin说"
  "531838578|tier2-xiaoa-finance|小A学财经"
  "472747194|tier2-wushi-finance|巫师财经"
  "508709785|tier2-wuyifei|温义飞今天插旗了吗"
  "520155988|tier2-suozhang-linchao|所长林超"
  "26995758|tier3-dasheng|花果山-大圣"
)

cd "C:/Users/hangn/.claude/skills/bilibili-creator-dive" || exit 1

i=0
total=${#ACCOUNTS[@]}
for entry in "${ACCOUNTS[@]}"; do
  i=$((i+1))
  IFS='|' read -r uid slug name <<< "$entry"
  echo "[$(date +%H:%M:%S)] [$i/$total] Probing $name (UID=$uid, slug=$slug)" | tee -a "$LOG"
  start=$(date +%s)
  python -m scripts.probe_channel "https://space.bilibili.com/$uid" "$slug" --out "$OUT_DIR" --refresh >> "$LOG" 2>&1
  rc=$?
  end=$(date +%s)
  elapsed=$((end-start))
  if [ -f "$OUT_DIR/$slug/video_list.tsv" ]; then
    count=$(($(wc -l < "$OUT_DIR/$slug/video_list.tsv") - 1))
    echo "[$(date +%H:%M:%S)] [$i/$total] OK $name -- $count videos in ${elapsed}s" | tee -a "$LOG"
  else
    echo "[$(date +%H:%M:%S)] [$i/$total] FAIL $name -- exit=$rc, no video_list.tsv after ${elapsed}s" | tee -a "$LOG"
  fi
  # Small delay to avoid rate limit
  sleep 3
done

echo "[$(date +%H:%M:%S)] BATCH PROBE DONE" | tee -a "$LOG"
