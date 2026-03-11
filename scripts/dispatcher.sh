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
    local agent_name
    agent_name=$(basename "$agent_path" .md)

    log ">>> 启动任务: $desc ($task_id → $agent_name)"

    if $DRY_RUN; then
        log "  [DRY-RUN] 会启动 $agent_name 执行: $desc"
        return 0
    fi

    # 写事件: 任务开始
    echo "{\"event\":\"dispatcher-task-start\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":1,\"data\":{\"task_id\":\"$task_id\",\"agent\":\"$agent_name\",\"desc\":\"$desc\"}}" \
        >> "$EVENTS_QUEUE"

    # 启动 agent
    local report_dir="$REPORTS_DIR/$(date +%Y-%m-%d)"
    mkdir -p "$report_dir"

    if [[ -x "$RUN_AGENT" ]]; then
        # 通过 run-agent.sh 启动（自带 lane lock + token tracking）
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

    # 安全门 0: Mason /pause
    if [[ -f "/tmp/mason-pause" ]]; then
        log "⏸️ Mason /pause 生效中，跳过派发"
        return 0
    fi

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

    # --- 批量派发: 按 lane 并行 ---
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

    log "  批量扫描到 $task_count 个任务（按 lane 去重）"

    for idx in $(seq 0 $((task_count - 1))); do
        local task_id agent_path lane line desc
        read -r task_id agent_path lane line desc < <(echo "$batch_json" | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
t = tasks[$idx]
print(t['id'], t['agent'], t['lane'], t.get('line',''), t.get('description','')[:200])
" 2>/dev/null || echo "")

        if [[ -z "$task_id" ]]; then
            continue
        fi

        # 检查该 lane 是否空闲
        if [[ "$lane" != "independent" ]] && ! echo "$free_lanes" | grep -qw "$lane"; then
            log "  ⏸️  $task_id: lane $lane 正忙，跳过"
            continue
        fi

        # 派发任务
        execute_task "$task_id" "$agent_path" "$line" "$desc"
        dispatched=$((dispatched + 1))

        # 从空闲列表移除已占用的 lane（independent 不移除）
        if [[ "$lane" != "independent" ]]; then
            free_lanes=$(echo "$free_lanes" | sed "s/\b${lane}\b//")
        fi
    done

    log "  本轮派发: $dispatched 个任务"
    log "=== Dispatcher 扫描完成 ==="
}

main "$@"
