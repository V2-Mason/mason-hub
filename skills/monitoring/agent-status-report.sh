#!/bin/bash
# agent-status-report.sh — SRE 全局状态报告
# 用法: agent-status-report.sh [--slack <channel_id>]
#
# 从 audit.jsonl 统计全局 agent 状态，生成结构化报告

set -euo pipefail

HUB_DIR="$HOME/mason-hub"
AUDIT_FILE="$HUB_DIR/logs/audit.jsonl"
AUDIT_DOMAIN="$HUB_DIR/domains/ecommerce/projects/srx/audit.jsonl"
TASK_LOG_DIR="$HUB_DIR/logs/tasks"
SKILLS_DIR="$HUB_DIR/skills"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"

SLACK_CHANNEL=""
if [ "${1:-}" = "--slack" ] && [ -n "${2:-}" ]; then
  SLACK_CHANNEL="$2"
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOW_EPOCH=$(date +%s)
TWENTY_FOUR_H=$((24 * 3600))
SEVEN_DAYS=$((7 * 86400))

echo "=== AGENT STATUS REPORT ==="
echo "Generated: $NOW"
echo ""

# --- 1. Agent 调用统计（过去 24h）---
echo "--- 1. Agent Activity (24h) ---"

if [ -f "$AUDIT_FILE" ] && [ -s "$AUDIT_FILE" ]; then
  python3 -c "
import json, sys
from datetime import datetime, timedelta, timezone

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
stats = {}  # agent -> {total, success, failed}

for path in ['$AUDIT_FILE', '$AUDIT_DOMAIN']:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    r = json.loads(line)
                    ts = r.get('timestamp', '')
                    if not ts: continue
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if dt < cutoff: continue
                    agent = r.get('agent', 'unknown')
                    status = r.get('status', '')
                    if agent not in stats:
                        stats[agent] = {'total': 0, 'success': 0, 'failed': 0}
                    stats[agent]['total'] += 1
                    if status == 'completed':
                        stats[agent]['success'] += 1
                    elif 'fail' in status:
                        stats[agent]['failed'] += 1
                except: continue
    except: continue

if not stats:
    print('  No agent activity in past 24h')
else:
    for agent, s in sorted(stats.items()):
        rate = (s['success'] / s['total'] * 100) if s['total'] > 0 else 0
        symbol = '✅' if s['failed'] == 0 else '⚠️'
        print(f'  {symbol} {agent}: {s[\"total\"]} calls, {s[\"success\"]} ok, {s[\"failed\"]} failed ({rate:.0f}%)')
" 2>/dev/null || echo "  (parse error)"
else
  echo "  No audit log found"
fi

# --- 2. 最近失败的任务 ---
echo ""
echo "--- 2. Recent Failures (7d) ---"

if [ -f "$AUDIT_FILE" ] && [ -s "$AUDIT_FILE" ]; then
  python3 -c "
import json
from datetime import datetime, timedelta, timezone

cutoff = datetime.now(timezone.utc) - timedelta(days=7)
failures = []

for path in ['$AUDIT_FILE', '$AUDIT_DOMAIN']:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    r = json.loads(line)
                    ts = r.get('timestamp', '')
                    if not ts: continue
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if dt < cutoff: continue
                    status = r.get('status', '')
                    if 'fail' in status:
                        failures.append({
                            'time': ts[:16],
                            'agent': r.get('agent', '?'),
                            'task': r.get('task_id', r.get('task', '?'))[:40],
                            'status': status
                        })
                except: continue
    except: continue

if not failures:
    print('  No failures in past 7 days ✅')
else:
    for f in failures[-10:]:  # last 10
        print(f'  ❌ {f[\"time\"]} | {f[\"agent\"]} | {f[\"task\"]} | {f[\"status\"]}')
    if len(failures) > 10:
        print(f'  ... and {len(failures) - 10} more')
" 2>/dev/null || echo "  (parse error)"
else
  echo "  No audit log"
fi

# --- 3. Token 消耗趋势（过去 7 天）---
echo ""
echo "--- 3. Token Usage (7d) ---"

API_LOG="$HUB_DIR/logs/api_usage.jsonl"
if [ -f "$API_LOG" ] && [ -s "$API_LOG" ]; then
  python3 -c "
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict

cutoff = datetime.now(timezone.utc) - timedelta(days=7)
daily = defaultdict(lambda: {'input': 0, 'output': 0, 'cost': 0.0})

with open('$API_LOG') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
            ts = r.get('timestamp', '')
            if not ts: continue
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if dt < cutoff: continue
            day = ts[:10]
            daily[day]['input'] += r.get('input_tokens', 0)
            daily[day]['output'] += r.get('output_tokens', 0)
            daily[day]['cost'] += r.get('cost_usd', 0.0)
        except: continue

if not daily:
    print('  No token data in past 7 days')
else:
    total_cost = 0
    for day in sorted(daily.keys()):
        d = daily[day]
        total_cost += d['cost']
        print(f'  {day}: {d[\"input\"]:>8} in / {d[\"output\"]:>8} out | \${d[\"cost\"]:.3f}')
    print(f'  Total: \${total_cost:.3f}')
" 2>/dev/null || echo "  (no data or parse error)"
else
  echo "  No api_usage.jsonl found"
fi

# --- 4. 记忆文件状态 ---
echo ""
echo "--- 4. Memory Files ---"

for f in "$HUB_DIR/memory"/*_lessons.md; do
  [ -f "$f" ] || continue
  agent=$(basename "$f" _lessons.md)
  size=$(stat -c %s "$f" 2>/dev/null || echo 0)
  size_kb=$(( size / 1024 ))
  if [ "$size" -ge 51200 ]; then
    echo "  🔴 $agent: ${size_kb}KB (AT LIMIT)"
  elif [ "$size" -ge 10240 ]; then
    echo "  ⚠️ $agent: ${size_kb}KB (consider compaction)"
  else
    echo "  ✅ $agent: ${size_kb}KB"
  fi
done

# --- 5. Skills 脚本健康 ---
echo ""
echo "--- 5. Skills Health ---"

broken=0
for script in "$SKILLS_DIR"/*.sh; do
  [ -f "$script" ] || continue
  name=$(basename "$script")
  if [ -x "$script" ]; then
    echo "  ✅ $name"
  else
    echo "  ❌ $name (not executable)"
    broken=$((broken + 1))
  fi
done

# --- 6. 系统资源 ---
echo ""
echo "--- 6. System Resources ---"

disk_pct=$(df -h / | awk 'NR==2{print $5}')
mem_available=$(free -h | awk '/^Mem:/{print $7}')
mem_used_pct=$(free | awk '/^Mem:/{printf "%.0f", $3/$2*100}')
echo "  Disk usage: $disk_pct"
echo "  Memory available: $mem_available (${mem_used_pct}% used)"

# --- 6b. 进程健康检查 ---
echo ""
echo "--- 6b. Process Health ---"

# Zombie 检测
zombie_count=$(ps -eo stat | grep -c '^Z' || true)
if [ "$zombie_count" -gt 0 ]; then
  echo "  🔴 Zombie processes: $zombie_count"
  ps -eo pid,ppid,stat,comm | awk '$3 ~ /Z/' | head -5 | while read line; do
    echo "    $line"
  done
else
  echo "  ✅ No zombie processes"
fi

# Top 5 内存消耗进程
echo "  Top memory consumers:"
ps -eo pid,rss,comm --sort=-rss | head -6 | tail -5 | while read pid rss comm; do
  mb=$((rss / 1024))
  echo "    ${comm}: ${mb}MB (PID $pid)"
done

# 内存使用率告警
if [ "$mem_used_pct" -ge 80 ]; then
  echo "  🔴 Memory usage critical: ${mem_used_pct}%"
elif [ "$mem_used_pct" -ge 60 ]; then
  echo "  ⚠️ Memory usage elevated: ${mem_used_pct}%"
fi

# 异常进程检测：同名进程过多（可能泄漏）
echo "  Process count check:"
ps -eo comm | sort | uniq -c | sort -rn | head -10 | while read count name; do
  if [ "$count" -ge 5 ] && [ "$name" != "kworker/u4:0" ] && [ "$name" != "kworker/0:0" ]; then
    echo "    ⚠️ $name: $count instances"
  fi
done

# --- 7. Task Logs ---
echo ""
echo "--- 7. Task Logs ---"

if [ -d "$TASK_LOG_DIR" ]; then
  total_files=$(ls "$TASK_LOG_DIR" 2>/dev/null | wc -l)
  summaries=$(ls "$TASK_LOG_DIR"/*_summary.json 2>/dev/null | wc -l || echo 0)
  echo "  Total files: $total_files"
  echo "  Task summaries: $summaries"
else
  echo "  No task log directory"
fi

echo ""
echo "=== END REPORT ==="

# --- Slack 输出 ---
if [ -n "$SLACK_CHANNEL" ] && [ -x "$SLACK_NOTIFY" ]; then
  # 构建简洁的 Slack 摘要
  ALERTS=""
  [ "$zombie_count" -gt 0 ] && ALERTS="${ALERTS} | 🔴 Zombies: $zombie_count"
  [ "$mem_used_pct" -ge 80 ] && ALERTS="${ALERTS} | 🔴 Mem: ${mem_used_pct}%"
  SUMMARY="📊 *Agent Status Report* | $(date +%Y-%m-%d)
Disk: $disk_pct | Mem: ${mem_used_pct}% used ($mem_available free) | Skills broken: $broken${ALERTS}
详细报告请查看 GCP logs"
  "$SLACK_NOTIFY" "$SLACK_CHANNEL" "$SUMMARY" "SRE Bot" ":chart_with_upwards_trend:" 2>/dev/null || true
fi
