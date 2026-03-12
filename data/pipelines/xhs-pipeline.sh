#!/usr/bin/env bash
# xhs-pipeline.sh — XHS 主干管道编排器
# 维护者: EMP_0014 (Data Engineer)
#
# 串联完整管道: 采集 → 同步 → 清洗+分析+策略 → 同步结果 → 优化周期
# 每段检查上游 marker 文件再运行，任意段失败 → 停止并通知
#
# 用法:
#   bash xhs-pipeline.sh --full                    # 全量运行（从采集开始）
#   bash xhs-pipeline.sh --from sync               # 从同步开始（跳过采集）
#   bash xhs-pipeline.sh --from analyze             # 从分析开始（假定数据已同步）
#   bash xhs-pipeline.sh --from optimize            # 只跑优化周期
#   bash xhs-pipeline.sh --status                   # 查看各段 marker 状态
#   bash xhs-pipeline.sh --task 1 --full            # 指定采集任务号
#
# 设计原则:
#   - 不过度工程化: marker 文件 = 最简接口
#   - 上游写 .done_<stage>_YYYY-MM-DD，下游检查后再跑
#   - 每段完成后 emit event，event_router 可异步触发下游
#   - 此脚本是同步编排器，event_router 是异步编排器，两者互补

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

MARKER_DIR="$HUB_DIR/data/pipelines/markers"
TODAY=$(TZ='America/New_York' date '+%Y-%m-%d')
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh

mkdir -p "$MARKER_DIR"

# --- Parse args ---
MODE=""
START_FROM=""
CRAWL_TASK=1
CRAWL_ARGS=""
ANALYZE_ARGS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) MODE="full"; shift ;;
    --from) START_FROM="$2"; shift 2 ;;
    --status) MODE="status"; shift ;;
    --task) CRAWL_TASK="$2"; shift 2 ;;
    --no-slack) ANALYZE_ARGS="$ANALYZE_ARGS --no-slack"; shift ;;
    --no-delay) CRAWL_ARGS="$CRAWL_ARGS --no-delay"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$MODE" ] && [ -z "$START_FROM" ]; then
  echo "Usage: xhs-pipeline.sh [--full | --from <crawl|sync|analyze|optimize> | --status]"
  echo ""
  echo "Stages: crawl → sync → analyze (clean+analysis+briefing+sync) → optimize"
  exit 1
fi

# --- Helper: check marker ---
check_marker() {
  local stage="$1"
  local date="${2:-$TODAY}"
  local marker="$MARKER_DIR/.done_${stage}_${date}"
  if [ -f "$marker" ]; then
    echo "OK"
    return 0
  fi
  echo "MISSING"
  return 1
}

# --- Status mode ---
if [ "$MODE" = "status" ]; then
  echo "=== XHS Pipeline Status ($TODAY) ==="
  echo ""
  for stage in crawl sync analyze optimize; do
    marker="$MARKER_DIR/.done_${stage}_${TODAY}"
    if [ -f "$marker" ]; then
      age_sec=$(( $(date +%s) - $(stat -c %Y "$marker") ))
      age_min=$(( age_sec / 60 ))
      echo "  [OK]      $stage — $(cat "$marker" 2>/dev/null | head -c 120) (${age_min}m ago)"
    else
      echo "  [PENDING] $stage"
    fi
  done
  echo ""
  # Show last 3 days
  echo "Recent markers:"
  ls -lt "$MARKER_DIR"/.done_* 2>/dev/null | head -12 | while read -r line; do
    echo "  $line"
  done
  exit 0
fi

# --- Determine start stage ---
STAGES=("crawl" "sync" "analyze" "optimize")
START_IDX=0

if [ "$MODE" = "full" ]; then
  START_IDX=0
elif [ -n "$START_FROM" ]; then
  case "$START_FROM" in
    crawl)   START_IDX=0 ;;
    sync)    START_IDX=1 ;;
    analyze) START_IDX=2 ;;
    optimize) START_IDX=3 ;;
    *) echo "ERROR: Unknown stage: $START_FROM"; exit 1 ;;
  esac
fi

echo "=== XHS Pipeline — Starting from: ${STAGES[$START_IDX]} ==="
echo "Date: $TODAY"
echo "Time: $(TZ='America/New_York' date '+%Y-%m-%d %H:%M ET')"
echo ""

log_event "xhs-pipeline" "orchestrator" "start" "Starting from ${STAGES[$START_IDX]}"

PIPELINE_OK=true

# --- Stage 1: Crawl ---
if [ "$START_IDX" -le 0 ]; then
  echo ">>> Stage 1/4: Crawl (task $CRAWL_TASK)"
  if bash "$HUB_DIR/skills/xhs/xhs-crawl.sh" --task "$CRAWL_TASK" --no-delay $CRAWL_ARGS; then
    echo "  Crawl OK"
  else
    echo "  ERROR: Crawl failed"
    log_event "xhs-pipeline" "orchestrator" "error" "Crawl failed"
    notify_slack "$SLACK_CHANNEL" "XHS Pipeline FAIL at crawl stage" "Pipeline" ":x:"
    exit 1
  fi
  echo ""
fi

# --- Stage 2: Sync (Aliyun → GCP mirror) ---
if [ "$START_IDX" -le 1 ]; then
  echo ">>> Stage 2/4: Data Sync (Aliyun → GCP)"
  # Check crawl marker (skip if starting from sync directly)
  if [ "$START_IDX" -le 0 ]; then
    if ! check_marker "crawl" "$TODAY" > /dev/null 2>&1; then
      echo "  WARNING: No crawl marker for today, syncing anyway (data may be stale)"
    fi
  fi
  if bash "$HUB_DIR/data/pipelines/data-sync.sh"; then
    # Write sync marker
    echo "{\"timestamp\":\"$(date -Iseconds)\"}" > "$MARKER_DIR/.done_sync_${TODAY}"
    echo "  Sync OK"
  else
    echo "  ERROR: Data sync failed"
    log_event "xhs-pipeline" "orchestrator" "error" "Data sync failed"
    notify_slack "$SLACK_CHANNEL" "XHS Pipeline FAIL at sync stage" "Pipeline" ":x:"
    exit 1
  fi
  echo ""
fi

# --- Stage 3: Analyze (clean + analysis + briefing + sync results back) ---
if [ "$START_IDX" -le 2 ]; then
  echo ">>> Stage 3/4: Analyze (clean → analysis → briefing → sync)"
  # xhs-analyze.sh now includes data-sync at the end (step 6/6)
  if bash "$HUB_DIR/skills/xhs/xhs-analyze.sh" $ANALYZE_ARGS; then
    echo "  Analyze OK"
  else
    echo "  ERROR: Analysis failed"
    log_event "xhs-pipeline" "orchestrator" "error" "Analysis failed"
    notify_slack "$SLACK_CHANNEL" "XHS Pipeline FAIL at analyze stage" "Pipeline" ":x:"
    exit 1
  fi
  echo ""
fi

# --- Stage 4: Optimization cycle ---
if [ "$START_IDX" -le 3 ]; then
  echo ">>> Stage 4/4: Optimization cycle"
  # Check analyze marker
  if [ "$START_IDX" -le 2 ]; then
    if ! check_marker "analyze" "$TODAY" > /dev/null 2>&1; then
      echo "  WARNING: No analyze marker for today, optimization may use stale data"
    fi
  fi
  if bash "$HUB_DIR/skills/agent-ops/optimization-cycle.sh"; then
    # Write optimize marker
    echo "{\"timestamp\":\"$(date -Iseconds)\"}" > "$MARKER_DIR/.done_optimize_${TODAY}"
    echo "  Optimization OK"
  else
    echo "  WARNING: Optimization cycle failed (non-blocking)"
    log_event "xhs-pipeline" "orchestrator" "info" "Optimization cycle failed (non-blocking)"
  fi
  echo ""
fi

echo "=== XHS Pipeline Complete ==="
log_event "xhs-pipeline" "orchestrator" "end" "Pipeline complete, started from ${STAGES[$START_IDX]}"

"$HUB_DIR/scripts/emit_event.sh" "xhs-pipeline-complete" "xhs-pipeline.sh" "ok" 1 \
  "{\"start_from\":\"${STAGES[$START_IDX]}\",\"date\":\"$TODAY\"}" 2>/dev/null || true
