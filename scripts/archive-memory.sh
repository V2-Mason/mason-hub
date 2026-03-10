#!/usr/bin/env bash
# archive-memory.sh — Gateway 记忆归档
#
# 将 gateway-memory.jsonl 中超过 7 天的 resolved/monitoring 条目
# 归档到 data/archive/gateway-YYYY-MM.jsonl，保持活跃记忆精简。
#
# 规则：
#   - resolved/monitoring 超过 7 天 → 归档
#   - will_retry/pending_mason/suggestion/emitted → 永不归档（直到状态变更）
#   - 归档文件按月切分
#
# 用法：
#   bash scripts/archive-memory.sh              # 执行归档
#   bash scripts/archive-memory.sh --dry-run    # 只显示会做什么
#   bash scripts/archive-memory.sh --status     # 查看统计

set -euo pipefail

HUB_DIR="${HUB_DIR:-$HOME/mason-hub}"
MEMORY_FILE="$HUB_DIR/data/gateway-memory.jsonl"
ARCHIVE_DIR="$HUB_DIR/data/archive"
LOG_FILE="$HUB_DIR/logs/gateway.log"
DRY_RUN=false
RETENTION_DAYS=7

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] archive-memory: $*" | tee -a "$LOG_FILE"
}

if [[ "${1:-}" == "--status" ]]; then
    if [[ ! -f "$MEMORY_FILE" ]]; then
        echo "记忆文件不存在: $MEMORY_FILE"
        exit 0
    fi
    total=$(wc -l < "$MEMORY_FILE")
    echo "活跃记忆: $total 条"
    if [[ -d "$ARCHIVE_DIR" ]]; then
        for f in "$ARCHIVE_DIR"/gateway-*.jsonl; do
            [[ -f "$f" ]] || continue
            count=$(wc -l < "$f")
            echo "归档 $(basename "$f"): $count 条"
        done
    fi
    exit 0
fi

if [[ ! -f "$MEMORY_FILE" ]]; then
    log "记忆文件不存在，跳过归档"
    exit 0
fi

mkdir -p "$ARCHIVE_DIR"

# 用 Python 做归档（JSON 解析更可靠）
python3 -c "
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

memory_file = Path('$MEMORY_FILE')
archive_dir = Path('$ARCHIVE_DIR')
retention_days = $RETENTION_DAYS
dry_run = $( $DRY_RUN && echo 'True' || echo 'False' )
cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

# 可归档的状态
ARCHIVABLE = {'resolved', 'monitoring'}
# 永不归档的状态
KEEP_ALWAYS = {'will_retry', 'pending_mason', 'suggestion', 'emitted'}

active = []
to_archive = defaultdict(list)  # month_key -> items

with open(memory_file) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            active.append(line)  # 解析失败的保留
            continue

        status = item.get('status', 'unknown')
        ts_str = item.get('timestamp', '')

        # 解析时间
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            active.append(line)  # 时间解析失败的保留
            continue

        # 判断是否归档
        if status in ARCHIVABLE and ts < cutoff:
            month_key = ts.strftime('%Y-%m')
            to_archive[month_key].append(line)
        else:
            active.append(line)

# 统计
total_archive = sum(len(v) for v in to_archive.values())

if total_archive == 0:
    print('无需归档的条目')
    sys.exit(0)

print(f'归档: {total_archive} 条 → 保留: {len(active)} 条')

if dry_run:
    for month, items in sorted(to_archive.items()):
        print(f'  [DRY-RUN] gateway-{month}.jsonl ← {len(items)} 条')
    sys.exit(0)

# 写归档文件（追加模式）
for month, items in sorted(to_archive.items()):
    archive_file = archive_dir / f'gateway-{month}.jsonl'
    with open(archive_file, 'a') as f:
        for item_line in items:
            f.write(item_line + '\n')
    print(f'  gateway-{month}.jsonl ← {len(items)} 条')

# 写回活跃记忆
with open(memory_file, 'w') as f:
    for item_line in active:
        f.write(item_line + '\n')

print(f'完成: 活跃 {len(active)} 条, 归档 {total_archive} 条')
"
