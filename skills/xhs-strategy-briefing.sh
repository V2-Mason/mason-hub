#!/bin/bash
# xhs-strategy-briefing.sh — 已合并到 xhs-analyze.sh
# 保留此脚本做向后兼容，实际调用 xhs-analyze.sh --no-enrich
#
# 如需单独跑市场信号（不重跑分析），用这个脚本。
# 完整管道（含富化+趋势）请用 xhs-analyze.sh。

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
ANALYSIS_DIR="$MC_DIR/analysis"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh
TODAY=$(TZ='America/New_York' date '+%Y-%m-%d')

NO_SLACK=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-slack) NO_SLACK=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== XHS 市场信号（单独模式） ==="
echo "Time: $(TZ='America/New_York' date '+%Y-%m-%d %H:%M ET')"

log_event "xhs-strategy" "market-signals" "start" "Generating market signals (standalone)"

# --- 同步市场信号脚本 ---
echo ""
echo "--- Syncing market signals script ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/_xhs_strategy_briefing.py" "$ALIYUN:$MC_DIR/xhs_briefing.py"

# --- 找最新的分析 JSON（优先用 enriched 版本）---
LATEST_ENRICHED=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "ls -t $ANALYSIS_DIR/analysis_*_enriched.json 2>/dev/null | head -1" 2>/dev/null)
LATEST_BASE=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "ls -t $ANALYSIS_DIR/analysis_*.json 2>/dev/null | grep -v enriched | head -1" 2>/dev/null)

LATEST_ANALYSIS="${LATEST_ENRICHED:-$LATEST_BASE}"

if [ -z "$LATEST_ANALYSIS" ]; then
  echo "ERROR: 没有找到分析 JSON，请先跑 xhs-analyze.sh"
  log_event "xhs-strategy" "market-signals" "error" "No analysis JSON found"
  exit 1
fi

echo "Using analysis: $LATEST_ANALYSIS"

# --- 找趋势 JSON ---
TRENDS_ARG=""
LATEST_TRENDS=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "ls -t $ANALYSIS_DIR/trends/*.json 2>/dev/null | head -1" 2>/dev/null)
if [ -n "$LATEST_TRENDS" ]; then
  TRENDS_ARG="--trends '$LATEST_TRENDS'"
  echo "Using trends: $LATEST_TRENDS"
fi

# --- 生成市场信号 ---
echo ""
echo "--- Generating market signals ---"
BRIEFING_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python xhs_briefing.py '$LATEST_ANALYSIS' '$ANALYSIS_DIR' $TRENDS_ARG 2>&1")

BRIEFING_EXIT=$?
echo "$BRIEFING_OUTPUT"

if [ $BRIEFING_EXIT -ne 0 ]; then
  echo "ERROR: Market signals failed (exit $BRIEFING_EXIT)"
  log_event "xhs-strategy" "market-signals" "error" "Market signals failed (exit $BRIEFING_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 市场信号失败*: exit $BRIEFING_EXIT" "XHS Analyst" ":x:"
  exit 1
fi

log_event "xhs-strategy" "market-signals" "end" "Market signals generated from $LATEST_ANALYSIS"

# --- Slack 摘要 ---
if [ "$NO_SLACK" = false ]; then
  MSG="📋 *XHS 市场信号已更新* ($TODAY)
详见看板: http://106.14.44.68/xhs/
数据来源: $(basename "$LATEST_ANALYSIS")"
  notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Analyst" ":memo:"
  echo ""
  echo "Slack notified"
fi

echo ""
echo "=== Market Signals Complete ==="
