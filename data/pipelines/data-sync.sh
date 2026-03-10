#!/usr/bin/env bash
# data-sync.sh — 阿里云数据镜像同步到 GCP
# 维护者: EMP_0014 (Data Engineer)
# 设计文档: docs/plans/2026-03-10-data-unified-storage.md (方案 A)
#
# 功能:
#   1. sqlite3 .backup 阿里云 XHS 数据库（避免锁冲突）
#   2. scp 备份文件到 GCP data/mirror/
#   3. 同步最新分析 JSON 和策略简报
#   4. 写 .last_sync 时间戳
#
# 用法:
#   bash data-sync.sh              # 手动运行
#   bash data-sync.sh --slack      # 运行并发 Slack 通知
#   cron: 在阿里云采集完成后触发

set -uo pipefail

# ─── 配置 ───
SSH_HOST="root@106.14.44.68"
SSH_TIMEOUT=10
MIRROR_DIR="/home/hangn/mason-hub/data/mirror"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SLACK_CHANNEL="#system-alerts"
SEND_SLACK=false

REMOTE_DB="/opt/mediacrawler/database/sqlite_tables.db"
REMOTE_ANALYSIS_DIR="/opt/mediacrawler/analysis"
REMOTE_BRIEFINGS_DIR="/opt/mediacrawler/analysis/briefings"

TIMESTAMP=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S CST')

# Parse args
for arg in "$@"; do
  case "$arg" in
    --slack) SEND_SLACK=true ;;
  esac
done

# ─── 初始化 ───
mkdir -p "$MIRROR_DIR/analysis" "$MIRROR_DIR/briefings"

SYNC_OK=0
SYNC_FAIL=0
DETAILS=""

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# ─── Step 1: SQLite 数据库备份 + 传输 ───
log "Step 1: 备份阿里云 SQLite 数据库..."
REMOTE_BACKUP="/tmp/sqlite_tables_backup.db"

if ssh -o ConnectTimeout="$SSH_TIMEOUT" "$SSH_HOST" \
    "sqlite3 '$REMOTE_DB' '.backup $REMOTE_BACKUP'" 2>/dev/null; then
  log "  远程 .backup 完成，开始 scp..."
  if scp -o ConnectTimeout="$SSH_TIMEOUT" \
      "$SSH_HOST:$REMOTE_BACKUP" "$MIRROR_DIR/sqlite_tables.db" 2>/dev/null; then
    DB_SIZE=$(du -h "$MIRROR_DIR/sqlite_tables.db" 2>/dev/null | cut -f1)
    log "  数据库同步成功 ($DB_SIZE)"
    DETAILS+="  sqlite_tables.db: OK ($DB_SIZE)\n"
    SYNC_OK=$(( SYNC_OK + 1 ))
    # 清理远程临时文件
    ssh -o ConnectTimeout="$SSH_TIMEOUT" "$SSH_HOST" "rm -f '$REMOTE_BACKUP'" 2>/dev/null || true
  else
    log "  ERROR: scp 传输失败"
    DETAILS+="  sqlite_tables.db: FAIL (scp error)\n"
    SYNC_FAIL=$(( SYNC_FAIL + 1 ))
  fi
else
  log "  ERROR: 远程 .backup 失败（SSH 连接或 sqlite3 错误）"
  DETAILS+="  sqlite_tables.db: FAIL (backup error)\n"
  SYNC_FAIL=$(( SYNC_FAIL + 1 ))
fi

# ─── Step 2: 同步分析 JSON（最近 7 天） ───
log "Step 2: 同步分析 JSON..."

# 同步顶层 analysis_*.json + 子目录 (comments/, trends/)
RECENT_JSON=$(ssh -n -o ConnectTimeout="$SSH_TIMEOUT" "$SSH_HOST" \
  "find '$REMOTE_ANALYSIS_DIR' -maxdepth 2 -name '*.json' -mtime -7 -printf '%P\n' 2>/dev/null" 2>/dev/null) || true

if [ -n "$RECENT_JSON" ]; then
  JSON_COUNT=0
  JSON_FAIL_COUNT=0
  while IFS= read -r fname; do
    [ -z "$fname" ] && continue
    # 创建子目录（如 comments/, trends/）
    fname_dir=$(dirname "$fname")
    [ "$fname_dir" != "." ] && mkdir -p "$MIRROR_DIR/analysis/$fname_dir"
    if scp -o ConnectTimeout="$SSH_TIMEOUT" \
        "$SSH_HOST:$REMOTE_ANALYSIS_DIR/$fname" "$MIRROR_DIR/analysis/$fname" 2>/dev/null; then
      JSON_COUNT=$(( JSON_COUNT + 1 ))
    else
      JSON_FAIL_COUNT=$(( JSON_FAIL_COUNT + 1 ))
    fi
  done <<< "$RECENT_JSON"
  log "  分析 JSON: ${JSON_COUNT} 成功, ${JSON_FAIL_COUNT} 失败"
  DETAILS+="  analysis/*.json: ${JSON_COUNT} synced"
  [ "$JSON_FAIL_COUNT" -gt 0 ] && DETAILS+=", ${JSON_FAIL_COUNT} failed"
  DETAILS+="\n"
  [ "$JSON_COUNT" -gt 0 ] && SYNC_OK=$(( SYNC_OK + 1 ))
  [ "$JSON_FAIL_COUNT" -gt 0 ] && SYNC_FAIL=$(( SYNC_FAIL + 1 ))
else
  log "  无最近 7 天的分析 JSON（或 SSH 失败）"
  DETAILS+="  analysis/*.json: 无文件或连接失败\n"
fi

# ─── Step 3: 同步策略简报（最近 7 天） ───
log "Step 3: 同步策略简报..."

RECENT_BRIEFINGS=$(ssh -o ConnectTimeout="$SSH_TIMEOUT" "$SSH_HOST" \
  "find '$REMOTE_BRIEFINGS_DIR' -maxdepth 1 -name '*.json' -mtime -7 -printf '%f\n' 2>/dev/null" 2>/dev/null) || true

if [ -n "$RECENT_BRIEFINGS" ]; then
  BR_COUNT=0
  BR_FAIL_COUNT=0
  while IFS= read -r fname; do
    [ -z "$fname" ] && continue
    if scp -o ConnectTimeout="$SSH_TIMEOUT" \
        "$SSH_HOST:$REMOTE_BRIEFINGS_DIR/$fname" "$MIRROR_DIR/briefings/$fname" 2>/dev/null; then
      BR_COUNT=$(( BR_COUNT + 1 ))
    else
      BR_FAIL_COUNT=$(( BR_FAIL_COUNT + 1 ))
    fi
  done <<< "$RECENT_BRIEFINGS"
  log "  策略简报: ${BR_COUNT} 成功, ${BR_FAIL_COUNT} 失败"
  DETAILS+="  briefings/*.json: ${BR_COUNT} synced"
  [ "$BR_FAIL_COUNT" -gt 0 ] && DETAILS+=", ${BR_FAIL_COUNT} failed"
  DETAILS+="\n"
  [ "$BR_COUNT" -gt 0 ] && SYNC_OK=$(( SYNC_OK + 1 ))
  [ "$BR_FAIL_COUNT" -gt 0 ] && SYNC_FAIL=$(( SYNC_FAIL + 1 ))
else
  log "  无最近 7 天的策略简报（或 SSH 失败）"
  DETAILS+="  briefings/*.json: 无文件或连接失败\n"
fi

# ─── Step 4: 写 .last_sync 时间戳 ───
echo "$TIMESTAMP" > "$MIRROR_DIR/.last_sync"
log "写入 .last_sync: $TIMESTAMP"

# ─── 汇总 ───
TOTAL=$(( SYNC_OK + SYNC_FAIL ))
log "=== 同步完成: ${SYNC_OK}/${TOTAL} 成功, ${SYNC_FAIL} 失败 ==="

if [ "$SEND_SLACK" = true ]; then
  SLACK_MSG="Data Sync -- $TIMESTAMP
${SYNC_OK}/${TOTAL} 成功"
  [ "$SYNC_FAIL" -gt 0 ] && SLACK_MSG+="，${SYNC_FAIL} 失败"
  SLACK_MSG+="
$(echo -e "$DETAILS")"
  bash "$SLACK_NOTIFY" "$SLACK_CHANNEL" "$SLACK_MSG" 2>/dev/null || true
  log "Slack 通知已发送"
fi

# 只在全部失败时返回非零退出码
if [ "$SYNC_OK" -eq 0 ] && [ "$TOTAL" -gt 0 ]; then
  "$HUB_DIR/scripts/emit_event.sh" "data-sync-failed" "data-sync.sh" "failed" 2 "{\"synced\":$SYNC_OK,\"total\":$TOTAL}" 2>/dev/null || true
  exit 1
fi

# 发射事件: 数据同步完成
"$HUB_DIR/scripts/emit_event.sh" "data-sync-complete" "data-sync.sh" "ok" 1 "{\"synced\":$SYNC_OK,\"total\":$TOTAL}" 2>/dev/null || true
exit 0
