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

# --- 记录开始 ---
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[$START_TIME] === $AGENT_NAME 开始执行 ===" >> "$LOG_FILE"
echo "[$START_TIME] 任务: $TASK" >> "$LOG_FILE"
echo "<<<AGENT_START $AGENT_NAME>>>"

# --- 调用 claude -p ---
OUTPUT=$(cd "$HUB_DIR" && claude -p \
  --system-prompt "$SYSPROMPT" \
  "$TASK" 2>&1)

# --- 输出到终端 + 日志 ---
echo "$OUTPUT"
echo "$OUTPUT" >> "$LOG_FILE"

# --- 写 audit 记录 ---
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TASK_SUMMARY=$(printf %s "$TASK" | head -c 50)
TASK_SUMMARY=${TASK_SUMMARY//$'\n'/ }
echo "{\"timestamp\":\"$END_TIME\",\"agent\":\"$AGENT_NAME\",\"task\":\"$TASK_SUMMARY\",\"status\":\"completed\"}" >> "$AUDIT_FILE"

echo "" >> "$LOG_FILE"
echo "[$END_TIME] === $AGENT_NAME 执行完毕 ===" >> "$LOG_FILE"
echo "<<<AGENT_END>>>"
echo "任务完成，结果已记录"
