#!/bin/bash
# log-query.sh — agent.log 结构化日志查询工具
# 用法:
#   log-query.sh                         # 最近 20 条
#   log-query.sh --agent EMP_0001        # 按 agent 过滤
#   log-query.sh --type error            # 按 event_type 过滤
#   log-query.sh --since 2026-03-12      # 按日期过滤
#   log-query.sh --task-id task_xxx      # 按 task_id 过滤
#   log-query.sh --tail 50              # 最近 N 条
#   log-query.sh --stats                 # 统计摘要
#   可组合: log-query.sh --agent EMP_0001 --type error --since 2026-03-10

set -euo pipefail

LOG_FILE="${HOME}/mason-hub/logs/agent.log"
AGENT_FILTER=""
TYPE_FILTER=""
SINCE_FILTER=""
TASK_FILTER=""
TAIL_N=20
SHOW_STATS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)   AGENT_FILTER="$2"; shift 2 ;;
    --type)    TYPE_FILTER="$2"; shift 2 ;;
    --since)   SINCE_FILTER="$2"; shift 2 ;;
    --task-id) TASK_FILTER="$2"; shift 2 ;;
    --tail)    TAIL_N="$2"; shift 2 ;;
    --stats)   SHOW_STATS=true; shift ;;
    --all)     TAIL_N=0; shift ;;
    -h|--help)
      echo "用法: log-query.sh [选项]"
      echo "  --agent <id>      按 agent_id 过滤"
      echo "  --type <type>     按 event_type 过滤 (start|output|verify|error|crash|info)"
      echo "  --since <date>    起始日期 (YYYY-MM-DD)"
      echo "  --task-id <id>    按 task_id 过滤"
      echo "  --tail <N>        最近 N 条 (默认 20)"
      echo "  --all             显示全部"
      echo "  --stats           统计摘要"
      exit 0
      ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [ ! -f "$LOG_FILE" ]; then
  echo "❌ 日志文件不存在: $LOG_FILE"
  exit 1
fi

if $SHOW_STATS; then
  python3 -c "
import json, sys
from collections import Counter

agents = Counter()
types = Counter()
dates = Counter()
total = 0

with open('$LOG_FILE', 'r', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
            total += 1
            agents[obj.get('agent_id', '?')] += 1
            types[obj.get('event_type', '?')] += 1
            ts = obj.get('timestamp', '')[:10]
            if ts: dates[ts] += 1
        except:
            pass

print(f'📊 agent.log 统计 (共 {total} 条)')
print()
print('按 Agent:')
for k, v in agents.most_common(10):
    print(f'  {k}: {v}')
print()
print('按 Event Type:')
for k, v in types.most_common():
    print(f'  {k}: {v}')
print()
print('按日期:')
for k, v in sorted(dates.items()):
    print(f'  {k}: {v}')
"
  exit 0
fi

# 查询过滤
python3 -c "
import json, sys

agent_f = '$AGENT_FILTER'
type_f = '$TYPE_FILTER'
since_f = '$SINCE_FILTER'
task_f = '$TASK_FILTER'
tail_n = int('$TAIL_N')

results = []
with open('$LOG_FILE', 'r', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
        except:
            continue

        if agent_f and obj.get('agent_id', '') != agent_f:
            continue
        if type_f and obj.get('event_type', '') != type_f:
            continue
        if since_f and obj.get('timestamp', '') < since_f:
            continue
        if task_f and obj.get('task_id', '') != task_f:
            continue

        results.append(obj)

if tail_n > 0:
    results = results[-tail_n:]

for obj in results:
    ts = obj.get('timestamp', '?')[:19]
    agent = obj.get('agent_id', '?')
    etype = obj.get('event_type', '?')
    elapsed = obj.get('elapsed_s', '')
    msg = obj.get('message', '')[:120]
    elapsed_str = f' [{elapsed}s]' if elapsed != '' else ''
    print(f'{ts} | {agent:<12} | {etype:<8} |{elapsed_str} {msg}')
"
