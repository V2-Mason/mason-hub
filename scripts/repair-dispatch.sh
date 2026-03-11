#!/usr/bin/env bash
# repair-dispatch.sh — 修复调度器
#
# 读取 repair_queue.json 中的 pending 任务，启动 claude -p 修复 session。
# 由 dispatcher.sh 在收到 repair 事件时调用。
#
# 用法:
#   ./repair-dispatch.sh              # 处理队列中的 pending 任务
#   ./repair-dispatch.sh --dry-run    # 只显示会做什么
#   ./repair-dispatch.sh --status     # 查看队列状态

set -euo pipefail

HUB_DIR="${HUB_DIR:-$HOME/mason-hub}"
QUEUE_FILE="$HUB_DIR/data/repair_queue.json"
PROMPT_FILE="$HUB_DIR/scripts/repair-prompt.md"
REPAIR_LOCK="/tmp/repair-session.lock"
HEARTBEAT_LOCK="$HUB_DIR/data/gateway.lock"
LOG_FILE="$HUB_DIR/logs/repair.log"
MAX_ATTEMPTS=3
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] $*" >> "$LOG_FILE"
    echo "[$ts] $*" >&2
}

# 检查是否有 pending 的修复任务
get_pending_items() {
    python3 -c "
import json, sys
try:
    queue = json.load(open('$QUEUE_FILE'))
    pending = [i for i in queue if i.get('status') == 'pending' and i.get('attempts', 0) < $MAX_ATTEMPTS]
    if pending:
        for item in pending:
            print(json.dumps(item, ensure_ascii=False))
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
" 2>/dev/null
}

# 检查 heartbeat 是否在运行
heartbeat_running() {
    if [[ -f "$HEARTBEAT_LOCK" ]]; then
        local lock_data pid
        lock_data=$(cat "$HEARTBEAT_LOCK" 2>/dev/null || echo "{}")
        pid=$(echo "$lock_data" | python3 -c "import json,sys; print(json.load(sys.stdin).get('pid',0))" 2>/dev/null || echo 0)
        if [[ "$pid" -gt 0 ]] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# 主流程
main() {
    if [[ "${1:-}" == "--status" ]]; then
        python3 "$HUB_DIR/scripts/submit-repair.py" status
        return 0
    fi

    # 检查 repair lock（防止多个 repair session 并发）
    if [[ -f "$REPAIR_LOCK" ]]; then
        local lock_pid
        lock_pid=$(cat "$REPAIR_LOCK" 2>/dev/null || echo 0)
        if kill -0 "$lock_pid" 2>/dev/null; then
            log "repair session 正在运行 (PID: $lock_pid)，跳过"
            return 0
        fi
        rm -f "$REPAIR_LOCK"
    fi

    # 检查有没有 pending 的修复任务
    local pending
    pending=$(get_pending_items)
    if [[ -z "$pending" ]]; then
        log "无 pending 的修复任务"
        return 0
    fi

    # 取第一个 pending 任务
    local item_json item_id issue
    item_json=$(echo "$pending" | head -1)
    item_id=$(echo "$item_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
    issue=$(echo "$item_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['issue'])")

    log ">>> 启动修复: $item_id — $issue"

    if $DRY_RUN; then
        log "[DRY-RUN] 会启动 claude -p 修复: $issue"
        log "[DRY-RUN] allowedTools: Bash(git *),Bash(python3 *),Bash(bash scripts/*),Bash(scp *),Bash(systemctl restart surenxuan-fastapi),Bash(systemctl restart ssh-tunnel),Bash(systemctl restart mason-gateway),Edit,Read"
        return 0
    fi

    # 写 lockfile
    echo $$ > "$REPAIR_LOCK"
    trap 'rm -f "$REPAIR_LOCK"' EXIT

    # 读取 repair prompt
    local system_prompt
    if [[ -f "$PROMPT_FILE" ]]; then
        system_prompt=$(cat "$PROMPT_FILE")
    else
        system_prompt="你是修复工程师。读取 data/repair_queue.json，修复 pending 的问题。"
    fi

    # 组装任务描述
    local task_prompt
    task_prompt="修复任务: $issue

问题详情:
$item_json

请按照你的行为定义执行修复。完成后用 python3 scripts/submit-repair.py update $item_id --status <结果> 更新队列。"

    # 启动 claude -p
    local report_dir="$HUB_DIR/data/reports/$(date +%Y-%m-%d)"
    mkdir -p "$report_dir"
    local report_file="$report_dir/repair_${item_id}.log"

    log "启动 claude -p (allowedTools 硬门控)"

    # claude -p 执行修复
    # --permission-mode dontAsk: 不在 allowedTools 里的操作自动拒绝
    # --allowedTools: 精确控制放行范围
    # unset CLAUDECODE: 允许在 Gateway/Dispatcher 子进程中启动 claude -p（非嵌套）
    unset CLAUDECODE 2>/dev/null || true
    cd "$HUB_DIR"
    claude -p "$task_prompt" \
        --permission-mode dontAsk \
        --allowedTools "Bash(git *),Bash(python3 *),Bash(bash scripts/*),Bash(scp *),Bash(systemctl restart surenxuan-fastapi),Bash(systemctl restart ssh-tunnel),Bash(systemctl restart mason-gateway),Edit,Read,Write" \
        --append-system-prompt "$system_prompt" \
        > "$report_file" 2>&1
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "claude -p 完成 (exit 0)"
    else
        log "claude -p 异常退出 (exit $exit_code)"
        # 如果 claude -p 自身崩溃，标记为 repair_attempted 让下次重试
        python3 "$HUB_DIR/scripts/submit-repair.py" update "$item_id" \
            --status repair_attempted \
            --fix "claude -p 异常退出 (exit $exit_code)" \
            --test-result "未完成" >> "$LOG_FILE" 2>&1
    fi

    # 检查修复结果（claude -p 应该已经调了 submit-repair.py update）
    local final_status
    final_status=$(python3 -c "
import json
queue = json.load(open('$QUEUE_FILE'))
for item in queue:
    if item['id'] == '$item_id':
        print(item.get('status', 'unknown'))
        break
" 2>/dev/null || echo "unknown")

    if [[ "$final_status" == "pending" ]]; then
        # claude -p 没更新状态（可能忘了调 submit-repair.py）
        log "⚠️ claude -p 未更新队列状态，标记为 repair_attempted"
        python3 "$HUB_DIR/scripts/submit-repair.py" update "$item_id" \
            --status repair_attempted \
            --fix "session 完成但未更新状态" >> "$LOG_FILE" 2>&1
    fi

    # 检查 attempts 是否达到上限
    local attempts
    attempts=$(python3 -c "
import json
queue = json.load(open('$QUEUE_FILE'))
for item in queue:
    if item['id'] == '$item_id':
        print(item.get('attempts', 0))
        break
" 2>/dev/null || echo "0")

    if [[ "$attempts" -ge "$MAX_ATTEMPTS" ]]; then
        log "🔴 $item_id 已尝试 $attempts 次，升级为 pending_mason"
        python3 "$HUB_DIR/scripts/submit-repair.py" update "$item_id" \
            --status pending_mason \
            --fix "已尝试 $attempts 次修复均未成功" >> "$LOG_FILE" 2>&1

        # 发 Slack 通知
        if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
            curl -s -X POST "$SLACK_WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "{\"text\":\"🔴 Repair Agent: $issue — 已尝试 $attempts 次修复未成功，需要 Mason 介入\"}" \
                > /dev/null 2>&1
        fi
    fi

    log "<<< 修复完成: $item_id (status: $final_status, attempts: $attempts)"
}

main "$@"
