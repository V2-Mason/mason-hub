#!/bin/bash
set -euo pipefail

HUB_DIR="$HOME/mason-hub"
SKILLS_DIR="$HUB_DIR/skills"
LOG_FILE="$HUB_DIR/logs/agent.log"
AUDIT_FILE="$HUB_DIR/domains/ecommerce/projects/srx/audit.jsonl"
AUDIT_LOG="$HUB_DIR/logs/audit.jsonl"
TASK_LOG_DIR="$HUB_DIR/logs/tasks"
MEMORY_DIR="$HUB_DIR/memory"
MAX_VERIFY_ROUNDS=3
MAX_PM_RETRIES=2

# --- Chain depth 限制（防止无限递归）---
CHAIN_DEPTH=${CHAIN_DEPTH:-0}
MAX_CHAIN_DEPTH=10

if [ "$CHAIN_DEPTH" -ge "$MAX_CHAIN_DEPTH" ]; then
  echo "🛑 Chain depth limit reached ($MAX_CHAIN_DEPTH). Force stopping."
  if [ -x "$SLACK_NOTIFY" ]; then
    "$SLACK_NOTIFY" "#mason-alerts" "🛑 自动 escalation 链达到深度上限 ($MAX_CHAIN_DEPTH)。需要 Mason 手动介入。" "QA Bot" ":warning:" 2>/dev/null || true
  fi
  exit 1
fi

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

# --- 允许从 Claude Code session 内嵌套调用 ---
unset CLAUDECODE 2>/dev/null || true

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
TASK_ID=$(echo "$TASK" | grep -oP '(?:task_id:\s*)\K[A-Za-z0-9_\-]+' | head -1)
if [ -z "$TASK_ID" ]; then
  TASK_ID=$(echo "$TASK" | grep -oP 'srx_\d{8}_\w+' | head -1)
fi
if [ -z "$TASK_ID" ]; then
  TASK_ID="task_${AGENT_NAME}_$(date +%s)"
fi
mkdir -p "$TASK_LOG_DIR"

# --- Phase 2: 经验记忆注入 ---
LESSONS_FILE="$MEMORY_DIR/${AGENT_NAME}_lessons.md"
if [ -f "$LESSONS_FILE" ] && [ -s "$LESSONS_FILE" ]; then
  SYSPROMPT="${SYSPROMPT}

---
## 历史经验（来自过去任务的教训，请参考但不必完全遵循）

$(cat "$LESSONS_FILE")"
fi

# --- 提取 launcher_args（从 YAML frontmatter）---
LAUNCHER_ARGS=$(awk 'BEGIN{c=0; in_la=0} /^---$/{c++; next} c>=2{exit} c==1{
  if(/^launcher_args:/){in_la=1; next}
  if(in_la && /^  - /){gsub(/^  - /,""); printf "%s ", $0; next}
  if(in_la && !/^  /){in_la=0}
}' "$AGENT_FILE")

# --- 辅助函数：调用 claude -p 并记录 token ---
call_claude() {
  local prompt="$1"
  local json_out
  json_out=$(cd "$RUN_DIR" && claude -p \
    --output-format json \
    $LAUNCHER_ARGS \
    --system-prompt "$SYSPROMPT" \
    "$prompt" 2>&1)
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
  local map_file="$SKILLS_DIR/test-map.json"
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

# --- 记录开始 ---
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_EPOCH=$(date +%s)
echo "[$START_TIME] === $AGENT_NAME 开始执行 ===" >> "$LOG_FILE"
echo "[$START_TIME] 任务: $TASK" >> "$LOG_FILE"
echo "[$START_TIME] 工作目录: $RUN_DIR" >> "$LOG_FILE"
echo "[$START_TIME] 强制验证: $HAS_VERIFY_LOOP" >> "$LOG_FILE"
echo "<<<AGENT_START $AGENT_NAME>>>"

# === 主执行逻辑 ===

# 记录 agent 调用前的 git diff baseline（用于只检测 agent 新增的改动）
GIT_BASELINE=$(cd "$RUN_DIR" && git diff --name-only 2>/dev/null | grep -E '\.(py|jsx|js|ts)$' | sort || true)

if [ "$HAS_VERIFY_LOOP" = false ]; then
  # --- 非开发类 agent：直接执行，无验证 ---
  # Phase 1: 保存输入日志
  echo "$TASK" > "${TASK_LOG_DIR}/${TASK_ID}_round1_input.txt"

  JSON_OUTPUT=$(call_claude "$TASK")
  OUTPUT=$(extract_result "$JSON_OUTPUT")

  # Phase 1: 保存输出日志
  echo "$JSON_OUTPUT" > "${TASK_LOG_DIR}/${TASK_ID}_round1_output.json"

  echo "$OUTPUT"
  echo "$OUTPUT" >> "$LOG_FILE"

  END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  END_EPOCH=$(date +%s)
  DURATION=$((END_EPOCH - START_EPOCH))
  TASK_SUMMARY=$(printf %s "$TASK" | head -c 50)
  TASK_SUMMARY=${TASK_SUMMARY//$'\n'/ }

  # Phase 1: 生成 summary
  cat > "${TASK_LOG_DIR}/${TASK_ID}_summary.json" <<EOSUMMARY
{"task_id":"$TASK_ID","agent":"$AGENT_NAME","start_time":"$START_TIME","end_time":"$END_TIME","total_rounds":1,"final_status":"completed","task_log_dir":"$TASK_LOG_DIR"}
EOSUMMARY

  echo "{\"timestamp\":\"$END_TIME\",\"agent\":\"$AGENT_NAME\",\"task\":\"$TASK_SUMMARY\",\"status\":\"completed\",\"task_log_dir\":\"$TASK_LOG_DIR/${TASK_ID}_*\"}" >> "$AUDIT_FILE"
  log_api_usage "$JSON_OUTPUT" "$DURATION"

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
          agents/EMP_0005.md "$NEW_TASK" "${SLACK_CHANNEL:-}"
        ;;
      "escalate_to_platform_dev")
        CONTEXT=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('context',''))" 2>/dev/null)
        echo "⬆️ Escalating to Platform Dev (chain depth: $((CHAIN_DEPTH+1)))"
        send_slack_notify "⬆️ PM escalate 给 Platform Dev"
        CHAIN_DEPTH=$((CHAIN_DEPTH+1)) bash "$HUB_DIR/scripts/run-agent.sh" \
          agents/EMP_0002.md "Escalation from PM. task_id: $TASK_ID. $CONTEXT" "${SLACK_CHANNEL:-}"
        ;;
      "escalate_to_mason")
        CONTEXT=$(echo "$ACTION_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('context',''))" 2>/dev/null)
        echo "🔴 Escalating to Mason"
        if [ -x "$SLACK_NOTIFY" ]; then
          "$SLACK_NOTIFY" "#mason-alerts" "🔴 需要 Mason 决策: 任务 $TASK_ID - $CONTEXT" "QA Bot" ":rotating_light:" 2>/dev/null || true
        fi
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
    echo "[$START_TIME] --- 第 $ROUND 轮执行 ---" >> "$LOG_FILE"
    echo "--- Round $ROUND / $MAX_VERIFY_ROUNDS ---"

    # Phase 1: 保存本轮输入
    echo "$CURRENT_PROMPT" > "${TASK_LOG_DIR}/${TASK_ID}_round${ROUND}_input.txt"

    # Step 1: Call claude -p
    JSON_OUTPUT=$(call_claude "$CURRENT_PROMPT")
    OUTPUT=$(extract_result "$JSON_OUTPUT")

    # Phase 1: 保存本轮输出
    echo "$JSON_OUTPUT" > "${TASK_LOG_DIR}/${TASK_ID}_round${ROUND}_output.json"

    ROUND_EPOCH=$(date +%s)
    ROUND_DURATION=$((ROUND_EPOCH - START_EPOCH))
    log_api_usage "$JSON_OUTPUT" "$ROUND_DURATION"

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
    VERIFY_OUTPUT=$("$SKILLS_DIR/dev-verify-loop.sh" "$MODIFIED" "$TEST_MODULE" 2>&1) || VERIFY_EXIT=$?

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
      ERROR_BRIEF=$(echo "$VERIFY_OUTPUT" | grep -E "FAIL|ERROR|assert|Error" | head -5 | tr '\n' ' ' | head -c 300)
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

    echo "{\"timestamp\":\"$END_TIME\",\"agent\":\"$AGENT_NAME\",\"task\":\"$TASK_SUMMARY\",\"status\":\"completed\",\"verify_rounds\":$ROUND,\"task_log_dir\":\"$TASK_LOG_DIR/${TASK_ID}_*\"}" >> "$AUDIT_FILE"

    # Phase 2: 成功时记录经验
    LESSONS_SIZE=$(stat -c %s "$LESSONS_FILE" 2>/dev/null || echo 0)
    if [ -f "$LESSONS_FILE" ] && [ "$LESSONS_SIZE" -lt 51200 ]; then
      LESSON_PROMPT="任务完成。请用 1-3 句话总结这次任务中值得记住的经验教训（遇到了什么坑、怎么解决的、下次该注意什么）。只输出经验内容，格式：## $(date +%Y-%m-%d): <模块名>\n- <经验1>\n- <经验2>"
      LESSON_JSON=$(cd "$RUN_DIR" && claude -p \
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
    ROOT_CAUSE=$(echo "$OUTPUT" | grep -iE "root.?cause|根因|原因|problem|issue" | head -2 | tr '\n' ' ' | head -c 200)
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

    # 3.3 写入审计日志
    echo "$FAIL_SUMMARY" >> "$AUDIT_LOG"
    echo "{\"timestamp\":\"$END_TIME\",\"agent\":\"$AGENT_NAME\",\"task\":\"$TASK_SUMMARY\",\"status\":\"repair_failed\",\"verify_rounds\":$ROUND,\"task_log_dir\":\"$TASK_LOG_DIR/${TASK_ID}_*\"}" >> "$AUDIT_FILE"

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
      SLACK_MSG="🔴 任务 ${TASK_ID_EXTRACTED} 已耗尽所有自动修复机会（Dev 3轮 × PM ${MAX_PM_RETRIES}次 = 共 $((MAX_VERIFY_ROUNDS * (PM_RETRY_COUNT + 1))) 轮尝试）\n自动 escalate 给 Platform Dev (EMP_0002)\n失败摘要：${ROUND_SUMMARIES}\n根因判断：${ROOT_CAUSE:-无}"
    else
      SLACK_MSG="⚠️ 任务 ${TASK_ID_EXTRACTED} 3 轮修复失败（PM 第 $((PM_RETRY_COUNT))/2 次分配）\n剩余 PM 重试次数：${PM_RETRIES_LEFT}\n失败摘要：${ROUND_SUMMARIES}\n根因判断：${ROOT_CAUSE:-无}\n请 PM 评估下一步。"
    fi
    send_slack_notify "$(echo -e "$SLACK_MSG")"

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
          agents/EMP_0001.md \
          "评估 Dev 失败任务。task_id: $TASK_ID_EXTRACTED。PM 重试次数: $PM_RETRY_COUNT/$MAX_PM_RETRIES。请读取 $TASK_LOG_DIR/${TASK_ID_EXTRACTED}_*.json 和 $AUDIT_LOG。运行 ~/mason-hub/skills/check-escalation.sh --task $TASK_ID_EXTRACTED 查看完整历史。判断失败类型（A-E），决定下一步。在回复最后一行输出 ACTION。" \
          "${SLACK_CHANNEL:-}"
      else
        echo "⬆️ PM retries exhausted. Auto-escalating to Platform Dev (chain depth: $((CHAIN_DEPTH+1)))"
        send_slack_notify "⬆️ 任务 $TASK_ID_EXTRACTED 已耗尽 PM 重试次数（$MAX_PM_RETRIES/$MAX_PM_RETRIES），自动 escalate 给 Platform Dev"
        CHAIN_DEPTH=$((CHAIN_DEPTH+1)) bash "$HUB_DIR/scripts/run-agent.sh" \
          agents/EMP_0002.md \
          "接收 escalation。task_id: $TASK_ID_EXTRACTED。Dev 3轮×$((PM_RETRY_COUNT+1))次均失败。请读取 $TASK_LOG_DIR/${TASK_ID_EXTRACTED}_*.json，分析根因并尝试修复。" \
          "${SLACK_CHANNEL:-}"
      fi
    elif [ "$AGENT_NAME" = "EMP_0002" ]; then
      echo "🔴 Platform Dev also failed. Escalating to Mason."
      if [ -x "$SLACK_NOTIFY" ]; then
        "$SLACK_NOTIFY" "#mason-alerts" "🔴 任务 $TASK_ID_EXTRACTED 所有自动修复均失败（Dev + PM + Platform Dev）。需要 Mason 手动介入。完整日志：$TASK_LOG_DIR/${TASK_ID_EXTRACTED}_*" "QA Bot" ":rotating_light:" 2>/dev/null || true
      fi
    fi
  fi
fi

echo "" >> "$LOG_FILE"
echo "[$END_TIME] === $AGENT_NAME 执行完毕 ===" >> "$LOG_FILE"
echo "<<<AGENT_END>>>"
echo "任务完成，结果已记录"
