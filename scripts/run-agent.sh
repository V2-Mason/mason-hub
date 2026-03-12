#!/bin/bash
set -euo pipefail

# 确保 cron 环境能找到正确版本的 claude（~/.local/bin 优先于 /usr/bin）
export PATH="$HOME/.local/bin:$PATH"

HUB_DIR="$HOME/mason-hub"
SKILLS_DIR="$HUB_DIR/skills"
NOTIFY_MASON="$SKILLS_DIR/notify-mason.sh"
LOG_FILE="$HUB_DIR/logs/agent.log"
AUDIT_FILE="$HUB_DIR/domains/ecommerce/projects/srx/audit.jsonl"
AUDIT_LOG="$HUB_DIR/logs/audit.jsonl"
TASK_LOG_DIR="$HUB_DIR/logs/tasks"
MEMORY_DIR="$HUB_DIR/memory"
MAX_VERIFY_ROUNDS=3
MAX_PM_RETRIES=2

# --- 结构化任务元数据（Dispatcher 通过环境变量传入）---
TASK_EXPECTED_OUTPUT="${TASK_EXPECTED_OUTPUT:-}"
TASK_VERIFY_COMMAND="${TASK_VERIFY_COMMAND:-}"
TASK_OUTPUT_PATH="${TASK_OUTPUT_PATH:-}"
TASK_MAX_DURATION="${TASK_MAX_DURATION:-0}"
TASK_CONTEXT_FILES="${TASK_CONTEXT_FILES:-}"
TASK_TYPE="${TASK_TYPE:-execute}"

# --- Chain depth 限制（防止无限递归）---
CHAIN_DEPTH=${CHAIN_DEPTH:-0}
MAX_CHAIN_DEPTH=10

if [ "$CHAIN_DEPTH" -ge "$MAX_CHAIN_DEPTH" ]; then
  echo "🛑 Chain depth limit reached ($MAX_CHAIN_DEPTH). Force stopping."
  if [ -x "$SLACK_NOTIFY" ]; then
    "$SLACK_NOTIFY" "#mason-alerts" "🛑 自动 escalation 链达到深度上限 ($MAX_CHAIN_DEPTH)。需要 Mason 手动介入。" "QA Bot" ":warning:" 2>/dev/null || true
  fi
  [ -x "$NOTIFY_MASON" ] && "$NOTIFY_MASON" "Escalation 链超限" "自动 escalation 达到深度上限 ($MAX_CHAIN_DEPTH)，需要手动介入" "alert" 2>/dev/null || true
  exit 1
fi

# --- 参数检查 ---
if [ $# -lt 2 ]; then
  echo "用法: $0 <agent配置文件> <任务内容>"
  echo "示例: $0 agents/EMP_0000/config.md \"读取context.json并分析\""
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
# 支持新格式 agents/EMP_0002/config.md 和旧格式 agents/EMP_0002/config.md
if [[ "$(basename "$1")" == "config.md" ]]; then
  AGENT_NAME=$(basename "$(dirname "$1")")
else
  AGENT_NAME=$(basename "$1" .md)
fi

# --- Lane Queue: serial execution lock ---
LANE_LOCK="$HUB_DIR/scripts/lane-lock.sh"
AGENT_LANE=""
if [ -x "$LANE_LOCK" ]; then
  AGENT_LANE=$("$LANE_LOCK" get-lane "$AGENT_NAME")
  if [ -n "$AGENT_LANE" ]; then
    # Check if parent already holds this lane (chain execution)
    if [ "${LANE_LOCK_HELD:-}" = "$AGENT_LANE" ]; then
      echo "[lane-lock] Lane $AGENT_LANE inherited from parent" >&2
      AGENT_LANE=""  # don't release on exit
    elif ! "$LANE_LOCK" acquire "$AGENT_LANE" "$AGENT_NAME" "${TASK_ID:-unknown}" --wait 1200; then
      echo "❌ Cannot acquire $AGENT_LANE lane lock" >&2
      exit 1
    else
      export LANE_LOCK_HELD="$AGENT_LANE"
    fi
  fi
fi

cleanup() {
  local exit_code=$?
  # 记录异常退出（非正常结束 + 非参数错误）
  if [ $exit_code -ne 0 ] && [ $exit_code -ne 1 ]; then
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] ❌ run-agent.sh 异常退出 (code=$exit_code, agent=${AGENT_NAME:-unknown}, line=${BASH_LINENO[0]:-?})" >> "$LOG_FILE" 2>/dev/null || true
    echo "[$ts] ❌ run-agent.sh 异常退出 (code=$exit_code, agent=${AGENT_NAME:-unknown})" >&2
  fi
  # 释放 lane lock
  if [ -n "${AGENT_LANE:-}" ] && [ -x "${LANE_LOCK:-}" ]; then
    "$LANE_LOCK" release "$AGENT_LANE" "$AGENT_NAME" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# --- 加载 API key ---
source ~/slack-bot/.env
export ANTHROPIC_API_KEY

# --- 检测 Claude Code session 嵌套（claude -p 不支持嵌套）---
if [ "${CLAUDECODE:-}" = "1" ]; then
  echo "❌ 错误：不能在 Claude Code session 内运行 run-agent.sh（claude -p 不支持嵌套）"
  echo "请用以下替代方式："
  echo "  1. 另开终端运行"
  echo "  2. 使用 /dev-task 等 skill 替代"
  exit 1
fi

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

# --- Worktree 模式（USE_WORKTREE=1 时在独立分支上工作）---
WORKTREE_BRANCH=""
WORKTREE_DIR=""
USE_WORKTREE="${USE_WORKTREE:-0}"
if [ "$USE_WORKTREE" = "1" ] && [ "$RUN_DIR" = "$HUB_DIR" ]; then
  WORKTREE_SCRIPT="$HUB_DIR/scripts/worktree.sh"
  if [ -x "$WORKTREE_SCRIPT" ]; then
    WT_OUTPUT=$("$WORKTREE_SCRIPT" create "$AGENT_NAME" "$TASK_ID" "$(echo "$TASK" | head -c 80)" 2>&1) || true
    # 最后一行是目录路径
    WORKTREE_DIR=$(echo "$WT_OUTPUT" | tail -1)
    if [ -d "$WORKTREE_DIR" ]; then
      RUN_DIR="$WORKTREE_DIR"
      WORKTREE_BRANCH="agent/${AGENT_NAME}/${TASK_ID}"
      echo "[worktree] Agent 将在分支上工作: $WORKTREE_BRANCH → $WORKTREE_DIR" >&2
      log_structured "info" "Worktree mode: branch=$WORKTREE_BRANCH dir=$WORKTREE_DIR"
    else
      echo "[worktree] ⚠️ 创建失败，回退到 main 直接工作" >&2
      USE_WORKTREE=0
    fi
  else
    echo "[worktree] ⚠️ worktree.sh 不存在，回退到 main 直接工作" >&2
    USE_WORKTREE=0
  fi
fi

# --- 提取 skills 数组（从 YAML frontmatter）---
HAS_VERIFY_LOOP=false
SKILLS_RAW=$(awk 'BEGIN{c=0; in_skills=0} /^---$/{c++; next} c>=2{exit} c==1{
  if(/^skills:/){in_skills=1; if(/\[\]/){in_skills=0}; next}
  if(in_skills && /^  - /){gsub(/^  - /,""); print; next}
  if(in_skills && !/^  /){in_skills=0}
}' "$AGENT_FILE")
if echo "$SKILLS_RAW" | grep -q "dev-verify-loop"; then
  HAS_VERIFY_LOOP=true
fi

# --- Phase 1: Task ID 提取 ---
TASK_ID=$(echo "$TASK" | grep -oP '(?:task_id:\s*)\K[A-Za-z0-9_\-]+' | head -1 || true)
if [ -z "$TASK_ID" ]; then
  TASK_ID=$(echo "$TASK" | grep -oP 'srx_\d{8}_\w+' | head -1 || true)
fi
if [ -z "$TASK_ID" ]; then
  TASK_ID="task_${AGENT_NAME}_$(date +%s)"
fi
mkdir -p "$TASK_LOG_DIR"

# --- Phase 2: 经验记忆注入（语义搜索优先，全量回退）---
# 预算：注入内容不超过 MAX_INJECT_CHARS 字符（约 MAX_INJECT_CHARS/4 tokens）
MAX_INJECT_CHARS=16000  # ~4000 tokens
INJECT_USED=${#SYSPROMPT}

inject_if_exists() {
  local file="$1"
  local label="$2"
  if [ -f "$file" ] && [ -s "$file" ]; then
    local file_size
    file_size=$(stat -c %s "$file")
    local total_after=$(( INJECT_USED + file_size + 50 ))
    local budget=$(( ${#SYSPROMPT} + MAX_INJECT_CHARS ))

    if [ "$total_after" -gt "$budget" ]; then
      echo "[context-budget] SKIP $label (${file_size}B would exceed budget)" >&2
      return
    fi

    SYSPROMPT="${SYSPROMPT}

---
## ${label}

$(cat "$file")"
    INJECT_USED=${#SYSPROMPT}
  fi
}

VENV_PYTHON="$HUB_DIR/.venv/bin/python3"
inject_semantic_search() {
  local task_desc="$1"
  if [ ! -x "$VENV_PYTHON" ]; then
    return 1
  fi
  if [ ! -d "$HUB_DIR/memory/chroma_db" ]; then
    return 1
  fi
  local doc_count
  doc_count=$("$VENV_PYTHON" -c "
import chromadb
c = chromadb.PersistentClient(path='$HUB_DIR/memory/chroma_db')
try:
    print(c.get_collection('agent_memory').count())
except:
    print(0)
" 2>/dev/null) || doc_count=0
  if [ "$doc_count" -eq 0 ] 2>/dev/null; then
    return 1
  fi
  local search_result
  search_result=$("$VENV_PYTHON" "$HUB_DIR/scripts/memory-search.py" \
    "$task_desc" --scope all --top 5 --format inject 2>/dev/null) || return 1
  if [ -n "$search_result" ] && [ ${#search_result} -gt 20 ]; then
    echo "$search_result"
    return 0
  fi
  return 1
}

# 策略：语义搜索优先（跨 agent 精准召回），失败才回退全量 lessons
# 之前两个都注入，浪费 ~1000-2000 tokens
SEMANTIC_RESULT=$(inject_semantic_search "$TASK" 2>/dev/null) || SEMANTIC_RESULT=""
if [ -n "$SEMANTIC_RESULT" ]; then
  SYSPROMPT="${SYSPROMPT}

---
${SEMANTIC_RESULT}"
  INJECT_USED=${#SYSPROMPT}
  echo "[context] Layer 3 semantic search for $AGENT_NAME (skipping full lessons)" >&2
else
  # 回退：全量注入 lessons 文件
  LESSONS_FILE="$HUB_DIR/agents/${AGENT_NAME}/memory/lessons.md"
  if [ -f "$LESSONS_FILE" ] && [ -s "$LESSONS_FILE" ]; then
    SYSPROMPT="${SYSPROMPT}

---
## 历史经验（来自过去任务的教训，请参考但不必完全遵循）

$(cat "$LESSONS_FILE")"
    INJECT_USED=${#SYSPROMPT}
  fi
  echo "[context] Layer 2 full lessons fallback for $AGENT_NAME" >&2
fi

# --- Phase 2.5: 知识注入（context_files 优先，否则按角色默认）---
if [ -n "$TASK_CONTEXT_FILES" ]; then
  # 任务指定了精确的 context files → 跳过默认 knowledge 注入
  IFS=',' read -ra CTX_FILES <<< "$TASK_CONTEXT_FILES"
  for ctx_file in "${CTX_FILES[@]}"; do
    ctx_file=$(echo "$ctx_file" | xargs)  # trim whitespace
    local_path="$HUB_DIR/$ctx_file"
    if [ -f "$local_path" ]; then
      inject_if_exists "$local_path" "📄 Context: $ctx_file"
    fi
  done
  echo "[context] Task-specific context files: $TASK_CONTEXT_FILES" >&2
else
  # 默认：按 agent 角色注入知识文件
  case "$AGENT_NAME" in
    EMP_0000)  # Meta Manager — 全局知识
      inject_if_exists "$HUB_DIR/meta/knowledge_base.md" "系统知识库"
      ;;
    EMP_0001)  # PM — 项目决策 + 电商知识
      inject_if_exists "$HUB_DIR/domains/ecommerce/projects/srx/decisions.md" "素仁轩决策记录"
      inject_if_exists "$HUB_DIR/domains/ecommerce/knowledge_base.md" "电商知识库"
      ;;
    EMP_0003)  # Domain Manager — 电商知识 + 决策
      inject_if_exists "$HUB_DIR/domains/ecommerce/knowledge_base.md" "电商知识库"
      inject_if_exists "$HUB_DIR/domains/ecommerce/projects/srx/decisions.md" "素仁轩决策记录"
      ;;
    EMP_0005)  # Dev — 项目决策（轻量）
      inject_if_exists "$HUB_DIR/domains/ecommerce/projects/srx/decisions.md" "素仁轩决策记录"
      ;;
    # EMP_0002 (Platform Dev), EMP_0004 (SRE), EMP_0006 (Scout) — 无额外知识注入
  esac
fi

# --- Phase 2.6: 收工流程注入（query 类任务跳过）---
if [ "$TASK_TYPE" != "query" ]; then
  POST_TASK_FILE="$HUB_DIR/docs/procedures/post-task.md"
  if [ -f "$POST_TASK_FILE" ]; then
    inject_if_exists "$POST_TASK_FILE" "⚠️ 收工流程（任务完成后必须执行）"
  fi
else
  echo "[context] SKIP post-task (task_type=query)" >&2
fi

# --- Phase 2.7: Gene 行为原语注入（query 类任务跳过）---
if [ "$TASK_TYPE" != "query" ]; then
  GENES_DIR="$HUB_DIR/shared/genes"
  case "$AGENT_NAME" in
    EMP_0002|EMP_0004|EMP_0005|EMP_0009|EMP_0014)
      inject_if_exists "$GENES_DIR/skeptical_verification.md" "🧬 Gene: Skeptical Verification"
      ;;
    EMP_0000|EMP_0001|EMP_0003|EMP_0008)
      inject_if_exists "$GENES_DIR/practical_epistemology.md" "🧬 Gene: Practical Epistemology"
      ;;
  esac
  case "$AGENT_NAME" in
    EMP_0002|EMP_0004)
      # SRE + Platform Dev：注入 Ashby 多样性基因
      inject_if_exists "$GENES_DIR/ashby_variety.md" "🧬 Gene: Ashby Variety Check"
      ;;
  esac
else
  echo "[context] SKIP genes (task_type=query)" >&2
fi

# --- Phase 2.8: 结构化任务元数据注入 ---
if [ -n "$TASK_EXPECTED_OUTPUT" ]; then
  TASK="${TASK}

## 预期产出
${TASK_EXPECTED_OUTPUT}"
fi
if [ -n "$TASK_OUTPUT_PATH" ]; then
  TASK="${TASK}

## 输出路径
结果写入: ${TASK_OUTPUT_PATH}"
fi

# --- 提取 launcher_args（从 YAML frontmatter）---
LAUNCHER_ARGS=$(awk 'BEGIN{c=0; in_la=0} /^---$/{c++; next} c>=2{exit} c==1{
  if(/^launcher_args:/){in_la=1; next}
  if(in_la && /^  - /){gsub(/^  - /,""); printf "%s ", $0; next}
  if(in_la && !/^  /){in_la=0}
}' "$AGENT_FILE")

# --- 辅助函数：调用 claude -p 并记录 token ---
# 走 Max 订阅（OAuth）而非 API key 计费：unset ANTHROPIC_API_KEY
# Gateway (mason-gateway.py) 仍走 API key，这里只影响 claude -p
call_claude() {
  local prompt="$1"
  local json_out
  json_out=$(cd "$RUN_DIR" && unset ANTHROPIC_API_KEY && claude -p \
    --output-format json \
    $LAUNCHER_ARGS \
    --system-prompt "$SYSPROMPT" \
    "$prompt" 2>&1)

  # 检测 Max 限额错误，记录并通知
  if echo "$json_out" | grep -qiE 'rate.limit|quota|exceeded|capacity'; then
    echo "⚠️ Max 订阅限额触发，任务延迟" >&2
    local EMIT_EVENT="$HUB_DIR/scripts/emit_event.sh"
    if [ -x "$EMIT_EVENT" ]; then
      "$EMIT_EVENT" "max-rate-limit" "$AGENT_NAME" "warning" 2 \
        "{\"agent\":\"$AGENT_NAME\",\"error\":\"max_subscription_rate_limit\"}" 2>/dev/null || true
    fi
  fi

  echo "$json_out"
}

extract_result() {
  local json_out="$1"
  python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" <<< "$json_out" 2>/dev/null || echo "$json_out"
}

log_api_usage() {
  local json_out="$1"
  local dur="$2"
  python3 "$HUB_DIR/scripts/api_logger.py" \
    --agent-id "$AGENT_NAME" \
    --agent-name "$AGENT_NAME" \
    --action "run-agent" \
    --duration "$dur" \
    --json-result "$json_out" 2>/dev/null || true
}

# --- 辅助函数：从 claude JSON 输出提取 token/cost 数据（供审计记录使用）---
extract_token_data() {
  local json_out="$1"
  python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    u = data.get('usage', {})
    inp = u.get('input_tokens', 0) + u.get('cache_creation_input_tokens', 0) + u.get('cache_read_input_tokens', 0)
    out = u.get('output_tokens', 0)
    cost = data.get('total_cost_usd', 0)
    turns = data.get('num_turns', 1)
    model = ''
    mu = data.get('modelUsage', {})
    if mu:
        model = list(mu.keys())[0] if mu else ''
    print(json.dumps({'input_tokens': inp, 'output_tokens': out, 'cost_usd': round(cost, 6), 'num_turns': turns, 'model': model}))
except:
    print('{}')
" <<< "$json_out" 2>/dev/null || echo "{}"
}

# --- 辅助函数：写统一审计记录 ---
write_audit() {
  local status="$1"
  local extra_fields="$2"  # 额外 JSON 字段（逗号开头）
  local token_json="$3"    # extract_token_data 的输出
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local end_epoch
  end_epoch=$(date +%s)
  local dur=$((end_epoch - START_EPOCH))
  local task_brief
  task_brief=$(printf '%s' "$TASK" | head -c 80 | tr '\n' ' ' | tr '"' "'")

  # 解析 token 数据
  local inp out cost turns model
  inp=$(echo "$token_json" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('input_tokens',0))" 2>/dev/null || echo 0)
  out=$(echo "$token_json" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('output_tokens',0))" 2>/dev/null || echo 0)
  cost=$(echo "$token_json" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('cost_usd',0))" 2>/dev/null || echo 0)
  turns=$(echo "$token_json" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('num_turns',1))" 2>/dev/null || echo 1)
  model=$(echo "$token_json" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('model',''))" 2>/dev/null || echo "")

  printf '{"timestamp":"%s","task_id":"%s","agent":"%s","task":"%s","status":"%s","duration":%d,"input_tokens":%s,"output_tokens":%s,"cost_usd":%s,"num_turns":%s,"model":"%s"%s}\n' \
    "$ts" "$TASK_ID" "$AGENT_NAME" "$task_brief" "$status" "$dur" "$inp" "$out" "$cost" "$turns" "$model" "$extra_fields" >> "$AUDIT_LOG"
}

# --- 辅助函数：从 agent 输出中提取修改的文件 ---
# 使用 GIT_BASELINE（调用前快照）来只检测 agent 实际造成的改动
extract_modified_files() {
  local output="$1"
  # Method 1: Parse agent output for file path patterns
  local files
  files=$(echo "$output" | grep -oP '(?:~/surenxuan/|/home/hangn/surenxuan/|(?:backend|frontend)/)\S+\.(?:py|jsx|js|ts)' | sort -u | head -20 || true)
  files=$(echo "$files" | sed "s|$HOME/surenxuan/||g" | sed 's|~/surenxuan/||g' | sort -u || true)
  # Method 2: Compare git diff against pre-agent baseline (only new changes)
  local git_files_now git_new_files
  git_files_now=$(cd "$RUN_DIR" && git diff --name-only 2>/dev/null | grep -E '\.(py|jsx|js|ts)$' | sort || true)
  git_new_files=$(comm -13 <(echo "$GIT_BASELINE") <(echo "$git_files_now") 2>/dev/null || true)
  # Combine and deduplicate
  echo -e "${files}\n${git_new_files}" | sort -u | grep -v '^$' | paste -sd',' - || true
}

# --- 辅助函数：用 test-map.json 查找测试模块 ---
find_test_modules() {
  local modified_files="$1"
  local map_file="$SKILLS_DIR/dev-tools/test-map.json"
  if [ ! -f "$map_file" ]; then
    echo ""
    return
  fi
  python3 -c "
import json, sys
with open('$map_file') as f:
    tmap = json.load(f)
files = '$modified_files'.split(',')
modules = set()
for f in files:
    f = f.strip()
    for pattern, mods in tmap.items():
        if pattern.rstrip('*') in f or f == pattern:
            modules.update(mods)
if modules:
    # Return the first matched module (most specific)
    print(list(modules)[0])
" 2>/dev/null || echo ""
}

# --- 辅助函数：发送 Slack 通知 ---
send_slack_notify() {
  local message="$1"
  local channel="${SLACK_CHANNEL:-}"
  if [ -n "$channel" ] && [ -x "$SLACK_NOTIFY" ]; then
    "$SLACK_NOTIFY" "$channel" "$message" "QA Bot" ":test_tube:" 2>/dev/null || true
  fi
}

# --- 辅助函数：格式化 Slack 结构化消息 ---
format_slack_message() {
  local status="$1"   # success | failed | escalated
  local agent="$2"
  local task_id="$3"
  local rounds="$4"
  local details="$5"  # extra info (error summary, etc.)
  local duration="$6"

  local emoji duration_str
  case "$status" in
    success)   emoji="✅" ;;
    failed)    emoji="❌" ;;
    escalated) emoji="⬆️" ;;
    *)         emoji="ℹ️" ;;
  esac

  if [ -n "$duration" ] && [ "$duration" -gt 0 ] 2>/dev/null; then
    local mins=$((duration / 60))
    local secs=$((duration % 60))
    duration_str="${mins}m${secs}s"
  else
    duration_str="N/A"
  fi

  echo "${emoji} *${task_id}* | ${agent} | ${rounds} 轮 | ${duration_str}
${details}"
}

# --- 结构化日志函数 ---
log_structured() {
  local event_type="$1"
  local message="$2"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local safe_msg
  safe_msg=$(printf '%s' "$message" | tr '"' "'" | tr '\n' ' ' | head -c 500)
  printf '{"timestamp":"%s","agent_id":"%s","task_id":"%s","event_type":"%s","message":"%s"}\n' \
    "$ts" "$AGENT_NAME" "$TASK_ID" "$event_type" "$safe_msg" >> "$LOG_FILE"
}

# --- 记录开始 ---
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_EPOCH=$(date +%s)
TASK_BRIEF=$(printf '%s' "$TASK" | head -c 200 | tr '\n' ' ')
log_structured "start" "Task started. Work dir: $RUN_DIR. Verify: $HAS_VERIFY_LOOP. Task: $TASK_BRIEF"
echo "<<<AGENT_START $AGENT_NAME>>>"

# === 主执行逻辑 ===

# 记录 agent 调用前的 git diff baseline（用于只检测 agent 新增的改动）
GIT_BASELINE=$(cd "$RUN_DIR" && git diff --name-only 2>/dev/null | grep -E '\.(py|jsx|js|ts)$' | sort || true)

if [ "$HAS_VERIFY_LOOP" = false ]; then
  # --- 非开发类 agent：直接执行，无验证 ---
  # Phase 1: 保存输入日志
  echo "$TASK" > "${TASK_LOG_DIR}/${TASK_ID}_round1_input.txt"

  JSON_OUTPUT=$(call_claude "$TASK") || true
  OUTPUT=$(extract_result "$JSON_OUTPUT")

  # Phase 1: 保存输出日志
  echo "$JSON_OUTPUT" > "${TASK_LOG_DIR}/${TASK_ID}_round1_output.json"

  END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  END_EPOCH=$(date +%s)
  DURATION=$((END_EPOCH - START_EPOCH))
  TASK_SUMMARY=$(printf %s "$TASK" | head -c 50)
  TASK_SUMMARY=${TASK_SUMMARY//$'\n'/ }

  # 检查 claude -p 是否返回有效输出
  if [ -z "$OUTPUT" ] || [ ${#OUTPUT} -lt 10 ]; then
    echo "❌ claude -p 返回空或无效输出 (len=${#OUTPUT})" >&2
    TOKEN_DATA=$(extract_token_data "$JSON_OUTPUT")
    write_audit "failed" ',"error":"empty_output"' "$TOKEN_DATA"
    EMIT_EVENT="$HUB_DIR/scripts/emit_event.sh"
    if [ -x "$EMIT_EVENT" ]; then
      "$EMIT_EVENT" "agent-task-failed" "$AGENT_NAME" "error" 2 \
        "{\"task_id\":\"$TASK_ID\",\"agent\":\"$AGENT_NAME\",\"error\":\"empty_output\",\"duration\":$DURATION}" 2>/dev/null || true
    fi
    exit 1
  fi

  echo "$OUTPUT"
  echo "$OUTPUT" >> "$LOG_FILE"

  # Phase 1: 生成 summary
  cat > "${TASK_LOG_DIR}/${TASK_ID}_summary.json" <<EOSUMMARY
{"task_id":"$TASK_ID","agent":"$AGENT_NAME","start_time":"$START_TIME","end_time":"$END_TIME","total_rounds":1,"final_status":"completed","task_log_dir":"$TASK_LOG_DIR"}
EOSUMMARY

  TOKEN_DATA=$(extract_token_data "$JSON_OUTPUT")
  write_audit "completed" "" "$TOKEN_DATA"
  log_api_usage "$JSON_OUTPUT" "$DURATION"

  # 发射任务完成事件（供 Dispatcher/Gateway 追踪）
  EMIT_EVENT="$HUB_DIR/scripts/emit_event.sh"
  if [ -x "$EMIT_EVENT" ]; then
    "$EMIT_EVENT" "agent-task-complete" "$AGENT_NAME" "ok" 1 \
      "{\"task_id\":\"$TASK_ID\",\"agent\":\"$AGENT_NAME\",\"status\":\"completed\",\"duration\":$DURATION}" 2>/dev/null || true
  fi

  # Phase 3: 非开发类 agent 的 ACTION 解析
  ACTION_LINE=$(echo "$OUTPUT" | grep "^ACTION:" | tail -1)
  if [ -n "$ACTION_LINE" ]; then
    ACTION_JSON=$(echo "$ACTION_LINE" | sed 's/^ACTION://')
    ACTION_TYPE=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type',''))" 2>/dev/null || echo "")

    case "$ACTION_TYPE" in
      "reassign_to_dev")
        NEW_TASK=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_task',''))" 2>/dev/null)
        RETRY_COUNT=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('retry_count',0))" 2>/dev/null)
        echo "🔄 PM reassigning to Dev (retry $RETRY_COUNT, chain depth: $((CHAIN_DEPTH+1)))"
        send_slack_notify "🔄 PM 重新分配任务给 Dev（第 ${RETRY_COUNT} 次重分配）"
        CHAIN_DEPTH=$((CHAIN_DEPTH+1)) bash "$HUB_DIR/scripts/run-agent.sh" \
          agents/EMP_0005/config.md "$NEW_TASK" "${SLACK_CHANNEL:-}"
        ;;
      "escalate_to_platform_dev")
        CONTEXT=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('context',''))" 2>/dev/null)
        echo "⬆️ Escalating to Platform Dev (chain depth: $((CHAIN_DEPTH+1)))"
        send_slack_notify "⬆️ PM escalate 给 Platform Dev"
        CHAIN_DEPTH=$((CHAIN_DEPTH+1)) bash "$HUB_DIR/scripts/run-agent.sh" \
          agents/EMP_0002/config.md "Escalation from PM. task_id: $TASK_ID. $CONTEXT" "${SLACK_CHANNEL:-}"
        ;;
      "escalate_to_mason")
        CONTEXT=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('context',''))" 2>/dev/null)
        echo "🔴 Escalating to Mason"
        if [ -x "$SLACK_NOTIFY" ]; then
          "$SLACK_NOTIFY" "#mason-alerts" "🔴 需要 Mason 决策: 任务 $TASK_ID - $CONTEXT" "QA Bot" ":rotating_light:" 2>/dev/null || true
        fi
        [ -x "$NOTIFY_MASON" ] && "$NOTIFY_MASON" "需要决策: $TASK_ID" "$CONTEXT" "alert" 2>/dev/null || true
        ;;
      "task_complete")
        SUMMARY=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('summary',''))" 2>/dev/null)
        echo "✅ Task chain completed: $SUMMARY"
        send_slack_notify "✅ 任务 $TASK_ID 完成：$SUMMARY"
        ;;
    esac
  fi

else
  # --- 开发类 agent：执行 + 强制验证循环 ---
  ROUND=0
  VERIFY_PASSED=false
  ATTEMPTS_JSON="["
  CURRENT_PROMPT="$TASK"

  while [ $ROUND -lt $MAX_VERIFY_ROUNDS ]; do
    ROUND=$((ROUND + 1))
    log_structured "info" "Round $ROUND / $MAX_VERIFY_ROUNDS started"
    echo "--- Round $ROUND / $MAX_VERIFY_ROUNDS ---"

    # Phase 1: 保存本轮输入
    echo "$CURRENT_PROMPT" > "${TASK_LOG_DIR}/${TASK_ID}_round${ROUND}_input.txt"

    # Step 1: Call claude -p
    JSON_OUTPUT=$(call_claude "$CURRENT_PROMPT") || true
    OUTPUT=$(extract_result "$JSON_OUTPUT")

    # Phase 1: 保存本轮输出
    echo "$JSON_OUTPUT" > "${TASK_LOG_DIR}/${TASK_ID}_round${ROUND}_output.json"

    ROUND_EPOCH=$(date +%s)
    ROUND_DURATION=$((ROUND_EPOCH - START_EPOCH))
    log_api_usage "$JSON_OUTPUT" "$ROUND_DURATION"

    # 检查 claude -p 是否返回有效输出
    if [ -z "$OUTPUT" ] || [ ${#OUTPUT} -lt 10 ]; then
      echo "❌ claude -p 返回空或无效输出 (round $ROUND, len=${#OUTPUT})" >&2
      TOKEN_DATA=$(extract_token_data "$JSON_OUTPUT")
      write_audit "failed" ",\"error\":\"empty_output_round${ROUND}\",\"verify_round\":$ROUND" "$TOKEN_DATA"
      exit 1
    fi

    echo "$OUTPUT" >> "$LOG_FILE"

    # Step 2: Extract modified files
    MODIFIED=$(extract_modified_files "$OUTPUT")
    if [ -z "$MODIFIED" ]; then
      echo "[verify] No modified files detected, skipping verification"
      echo "$OUTPUT"
      VERIFY_PASSED=true
      break
    fi
    echo "[verify] Modified files: $MODIFIED"

    # Step 3: Find test module
    TEST_MODULE=$(find_test_modules "$MODIFIED")
    echo "[verify] Test module: ${TEST_MODULE:-full suite}"

    # Step 4: Run dev-verify-loop
    echo "[verify] Running verification..."
    VERIFY_EXIT=0
    VERIFY_OUTPUT=$("$SKILLS_DIR/dev-tools/dev-verify-loop.sh" "$MODIFIED" "$TEST_MODULE" 2>&1) || VERIFY_EXIT=$?

    echo "$VERIFY_OUTPUT" >> "$LOG_FILE"

    # Build attempt record
    CHANGES_BRIEF=$(echo "$MODIFIED" | head -c 200)
    if [ $VERIFY_EXIT -eq 0 ]; then
      ERROR_BRIEF="none"
      VERIFY_PASSED=true
      ATTEMPTS_JSON="${ATTEMPTS_JSON}{\"round\":$ROUND,\"changes\":\"$CHANGES_BRIEF\",\"error\":\"none\"}"
      echo "[verify] Round $ROUND: PASSED"
      echo "$OUTPUT"
      echo ""
      echo "$VERIFY_OUTPUT"
      break
    else
      ERROR_BRIEF=$(echo "$VERIFY_OUTPUT" | grep -E "FAIL|ERROR|assert|Error" | head -5 | tr '\n' ' ' | head -c 300 || true)
      ERROR_BRIEF=${ERROR_BRIEF//\"/\\\"}  # escape quotes for JSON
      ATTEMPTS_JSON="${ATTEMPTS_JSON}{\"round\":$ROUND,\"changes\":\"$CHANGES_BRIEF\",\"error\":\"$ERROR_BRIEF\"}"
      [ $ROUND -lt $MAX_VERIFY_ROUNDS ] && ATTEMPTS_JSON="${ATTEMPTS_JSON},"
      echo "[verify] Round $ROUND: FAILED"

      if [ $ROUND -lt $MAX_VERIFY_ROUNDS ]; then
        # Construct fix prompt for next round
        CURRENT_PROMPT="验证失败，请修复以下问题然后重新修改代码：

--- 验证输出 ---
$VERIFY_OUTPUT
--- 原始任务 ---
$TASK"
      fi
    fi
  done

  ATTEMPTS_JSON="${ATTEMPTS_JSON}]"

  # --- 结果处理 ---
  END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  END_EPOCH=$(date +%s)
  DURATION=$((END_EPOCH - START_EPOCH))
  TASK_SUMMARY=$(printf %s "$TASK" | head -c 50)
  TASK_SUMMARY=${TASK_SUMMARY//$'\n'/ }

  if [ "$VERIFY_PASSED" = true ]; then
    # Phase 1: 生成 summary
    cat > "${TASK_LOG_DIR}/${TASK_ID}_summary.json" <<EOSUMMARY
{"task_id":"$TASK_ID","agent":"$AGENT_NAME","start_time":"$START_TIME","end_time":"$END_TIME","total_rounds":$ROUND,"final_status":"completed","task_log_dir":"$TASK_LOG_DIR"}
EOSUMMARY

    TOKEN_DATA=$(extract_token_data "$JSON_OUTPUT")
    write_audit "completed" ",\"verify_rounds\":$ROUND" "$TOKEN_DATA"

    # 发射任务完成事件（供 Dispatcher/Gateway 追踪）
    EMIT_EVENT="$HUB_DIR/scripts/emit_event.sh"
    if [ -x "$EMIT_EVENT" ]; then
      "$EMIT_EVENT" "agent-task-complete" "$AGENT_NAME" "ok" 1 \
        "{\"task_id\":\"$TASK_ID\",\"agent\":\"$AGENT_NAME\",\"status\":\"completed\",\"rounds\":$ROUND,\"duration\":$DURATION}" 2>/dev/null || true
    fi

    # Slack 结构化成功通知
    SLACK_SUCCESS_MSG=$(format_slack_message "success" "$AGENT_NAME" "$TASK_ID" "$ROUND" "修改文件: ${MODIFIED:-none}" "$DURATION")
    send_slack_notify "$SLACK_SUCCESS_MSG"

    # Phase 2: 成功时记录经验
    LESSONS_SIZE=$(stat -c %s "$LESSONS_FILE" 2>/dev/null || echo 0)
    if [ -f "$LESSONS_FILE" ] && [ "$LESSONS_SIZE" -lt 51200 ]; then
      LESSON_PROMPT="任务完成。请用 1-3 句话总结这次任务中值得记住的经验教训（遇到了什么坑、怎么解决的、下次该注意什么）。只输出经验内容，格式：## $(date +%Y-%m-%d): <模块名>\n- <经验1>\n- <经验2>"
      LESSON_JSON=$(cd "$RUN_DIR" && unset ANTHROPIC_API_KEY && claude -p \
        --output-format json \
        --system-prompt "你是一个代码开发助手。简洁地总结经验教训。" \
        "$LESSON_PROMPT" 2>/dev/null) || true
      LESSON=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" <<< "$LESSON_JSON" 2>/dev/null || echo "")
      if [ -n "$LESSON" ] && [ ${#LESSON} -gt 10 ]; then
        echo -e "\n$LESSON" >> "$LESSONS_FILE"
      fi
    elif [ "$LESSONS_SIZE" -ge 51200 ]; then
      echo "⚠️ Lessons file for $AGENT_NAME exceeds 50KB limit. Skipping."
    fi
  else
    # === 补丁 3：失败处理 ===

    # 3.1 恢复代码
    echo "[repair_failed] 3 rounds failed. Restoring code..."
    cd "$RUN_DIR" && git checkout -- . 2>/dev/null || true
    echo "[repair_failed] Code restored to last commit state"

    # 3.2 生成失败摘要
    ROOT_CAUSE=$(echo "$OUTPUT" | grep -iE "root.?cause|根因|原因|problem|issue" | head -2 | tr '\n' ' ' | head -c 200 || true)
    ROOT_CAUSE=${ROOT_CAUSE//\"/\\\"}
    TASK_ID_EXTRACTED="$TASK_ID"

    # 3.2.1 计算 PM 重试次数
    PM_RETRY_COUNT=0
    MAX_PM_RETRIES=2
    if [ -f "$AUDIT_LOG" ] && [ "$TASK_ID_EXTRACTED" != "unknown" ]; then
      PM_RETRY_COUNT=$(python3 -c "
import json, sys
count = 0
with open('$AUDIT_LOG') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
            if r.get('task_id') == '$TASK_ID_EXTRACTED' and r.get('status') == 'repair_failed':
                count = max(count, r.get('pm_retry_count', 0) + 1)
        except: continue
print(count)
" 2>/dev/null || echo "0")
      PM_RETRY_COUNT=${PM_RETRY_COUNT:-0}
    fi

    FAIL_SUMMARY="{\"task_id\":\"$TASK_ID_EXTRACTED\",\"agent\":\"$AGENT_NAME\",\"status\":\"repair_failed\",\"pm_retry_count\":$PM_RETRY_COUNT,\"attempts\":$ATTEMPTS_JSON,\"root_cause_guess\":\"$ROOT_CAUSE\",\"code_restored\":true,\"timestamp\":\"$END_TIME\"}"

    # Phase 1: 生成失败 summary
    cat > "${TASK_LOG_DIR}/${TASK_ID}_summary.json" <<EOSUMMARY
{"task_id":"$TASK_ID","agent":"$AGENT_NAME","start_time":"$START_TIME","end_time":"$END_TIME","total_rounds":$ROUND,"final_status":"repair_failed","pm_retry_count":$PM_RETRY_COUNT,"task_log_dir":"$TASK_LOG_DIR"}
EOSUMMARY

    # 3.3 写入审计日志（统一格式 + token 数据）
    TOKEN_DATA=$(extract_token_data "$JSON_OUTPUT")
    write_audit "repair_failed" ",\"verify_rounds\":$ROUND,\"pm_retry_count\":$PM_RETRY_COUNT,\"root_cause_guess\":\"$ROOT_CAUSE\"" "$TOKEN_DATA"

    # 发射任务失败事件（供 Dispatcher/Gateway 追踪）
    EMIT_EVENT="$HUB_DIR/scripts/emit_event.sh"
    if [ -x "$EMIT_EVENT" ]; then
      "$EMIT_EVENT" "agent-task-complete" "$AGENT_NAME" "error" 2 \
        "{\"task_id\":\"$TASK_ID\",\"agent\":\"$AGENT_NAME\",\"status\":\"repair_failed\",\"rounds\":$ROUND,\"duration\":$DURATION}" 2>/dev/null || true
    fi

    # 3.4 Slack 通知
    # Build per-round error summary
    ROUND_SUMMARIES=""
    for i in $(seq 1 $MAX_VERIFY_ROUNDS); do
      ERR=$(echo "$ATTEMPTS_JSON" | python3 -c "import sys,json; a=json.load(sys.stdin); print(a[$i-1]['error'][:80] if $i<=len(a) else 'N/A')" 2>/dev/null || echo "parse error")
      ROUND_SUMMARIES="${ROUND_SUMMARIES}\n- 第${i}轮: ${ERR}"
    done

    PM_RETRIES_LEFT=$((MAX_PM_RETRIES - PM_RETRY_COUNT))
    if [ "$PM_RETRIES_LEFT" -lt 0 ]; then PM_RETRIES_LEFT=0; fi

    if [ "$PM_RETRY_COUNT" -ge "$MAX_PM_RETRIES" ]; then
      FAIL_DETAIL="自动 escalate → Platform Dev\n$(echo -e "$ROUND_SUMMARIES")\n根因: ${ROOT_CAUSE:-无}"
      SLACK_MSG=$(format_slack_message "escalated" "$AGENT_NAME" "$TASK_ID_EXTRACTED" "$ROUND" "$(echo -e "$FAIL_DETAIL")" "$DURATION")
    else
      FAIL_DETAIL="PM 重试 ${PM_RETRY_COUNT}/${MAX_PM_RETRIES}，剩余 ${PM_RETRIES_LEFT} 次\n$(echo -e "$ROUND_SUMMARIES")\n根因: ${ROOT_CAUSE:-无}"
      SLACK_MSG=$(format_slack_message "failed" "$AGENT_NAME" "$TASK_ID_EXTRACTED" "$ROUND" "$(echo -e "$FAIL_DETAIL")" "$DURATION")
    fi
    send_slack_notify "$SLACK_MSG"

    # Phase 2: 失败时记录经验
    LESSONS_SIZE=$(stat -c %s "$LESSONS_FILE" 2>/dev/null || echo 0)
    if [ -f "$LESSONS_FILE" ] && [ "$LESSONS_SIZE" -lt 51200 ]; then
      ERROR_HEAD=$(echo "$ATTEMPTS_JSON" | python3 -c "import sys,json; a=json.load(sys.stdin); print('; '.join([x.get('error','')[:60] for x in a]))" 2>/dev/null || echo "parse error")
      echo -e "\n## $(date +%Y-%m-%d): [FAILED] $TASK_ID_EXTRACTED\n- ${ROUND}轮修复失败\n- 错误摘要：$ERROR_HEAD\n- 已 escalate" >> "$LESSONS_FILE"
    fi

    echo ""
    echo "=== REPAIR FAILED ==="
    echo "Task: $TASK_ID_EXTRACTED"
    echo "Rounds: $ROUND / $MAX_VERIFY_ROUNDS"
    echo "PM retry: $PM_RETRY_COUNT / $MAX_PM_RETRIES"
    echo "Code restored: yes"
    echo -e "Errors:$ROUND_SUMMARIES"
    echo "Failure summary written to: $AUDIT_LOG"

    # Phase 3: 链式触发 — Dev 失败后自动触发 PM 或 Platform Dev
    if [ "$AGENT_NAME" = "EMP_0005" ]; then
      if [ "$PM_RETRY_COUNT" -lt "$MAX_PM_RETRIES" ]; then
        echo "🔄 Auto-triggering PM evaluation (chain depth: $((CHAIN_DEPTH+1)), PM retry: $((PM_RETRY_COUNT+1))/$MAX_PM_RETRIES)"
        send_slack_notify "🔄 任务 $TASK_ID_EXTRACTED Dev 修复失败，自动触发 PM 评估（第 $((PM_RETRY_COUNT+1))/$MAX_PM_RETRIES 次）"
        CHAIN_DEPTH=$((CHAIN_DEPTH+1)) bash "$HUB_DIR/scripts/run-agent.sh" \
          agents/EMP_0001/config.md \
          "评估 Dev 失败任务。task_id: $TASK_ID_EXTRACTED。PM 重试次数: $PM_RETRY_COUNT/$MAX_PM_RETRIES。请读取 $TASK_LOG_DIR/${TASK_ID_EXTRACTED}_*.json 和 $AUDIT_LOG。运行 ~/mason-hub/skills/monitoring/check-escalation.sh --task $TASK_ID_EXTRACTED 查看完整历史。判断失败类型（A-E），决定下一步。在回复最后一行输出 ACTION。" \
          "${SLACK_CHANNEL:-}"
      else
        echo "⬆️ PM retries exhausted. Auto-escalating to Platform Dev (chain depth: $((CHAIN_DEPTH+1)))"
        send_slack_notify "⬆️ 任务 $TASK_ID_EXTRACTED 已耗尽 PM 重试次数（$MAX_PM_RETRIES/$MAX_PM_RETRIES），自动 escalate 给 Platform Dev"
        CHAIN_DEPTH=$((CHAIN_DEPTH+1)) bash "$HUB_DIR/scripts/run-agent.sh" \
          agents/EMP_0002/config.md \
          "接收 escalation。task_id: $TASK_ID_EXTRACTED。Dev 3轮×$((PM_RETRY_COUNT+1))次均失败。请读取 $TASK_LOG_DIR/${TASK_ID_EXTRACTED}_*.json，分析根因并尝试修复。" \
          "${SLACK_CHANNEL:-}"
      fi
    elif [ "$AGENT_NAME" = "EMP_0002" ]; then
      echo "🔴 Platform Dev also failed. Escalating to Mason."
      if [ -x "$SLACK_NOTIFY" ]; then
        "$SLACK_NOTIFY" "#mason-alerts" "🔴 任务 $TASK_ID_EXTRACTED 所有自动修复均失败（Dev + PM + Platform Dev）。需要 Mason 手动介入。完整日志：$TASK_LOG_DIR/${TASK_ID_EXTRACTED}_*" "QA Bot" ":rotating_light:" 2>/dev/null || true
      fi
      [ -x "$NOTIFY_MASON" ] && "$NOTIFY_MASON" "所有自动修复失败: $TASK_ID_EXTRACTED" "Dev + PM + Platform Dev 均失败，需要手动介入" "alert" 2>/dev/null || true
    fi
  fi
fi

# --- Worktree 收尾：提示 merge 信息 ---
if [ -n "${WORKTREE_BRANCH:-}" ] && [ -n "${WORKTREE_DIR:-}" ]; then
  # 检查 worktree 中是否有新 commit（相对于 main）
  WT_COMMITS=$(cd "$WORKTREE_DIR" && git log --oneline main.."$WORKTREE_BRANCH" 2>/dev/null | wc -l || echo 0)
  if [ "$WT_COMMITS" -gt 0 ]; then
    echo ""
    echo "📌 Worktree 工作完成，分支 $WORKTREE_BRANCH 有 $WT_COMMITS 个新 commit"
    echo "   合并: scripts/worktree.sh merge $WORKTREE_BRANCH"
    echo "   清理: scripts/worktree.sh cleanup $WORKTREE_BRANCH"
    log_structured "info" "Worktree branch $WORKTREE_BRANCH has $WT_COMMITS new commits pending merge"
  else
    # 无改动，直接清理
    "$HUB_DIR/scripts/worktree.sh" cleanup "$WORKTREE_BRANCH" 2>/dev/null || true
    echo "[worktree] 无改动，已自动清理 worktree" >&2
  fi
fi

log_structured "end" "Task finished. Duration: ${DURATION}s"
echo "<<<AGENT_END>>>"
echo "任务完成，结果已记录"
