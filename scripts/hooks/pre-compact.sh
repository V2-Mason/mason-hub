#!/bin/bash
# PreCompact Hook: 压缩前记忆冲刷（借鉴 OpenClaw）
#
# 触发时机：context window 快满，Claude Code 自动压缩之前
# 做什么：从 transcript 提取关键信息，写入 daily log
# 为什么：压缩后对话历史被丢弃，关键信息必须先持久化
#
# stdin: {"session_id":"...","transcript_path":"...","trigger":"auto|manual","cwd":"..."}
# exit 0: 继续压缩

set -uo pipefail

HUB_DIR="${HUB_DIR:-/home/hangn/mason-hub}"
DAILY_DIR="$HUB_DIR/memory/daily"
DAILY_FILE="$DAILY_DIR/$(date +%Y-%m-%d).md"

mkdir -p "$DAILY_DIR"

# 读取 stdin
INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','')[:8])" 2>/dev/null || echo "?")
TRIGGER=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('trigger','auto'))" 2>/dev/null || echo "auto")

# 如果拿不到 transcript，只记录事件本身
if [[ -z "$TRANSCRIPT_PATH" ]] || [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  # 确保日志文件有表头
  if [[ ! -f "$DAILY_FILE" ]]; then
    cat > "$DAILY_FILE" <<DAILYHDR
# $(date +%Y-%m-%d) 每日日志

| 时间 | Agent | 任务 | 结果 | 备注 |
|------|-------|------|------|------|
DAILYHDR
  fi
  echo "| $(date +%H:%M) | session | compact($TRIGGER) | ⚡ | sid:$SESSION_ID |" >> "$DAILY_FILE"
  exit 0
fi

# 从 transcript 提取关键信息
# transcript 是 JSONL 格式，每行一个消息
# 提取最近的 assistant 消息中的关键决策/发现
SUMMARY=$(python3 -c "
import json, sys

transcript_path = '$TRANSCRIPT_PATH'
lines = []
try:
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except:
                pass
except:
    sys.exit(0)

# 取最后 20 条消息
recent = lines[-20:] if len(lines) > 20 else lines

# 提取 assistant 文本消息
key_points = []
for msg in recent:
    role = msg.get('role', '')
    if role == 'assistant':
        content = msg.get('content', '')
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                    # 提取包含关键词的行
                    for line in text.split('\n'):
                        line = line.strip()
                        if any(kw in line for kw in ['完成', '修复', '发现', '问题', '决策', '建议', '错误', '成功', '失败', 'TODO', 'FIXME', '注意']):
                            if len(line) > 10 and len(line) < 200:
                                key_points.append(line)
        elif isinstance(content, str) and len(content) > 20:
            for line in content.split('\n'):
                line = line.strip()
                if any(kw in line for kw in ['完成', '修复', '发现', '问题', '决策', '建议']):
                    if len(line) > 10 and len(line) < 200:
                        key_points.append(line)

# 去重 + 限制数量
seen = set()
unique = []
for p in key_points:
    if p not in seen:
        seen.add(p)
        unique.append(p)

# 输出最多 5 条
for p in unique[-5:]:
    print(p)
" 2>/dev/null) || SUMMARY=""

# 写入 daily log
if [[ ! -f "$DAILY_FILE" ]]; then
  cat > "$DAILY_FILE" <<DAILYHDR
# $(date +%Y-%m-%d) 每日日志

| 时间 | Agent | 任务 | 结果 | 备注 |
|------|-------|------|------|------|
DAILYHDR
fi

echo "| $(date +%H:%M) | session | compact($TRIGGER) | ⚡ | sid:$SESSION_ID |" >> "$DAILY_FILE"

# 如果提取到关键信息，追加为备注
if [[ -n "$SUMMARY" ]]; then
  echo "" >> "$DAILY_FILE"
  echo "**Compact 前记忆冲刷 (sid:$SESSION_ID):**" >> "$DAILY_FILE"
  echo "$SUMMARY" | while IFS= read -r line; do
    echo "- $line" >> "$DAILY_FILE"
  done
  echo "" >> "$DAILY_FILE"
fi

exit 0
