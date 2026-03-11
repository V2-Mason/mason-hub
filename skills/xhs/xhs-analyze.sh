#!/bin/bash
# xhs-analyze.sh — XHS 市场信号管道
# 用法: xhs-analyze.sh [--project <id>] [--no-slack] [--no-enrich] [--no-comments] [--enrich-top-n 3] [--comment-top-n 10]
#
# --project: 从 projects.json 读取关键词，输出到 projects/{id}/xhs/
#            不传则全量分析 + 输出到原路径（向后兼容）
#
# 流程:
# 1. SCP 脚本到阿里云 → 跑分析 → analysis_YYYY-MM-DD.json
# 2. (可选) 粉丝量富化 → analysis_YYYY-MM-DD_enriched.json
# 3. (可选) 评论采集 → xhs_note_comment 表 + comments/YYYY-MM-DD.json
# 4. (可选) 趋势对比 → trends/YYYY-MM-DD.json
# 5. 市场信号生成 → briefings/YYYY-MM-DD.json
# 6. Slack 摘要

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh (default)
TODAY=$(TZ='America/New_York' date '+%Y-%m-%d')

NO_SLACK=false
NO_ENRICH=false
NO_COMMENTS=false
ENRICH_TOP_N=20
COMMENT_TOP_N=10
COMMENT_MAX=20
PROJECT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --no-slack) NO_SLACK=true; shift ;;
    --no-enrich) NO_ENRICH=true; shift ;;
    --no-comments) NO_COMMENTS=true; shift ;;
    --enrich-top-n) ENRICH_TOP_N="$2"; shift 2 ;;
    --comment-top-n) COMMENT_TOP_N="$2"; shift 2 ;;
    --comment-max) COMMENT_MAX="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# --- Project config ---
KEYWORDS_ARG=""
KEYWORDS_CSV=""
PROJECT_NAME=""
ANALYSIS_DIR="$MC_DIR/analysis"  # default (backward compatible)

if [ -n "$PROJECT" ]; then
  PROJECTS_FILE="$HUB_DIR/skills/projects.json"
  if [ ! -f "$PROJECTS_FILE" ]; then
    echo "ERROR: projects.json not found at $PROJECTS_FILE"
    exit 1
  fi

  # Extract project config using python (jq not available on all systems)
  PROJECT_CONFIG=$(python3 -c "
import json, sys
with open('$PROJECTS_FILE') as f:
    projects = json.load(f)
p = projects.get('$PROJECT')
if not p:
    print('ERROR: project $PROJECT not found', file=sys.stderr)
    sys.exit(1)
xhs = p.get('platforms', {}).get('xhs')
if not xhs:
    print('ERROR: project $PROJECT has no xhs platform', file=sys.stderr)
    sys.exit(1)
print(p['name'])
print(','.join(xhs['keywords']))
print(p.get('slack_channel', ''))
" 2>&1)

  if [ $? -ne 0 ]; then
    echo "$PROJECT_CONFIG"
    exit 1
  fi

  PROJECT_NAME=$(echo "$PROJECT_CONFIG" | sed -n '1p')
  KEYWORDS_CSV=$(echo "$PROJECT_CONFIG" | sed -n '2p')
  PROJECT_SLACK=$(echo "$PROJECT_CONFIG" | sed -n '3p')

  if [ -n "$PROJECT_SLACK" ]; then
    SLACK_CHANNEL="$PROJECT_SLACK"
  fi

  KEYWORDS_ARG="--keywords '$KEYWORDS_CSV'"
  ANALYSIS_DIR="$MC_DIR/projects/$PROJECT/xhs"
fi

echo "=== XHS 市场信号管道 ==="
echo "Time: $(TZ='America/New_York' date '+%Y-%m-%d %H:%M ET')"
if [ -n "$PROJECT" ]; then
  echo "Project: $PROJECT ($PROJECT_NAME)"
  echo "Keywords: $KEYWORDS_CSV"
fi

log_event "xhs-analysis" "market-signals" "start" "Starting market signals pipeline${PROJECT:+ (project: $PROJECT)}"

# --- 确保目录存在 ---
ssh -o ConnectTimeout=10 "$ALIYUN" "mkdir -p $ANALYSIS_DIR/briefings $ANALYSIS_DIR/trends $ANALYSIS_DIR/comments" 2>/dev/null

# === STEP 1: 基础分析 ===
echo ""
echo "--- [1/6] Syncing & running analysis ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/xhs-analyze-viral.py" "$ALIYUN:$MC_DIR/xhs_analyze.py"

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
  "cd $MC_DIR && source venv/bin/activate && python xhs_analyze.py --json-out '$JSON_OUT' $KEYWORDS_ARG 2>&1")

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
  echo "--- [2/6] Creator enrichment (top $ENRICH_TOP_N) ---"
  scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/_xhs_enrich_creators.py" "$ALIYUN:$MC_DIR/_enrich_creators.py" 2>/dev/null

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
  echo "--- [2/6] Creator enrichment: SKIPPED (--no-enrich) ---"
fi

# === STEP 3: 评论采集 (可选，非阻塞) ===
if [ "$NO_COMMENTS" = false ]; then
  echo ""
  echo "--- [3/6] Comment collection (top $COMMENT_TOP_N notes, max $COMMENT_MAX/note) ---"
  scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/_xhs_collect_comments.py" "$ALIYUN:$MC_DIR/_collect_comments.py" 2>/dev/null

  COMMENT_OUTPUT=$(ssh -o ConnectTimeout=60 -o ServerAliveInterval=60 "$ALIYUN" \
    "cd $MC_DIR && source venv/bin/activate && python _collect_comments.py --account MAIN --top-n $COMMENT_TOP_N --max-comments $COMMENT_MAX 2>&1")

  COMMENT_EXIT=$?
  echo "$COMMENT_OUTPUT"

  if [ $COMMENT_EXIT -eq 0 ]; then
    echo "Comment collection OK"
    log_event "xhs-analysis" "market-signals" "info" "Comments collected"

    # Run comment analysis
    scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/_xhs_comment_analysis.py" "$ALIYUN:$MC_DIR/_comment_analysis.py" 2>/dev/null

    COMMENT_ANALYSIS_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
      "cd $MC_DIR && source venv/bin/activate && python _comment_analysis.py --json-out '$ANALYSIS_DIR/comments/${TODAY}.json' $KEYWORDS_ARG 2>&1")

    echo "$COMMENT_ANALYSIS_OUTPUT"
  elif [ $COMMENT_EXIT -eq 3 ]; then
    echo "Comment collection skipped (no data)"
  else
    echo "WARNING: Comment collection failed (exit $COMMENT_EXIT), non-blocking"
    log_event "xhs-analysis" "market-signals" "info" "Comment collection failed (exit $COMMENT_EXIT), non-blocking"
  fi
else
  echo ""
  echo "--- [3/6] Comment collection: SKIPPED (--no-comments) ---"
fi

# === STEP 4: 趋势对比 (可选，非阻塞) ===
echo ""
echo "--- [4/6] Trend comparison ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/xhs-trend-compare.py" "$ALIYUN:$MC_DIR/_trend_compare.py" 2>/dev/null

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

# === STEP 5: 市场信号 ===
echo ""
echo "--- [5/6] Market signals ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/_xhs_strategy_briefing.py" "$ALIYUN:$MC_DIR/xhs_briefing.py" 2>/dev/null

# Check if comments JSON exists for this date
COMMENTS_ARG=""
COMMENTS_JSON="$ANALYSIS_DIR/comments/${TODAY}.json"
COMMENTS_EXISTS=$(ssh -o ConnectTimeout=10 "$ALIYUN" "test -f '$COMMENTS_JSON' && echo yes || echo no" 2>/dev/null)
if [ "$COMMENTS_EXISTS" = "yes" ]; then
  COMMENTS_ARG="--comments '$COMMENTS_JSON'"
fi

BRIEFING_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python xhs_briefing.py '$SIGNAL_INPUT' '$ANALYSIS_DIR' $TRENDS_ARG $COMMENTS_ARG 2>&1")

BRIEFING_EXIT=$?
echo "$BRIEFING_OUTPUT"

if [ $BRIEFING_EXIT -ne 0 ]; then
  echo "ERROR: Market signals failed (exit $BRIEFING_EXIT)"
  log_event "xhs-analysis" "market-signals" "error" "Market signals failed (exit $BRIEFING_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 市场信号失败*: exit $BRIEFING_EXIT" "XHS Analyst" ":x:"
  exit 1
fi

log_event "xhs-analysis" "market-signals" "end" "Pipeline done, $NOTE_COUNT notes${PROJECT:+ (project: $PROJECT)}"

# === SLACK 摘要 ===
if [ "$NO_SLACK" = false ]; then
  scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/_xhs_slack_summary.py" "$ALIYUN:$MC_DIR/_slack_summary.py" 2>/dev/null

  DASHBOARD_URL="http://106.14.44.68/xhs/"
  if [ -n "$PROJECT" ]; then
    DASHBOARD_URL="http://106.14.44.68/market/$PROJECT/"
  fi

  SUMMARY=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
    "cd $MC_DIR && source venv/bin/activate && python _slack_summary.py '$SIGNAL_INPUT' --dashboard-url '$DASHBOARD_URL'" 2>/dev/null)

  if [ -n "$SUMMARY" ]; then
    PROJECT_LABEL=""
    if [ -n "$PROJECT_NAME" ]; then
      PROJECT_LABEL=" [$PROJECT_NAME]"
    fi
    MSG="📊 *XHS 市场信号更新*${PROJECT_LABEL} ($TODAY)
$SUMMARY"
    notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Analyst" ":bar_chart:"
    echo ""
    echo "Slack notified"
  fi
fi

echo ""
echo "=== Pipeline Complete ==="
