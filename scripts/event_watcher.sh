#!/usr/bin/env bash
# event_watcher.sh — inotify 实时事件监听
#
# 监听 /data/events/queue.jsonl 文件变化，
# 有新事件写入时立刻调用 event_router.py 处理。
#
# 由 systemd 管理（event-watcher.service）

set -euo pipefail

HUB_DIR="${HUB_DIR:-$HOME/mason-hub}"
QUEUE_FILE="$HUB_DIR/data/events/queue.jsonl"
ROUTER="$HUB_DIR/scripts/event_router.py"
LOG="$HUB_DIR/logs/event_watcher.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

# 确保 queue 文件存在
touch "$QUEUE_FILE"

log "Event watcher 启动，监听 $QUEUE_FILE"

# inotifywait 监听文件修改
# -m = monitor 模式（持续监听）
# -e modify = 只在文件内容变化时触发
# --format %e = 输出事件类型
inotifywait -m -e modify "$QUEUE_FILE" --format '%e' 2>/dev/null |
while read -r event; do
    log "检测到文件变化: $event"

    # 防抖：等 1 秒让写入完成（多行可能快速写入）
    sleep 1

    # 调用 event_router 处理新事件
    python3 "$ROUTER" --process-new >> "$LOG" 2>&1 || true

    log "处理完成"
done
