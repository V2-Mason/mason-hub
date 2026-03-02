#!/bin/bash
# xhs-strategy-briefing.sh — XHS 策略简报生成
# 用法: xhs-strategy-briefing.sh [--no-slack]
#
# 流程:
# 1. SCP 策略简报脚本到阿里云
# 2. 读取最新的分析 JSON → 生成策略简报
# 3. 简报存阿里云 /opt/mediacrawler/analysis/briefings/
# 4. Slack 推送摘要

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
ANALYSIS_DIR="$MC_DIR/analysis"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh
TODAY=$(TZ=Asia/Shanghai date '+%Y-%m-%d')

NO_SLACK=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-slack) NO_SLACK=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== XHS 策略简报 ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

log_event "xhs-strategy" "briefing" "start" "Generating briefing"

# --- 同步策略简报脚本 ---
echo ""
echo "--- Syncing briefing script ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/_xhs_strategy_briefing.py" "$ALIYUN:$MC_DIR/xhs_briefing.py"

# --- 找最新的分析 JSON ---
LATEST_ANALYSIS=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "ls -t $ANALYSIS_DIR/analysis_*.json 2>/dev/null | head -1" 2>/dev/null)

if [ -z "$LATEST_ANALYSIS" ]; then
  echo "ERROR: 没有找到分析 JSON，请先跑 xhs-analyze.sh"
  log_event "xhs-strategy" "briefing" "error" "No analysis JSON found"
  exit 1
fi

echo "Using analysis: $LATEST_ANALYSIS"

# --- 生成策略简报 ---
echo ""
echo "--- Generating briefing ---"
BRIEFING_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python xhs_briefing.py '$LATEST_ANALYSIS' '$ANALYSIS_DIR' 2>&1")

BRIEFING_EXIT=$?
echo "$BRIEFING_OUTPUT"

if [ $BRIEFING_EXIT -ne 0 ]; then
  echo "ERROR: Briefing failed (exit $BRIEFING_EXIT)"
  log_event "xhs-strategy" "briefing" "error" "Briefing failed (exit $BRIEFING_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 策略简报失败*: exit $BRIEFING_EXIT" "XHS Strategy" ":x:"
  exit 1
fi

log_event "xhs-strategy" "briefing" "end" "Briefing generated from $LATEST_ANALYSIS"

# --- Slack 摘要 ---
if [ "$NO_SLACK" = false ]; then
  # 从简报脚本输出中提取关键信息（它已经打印了人类可读的摘要）
  # 只推送简短通知
  MSG="📋 *XHS 策略简报已生成* ($TODAY)
详见阿里云: $ANALYSIS_DIR/briefings/$TODAY.json
数据来源: $LATEST_ANALYSIS"
  notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Strategy" ":memo:"
  echo ""
  echo "Slack notified"
fi

echo ""
echo "=== Briefing Complete ==="
