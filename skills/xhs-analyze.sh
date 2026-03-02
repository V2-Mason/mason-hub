#!/bin/bash
# xhs-analyze.sh — XHS 数据分析调度器
# 用法: xhs-analyze.sh [--no-slack]
#
# 流程:
# 1. SCP 分析脚本到阿里云
# 2. 在阿里云跑分析（数据不出境）
# 3. JSON 结果存阿里云 /opt/mediacrawler/analysis/
# 4. 文字摘要推 Slack #socialmesh

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

echo "=== XHS 数据分析 ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

log_event "xhs-analysis" "weekly-analysis" "start" "Starting analysis"

# --- 确保分析目录存在 ---
ssh -o ConnectTimeout=10 "$ALIYUN" "mkdir -p $ANALYSIS_DIR" 2>/dev/null

# --- 同步分析脚本（避免 SSH heredoc 嵌 Python 的转义问题）---
echo ""
echo "--- Syncing analysis script ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs-analyze-viral.py" "$ALIYUN:$MC_DIR/xhs_analyze.py"

# --- 检查数据库 ---
NOTE_COUNT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "sqlite3 $MC_DIR/database/sqlite_tables.db 'SELECT COUNT(*) FROM xhs_note'" 2>/dev/null || echo "0")

if [ "$NOTE_COUNT" -eq 0 ]; then
  echo "SKIP: 数据库为空"
  log_event "xhs-analysis" "weekly-analysis" "info" "Skipped: empty database"
  exit 0
fi

echo "Notes in DB: $NOTE_COUNT"

# --- 跑分析 ---
JSON_OUT="$ANALYSIS_DIR/analysis_${TODAY}.json"

echo ""
echo "--- Running analysis ---"
ANALYSIS_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python xhs_analyze.py --json-out '$JSON_OUT' 2>&1")

ANALYSIS_EXIT=$?
echo "$ANALYSIS_OUTPUT"

if [ $ANALYSIS_EXIT -ne 0 ]; then
  echo "ERROR: Analysis failed (exit $ANALYSIS_EXIT)"
  log_event "xhs-analysis" "weekly-analysis" "error" "Analysis failed (exit $ANALYSIS_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 分析失败*: exit $ANALYSIS_EXIT" "XHS Analyst" ":x:"
  exit 1
fi

log_event "xhs-analysis" "weekly-analysis" "end" "Analysis done, $NOTE_COUNT notes, output: $JSON_OUT"

# --- Slack 摘要（用独立 .py 避免 SSH 引号转义问题）---
if [ "$NO_SLACK" = false ]; then
  scp -o ConnectTimeout=10 "$HUB_DIR/skills/_xhs_slack_summary.py" "$ALIYUN:$MC_DIR/_slack_summary.py" 2>/dev/null
  SUMMARY=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
    "cd $MC_DIR && source venv/bin/activate && python _slack_summary.py '$JSON_OUT'" 2>/dev/null)

  if [ -n "$SUMMARY" ]; then
    MSG="📊 *XHS 数据分析完成* ($TODAY)
$SUMMARY"
    notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Analyst" ":bar_chart:"
    echo ""
    echo "Slack notified"
  fi
fi

echo ""
echo "=== Analysis Complete ==="
