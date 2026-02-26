#!/bin/bash
# claude-logged.sh — 带 token 追踪的 claude -p 包装脚本
# 用法: claude-logged.sh <agent-id> <agent-name> <prompt> [额外claude参数...]
# 功能: 调用 claude -p --output-format json，提取文本结果输出到终端，
#       同时将 token 用量记录到 api_usage.jsonl
set -euo pipefail

HUB_DIR="$HOME/mason-hub"

if [ $# -lt 3 ]; then
  echo "用法: $0 <agent-id> <agent-name> <prompt> [额外claude参数...]"
  exit 1
fi

AGENT_ID="$1"
AGENT_NAME="$2"
PROMPT="$3"
shift 3

# 调用 claude -p 并获取 JSON 输出
JSON_OUTPUT=$(cd "$HUB_DIR" && claude -p --output-format json "$@" "$PROMPT" 2>&1)

# 提取文本结果输出到终端
echo "$JSON_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null || echo "$JSON_OUTPUT"

# 记录到 api_usage.jsonl
python3 "$HUB_DIR/scripts/api_logger.py" \
  --agent-id "$AGENT_ID" \
  --agent-name "$AGENT_NAME" \
  --action "hq-session" \
  --json-result "$JSON_OUTPUT"
