#!/bin/bash
set -euo pipefail

HUB_DIR="$HOME/mason-hub"
LOG_FILE="$HUB_DIR/logs/agent.log"
AUDIT_FILE="$HUB_DIR/domains/ecommerce/projects/srx/audit.jsonl"

# --- 参数检查 ---
if [ $# -lt 2 ]; then
  echo "用法: $0 <agent配置文件> <任务内容>"
  echo "示例: $0 agents/EMP_0000.md \"读取context.json并分析\""
  exit 1
fi

AGENT_FILE="$HUB_DIR/$1"
TASK="$2"
SLACK_CHANNEL="${3:-}"

# Export paths for agent to use slack_notify.sh
export SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
export SLACK_CHANNEL

if [ ! -f "$AGENT_FILE" ]; then
  echo "错误: 找不到配置文件 $AGENT_FILE"
  exit 1
fi

# --- 提取 agent 名称 ---
AGENT_NAME=$(basename "$1" .md)

# --- 加载 API key ---
source ~/slack-bot/.env
export ANTHROPIC_API_KEY

# --- 提取 markdown body（跳过 YAML frontmatter）---
SYSPROMPT=$(awk "BEGIN{c=0} /^---$/{c++; next} c>=2{print}" "$AGENT_FILE")

if [ -z "$SYSPROMPT" ]; then
  echo "错误: 无法从 $AGENT_FILE 提取 system prompt"
  exit 1
fi

# --- 提取 working_directory（从 YAML frontmatter）---
WORK_DIR=$(awk 'BEGIN{c=0} /^---$/{c++; next} c==1 && /^working_directory:/{gsub(/^working_directory:\s*/, ""); gsub(/~/, ENVIRON["HOME"]); print; exit}' "$AGENT_FILE")
if [ -n "$WORK_DIR" ] && [ -d "$WORK_DIR" ]; then
  RUN_DIR="$WORK_DIR"
else
  RUN_DIR="$HUB_DIR"
fi

# --- 记录开始 ---
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_EPOCH=$(date +%s)
echo "[$START_TIME] === $AGENT_NAME 开始执行 ===" >> "$LOG_FILE"
echo "[$START_TIME] 任务: $TASK" >> "$LOG_FILE"
echo "[$START_TIME] 工作目录: $RUN_DIR" >> "$LOG_FILE"
echo "<<<AGENT_START $AGENT_NAME>>>"

# --- 调用 claude -p（JSON 输出以获取 token 用量）---
JSON_OUTPUT=$(cd "$RUN_DIR" && claude -p \
  --output-format json \
  --system-prompt "$SYSPROMPT" \
  "$TASK" 2>&1)

# --- 从 JSON 中提取文本结果 ---
OUTPUT=$(echo "$JSON_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null || echo "$JSON_OUTPUT")

# --- 输出到终端 + 日志 ---
echo "$OUTPUT"
echo "$OUTPUT" >> "$LOG_FILE"

# --- 写 audit 记录 ---
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
END_EPOCH=$(date +%s)
DURATION=$((END_EPOCH - START_EPOCH))
TASK_SUMMARY=$(printf %s "$TASK" | head -c 50)
TASK_SUMMARY=${TASK_SUMMARY//$'\n'/ }
echo "{\"timestamp\":\"$END_TIME\",\"agent\":\"$AGENT_NAME\",\"task\":\"$TASK_SUMMARY\",\"status\":\"completed\"}" >> "$AUDIT_FILE"

# --- 写 api_usage 记录（从 JSON 提取精确 token 数据）---
python3 "$HUB_DIR/scripts/api_logger.py" \
  --agent-id "$AGENT_NAME" \
  --agent-name "$AGENT_NAME" \
  --action "run-agent" \
  --duration "$DURATION" \
  --json-result "$JSON_OUTPUT"

echo "" >> "$LOG_FILE"
echo "[$END_TIME] === $AGENT_NAME 执行完毕 ===" >> "$LOG_FILE"
echo "<<<AGENT_END>>>"
echo "任务完成，结果已记录"
