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
    echo "[$ts] $*" | tee -a "$LOG_FILE"
}

# === 安全门 1: 时间窗口 ===
check_time_window() {
    local cst_hour
    cst_hour=$(TZ=Asia/Shanghai date +%H)
    if (( cst_hour >= 8 && cst_hour < 22 )); then
        return 0
    fi
    log "安全门 [时间]: 当前 CST $cst_hour 时，不在 08:00-22:00 窗口内"
    return 1
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

# === 安全门 4: 无正在运行的 agent ===
check_no_running_agent() {
    if pgrep -f "claude.*-p" > /dev/null 2>&1; then
        log "安全门 [并发]: 已有 claude agent 在运行，跳过本轮"
        return 1
    fi
    return 0
}

# === 任务匹配 ===
# 可自主执行的任务定义
# 格式: task_id|owner_agent|capability_line|description
AUTONOMOUS_TASKS=(
    "searxng-docker|EMP_0002|自治线|SearXNG Docker 部署"
    "unit-tests|EMP_0002|数据线|关键函数单元测试"
    "health-fix|EMP_0014|数据线|data_health_check 数据集修复"
    "socialmesh-basic|EMP_0009|内容线|SocialMesh 基础功能"
    "skill-pairing|EMP_0002|自治线|cron agent 配对 /skill"
)

find_actionable_task() {
    local task_id owner line desc status

    for task_def in "${AUTONOMOUS_TASKS[@]}"; do
        IFS='|' read -r task_id owner line desc <<< "$task_def"

        # 安全门 2: 检查能力线状态
        status=$(get_line_status "$line")
        if [[ "$status" != "active" ]]; then
            log "  跳过 $task_id: 能力线 $line 状态为 $status (需要 active)"
            continue
        fi

        # 检查 backlog 中该任务是否未完成
        if grep -q "\[x\].*${task_id}" "$BACKLOG" 2>/dev/null; then
            log "  跳过 $task_id: backlog 中已标记完成"
            continue
        fi

        # 找到可执行任务
        echo "$task_id|$owner|$line|$desc"
        return 0
    done

    return 1
}

# === 执行任务 ===
execute_task() {
    local task_id="$1" owner="$2" line="$3" desc="$4"

    log ">>> 启动任务: $desc ($task_id → $owner)"

    if $DRY_RUN; then
        log "  [DRY-RUN] 会启动 $owner 执行: $desc"
        return 0
    fi

    # 写事件: 任务开始
    echo "{\"event\":\"dispatcher-task-start\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":1,\"data\":{\"task_id\":\"$task_id\",\"agent\":\"$owner\",\"desc\":\"$desc\"}}" \
        >> "$EVENTS_QUEUE"

    # 启动 agent
    local report_dir="$REPORTS_DIR/$(date +%Y-%m-%d)"
    mkdir -p "$report_dir"

    if [[ -x "$RUN_AGENT" ]]; then
        # 通过 run-agent.sh 启动（自带 lane lock + token tracking）
        "$RUN_AGENT" "$owner" "自主任务: $desc" \
            > "$report_dir/${owner}_${task_id}.log" 2>&1 &
        local pid=$!
        log "  Agent $owner 已启动 (PID: $pid)"

        # 写事件: 任务启动完成
        echo "{\"event\":\"agent-task-started\",\"source\":\"dispatcher.sh\",\"timestamp\":\"$(date -Iseconds)\",\"status\":\"ok\",\"level\":0,\"data\":{\"task_id\":\"$task_id\",\"agent\":\"$owner\",\"pid\":$pid}}" \
            >> "$EVENTS_QUEUE"
    else
        log "  run-agent.sh 不存在或不可执行"
    fi
}

# === 主流程 ===
main() {
    if [[ "${1:-}" == "--status" ]]; then
        echo "Dispatcher 状态:"
        echo "  任务池: ${#AUTONOMOUS_TASKS[@]} 条"
        echo "  时间窗口: $(check_time_window && echo '✅ 在窗口内' || echo '❌ 窗口外')"
        echo "  正在运行的 agent: $(pgrep -cf 'claude.*-p' 2>/dev/null || echo 0)"
        for task_def in "${AUTONOMOUS_TASKS[@]}"; do
            IFS='|' read -r task_id owner line desc <<< "$task_def"
            status=$(get_line_status "$line")
            echo "  [$status] $task_id → $owner ($line): $desc"
        done
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

    # 安全门 1: 时间
    check_time_window || return 0

    # 安全门 4: 无并发
    check_no_running_agent || return 0

    # 安全门 3: 依赖
    check_dependencies_healthy || return 0

    # 先处理 event_router 的新事件
    python3 "$HUB_DIR/scripts/event_router.py" --process-new 2>&1 | tee -a "$LOG_FILE"

    # 再处理 pending 事件
    python3 "$HUB_DIR/scripts/event_router.py" --process-pending 2>&1 | tee -a "$LOG_FILE"

    # 检查 repair 队列（优先于常规任务）
    if check_repair_queue; then
        log "  repair 任务已处理，本轮结束"
        return 0
    fi

    # 找可执行任务
    local task_info
    if task_info=$(find_actionable_task); then
        IFS='|' read -r task_id owner line desc <<< "$task_info"
        execute_task "$task_id" "$owner" "$line" "$desc"
    else
        log "  无可执行任务"
    fi

    log "=== Dispatcher 扫描完成 ==="
}

main "$@"
