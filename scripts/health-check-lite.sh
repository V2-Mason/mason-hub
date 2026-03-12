#!/usr/bin/env bash
# health-check-lite.sh — 纯 bash 健康检查（替代 Gateway LLM 心跳）
#
# 零 token 成本。每小时 cron 触发。
# 正常 → 静默。异常 → emit_event + Slack 告警。
# mason-gateway.py 保留作为按需诊断工具，不再永驻。
#
# 检查项（来自 Gateway 轻巡逻辑）：
#   1. 磁盘使用率 >85%
#   2. 阿里云 SSH 连通性
#   3. 关键 systemd 服务状态
#   4. 数据健康检查（data_health_check.sh）
#   5. cron 任务注册数
#   6. 内存使用率 >90%

set -uo pipefail

HUB_DIR="${HUB_DIR:-/home/hangn/mason-hub}"
EMIT_EVENT="$HUB_DIR/scripts/emit_event.sh"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SLACK_CHANNEL="C0AGXNH7F6J"  # #system-alerts
LOG_FILE="$HUB_DIR/logs/heartbeat.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S ET')] $*" >> "$LOG_FILE"
}

alerts=()
details=()

# --- 1. 磁盘 ---
disk_pct=$(df / --output=pcent | tail -1 | tr -d '% ')
if [ "$disk_pct" -gt 85 ]; then
  alerts+=("磁盘 ${disk_pct}% (>85%)")
  details+=("disk_pct:${disk_pct}")
fi

# --- 2. 阿里云 SSH ---
if ! timeout 5 ssh -o ConnectTimeout=3 root@106.14.44.68 "echo ok" &>/dev/null; then
  alerts+=("阿里云 SSH 不通")
  details+=("aliyun_ssh:failed")
fi

# --- 3. 关键服务 ---
for svc in cron; do
  if ! systemctl is-active --quiet "$svc" 2>/dev/null; then
    alerts+=("服务 $svc 未运行")
    details+=("service_${svc}:down")
  fi
done

# --- 4. 数据健康检查 ---
if [ -x "$HUB_DIR/data/pipelines/data_health_check.sh" ]; then
  health_out=$(bash "$HUB_DIR/data/pipelines/data_health_check.sh" --no-emit 2>&1) || true
  fail_count=$(echo "$health_out" | grep -c '❌' || true)
  if [ "$fail_count" -gt 3 ]; then
    alerts+=("数据健康检查 ${fail_count} 项失败")
    details+=("data_health:${fail_count}_failed")
  fi
fi

# --- 5. Cron 任务数 ---
cron_count=$(crontab -l 2>/dev/null | grep -cE 'mason-hub|surenxuan' || echo 0)
if [ "$cron_count" -lt 5 ]; then
  alerts+=("Cron 任务仅 ${cron_count} 条 (<5)")
  details+=("cron_count:${cron_count}")
fi

# --- 6. 内存 ---
mem_pct=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$mem_pct" -gt 90 ]; then
  alerts+=("内存 ${mem_pct}% (>90%)")
  details+=("mem_pct:${mem_pct}")
fi

# --- 输出结果 ---
if [ ${#alerts[@]} -eq 0 ]; then
  log "[轻巡] ✅ 正常 (磁盘 ${disk_pct}%, 内存 ${mem_pct}%, cron ${cron_count} 条)"
  exit 0
fi

# 有异常
alert_text=$(printf '%s; ' "${alerts[@]}")
detail_json=$(printf '"%s",' "${details[@]}" | sed 's/,$//')
log "[轻巡] ⚠️ 发现 ${#alerts[@]} 个异常: $alert_text"

# Emit event（Dispatcher 可消费）
if [ -x "$EMIT_EVENT" ]; then
  "$EMIT_EVENT" "health-check-failed" "health-check-lite" "warning" 2 \
    "{\"alerts\":[${detail_json}],\"summary\":\"${alert_text}\"}" 2>/dev/null || true
fi

# Slack 告警
if [ -x "$SLACK_NOTIFY" ]; then
  "$SLACK_NOTIFY" "$SLACK_CHANNEL" "⚠️ 健康检查异常: ${alert_text}" 2>/dev/null || true
fi

exit 1
