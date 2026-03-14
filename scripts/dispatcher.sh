#!/usr/bin/env bash
# dispatcher.sh — 自主任务调度器
#
# 定期扫描 backlog，找到可自主执行的任务，启动对应 Agent。
# 四道安全门: 权限 → 状态 → 依赖 → 时间
#
# 用法:
#   ./dispatcher.sh              # 扫描并执行
#   ./dispatcher.sh --dry-run    # 只扫描不执行
#   ./dispatcher.sh --status     # 显示状态
#
# Cron: 0 * * * * /home/hangn/mason-hub/scripts/dispatcher.sh

set -euo pipefail

HUB_DIR="${HUB_DIR:-$HOME/mason-hub}"
SYSTEM_MAP="$HUB_DIR/SYSTEM_MAP.md"
BACKLOG="$HUB_DIR/tasks/backlog.md"
EVENTS_QUEUE="$HUB_DIR/data/events/queue.jsonl"
REPORTS_DIR="$HUB_DIR/data/reports"
LOCK_FILE="/tmp/dispatcher.lock"
LOG_FILE="$HUB_DIR/logs/dispatcher.log"
RUN_AGENT="$HUB_DIR/scripts/run-agent.sh"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    # 直接写文件，不用 tee（cron 的 >> 重定向会导致日志双写）
    echo "[$ts] $*" >> "$LOG_FILE"
}

# === 安全门 0: Mason 活跃 session 检测 ===
check_mason_session() {
    # Mason 在用 Claude Code 时，dispatcher 不派活（避免撞车）
    # 检测方式：是否有交互式 claude 进程（排除 run-agent.sh 派生的 claude -p）
    if pgrep -f 'claude' | while read pid; do
        # claude -p 是 agent 进程（非交互），不算 Mason session
        if ! grep -q '\-p' /proc/"$pid"/cmdline 2>/dev/null; then
            exit 0  # 找到交互式 claude = Mason 在线
        fi
    done; then
        log "⏸️  Mason 有活跃 session，本轮跳过"
        return 1
    fi
    return 0
}

# === 安全门 1: 时间窗口 ===
check_time_window() {
    # 24h 运行：任务去重 + lane lock + 每日上限 + 失败自动回滚已兜底
    return 0
}

# === 安全门 2: 系统状态 ===
# 从 SYSTEM_MAP 读取能力线状态
get_line_status() {
    local line_name="$1"
    # 找到对应能力线的状态字段
    grep -A5 "### .*${line_name}" "$SYSTEM_MAP" 2>/dev/null \
        | grep "^状态:" \
        | head -1 \
        | awk '{print $2}' \
        || echo "unknown"
}

# === 安全门 3: 依赖健康 ===
check_dependencies_healthy() {
    local health_script="$HUB_DIR/data/pipelines/data_health_check.sh"
    if [[ ! -f "$health_script" ]]; then
        log "安全门 [依赖]: health_check 脚本不存在，跳过检查"
        return 0  # 不阻塞
    fi
    # 不需要每次完整跑，检查上次结果即可
    return 0
}

# === Repair 队列检查 ===
check_repair_queue() {
    local repair_script="$HUB_DIR/scripts/repair-dispatch.sh"
    local queue_file="$HUB_DIR/data/repair_queue.json"

    [[ ! -f "$repair_script" ]] && return 1
    [[ ! -f "$queue_file" ]] && return 1

    # 检查有没有 pending 的修复任务
    local pending_count
    pending_count=$(python3 -c "
import json
queue = json.load(open('$queue_file'))
print(len([i for i in queue if i.get('status') == 'pending' and i.get('attempts', 0) < 3]))
" 2>/dev/null || echo "0")

    if [[ "$pending_count" -gt 0 ]]; then
        log "  发现 $pending_count 个 pending 修复任务，启动 repair-dispatch"
        if $DRY_RUN; then
            log "  [DRY-RUN] 会调用 repair-dispatch.sh"
            return 0
        fi
        bash "$repair_script" 2>&1 | tee -a "$LOG_FILE"
        return 0
    fi

    return 1
}

# === Lane 状态检查 ===
# 返回当前空闲的 lane 列表（用换行分隔）
get_free_lanes() {
    local all_lanes="platform ecommerce socialmesh independent"
    local free_lanes=""
    for lane in $all_lanes; do
        if [[ "$lane" == "independent" ]]; then
            # 独立 agent 不需要 lane lock，始终可用
            free_lanes="$free_lanes $lane"
            continue
        fi
        local lock_path="$HOME/mason-hub/locks/${lane}.lock"
        if [[ ! -d "$lock_path" ]]; then
            free_lanes="$free_lanes $lane"
        elif bash "$HUB_DIR/scripts/lane-lock.sh" cleanup 2>/dev/null | grep -q "Cleaning"; then
            # Stale lock cleaned, lane now free
            free_lanes="$free_lanes $lane"
        fi
    done
    echo "$free_lanes"
}

# === 任务匹配 ===
TASK_REGISTRY="$HUB_DIR/data/autonomous_tasks.yaml"

# 批量模式: 获取按 lane 分组的任务列表（JSON）
find_batch_tasks() {
    python3 "$HUB_DIR/scripts/find-actionable-task.py" --batch 2>/dev/null
}

# 兼容旧模式: 获取单个任务
find_actionable_task() {
    local task_info
    task_info=$(python3 "$HUB_DIR/scripts/find-actionable-task.py" 2>/dev/null)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]] || [[ -z "$task_info" ]]; then
        python3 "$HUB_DIR/scripts/find-actionable-task.py" --list 2>/dev/null | while read -r line; do
            log "  $line"
        done
        return 1
    fi

    echo "$task_info"
    return 0
}

# === 执行任务 ===
# 注意：任务去重已在 find-actionable-task.py 中完成（audit.jsonl 已完成检查 + report 运行检查）
# dispatcher 不需要额外的 pgrep 检查
execute_task() {
    local task_id="$1" agent_path="$2" line="$3" desc="$4"
    local expected_output="${5:-}" verify_command="${6:-}" output_path="${7:-}"
    local max_duration="${8:-0}" context_files="${9:-}" task_type="${10:-execute}"
    local account="${11:-}"
    local agent_name
    # 支持新格式 agents/EMP_0002/config.md 和旧格式 agents/EMP_0002.md
    if [[ "$(basename "$agent_path")" == "config.md" ]]; then
      agent_name=$(basename "$(dirname "$agent_path")")
    else
      agent_name=$(basename "$agent_path" .md)
    fi

    log ">>> 启动任务: $desc ($task_id → $agent_name, type=$task_type)"

    if $DRY_RUN; then
        log "  [DRY-RUN] 会启动 $agent_name 执行: $desc"
        return 0
    fi

    # 写事件: 任务开始
    echo "{\"event\":\"dispatcher-task-start\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":1,\"data\":{\"task_id\":\"$task_id\",\"agent\":\"$agent_name\",\"desc\":\"$desc\"}}" \
        >> "$EVENTS_QUEUE"

    # 启动 agent（结构化元数据通过环境变量传递）
    local report_dir="$REPORTS_DIR/$(date +%Y-%m-%d)"
    mkdir -p "$report_dir"

    if [[ -x "$RUN_AGENT" ]]; then
        TASK_EXPECTED_OUTPUT="$expected_output" \
        TASK_VERIFY_COMMAND="$verify_command" \
        TASK_OUTPUT_PATH="$output_path" \
        TASK_MAX_DURATION="$max_duration" \
        TASK_CONTEXT_FILES="$context_files" \
        TASK_TYPE="$task_type" \
        TASK_ACCOUNT="$account" \
        TASK_ACCEPTANCE_CRITERIA="${TASK_ACCEPTANCE_CRITERIA:-}" \
        TASK_ASSIGNED_BY="dispatcher" \
        "$RUN_AGENT" "$agent_path" "自主任务: $desc" \
            > "$report_dir/${agent_name}_${task_id}.log" 2>&1 &
        local pid=$!
        log "  Agent $agent_name 已启动 (PID: $pid)"

        # 写事件: 任务启动完成
        echo "{\"event\":\"agent-task-started\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":0,\"data\":{\"task_id\":\"$task_id\",\"agent\":\"$agent_name\",\"pid\":$pid}}" \
            >> "$EVENTS_QUEUE"
    else
        log "  run-agent.sh 不存在或不可执行"
    fi
}

# === 主流程 ===
main() {
    if [[ "${1:-}" == "--status" ]]; then
        local task_count
        task_count=$(python3 "$HUB_DIR/scripts/find-actionable-task.py" --count 2>/dev/null || echo "0")
        echo "Dispatcher 状态:"
        echo "  注册表: $TASK_REGISTRY"
        echo "  可执行任务: $task_count 条"
        echo "  时间窗口: $(check_time_window && echo '✅ 在窗口内' || echo '❌ 窗口外')"
        echo "  正在运行的 agent: $(pgrep -cf 'claude.*-p' 2>/dev/null || echo 0)"
        echo ""
        python3 "$HUB_DIR/scripts/find-actionable-task.py" --list 2>/dev/null
        return 0
    fi

    # 防止多实例
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE")
        if kill -0 "$lock_pid" 2>/dev/null; then
            log "Dispatcher 已在运行 (PID: $lock_pid)，跳过"
            return 0
        fi
        rm -f "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT

    log "=== Dispatcher 开始扫描 ==="

    # 安全门 0a: Mason /pause
    if [[ -f "/tmp/mason-pause" ]]; then
        log "⏸️ Mason /pause 生效中，跳过派发"
        return 0
    fi

    # 安全门 0b: Mason 活跃 session
    check_mason_session || return 0

    # 安全门 1: 时间
    check_time_window || return 0

    # 安全门 3: 依赖
    check_dependencies_healthy || return 0

    # 先处理 event_router 的新事件
    python3 "$HUB_DIR/scripts/event_router.py" --process-new 2>&1 | tee -a "$LOG_FILE"

    # 再处理 pending 事件
    python3 "$HUB_DIR/scripts/event_router.py" --process-pending 2>&1 | tee -a "$LOG_FILE"

    # 检查 repair 队列（优先于常规任务）
    if check_repair_queue; then
        log "  repair 任务已处理（repair 不和常规任务并行）"
        log "=== Dispatcher 扫描完成 ==="
        return 0
    fi

    # --- 每日规划优先（Meta Manager 生成的 daily_plan.yaml）---
    local daily_plan="$HUB_DIR/data/daily_plan.yaml"
    local today
    today=$(date +%Y-%m-%d)

    if [[ -f "$daily_plan" ]] && grep -q "date:.*${today}" "$daily_plan" 2>/dev/null; then
        log "  📋 发现今日 daily_plan.yaml，按规划派发"
        local plan_tasks
        plan_tasks=$(python3 -c "
import yaml, json, sys
with open('$daily_plan') as f:
    plan = yaml.safe_load(f)
tasks = plan.get('priorities', [])
# 过滤已完成的（检查 reports 目录是否有对应 log）
import os, glob
report_dir = '$REPORTS_DIR/$today'
done = set()
if os.path.isdir(report_dir):
    for f in os.listdir(report_dir):
        done.add(f.split('_')[0] + '_' + '_'.join(f.split('_')[1:]).split('.')[0])
remaining = [t for t in tasks if t.get('task_id', '') not in done]
print(json.dumps(remaining))
" 2>/dev/null) || plan_tasks="[]"

        local plan_count
        plan_count=$(echo "$plan_tasks" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

        if [[ "$plan_count" -gt 0 ]]; then
            log "  daily_plan: $plan_count 个任务待派发"
            local free_lanes
            free_lanes=$(get_free_lanes)

            for idx in $(seq 0 $((plan_count - 1))); do
                local plan_task
                plan_task=$(echo "$plan_tasks" | python3 -c "
import sys, json, shlex
tasks = json.load(sys.stdin)
t = tasks[$idx]
print(f'PLAN_TASK_ID={shlex.quote(t.get(\"task_id\", \"plan-task-$idx\"))}')
print(f'PLAN_AGENT={shlex.quote(t.get(\"agent\", \"\"))}')
print(f'PLAN_DESC={shlex.quote(t.get(\"description\", \"\")[:200])}')
print(f'PLAN_PRIORITY={shlex.quote(t.get(\"priority\", \"P1\"))}')
print(f'PLAN_MODE={shlex.quote(t.get(\"mode\", \"serial\"))}')
" 2>/dev/null) || continue
                eval "$plan_task"

                if [[ -z "${PLAN_AGENT:-}" ]] || [[ -z "${PLAN_DESC:-}" ]]; then
                    continue
                fi

                log "  📋 daily_plan 派发: $PLAN_TASK_ID → $(basename "$(dirname "$PLAN_AGENT")")"
                if ! $DRY_RUN; then
                    execute_task "$PLAN_TASK_ID" "$PLAN_AGENT" "daily-plan" "$PLAN_DESC" \
                        "" "" "" "0" "" "execute"
                else
                    log "  [DRY-RUN] 会启动 $PLAN_AGENT 执行: $PLAN_DESC"
                fi

                # serial 模式下只派发第一个，等下次 cron 再派下一个
                if [[ "${PLAN_MODE:-serial}" == "serial" ]]; then
                    log "  serial 模式，本轮只派发 1 个 daily_plan 任务"
                    break
                fi
            done

            log "=== Dispatcher 扫描完成（daily_plan 模式）==="
            return 0
        else
            log "  daily_plan 所有任务已完成，fallback 到静态扫描"
        fi
    fi

    # --- 批量派发: 按 lane 并行（fallback 到 autonomous_tasks.yaml）---
    local free_lanes
    free_lanes=$(get_free_lanes)
    log "  空闲 lanes: $free_lanes"

    local batch_json
    batch_json=$(find_batch_tasks)

    if [[ -z "$batch_json" ]] || [[ "$batch_json" == "[]" ]]; then
        log "  无可执行任务"
        log "=== Dispatcher 扫描完成 ==="
        return 0
    fi

    # 解析批量任务，按 lane 匹配空闲 lane 后派发
    local dispatched=0
    local task_count
    task_count=$(echo "$batch_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

    log "  批量扫描到 $task_count 个任务（按 lane+agent 去重）"

    for idx in $(seq 0 $((task_count - 1))); do
        # 用 Python 提取所有字段到临时文件，避免 read 的空格切分问题
        local tmp_task
        tmp_task=$(echo "$batch_json" | python3 -c "
import sys, json, shlex
tasks = json.load(sys.stdin)
t = tasks[$idx]
for k in ('id','agent','lane','line','description',
          'expected_output','verify_command','output_path',
          'max_duration','context_files','task_type',
          'tier','tier_script','tier_escalate_on_fail','account',
          'depends_on','acceptance_criteria'):
    v = str(t.get(k, ''))[:200]
    print(f'TASK_{k.upper()}={shlex.quote(v)}')
" 2>/dev/null) || continue
        eval "$tmp_task"

        if [[ -z "${TASK_ID:-}" ]]; then
            continue
        fi

        # 检查该 lane 是否空闲
        if [[ "$TASK_LANE" != "independent" ]] && ! echo "$free_lanes" | grep -qw "$TASK_LANE"; then
            log "  ⏸️  $TASK_ID: lane $TASK_LANE 正忙，跳过"
            continue
        fi

        # === v2: depends_on 检查 ===
        if [[ -n "${TASK_DEPENDS_ON:-}" ]]; then
            local deps_met=true
            IFS=',' read -ra DEPS <<< "$TASK_DEPENDS_ON"
            for dep in "${DEPS[@]}"; do
                dep=$(echo "$dep" | xargs)
                local dep_yaml="$HUB_DIR/data/tasks/${dep}.yaml"
                if [ -f "$dep_yaml" ]; then
                    local dep_status
                    dep_status=$(grep "^status:" "$dep_yaml" | head -1 | sed 's/status: *//' | tr -d '"')
                    if [[ "$dep_status" != "done" ]]; then
                        deps_met=false
                        break
                    fi
                else
                    deps_met=false
                    break
                fi
            done
            if ! $deps_met; then
                log "  ⏸️  $TASK_ID: depends_on 未满足 ($TASK_DEPENDS_ON)"
                continue
            fi
        fi

        # === v2: 动态 Agent 匹配（无指定 agent 时从能力索引匹配）===
        if [[ -z "${TASK_AGENT:-}" ]] || [[ "$TASK_AGENT" == "auto" ]]; then
            local cap_index="$HUB_DIR/data/roster/capability_index.json"
            if [[ -f "$cap_index" ]]; then
                local matched_agent
                matched_agent=$(python3 -c "
import json, sys
with open('$cap_index') as f:
    idx = json.load(f)
desc = '''${TASK_DESCRIPTION:-}'''.lower()
# 中文→能力映射
cn_map = {'部署':'infrastructure','服务器':'infrastructure','docker':'infrastructure',
  '店铺':'ecommerce','售后':'ecommerce','库存':'ecommerce','订单':'ecommerce',
  '视频':'video','剪辑':'video','内容':'content','文案':'content',
  '分析':'data_analysis','数据':'data_analysis','指标':'data_analysis',
  '管道':'data_engineering','管线':'data_engineering',
  '情报':'intelligence','趋势':'intelligence','监控':'intelligence',
  '运维':'devops','健康':'devops','告警':'devops',
  '前端':'frontend','页面':'frontend','ui':'frontend',
  '营销':'marketing','推广':'marketing','种草':'marketing',
  'xhs':'xhs','小红书':'xhs','红书':'xhs'}
# 从描述提取能力
matched_caps = set()
for cn, cap in cn_map.items():
    if cn in desc:
        matched_caps.add(cap)
for cap in idx.get('capabilities', {}).keys():
    if cap in desc:
        matched_caps.add(cap)
scores = {}
for cap in matched_caps:
    for a in idx.get('capabilities', {}).get(cap, []):
        info = idx['agents'].get(a, {})
        if info.get('can_own_tasks', False):
            scores[a] = scores.get(a, 0) + 1
if scores:
    best = max(scores, key=scores.get)
    print(f'agents/{best}/config.md')
" 2>/dev/null)
                if [[ -n "$matched_agent" ]]; then
                    log "  🎯 动态匹配: $TASK_ID → $matched_agent (能力索引)"
                    TASK_AGENT="$matched_agent"
                else
                    log "  ⚠️ $TASK_ID: 无 agent 且能力匹配失败，跳过"
                    continue
                fi
            else
                log "  ⚠️ $TASK_ID: 无 agent 且能力索引不存在，跳过"
                continue
            fi
        fi

        # === T1 直接执行：纯脚本任务不启动 Agent session ===
        if [[ "${TASK_TIER:-}" == "T1" ]] && [[ -n "${TASK_TIER_SCRIPT:-}" ]]; then
            log "  ⚡ T1 直接执行: $TASK_ID → $TASK_TIER_SCRIPT"
            if $DRY_RUN; then
                log "  [DRY-RUN] T1 会直接执行: $TASK_TIER_SCRIPT"
                dispatched=$((dispatched + 1))
                continue
            fi

            local t1_report_dir="$REPORTS_DIR/$(date +%Y-%m-%d)"
            mkdir -p "$t1_report_dir"
            local t1_log="$t1_report_dir/${TASK_ID}_t1.log"
            local t1_exit=0

            # 写事件: T1 任务开始
            echo "{\"event\":\"dispatcher-t1-start\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":0,\"data\":{\"task_id\":\"$TASK_ID\",\"script\":\"$TASK_TIER_SCRIPT\"}}" \
                >> "$EVENTS_QUEUE"

            (cd "$HUB_DIR" && bash -c "$TASK_TIER_SCRIPT") > "$t1_log" 2>&1 || t1_exit=$?

            if [[ $t1_exit -eq 0 ]]; then
                log "  ✅ T1 完成: $TASK_ID (exit 0)"
                echo "{\"event\":\"dispatcher-t1-complete\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":0,\"data\":{\"task_id\":\"$TASK_ID\",\"exit_code\":0}}" \
                    >> "$EVENTS_QUEUE"
                # 写审计记录（零 token 成本）
                printf '{"timestamp":"%s","task_id":"%s","agent":"T1-script","task":"%s","status":"completed","duration":0,"input_tokens":0,"output_tokens":0,"cost_usd":0,"num_turns":0,"model":"bash"}\n' \
                    "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$TASK_ID" "$(printf '%s' "$TASK_DESCRIPTION" | head -c 80 | tr '\n' ' ' | tr '"' "'")" >> "$HUB_DIR/logs/audit.jsonl"
            else
                log "  ❌ T1 失败: $TASK_ID (exit $t1_exit)"
                if [[ "${TASK_TIER_ESCALATE_ON_FAIL:-}" == "true" ]]; then
                    local t1_errors
                    t1_errors=$(tail -20 "$t1_log" | tr '\n' ' ' | head -c 200)
                    log "  ⬆️ T1 升级为 T3: 启动 Agent 修复"
                    execute_task "$TASK_ID" "$TASK_AGENT" "$TASK_LINE" \
                        "T1 脚本执行失败 (exit $t1_exit)。脚本: $TASK_TIER_SCRIPT。错误: $t1_errors。请诊断并修复。" \
                        "$TASK_EXPECTED_OUTPUT" "$TASK_VERIFY_COMMAND" "$TASK_OUTPUT_PATH" \
                        "$TASK_MAX_DURATION" "$TASK_CONTEXT_FILES" "$TASK_TASK_TYPE" \
                        "${TASK_ACCOUNT:-}"
                fi
            fi
            dispatched=$((dispatched + 1))
            continue
        fi

        # 派发任务（lane lock 由 run-agent.sh 自行管理互斥）
        execute_task "$TASK_ID" "$TASK_AGENT" "$TASK_LINE" "$TASK_DESCRIPTION" \
            "$TASK_EXPECTED_OUTPUT" "$TASK_VERIFY_COMMAND" "$TASK_OUTPUT_PATH" \
            "$TASK_MAX_DURATION" "$TASK_CONTEXT_FILES" "$TASK_TASK_TYPE" \
            "${TASK_ACCOUNT:-}"
        dispatched=$((dispatched + 1))
    done

    log "  本轮派发: $dispatched 个任务"
    log "=== Dispatcher 扫描完成 ==="
}

main "$@"
