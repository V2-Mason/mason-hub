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
#   write_shared_lesson <src> <domain> <tags> <sev> <title> <body> [task_id]
#   load_shared_lessons <agent_id>                # 按 domain+severity 加载相关经验
#
# Layer 说明：
#   0  = identity.md + state.md（T1 轻量任务）
#   01 = identity + state + soul + tools + memory.md（T3+ 完整任务，默认）

set -euo pipefail

# ============================================================
# check_permission — 权限校验（基于 shared/protocols/permissions.md）
# ============================================================
# 返回 0=允许，1=拒绝。escalate 时通过 stdout 返回强制 receiver
check_permission() {
  local sender="$1"
  local receiver="$2"
  local type="$3"

  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"

  # escalate 自动路由到 EMP_0000
  if [ "$type" = "escalate" ]; then
    echo "EMP_0000"
    return 0
  fi

  # task_assign 权限检查：只有 Manager/PM 能派任务
  if [ "$type" = "task_assign" ]; then
    local sender_name
    sender_name=$(grep "^name:" "$hub_dir/agents/$sender/identity.md" \
                  2>/dev/null | awk '{print $2}') || true
    case "$sender_name" in
      meta-manager|pm-srx|ecommerce-manager|pm-socialmesh)
        return 0 ;;
      *)
        echo "❌ ERROR: $sender ($sender_name) 无权发送 task_assign" >&2
        local now
        now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        printf '{"type":"permission_violation","sender":"%s","receiver":"%s","msg_type":"%s","timestamp":"%s"}\n' \
          "$sender" "$receiver" "$type" "$now" >> "$hub_dir/logs/audit.jsonl"
        return 1 ;;
    esac
  fi

  # review_response 权限检查：只有审核方能回复
  if [ "$type" = "review_response" ]; then
    case "$sender" in
      EMP_0000|EMP_0012)
        return 0 ;;
      *)
        echo "❌ ERROR: $sender 无权发送 review_response" >&2
        local now
        now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        printf '{"type":"permission_violation","sender":"%s","receiver":"%s","msg_type":"%s","timestamp":"%s"}\n' \
          "$sender" "$receiver" "$type" "$now" >> "$hub_dir/logs/audit.jsonl"
        return 1 ;;
    esac
  fi

  # 其他类型放行
  return 0
}

# ============================================================
# send_message — 写入接收方 inbox（含权限校验）
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

  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  mkdir -p "$inbox_dir"

  # 权限校验
  local perm_result
  perm_result=$(check_permission "$sender" "$receiver" "$type") || return 1

  # escalate 路由覆写
  if [ "$type" = "escalate" ] && [ -n "$perm_result" ]; then
    receiver="$perm_result"
  fi

  local inbox_file="$inbox_dir/inbox_${receiver}.jsonl"

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
# write_shared_lesson — 写入共享经验教训到 data/shared_lessons.jsonl
# ============================================================
# 用法: write_shared_lesson <source_agent> <domain> <tags_csv> <severity> <title> <body> [task_id]
# 写入: data/shared_lessons.jsonl（每行一条 JSON 记录）
# 去重: 按 title 精确匹配，已存在则跳过
write_shared_lesson() {
  local source_agent="$1"
  local domain="$2"
  local tags_csv="$3"
  local severity="$4"
  local title="$5"
  local body="$6"
  local task_id="${7:-}"

  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"
  local lessons_file="$hub_dir/data/shared_lessons.jsonl"

  mkdir -p "$hub_dir/data"

  # 去重：按 title 精确匹配（用 python3 做 JSON 感知搜索）
  if [ -f "$lessons_file" ]; then
    local dup_found
    dup_found=$(python3 -c "
import sys, json
target = sys.argv[1]
lessons_file = sys.argv[2]
try:
    with open(lessons_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get('title') == target:
                    print('1')
                    sys.exit(0)
            except:
                pass
except:
    pass
print('0')
" "$title" "$lessons_file")
    if [ "$dup_found" = "1" ]; then
      echo "⚠️  write_shared_lesson: 已存在相同 title，跳过写入: $title" >&2
      return 0
    fi
  fi

  # 生成顺序 ID: LESSON-YYYYMMDD-NNN
  local date_str
  date_str=$(date -u +"%Y%m%d")
  local seq=1
  if [ -f "$lessons_file" ]; then
    local count
    count=$(grep -c "\"LESSON-${date_str}-" "$lessons_file" 2>/dev/null || true)
    seq=$((count + 1))
  fi
  local lesson_id
  lesson_id=$(printf "LESSON-%s-%03d" "$date_str" "$seq")

  # 生成时间戳
  local created_at
  created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # 构造 JSON 记录（使用 python3 确保字段安全转义）
  local record
  record=$(python3 -c "
import sys, json

source_agent = sys.argv[1]
domain       = sys.argv[2]
tags_csv     = sys.argv[3]
severity     = sys.argv[4]
title        = sys.argv[5]
body         = sys.argv[6]
task_id_raw  = sys.argv[7]
lesson_id    = sys.argv[8]
created_at   = sys.argv[9]

tags = [t.strip() for t in tags_csv.split(',') if t.strip()]
task_id_val  = task_id_raw if task_id_raw else None

record = {
    'id':           lesson_id,
    'source_agent': source_agent,
    'domain':       domain,
    'tags':         tags,
    'severity':     severity,
    'title':        title,
    'body':         body,
    'task_id':      task_id_val,
    'created_at':   created_at,
}
print(json.dumps(record, ensure_ascii=False))
" "$source_agent" "$domain" "$tags_csv" "$severity" "$title" "$body" "$task_id" "$lesson_id" "$created_at")

  echo "$record" >> "$lessons_file"
  echo "📝 write_shared_lesson: [$lesson_id] $title → $lessons_file" >&2
}

# ============================================================
# load_shared_lessons <agent_id>
# 读取 data/shared_lessons.jsonl，过滤并输出相关经验到 stdout
# 过滤规则：
#   - severity=high → 所有 agent 可见
#   - 同 domain → 同领域 agent 可见
#   - 排除 source_agent == agent_id 自己写的
# ============================================================
load_shared_lessons() {
  local agent_id="${1:-}"
  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"
  local lessons_file="$hub_dir/data/shared_lessons.jsonl"
  local agents_yaml="$hub_dir/kernel/standards/agents.yaml"

  [[ -z "$agent_id" ]] && return 0
  [[ ! -f "$lessons_file" ]] && return 0
  [[ ! -s "$lessons_file" ]] && return 0

  python3 - "$agent_id" "$lessons_file" "$agents_yaml" << 'PYEOF'
import sys, json

agent_id   = sys.argv[1]
lessonfile = sys.argv[2]
agents_yaml = sys.argv[3]

# --- 从 agents.yaml 提取 agent domain（不依赖 PyYAML）---
import subprocess, os

agent_domain = ""
if os.path.isfile(agents_yaml):
    result = subprocess.run(
        ['grep', '-A4', f'id: {agent_id}', agents_yaml],
        capture_output=True, text=True
    )
    for line in result.stdout.split('\n'):
        if 'domain:' in line:
            agent_domain = line.split('domain:')[1].strip()
            break

# --- 读取并过滤 lessons ---
matched = []
with open(lessonfile, 'r', encoding='utf-8') as f:
    for raw in f:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue

        source = rec.get('source_agent', '')
        severity = rec.get('severity', 'normal')
        domain = rec.get('domain', '')

        # 排除自己写的
        if source == agent_id:
            continue

        # 可见条件：severity=high 或 同 domain
        visible = (severity == 'high') or (agent_domain and domain == agent_domain)
        if visible:
            matched.append(rec)

if not matched:
    sys.exit(0)

print(f"--- shared_lessons: {len(matched)} 条相关经验 ---")
print()
for rec in matched:
    severity = rec.get('severity', 'normal')
    tags     = ','.join(rec.get('tags', []))
    source   = rec.get('source_agent', '?')
    title    = rec.get('title', '')
    body     = rec.get('body', '')
    body_short = (body[:200] + '...') if len(body) > 200 else body

    print(f"[{severity}][{tags}] from {source} - {title}")
    print(f"  {body_short}")
    print()
PYEOF
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

  # --- agent_id 提取（shared_lessons 和 inbox 共用）---
  local agent_id
  agent_id=$(basename "$agent_dir")

  # --- shared_lessons: 加载跨 agent 共享经验（仅 layer 01）---
  if [ "$layer" = "01" ]; then
    local lessons_content
    lessons_content=$(load_shared_lessons "$agent_id") || true
    if [ -n "$lessons_content" ]; then
      echo ""
      echo "$lessons_content"
    fi
  fi

  # --- inbox: 启动时自动检查未读消息 ---
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

  # 失败时自动写入 shared_lesson
  if [ "$status" = "failed" ] && [ -n "$summary" ]; then
    local domain
    domain=$(grep -A4 "id: $agent_id" "${hub_dir}/kernel/standards/agents.yaml" 2>/dev/null \
      | grep "domain:" | head -1 | awk '{print $2}') || domain="unknown"
    [ -z "$domain" ] && domain="unknown"
    local short_summary
    short_summary=$(echo "$summary" | head -c 60)
    write_shared_lesson "$agent_id" "$domain" "failure,auto" "medium" \
      "任务 $task_id 失败: $short_summary" \
      "Agent: $agent_id | 任务: $task_id | 失败摘要: $summary" \
      "$task_id"
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
