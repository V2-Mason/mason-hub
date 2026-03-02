#!/bin/bash
# xhs-analyze.sh — XHS 市场信号管道
# 用法: xhs-analyze.sh [--no-slack] [--no-enrich] [--enrich-top-n 3]
#
# 流程:
# 1. SCP 脚本到阿里云 → 跑分析 → analysis_YYYY-MM-DD.json
# 2. (可选) 粉丝量富化 → analysis_YYYY-MM-DD_enriched.json
# 3. (可选) 趋势对比 → trends/YYYY-MM-DD.json
# 4. 市场信号生成 → briefings/YYYY-MM-DD.json
# 5. Slack 摘要

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
ANALYSIS_DIR="$MC_DIR/analysis"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh
TODAY=$(TZ=Asia/Shanghai date '+%Y-%m-%d')

NO_SLACK=false
NO_ENRICH=false
ENRICH_TOP_N=20
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-slack) NO_SLACK=true; shift ;;
    --no-enrich) NO_ENRICH=true; shift ;;
    --enrich-top-n) ENRICH_TOP_N="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== XHS 市场信号管道 ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

log_event "xhs-analysis" "market-signals" "start" "Starting market signals pipeline"

# --- 确保目录存在 ---
ssh -o ConnectTimeout=10 "$ALIYUN" "mkdir -p $ANALYSIS_DIR/briefings $ANALYSIS_DIR/trends" 2>/dev/null

# === STEP 1: 基础分析 ===
echo ""
echo "--- [1/4] Syncing & running analysis ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs-analyze-viral.py" "$ALIYUN:$MC_DIR/xhs_analyze.py"

NOTE_COUNT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "sqlite3 $MC_DIR/database/sqlite_tables.db 'SELECT COUNT(*) FROM xhs_note'" 2>/dev/null || echo "0")

if [ "$NOTE_COUNT" -eq 0 ]; then
  echo "SKIP: 数据库为空"
  log_event "xhs-analysis" "market-signals" "info" "Skipped: empty database"
  exit 0
fi

echo "Notes in DB: $NOTE_COUNT"

JSON_OUT="$ANALYSIS_DIR/analysis_${TODAY}.json"

ANALYSIS_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python xhs_analyze.py --json-out '$JSON_OUT' 2>&1")

ANALYSIS_EXIT=$?
echo "$ANALYSIS_OUTPUT"

if [ $ANALYSIS_EXIT -ne 0 ]; then
  echo "ERROR: Analysis failed (exit $ANALYSIS_EXIT)"
  log_event "xhs-analysis" "market-signals" "error" "Analysis failed (exit $ANALYSIS_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 分析失败*: exit $ANALYSIS_EXIT" "XHS Analyst" ":x:"
  exit 1
fi

log_event "xhs-analysis" "market-signals" "info" "Base analysis done: $JSON_OUT"

# Track which JSON to feed into market signals (base or enriched)
SIGNAL_INPUT="$JSON_OUT"

# === STEP 2: 粉丝量富化 (可选，非阻塞) ===
if [ "$NO_ENRICH" = false ]; then
  echo ""
  echo "--- [2/4] Creator enrichment (top $ENRICH_TOP_N) ---"
  scp -o ConnectTimeout=10 "$HUB_DIR/skills/_xhs_enrich_creators.py" "$ALIYUN:$MC_DIR/_enrich_creators.py" 2>/dev/null

  ENRICH_OUTPUT=$(ssh -o ConnectTimeout=60 -o ServerAliveInterval=60 "$ALIYUN" \
    "cd $MC_DIR && source venv/bin/activate && python _enrich_creators.py '$JSON_OUT' --top-n $ENRICH_TOP_N 2>&1")

  ENRICH_EXIT=$?
  echo "$ENRICH_OUTPUT"

  ENRICHED_JSON="${JSON_OUT%.json}_enriched.json"
  if [ $ENRICH_EXIT -eq 0 ]; then
    # Check if enriched file exists on remote
    ENRICHED_EXISTS=$(ssh -o ConnectTimeout=10 "$ALIYUN" "test -f '$ENRICHED_JSON' && echo yes || echo no" 2>/dev/null)
    if [ "$ENRICHED_EXISTS" = "yes" ]; then
      SIGNAL_INPUT="$ENRICHED_JSON"
      echo "Enrichment OK, using enriched JSON"
      log_event "xhs-analysis" "market-signals" "info" "Enrichment done: $ENRICHED_JSON"
    else
      echo "Enrichment ran but no enriched file found, using base JSON"
    fi
  elif [ $ENRICH_EXIT -eq 3 ]; then
    echo "Enrichment skipped (no data to enrich), using base JSON"
  else
    echo "WARNING: Enrichment failed (exit $ENRICH_EXIT), continuing with base JSON"
    log_event "xhs-analysis" "market-signals" "info" "Enrichment failed (exit $ENRICH_EXIT), non-blocking"
  fi
else
  echo ""
  echo "--- [2/4] Creator enrichment: SKIPPED (--no-enrich) ---"
fi

# === STEP 3: 趋势对比 (可选，非阻塞) ===
echo ""
echo "--- [3/4] Trend comparison ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs-trend-compare.py" "$ALIYUN:$MC_DIR/_trend_compare.py" 2>/dev/null

TREND_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python _trend_compare.py '$JSON_OUT' 2>&1")

TREND_EXIT=$?
echo "$TREND_OUTPUT"

TRENDS_JSON="$ANALYSIS_DIR/trends/${TODAY}.json"
TRENDS_ARG=""
if [ $TREND_EXIT -eq 0 ]; then
  TRENDS_EXISTS=$(ssh -o ConnectTimeout=10 "$ALIYUN" "test -f '$TRENDS_JSON' && echo yes || echo no" 2>/dev/null)
  if [ "$TRENDS_EXISTS" = "yes" ]; then
    TRENDS_ARG="--trends '$TRENDS_JSON'"
    echo "Trend comparison OK"
    log_event "xhs-analysis" "market-signals" "info" "Trends done: $TRENDS_JSON"
  fi
else
  echo "WARNING: Trend comparison failed (exit $TREND_EXIT), continuing without trends"
fi

# === STEP 4: 市场信号 ===
echo ""
echo "--- [4/4] Market signals ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/_xhs_strategy_briefing.py" "$ALIYUN:$MC_DIR/xhs_briefing.py" 2>/dev/null

BRIEFING_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python xhs_briefing.py '$SIGNAL_INPUT' '$ANALYSIS_DIR' $TRENDS_ARG 2>&1")

BRIEFING_EXIT=$?
echo "$BRIEFING_OUTPUT"

if [ $BRIEFING_EXIT -ne 0 ]; then
  echo "ERROR: Market signals failed (exit $BRIEFING_EXIT)"
  log_event "xhs-analysis" "market-signals" "error" "Market signals failed (exit $BRIEFING_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 市场信号失败*: exit $BRIEFING_EXIT" "XHS Analyst" ":x:"
  exit 1
fi

log_event "xhs-analysis" "market-signals" "end" "Pipeline done, $NOTE_COUNT notes"

# === SLACK 摘要 ===
if [ "$NO_SLACK" = false ]; then
  scp -o ConnectTimeout=10 "$HUB_DIR/skills/_xhs_slack_summary.py" "$ALIYUN:$MC_DIR/_slack_summary.py" 2>/dev/null
  SUMMARY=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
    "cd $MC_DIR && source venv/bin/activate && python _slack_summary.py '$SIGNAL_INPUT'" 2>/dev/null)

  if [ -n "$SUMMARY" ]; then
    MSG="📊 *XHS 市场信号更新* ($TODAY)
$SUMMARY"
    notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Analyst" ":bar_chart:"
    echo ""
    echo "Slack notified"
  fi
fi

echo ""
echo "=== Pipeline Complete ==="
