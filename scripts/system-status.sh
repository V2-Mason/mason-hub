#!/bin/bash
# system-status.sh — mason-hub 系统实时快照
# 用法：./scripts/system-status.sh [--json]

MASON_HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MASON_HUB_DIR"

echo "═══════════════════════════════════════"
echo "  mason-hub 系统状态 · $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════"
echo ""

echo "── EMP 状态 ──────────────────────────"
for emp_dir in agents/EMP_*/; do
  emp_id=$(basename "$emp_dir")
  state_file="$emp_dir/state.md"

  # 跳过不存在或 ARCHIVED 的
  [ -f "$emp_dir/identity.md" ] || continue
  if grep -q "ARCHIVED" "$emp_dir/identity.md" 2>/dev/null; then
    continue
  fi

  # 读取活跃任务
  active=$(grep -A1 "活跃任务" "$state_file" 2>/dev/null \
           | tail -1 | sed 's/^[[:space:]]*//')

  # 读取 inbox 未读数
  inbox_file="data/messages/inbox_${emp_id}.jsonl"
  unread=0
  if [ -f "$inbox_file" ] && [ -s "$inbox_file" ]; then
    unread=$(grep -c '"status":"unread"' "$inbox_file" 2>/dev/null || echo 0)
  fi

  # 状态指示
  if echo "$active" | grep -qE "^（无|$"; then
    status="💤 空闲"
  else
    status="⚙️  工作中"
  fi

  printf "  %-12s %s" "$emp_id" "$status"
  [ "$unread" -gt 0 ] && printf "  📬 %d条未读" "$unread"
  echo ""
done

echo ""
echo "── 消息队列 ──────────────────────────"
total_unread=0
for inbox in data/messages/inbox_*.jsonl; do
  [ -f "$inbox" ] || continue
  count=$(grep -ac '"status":"unread"' "$inbox" 2>/dev/null || true)
  count=${count:-0}
  total_unread=$((total_unread + count))
done
echo "  未读消息总数：$total_unread"

archive_count=0
if [ -d "data/messages/archive" ]; then
  archive_count=$(ls data/messages/archive/*.jsonl 2>/dev/null | wc -l)
fi
echo "  归档文件数：$archive_count"

echo ""
echo "── 今日任务统计 ──────────────────────"
today=$(date '+%Y-%m-%d')
completed=0; failed=0; violations=0
if [ -f "logs/audit.jsonl" ]; then
  completed=$(grep -a "$today" logs/audit.jsonl \
              | grep -ac '"status":"completed"' 2>/dev/null || true)
  failed=$(grep -a "$today" logs/audit.jsonl \
           | grep -ac '"status":"failed"' 2>/dev/null || true)
  violations=$(grep -a "$today" logs/audit.jsonl \
               | grep -ac '"type":"permission_violation"' 2>/dev/null || true)
  completed=${completed:-0}; failed=${failed:-0}; violations=${violations:-0}
fi
echo "  完成：$completed  失败：$failed  权限违规：$violations"

pending_review=0
if [ -f "data/failed_tasks_for_review.jsonl" ]; then
  pending_review=$(wc -l < "data/failed_tasks_for_review.jsonl")
fi
echo "  待人工裁决：$pending_review"

echo ""
echo "═══════════════════════════════════════"
