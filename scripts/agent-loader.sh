#!/bin/bash
# agent-loader.sh — v2 Agent 文件加载器 + inbox 通信
# 从 run-agent.sh 提取，适配 5 文件分层架构
#
# 用法：
#   source scripts/agent-loader.sh
#   load_agent_context <agent_dir> [layer]   # 组装 context 到 stdout
#   update_agent_state <agent_dir> <task_id> <status> [summary] [receiver]
#   send_message <sender> <receiver> <type> <task_id> <payload> [requires_response] [deadline]
#   check_inbox <agent_id>
#
# Layer 说明：
#   0  = identity.md + state.md（T1 轻量任务）
#   01 = identity + state + soul + tools + memory.md（T3+ 完整任务，默认）

set -euo pipefail

# ============================================================
# send_message — 写入接收方 inbox
# ============================================================
# 用法: send_message <sender> <receiver> <type> <task_id> <payload> [requires_response] [deadline]
# 写入: data/messages/inbox_<receiver>.jsonl
send_message() {
  local sender="$1"
  local receiver="$2"
  local type="$3"
  local task_id="$4"
  local payload="$5"
  local requires_response="${6:-false}"
  local deadline="${7:-null}"

  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"
  local inbox_dir="$hub_dir/data/messages"
  local inbox_file="$inbox_dir/inbox_${receiver}.jsonl"

  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  mkdir -p "$inbox_dir"

  # escalate 类型自动路由到 EMP_0000
  if [ "$type" = "escalate" ]; then
    receiver="EMP_0000"
    inbox_file="$inbox_dir/inbox_EMP_0000.jsonl"
  fi

  # 构造符合 message_schema.md 的 JSON 消息
  local payload_json
  payload_json=$(echo "$payload" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")

  local message
  message="{\"sender\":\"$sender\",\"receiver\":\"$receiver\",\"type\":\"$type\",\"task_id\":\"$task_id\",\"payload\":$payload_json,\"requires_response\":$requires_response,\"deadline\":\"$deadline\",\"timestamp\":\"$timestamp\",\"status\":\"unread\"}"

  echo "$message" >> "$inbox_file"
  echo "📨 send_message: $sender → $receiver [$type] $task_id → $inbox_file" >&2
}

# ============================================================
# check_inbox — 读取未读消息 + 归档到 archive + 从 inbox 移除
# ============================================================
# 用法: check_inbox <agent_id>
# stdout: 格式化的未读消息内容（注入 agent context）
# 归档: data/messages/archive/inbox_<agent_id>_YYYY-MM.jsonl
check_inbox() {
  local agent_id="$1"
  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"
  local inbox_file="$hub_dir/data/messages/inbox_${agent_id}.jsonl"

  # 文件不存在或为空：静默返回
  if [ ! -f "$inbox_file" ] || [ ! -s "$inbox_file" ]; then
    return 0
  fi

  # 读取 unread 消息，格式化输出，标记 read，归档后从 inbox 移除
  python3 -c "
import json, sys, os
from datetime import datetime, timezone

inbox_file = '$inbox_file'
agent_id = '$agent_id'
hub_dir = '$hub_dir'
archive_dir = os.path.join(hub_dir, 'data', 'messages', 'archive')
os.makedirs(archive_dir, exist_ok=True)

year_month = datetime.now(timezone.utc).strftime('%Y-%m')
archive_file = os.path.join(archive_dir, f'inbox_{agent_id}_{year_month}.jsonl')

unread = []
remaining = []

with open(inbox_file) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            if msg.get('status') == 'unread':
                unread.append(msg)
            else:
                remaining.append(line)
        except:
            remaining.append(line)

if not unread:
    sys.exit(0)

# stdout: 格式化输出注入 context
print('--- inbox: {} 条未读消息 ---'.format(len(unread)))
print()
for msg in unread:
    print('[{}] from {} · task_id: {}'.format(msg['type'], msg['sender'], msg['task_id']))
    print('payload: {}'.format(msg.get('payload', '')))
    if msg.get('requires_response') == True or msg.get('requires_response') == 'true':
        print('⚠️ requires_response: true')
    print()

# 归档: 标记 read 后 append 到 archive
with open(archive_file, 'a') as af:
    for msg in unread:
        msg['status'] = 'read'
        af.write(json.dumps(msg, ensure_ascii=False) + '\n')

# inbox 只保留非 unread 行（通常为空）
with open(inbox_file, 'w') as f:
    if remaining:
        f.write('\n'.join(remaining) + '\n')

sys.stderr.write('📬 check_inbox: {} 处理了 {} 条消息（归档到 archive/inbox_{}_{}.jsonl）\n'.format(
    agent_id, len(unread), agent_id, year_month))
"
}

# ============================================================
# load_agent_context — 组装 agent 上下文到 stdout
# ============================================================
load_agent_context() {
  local agent_dir="$1"
  local layer="${2:-01}"

  # --- 规范化路径 ---
  if [[ ! "$agent_dir" = /* ]]; then
    agent_dir="${HUB_DIR:-$HOME/mason-hub}/$agent_dir"
  fi

  if [ ! -d "$agent_dir" ]; then
    echo "❌ agent-loader: 目录不存在: $agent_dir" >&2
    return 1
  fi

  local identity="$agent_dir/identity.md"
  local state="$agent_dir/state.md"
  local soul="$agent_dir/soul.md"
  local tools="$agent_dir/tools.md"
  local memory="$agent_dir/memory/memory.md"
  local config_fallback="$agent_dir/config.md"

  # --- Layer 0: identity.md（必须存在，或 fallback 到 config.md）---
  if [ -f "$identity" ]; then
    echo "--- identity.md ---"
    # 跳过 YAML frontmatter，只输出 body
    awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$identity"
  elif [ -f "$config_fallback" ]; then
    echo "⚠️ agent-loader: identity.md 不存在，回退到 config.md" >&2
    echo "--- config.md (fallback) ---"
    awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$config_fallback"
    # fallback 模式下只输出 config.md，不继续加载其他 v2 文件
    return 0
  else
    echo "❌ agent-loader: 必须文件缺失: identity.md 和 config.md 都不存在" >&2
    return 1
  fi

  # --- Layer 0: state.md ---
  if [ -f "$state" ]; then
    echo ""
    echo "--- state.md ---"
    awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$state"
  else
    echo "⚠️ agent-loader: state.md 不存在，跳过" >&2
  fi

  # --- Layer 1（仅 layer=01 时加载）---
  if [ "$layer" = "01" ]; then
    if [ -f "$soul" ]; then
      echo ""
      echo "--- soul.md ---"
      cat "$soul"
    else
      echo "⚠️ agent-loader: soul.md 不存在，跳过" >&2
    fi

    if [ -f "$tools" ]; then
      echo ""
      echo "--- tools.md ---"
      cat "$tools"
    else
      echo "⚠️ agent-loader: tools.md 不存在，跳过" >&2
    fi

    if [ -f "$memory" ]; then
      echo ""
      echo "--- memory/memory.md ---"
      cat "$memory"
    else
      echo "⚠️ agent-loader: memory/memory.md 不存在，跳过" >&2
    fi
  fi

  # --- inbox: 启动时自动检查未读消息 ---
  local agent_id
  agent_id=$(basename "$agent_dir")
  local inbox_content
  inbox_content=$(check_inbox "$agent_id") || true
  if [ -n "$inbox_content" ]; then
    echo ""
    echo "$inbox_content"
  fi
}

# ============================================================
# update_agent_state — 覆写 state.md + 可选自动发送 task_complete
# ============================================================
# 用法: update_agent_state <agent_dir> <task_id> <status> [summary] [receiver]
# 第5参数 receiver: 如果存在且 status=completed，自动 send_message task_complete
update_agent_state() {
  local agent_dir="$1"
  local task_id="$2"
  local status="$3"  # completed / failed
  local summary="${4:-}"
  local receiver="${5:-}"

  if [[ ! "$agent_dir" = /* ]]; then
    agent_dir="${HUB_DIR:-$HOME/mason-hub}/$agent_dir"
  fi

  local agent_id
  agent_id=$(basename "$agent_dir")
  local state_file="$agent_dir/state.md"
  local old_issues=""

  # 保留"已知未解决问题"字段
  if [ -f "$state_file" ]; then
    old_issues=$(awk '/^## 已知未解决问题/{found=1; next} found && /^## /{found=0} found{print}' "$state_file")
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local today
  today=$(date +%Y-%m-%d)

  local status_label
  if [ "$status" = "completed" ]; then
    status_label="✅ completed"
  else
    status_label="❌ failed"
  fi

  cat > "$state_file" <<EOF
---
last_updated: $now
---

# $agent_id 当前状态

## 活跃任务
（无 · 待派发）

## 最近完成
- $today: [$task_id] $status_label${summary:+ — $summary}

## 等待 / 阻塞
（无）

## 已知未解决问题
${old_issues:-（无）}
EOF

  # 自动发送 task_complete / task_failed 消息
  if [ -n "$receiver" ]; then
    local msg_type="task_complete"
    if [ "$status" != "completed" ]; then
      msg_type="task_failed"
    fi
    send_message "$agent_id" "$receiver" "$msg_type" "$task_id" "${summary:-$status}"
  fi
}

# ============================================================
# extract_frontmatter_field — 从 identity.md 提取 frontmatter 字段
# ============================================================
extract_frontmatter_field() {
  local file="$1"
  local field="$2"
  awk -v f="$field" 'BEGIN{c=0} /^---$/{c++; next} c>=2{exit} c==1{
    if($0 ~ "^"f":"){gsub("^"f":\\s*", ""); print; exit}
  }' "$file" 2>/dev/null
}

# ============================================================
# extract_launcher_args — 从 identity.md 的 launcher 行提取参数
# ============================================================
extract_launcher_args() {
  local agent_dir="$1"
  if [[ ! "$agent_dir" = /* ]]; then
    agent_dir="${HUB_DIR:-$HOME/mason-hub}/$agent_dir"
  fi

  local identity="$agent_dir/identity.md"
  if [ -f "$identity" ]; then
    # 从 body 中提取 **launcher**: claude --args 格式
    grep -oP '^\*\*launcher\*\*:\s*claude\s+\K.*' "$identity" 2>/dev/null || true
  fi
}
