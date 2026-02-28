#!/bin/bash
# common.sh — 跨 Agent 共享的 shell 函数库
# 用法: source ~/mason-hub/shared/common.sh

HUB_DIR="${HUB_DIR:-$HOME/mason-hub}"
SLACK_NOTIFY="${SLACK_NOTIFY:-/home/hangn/slack-bot/slack_notify.sh}"
SRX_API="${SRX_API:-http://106.14.44.68:8000}"
LOG_DIR="${HUB_DIR}/logs"

# 结构化日志写入 agent.log (JSONL)
# 用法: log_event <agent_id> <task_id> <event_type> <message>
# event_type: start | end | error | info
log_event() {
  local agent_id="${1:-unknown}"
  local task_id="${2:-unknown}"
  local event_type="${3:-info}"
  local message="${4:-}"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local log_file="${LOG_DIR}/agent.log"

  printf '{"timestamp":"%s","agent_id":"%s","task_id":"%s","event_type":"%s","message":"%s"}\n' \
    "$timestamp" "$agent_id" "$task_id" "$event_type" \
    "$(echo "$message" | tr '"' "'" | tr '\n' ' ' | head -c 500)" \
    >> "$log_file"
}

# 发送 Slack 通知（安全封装）
# 用法: notify_slack <channel> <message> [username] [emoji]
notify_slack() {
  local channel="$1"
  local message="$2"
  local username="${3:-Agent}"
  local emoji="${4:-:robot_face:}"

  if [ -n "$channel" ] && [ -x "$SLACK_NOTIFY" ]; then
    "$SLACK_NOTIFY" "$channel" "$message" "$username" "$emoji" 2>/dev/null || true
  fi
}
