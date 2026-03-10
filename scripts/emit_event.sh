#!/usr/bin/env bash
# emit_event.sh — 通用事件发射工具
#
# 其他脚本在末尾调用此脚本写入事件。
# 用法:
#   emit_event.sh <event_type> <source> <status> <level> [json_data]
#
# 示例:
#   emit_event.sh data-sync-complete data-sync.sh ok 1 '{"rows":150}'
#   emit_event.sh health-check-failed health-check.sh failed 2
#   emit_event.sh agent-task-complete EMP_0008 ok 1 '{"task":"market-analysis"}'

set -euo pipefail

HUB_DIR="${HUB_DIR:-$HOME/mason-hub}"
QUEUE_FILE="$HUB_DIR/data/events/queue.jsonl"

EVENT_TYPE="${1:?用法: emit_event.sh <event> <source> <status> <level> [data]}"
SOURCE="${2:?缺少 source 参数}"
STATUS="${3:-ok}"
LEVEL="${4:-0}"
DATA="${5:-"{}"}"

mkdir -p "$(dirname "$QUEUE_FILE")"

TIMESTAMP=$(date -Iseconds)

python3 - "$EVENT_TYPE" "$SOURCE" "$TIMESTAMP" "$STATUS" "$LEVEL" "$DATA" "$QUEUE_FILE" << 'PYEOF'
import json, sys

event_type, source, timestamp, status, level_str, data_str, queue_file = sys.argv[1:8]
data = json.loads(data_str) if data_str and data_str != '{}' else {}
event = {
    "event": event_type,
    "source": source,
    "timestamp": timestamp,
    "status": status,
    "level": int(level_str),
    "data": data,
}
with open(queue_file, "a") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
PYEOF
