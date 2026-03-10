#!/usr/bin/env bash
# data_health_check.sh — 数据健康检查
# 检查 data_catalog.yaml 中所有 active 数据集的健康状态
# 维护者: EMP_0014 (Data Engineer)
# 用法: bash data_health_check.sh [--slack]

set -uo pipefail

CATALOG="/home/hangn/mason-hub/data/data_catalog.yaml"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SSH_HOST="root@106.14.44.68"
SSH_TIMEOUT=5
SEND_SLACK=false
NOW_EPOCH=$(date +%s)
TIMESTAMP=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')

# 加载凭证（用于 API 端点认证检查）
if [ -f "/home/hangn/mason-hub/.env" ]; then
  set -a; source "/home/hangn/mason-hub/.env"; set +a
fi
SRX_TOKEN=""

# Parse args
for arg in "$@"; do
  case "$arg" in
    --slack) SEND_SLACK=true ;;
  esac
done

# Counters
COUNT_OK=0
COUNT_WARN=0
COUNT_ERR=0
COUNT_SKIP=0
RESULTS=""

# ─── Helper: human-readable time ago ───
time_ago() {
  local seconds=$1
  if [ "$seconds" -lt 60 ]; then
    echo "${seconds}s 前"
  elif [ "$seconds" -lt 3600 ]; then
    echo "$(( seconds / 60 ))m 前"
  elif [ "$seconds" -lt 86400 ]; then
    echo "$(( seconds / 3600 ))h 前"
  else
    echo "$(( seconds / 86400 ))d 前"
  fi
}

# ─── Helper: parse frequency string to seconds ───
freq_to_seconds() {
  local freq="$1"
  # Match common patterns
  if echo "$freq" | grep -qi "每 *30 *分钟\|每30分钟"; then
    echo 1800
  elif echo "$freq" | grep -qi "实时\|用户操作"; then
    echo 86400  # real-time: check once per day
  elif echo "$freq" | grep -qi "每日\|每天"; then
    echo 86400
  elif echo "$freq" | grep -qi "周二.*五\|周二/五"; then
    # Twice a week ~= 3.5 days
    echo 302400
  elif echo "$freq" | grep -qi "每周"; then
    echo 604800
  elif echo "$freq" | grep -qi "随.*触发"; then
    # Triggered by another pipeline, assume weekly
    echo 604800
  else
    # Default: 1 week
    echo 604800
  fi
}

# ─── Helper: classify staleness ───
# Returns: ok / warn / err
classify() {
  local age_sec=$1
  local expected_sec=$2
  if [ "$age_sec" -le $(( expected_sec * 2 )) ]; then
    echo "ok"
  elif [ "$age_sec" -le $(( expected_sec * 5 )) ]; then
    echo "warn"
  else
    echo "err"
  fi
}

# ─── Parse catalog with inline Python ───
# Extracts: id, storage_type, location, table, update_frequency, status
# One line per dataset, fields separated by |||
PARSED=$(/home/hangn/mason-hub/.venv/bin/python3 -c "
import yaml, sys

with open('$CATALOG') as f:
    data = yaml.safe_load(f)

for ds in data.get('datasets', []):
    if ds.get('status') != 'active':
        continue
    sid = ds.get('id', '?')
    storage = ds.get('storage', {})
    stype = storage.get('type', 'unknown')
    loc = storage.get('location', '')
    table = storage.get('table', '')
    freq = ds.get('update_frequency', '')
    endpoints = storage.get('endpoints', [])
    ep = endpoints[0] if endpoints else ''
    # Use _ placeholder for empty fields to prevent tab collapsing
    fields = [sid, stype, loc, table or '_', freq, ep or '_']
    print('\t'.join(fields))
")

# ─── Check each dataset ───
while IFS=$'\t' read -r ds_id stype location table freq endpoint; do
  [ -z "$ds_id" ] && continue
  # Restore empty fields from placeholder
  [ "$table" = "_" ] && table=""
  [ "$endpoint" = "_" ] && endpoint=""

  expected_sec=$(freq_to_seconds "$freq")
  status="skip"
  detail=""

  case "$stype" in

    sqlite)
      # Determine if aliyun or gcp
      if echo "$location" | grep -q "^aliyun:"; then
        filepath="${location#aliyun:}"
        # SSH check with timeout
        ssh_result=$(ssh -n -o ConnectTimeout=$SSH_TIMEOUT -o StrictHostKeyChecking=no "$SSH_HOST" \
          "if [ -f '$filepath' ]; then
             mtime=\$(stat -c %Y '$filepath' 2>/dev/null || echo 0)
             rows=\$(sqlite3 '$filepath' 'SELECT COUNT(*) FROM $table' 2>/dev/null || echo '?')
             echo \"EXISTS|\$mtime|\$rows\"
           else
             echo 'MISSING|0|0'
           fi" 2>/dev/null || echo "SSH_FAIL|0|0")

        IFS='|' read -r ssh_status file_mtime row_count <<< "$ssh_result"
        if [ "$ssh_status" = "SSH_FAIL" ]; then
          status="err"
          detail="SSH 连接失败"
        elif [ "$ssh_status" = "MISSING" ]; then
          status="err"
          detail="文件不存在"
        else
          age=$(( NOW_EPOCH - file_mtime ))
          status=$(classify "$age" "$expected_sec")
          detail="更新于 $(time_ago "$age")，${row_count} 行"
        fi

      elif echo "$location" | grep -q "^gcp:"; then
        raw_path="${location#gcp:}"
        # Expand ~ and date patterns
        expanded_path=$(echo "$raw_path" | sed "s|~|/home/hangn|g")
        # Handle YYYY-MM-DD pattern: try today then yesterday
        if echo "$expanded_path" | grep -q "YYYY-MM-DD"; then
          today_path=$(echo "$expanded_path" | sed "s|YYYY-MM-DD|$(date +%Y-%m-%d)|g")
          yesterday_path=$(echo "$expanded_path" | sed "s|YYYY-MM-DD|$(date -d yesterday +%Y-%m-%d)|g")
          if [ -f "$today_path" ]; then
            filepath="$today_path"
          elif [ -f "$yesterday_path" ]; then
            filepath="$yesterday_path"
          else
            filepath="$today_path"  # will fail check below
          fi
        else
          filepath="$expanded_path"
        fi

        if [ -f "$filepath" ]; then
          file_mtime=$(stat -c %Y "$filepath" 2>/dev/null || echo 0)
          age=$(( NOW_EPOCH - file_mtime ))
          # Get row count from main table if specified, else report file size
          if [ -n "$table" ]; then
            row_count=$(sqlite3 "$filepath" "SELECT COUNT(*) FROM $table" 2>/dev/null || echo "?")
            row_count="${row_count} 行"
          else
            fsize=$(du -h "$filepath" 2>/dev/null | cut -f1)
            row_count="大小 ${fsize}"
          fi
          status=$(classify "$age" "$expected_sec")
          detail="更新于 $(time_ago "$age")，${row_count}"
        else
          status="err"
          detail="文件不存在: $(basename "${filepath}")"
        fi
      fi
      ;;

    json|markdown)
      if echo "$location" | grep -q "^aliyun:"; then
        filepath="${location#aliyun:}"
        # Handle date patterns
        if echo "$filepath" | grep -q "YYYY-MM-DD"; then
          today_file=$(echo "$filepath" | sed "s|YYYY-MM-DD|$(date +%Y-%m-%d)|g")
          yesterday_file=$(echo "$filepath" | sed "s|YYYY-MM-DD|$(date -d yesterday +%Y-%m-%d)|g")
          # SSH check both
          ssh_result=$(ssh -n -o ConnectTimeout=$SSH_TIMEOUT -o StrictHostKeyChecking=no "$SSH_HOST" \
            "if [ -f '$today_file' ]; then
               mtime=\$(stat -c %Y '$today_file' 2>/dev/null || echo 0)
               fsize=\$(du -h '$today_file' 2>/dev/null | cut -f1)
               echo \"EXISTS|\$mtime|\$fsize\"
             elif [ -f '$yesterday_file' ]; then
               mtime=\$(stat -c %Y '$yesterday_file' 2>/dev/null || echo 0)
               fsize=\$(du -h '$yesterday_file' 2>/dev/null | cut -f1)
               echo \"EXISTS|\$mtime|\$fsize\"
             else
               echo 'MISSING|0|0'
             fi" 2>/dev/null || echo "SSH_FAIL|0|0")

          IFS='|' read -r ssh_status file_mtime fsize <<< "$ssh_result"
          if [ "$ssh_status" = "SSH_FAIL" ]; then
            status="err"
            detail="SSH 连接失败"
          elif [ "$ssh_status" = "MISSING" ]; then
            status="err"
            detail="文件不存在"
          else
            age=$(( NOW_EPOCH - file_mtime ))
            status=$(classify "$age" "$expected_sec")
            detail="更新于 $(time_ago "$age")，大小 ${fsize}"
          fi
        else
          # No date pattern, check single file
          ssh_result=$(ssh -n -o ConnectTimeout=$SSH_TIMEOUT -o StrictHostKeyChecking=no "$SSH_HOST" \
            "if [ -f '$filepath' ]; then
               mtime=\$(stat -c %Y '$filepath' 2>/dev/null || echo 0)
               fsize=\$(du -h '$filepath' 2>/dev/null | cut -f1)
               echo \"EXISTS|\$mtime|\$fsize\"
             else
               echo 'MISSING|0|0'
             fi" 2>/dev/null || echo "SSH_FAIL|0|0")

          IFS='|' read -r ssh_status file_mtime fsize <<< "$ssh_result"
          if [ "$ssh_status" = "SSH_FAIL" ]; then
            status="err"
            detail="SSH 连接失败"
          elif [ "$ssh_status" = "MISSING" ]; then
            status="err"
            detail="文件不存在"
          else
            age=$(( NOW_EPOCH - file_mtime ))
            status=$(classify "$age" "$expected_sec")
            detail="更新于 $(time_ago "$age")，大小 ${fsize}"
          fi
        fi

      elif echo "$location" | grep -q "^gcp:"; then
        raw_path="${location#gcp:}"
        expanded_path=$(echo "$raw_path" | sed "s|~|/home/hangn|g")

        if echo "$expanded_path" | grep -q "YYYY-MM-DD"; then
          today_path=$(echo "$expanded_path" | sed "s|YYYY-MM-DD|$(date +%Y-%m-%d)|g")
          yesterday_path=$(echo "$expanded_path" | sed "s|YYYY-MM-DD|$(date -d yesterday +%Y-%m-%d)|g")
          if [ -f "$today_path" ]; then
            filepath="$today_path"
          elif [ -f "$yesterday_path" ]; then
            filepath="$yesterday_path"
          else
            filepath="$today_path"
          fi
        elif echo "$expanded_path" | grep -q '\*'; then
          # Glob pattern (e.g., *.md) — find most recent file
          parent_dir=$(dirname "$expanded_path")
          pattern=$(basename "$expanded_path")
          if [ -d "$parent_dir" ]; then
            filepath=$(find "$parent_dir" -maxdepth 1 -name "$pattern" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
            [ -z "$filepath" ] && filepath="$expanded_path"
          else
            filepath="$expanded_path"
          fi
        else
          filepath="$expanded_path"
        fi

        if [ -f "$filepath" ]; then
          file_mtime=$(stat -c %Y "$filepath" 2>/dev/null || echo 0)
          age=$(( NOW_EPOCH - file_mtime ))
          fsize=$(du -h "$filepath" 2>/dev/null | cut -f1)
          status=$(classify "$age" "$expected_sec")
          detail="更新于 $(time_ago "$age")，大小 ${fsize}"
        elif [ -d "$(dirname "$filepath")" ]; then
          # Directory exists but no matching file
          status="err"
          detail="文件不存在: $(basename "$filepath")"
        else
          status="err"
          detail="目录不存在: $(dirname "$filepath")"
        fi
      fi
      ;;

    markdown_files)
      # Directory of markdown files — check most recent
      if echo "$location" | grep -q "^gcp:"; then
        raw_path="${location#gcp:}"
        expanded_path=$(echo "$raw_path" | sed "s|~|/home/hangn|g")
        # Strip glob and get directory path
        dir_path=$(dirname "$expanded_path")

        if [ -d "$dir_path" ]; then
          latest=$(find "$dir_path" -maxdepth 1 -name "*.md" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
          if [ -n "$latest" ]; then
            file_mtime=$(echo "$latest" | cut -d'.' -f1)
            latest_file=$(echo "$latest" | cut -d' ' -f2-)
            age=$(( NOW_EPOCH - file_mtime ))
            file_count=$(find "$dir_path" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l)
            status=$(classify "$age" "$expected_sec")
            detail="更新于 $(time_ago "$age")，${file_count} 个文件"
          else
            status="err"
            detail="目录为空"
          fi
        else
          status="err"
          detail="目录不存在: $dir_path"
        fi
      fi
      ;;

    api_response)
      # Check API endpoint reachability (with JWT auth if available)
      if [ -n "$endpoint" ]; then
        # Extract host from location
        host="${location#aliyun:}"
        url="http://${host}${endpoint}"
        # Lazy login: get token on first API check
        if [ -z "$SRX_TOKEN" ] && [ -n "${SRX_API_EMAIL:-}" ] && [ -n "${SRX_API_PASSWORD:-}" ]; then
          SRX_TOKEN=$(curl -s -X POST "http://${host}/api/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"email\":\"$SRX_API_EMAIL\",\"password\":\"$SRX_API_PASSWORD\"}" 2>/dev/null \
            | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
        fi
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$SSH_TIMEOUT" \
          ${SRX_TOKEN:+-H "Authorization: Bearer $SRX_TOKEN"} "$url" 2>/dev/null || echo "000")
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
          status="ok"
          detail="API 可达 (HTTP $http_code)"
        elif [ "$http_code" = "000" ]; then
          status="err"
          detail="API 不可达 (连接超时)"
        else
          status="warn"
          detail="API 返回 HTTP $http_code"
        fi
      else
        status="skip"
        detail="无端点信息"
      fi
      ;;

    slack_message)
      status="skip"
      detail="Slack 消息类型，跳过"
      ;;

    jsonl)
      # JSONL file — check like regular file
      if echo "$location" | grep -q "^gcp:"; then
        raw_path="${location#gcp:}"
        expanded_path=$(echo "$raw_path" | sed "s|~|/home/hangn|g")
        if [ -f "$expanded_path" ]; then
          file_mtime=$(stat -c %Y "$expanded_path" 2>/dev/null || echo 0)
          age=$(( NOW_EPOCH - file_mtime ))
          line_count=$(wc -l < "$expanded_path" 2>/dev/null || echo "?")
          fsize=$(du -h "$expanded_path" 2>/dev/null | cut -f1)
          status=$(classify "$age" "$expected_sec")
          detail="更新于 $(time_ago "$age")，${line_count} 条，大小 ${fsize}"
        else
          status="err"
          detail="文件不存在"
        fi
      fi
      ;;

    stdout)
      status="skip"
      detail="stdout 类型，跳过"
      ;;

    *)
      status="skip"
      detail="未知类型: $stype"
      ;;
  esac

  # Format result line
  case "$status" in
    ok)
      RESULTS+="  :white_check_mark: ${ds_id} -- ${detail}"$'\n'
      COUNT_OK=$(( COUNT_OK + 1 ))
      ;;
    warn)
      RESULTS+="  :warning: ${ds_id} -- ${detail}"$'\n'
      COUNT_WARN=$(( COUNT_WARN + 1 ))
      ;;
    err)
      RESULTS+="  :x: ${ds_id} -- ${detail}"$'\n'
      COUNT_ERR=$(( COUNT_ERR + 1 ))
      ;;
    skip)
      RESULTS+="  :fast_forward: ${ds_id} -- ${detail}"$'\n'
      COUNT_SKIP=$(( COUNT_SKIP + 1 ))
      ;;
  esac

done <<< "$PARSED"

TOTAL=$(( COUNT_OK + COUNT_WARN + COUNT_ERR ))

# ─── Build output ───
OUTPUT=":bar_chart: 数据健康检查 -- ${TIMESTAMP} CST"$'\n'
OUTPUT+=""$'\n'
OUTPUT+="$RESULTS"
OUTPUT+=""$'\n'
OUTPUT+="总结: ${COUNT_OK}/${TOTAL} 健康"
[ "$COUNT_WARN" -gt 0 ] && OUTPUT+="，${COUNT_WARN} 警告"
[ "$COUNT_ERR" -gt 0 ] && OUTPUT+="，${COUNT_ERR} 异常"
[ "$COUNT_SKIP" -gt 0 ] && OUTPUT+="（${COUNT_SKIP} 跳过）"
OUTPUT+=""$'\n'

# ─── 数据量阈值检查 (方案 C 升级触发器) ───
TOTAL_SIZE_BYTES=0
# GCP 本地数据
for db in /home/hangn/mason-hub/tools/trendradar/output/news/*.db \
          /home/hangn/mason-hub/tools/trendradar/output/rss/*.db \
          /home/hangn/mason-hub/tools/radar-tracker/tracker.db \
          /home/hangn/mason-hub/data/mirror/*.db; do
  [ -f "$db" ] && TOTAL_SIZE_BYTES=$(( TOTAL_SIZE_BYTES + $(stat -c %s "$db" 2>/dev/null || echo 0) ))
done
# 阿里云数据
ALIYUN_SIZE=$(ssh -n -o ConnectTimeout=$SSH_TIMEOUT -o StrictHostKeyChecking=no "$SSH_HOST" \
  "du -sb /opt/mediacrawler/database/sqlite_tables.db /opt/mediacrawler/analysis/ 2>/dev/null | awk '{s+=\$1} END{print s+0}'" 2>/dev/null || echo 0)
TOTAL_SIZE_MB=$(( (TOTAL_SIZE_BYTES + ALIYUN_SIZE) / 1048576 ))

OUTPUT+="总数据量: ${TOTAL_SIZE_MB}MB"$'\n'
if [ "$TOTAL_SIZE_MB" -gt 50 ]; then
  OUTPUT+=":rotating_light: 数据总量 >50MB，建议评估方案 C (API 网关) 升级 — docs/plans/2026-03-10-data-unified-storage.md"$'\n'
fi

# ─── Output ───
echo "$OUTPUT"

if [ "$SEND_SLACK" = true ]; then
  echo ">>> 发送到 Slack #system-alerts ..."
  bash "$SLACK_NOTIFY" "#system-alerts" "$OUTPUT"
  echo ">>> 已发送"
fi
