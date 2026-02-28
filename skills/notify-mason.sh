#!/bin/bash
# notify-mason.sh — 推送消息到 Mason 手机
# 用法: notify-mason.sh <title> <content> [level]
#
# level:
#   info  — 只发 Slack（默认）
#   warn  — 发 Slack + Server酱推送
#   alert — 发 Slack + Server酱推送（高优先级）
#
# 推送通道（优先级）:
#   1. Server酱 (https://sct.ftqq.com/) — 微信推送
#   2. 企业微信 Webhook（备选）
#
# 环境变量:
#   SERVERCHAN_KEY — Server酱 SendKey（必须）
#   WECOM_WEBHOOK  — 企业微信 Webhook URL（备选）

set -uo pipefail

SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SLACK_ALERT_CHANNEL="#mason-alerts"

# --- 参数解析 ---
if [ $# -lt 2 ]; then
  echo "用法: $0 <title> <content> [level]"
  echo "  level: info (default), warn, alert"
  exit 1
fi

TITLE="$1"
CONTENT="$2"
LEVEL="${3:-info}"

echo "[notify-mason] Title: $TITLE"
echo "[notify-mason] Level: $LEVEL"

# --- 1. Slack 通知（所有 level 都发）---
if [ -x "$SLACK_NOTIFY" ]; then
  case "$LEVEL" in
    alert) EMOJI=":rotating_light:" ;;
    warn)  EMOJI=":warning:" ;;
    *)     EMOJI=":information_source:" ;;
  esac

  SLACK_MSG="*${TITLE}*
${CONTENT}"

  "$SLACK_NOTIFY" "$SLACK_ALERT_CHANNEL" "$SLACK_MSG" "Mason Alert" "$EMOJI" 2>/dev/null || true
  echo "[notify-mason] Slack sent to $SLACK_ALERT_CHANNEL"
fi

# --- 2. 手机推送（warn/alert 才触发）---
if [ "$LEVEL" = "info" ]; then
  echo "[notify-mason] Level=info, skip phone push"
  exit 0
fi

PUSH_SENT=false

# --- 2a. Server酱推送 ---
SERVERCHAN_KEY="${SERVERCHAN_KEY:-}"
if [ -n "$SERVERCHAN_KEY" ]; then
  echo "[notify-mason] Pushing via Server酱..."

  # URL encode title for Server酱
  ENCODED_TITLE=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$TITLE'))" 2>/dev/null || echo "$TITLE")

  SC_RESPONSE=$(timeout 10 curl -s -X POST \
    "https://sctapi.ftqq.com/${SERVERCHAN_KEY}.send" \
    -d "title=${ENCODED_TITLE}" \
    -d "desp=${CONTENT}" \
    2>/dev/null || echo "ERROR")

  SC_CODE=$(echo "$SC_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',999))" 2>/dev/null || echo "999")

  if [ "$SC_CODE" = "0" ]; then
    echo "[notify-mason] Server酱 push OK"
    PUSH_SENT=true
  else
    echo "[notify-mason] Server酱 push failed (code=$SC_CODE): $SC_RESPONSE"
  fi
fi

# --- 2b. 企业微信 Webhook（备选）---
WECOM_WEBHOOK="${WECOM_WEBHOOK:-}"
if [ "$PUSH_SENT" = false ] && [ -n "$WECOM_WEBHOOK" ]; then
  echo "[notify-mason] Falling back to WeCom webhook..."

  WECOM_RESPONSE=$(timeout 10 curl -s -X POST \
    "$WECOM_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"[$LEVEL] $TITLE\n$CONTENT\"}}" \
    2>/dev/null || echo "ERROR")

  WC_CODE=$(echo "$WECOM_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('errcode',999))" 2>/dev/null || echo "999")

  if [ "$WC_CODE" = "0" ]; then
    echo "[notify-mason] WeCom push OK"
    PUSH_SENT=true
  else
    echo "[notify-mason] WeCom push failed (code=$WC_CODE)"
  fi
fi

# --- 3. 结果 ---
if [ "$PUSH_SENT" = false ] && [ "$LEVEL" != "info" ]; then
  echo "[notify-mason] WARNING: No push channel available. Set SERVERCHAN_KEY or WECOM_WEBHOOK env var."
  echo "[notify-mason] Slack notification was still sent."
  exit 1
fi

echo "[notify-mason] Done."
