#!/bin/bash
# xhs-cookie-refresh.sh — QR 码扫码刷新 XHS Cookie
# 流程: Playwright 打开登录页 → 截图 QR → 发 Slack → 等扫码 → 自动保存 cookie
# 用法: xhs-cookie-refresh.sh [--timeout 180]

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHB976R9V"  # #rednote
QR_REMOTE="/tmp/xhs_qr.png"
QR_LOCAL="/tmp/xhs_qr.png"
STATUS_REMOTE="/tmp/xhs_login_status"
TIMEOUT=180

while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== XHS Cookie Refresh (QR Code) ==="
echo "Time: $(TZ='America/New_York' date '+%Y-%m-%d %H:%M ET')"
echo "Timeout: ${TIMEOUT}s"
echo ""

# --- 获取 Slack token ---
if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
  ENV_FILE="$(dirname "$SLACK_NOTIFY")/.env"
  if [ -f "$ENV_FILE" ]; then
    export $(grep -E '^SLACK_BOT_TOKEN=' "$ENV_FILE" | xargs)
  fi
fi
if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
  echo "ERROR: SLACK_BOT_TOKEN not found"
  exit 1
fi

# --- Step 1: 上传 Python 脚本到阿里云 ---
echo "--- Uploading login script ---"
PYFILE="$HUB_DIR/skills/_xhs_qr_login.py"
scp -o ConnectTimeout=10 "$PYFILE" "$ALIYUN:/tmp/_xhs_qr_login.py"

# 清理旧状态 + 杀残留进程
ssh -o ConnectTimeout=10 "$ALIYUN" "rm -f $QR_REMOTE $STATUS_REMOTE /tmp/xhs_login.log; pkill -f '_xhs_qr_login' 2>/dev/null; true" 2>/dev/null

# --- Step 2: 在阿里云启动登录脚本 (后台) ---
echo "--- Starting Playwright on Aliyun ---"
ssh -o ConnectTimeout=10 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && nohup python3 -u /tmp/_xhs_qr_login.py $TIMEOUT > /tmp/xhs_login.log 2>&1 &"
sleep 2  # 等进程启动
echo "Playwright started in background"

# --- Step 3: 等待 QR 截图就绪 ---
echo ""
echo "--- Waiting for QR screenshot ---"
QR_FOUND=false
SAW_STARTING=false
for i in $(seq 1 45); do
  sleep 2
  STATUS=$(ssh -o ConnectTimeout=5 "$ALIYUN" "cat $STATUS_REMOTE 2>/dev/null" 2>/dev/null || echo "")

  # 跟踪进程启动状态
  if [[ "$STATUS" == "STARTING" ]]; then
    SAW_STARTING=true
  fi

  if [[ "$STATUS" == "QR_READY" ]] || [[ "$STATUS" == QR_REFRESHED* ]]; then
    echo "QR code ready!"
    QR_FOUND=true
    break
  fi

  # 只有在确认新进程启动后才处理终态
  if [ "$SAW_STARTING" = true ] || [ -z "$STATUS" ]; then
    if [[ "$STATUS" == "SUCCESS" ]]; then
      echo "Playwright reports SUCCESS (possibly valid existing session)"
      QR_FOUND=true
      break
    fi
    if [[ "$STATUS" == ERROR* ]] || [[ "$STATUS" == "TIMEOUT" ]]; then
      echo "ERROR: Playwright failed — $STATUS"
      ssh "$ALIYUN" "cat /tmp/xhs_login.log" 2>/dev/null | tail -20
      exit 1
    fi
  else
    # 还没看到 STARTING，忽略旧状态
    if [[ -n "$STATUS" ]] && [[ "$STATUS" != "STARTING" ]]; then
      echo "  ignoring stale status: $STATUS"
      continue
    fi
  fi

  echo "  waiting... ($STATUS)"
done

if [ "$QR_FOUND" = false ]; then
  echo "ERROR: QR not ready after 90s"
  echo "DEBUG log:"
  ssh "$ALIYUN" "cat /tmp/xhs_login.log" 2>/dev/null | tail -20
  exit 1
fi

# --- Step 4: 下载 QR 截图 ---
echo ""
echo "--- Downloading QR screenshot ---"
scp -o ConnectTimeout=10 "$ALIYUN:$QR_REMOTE" "$QR_LOCAL" 2>/dev/null
if [ ! -f "$QR_LOCAL" ]; then
  echo "ERROR: Failed to download QR screenshot"
  exit 1
fi
echo "Downloaded: $QR_LOCAL ($(wc -c < "$QR_LOCAL") bytes)"

# --- Step 5: 发送 QR 到 Slack ---
echo ""
echo "--- Sending QR to Slack ---"

# Slack 新版文件上传 API (3-step)
upload_to_slack() {
  local FILE="$1" CHANNEL="$2" MSG="$3"
  local FSIZE
  FSIZE=$(wc -c < "$FILE")

  # Step 1: 获取上传 URL
  local URL_RESP
  URL_RESP=$(curl -s -X POST "https://slack.com/api/files.getUploadURLExternal" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "filename=xhs_qr.png" \
    --data-urlencode "length=$FSIZE")

  local URL_OK
  URL_OK=$(echo "$URL_RESP" | jq -r '.ok')
  if [ "$URL_OK" != "true" ]; then
    echo "ERROR: getUploadURLExternal failed: $(echo "$URL_RESP" | jq -r '.error')"
    return 1
  fi

  local UPLOAD_URL FILE_ID
  UPLOAD_URL=$(echo "$URL_RESP" | jq -r '.upload_url')
  FILE_ID=$(echo "$URL_RESP" | jq -r '.file_id')

  # Step 2: 上传文件内容
  curl -s -X POST "$UPLOAD_URL" -F "file=@$FILE" > /dev/null

  # Step 3: 完成上传并分享到频道
  local COMPLETE_RESP
  COMPLETE_RESP=$(curl -s -X POST "https://slack.com/api/files.completeUploadExternal" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"files\":[{\"id\":\"$FILE_ID\",\"title\":\"XHS QR Code\"}],\"channel_id\":\"$CHANNEL\",\"initial_comment\":\"$MSG\"}")

  local COMPLETE_OK
  COMPLETE_OK=$(echo "$COMPLETE_RESP" | jq -r '.ok')
  if [ "$COMPLETE_OK" = "true" ]; then
    echo "File uploaded to Slack successfully"
    return 0
  else
    echo "ERROR: completeUploadExternal failed: $(echo "$COMPLETE_RESP" | jq -r '.error')"
    return 1
  fi
}

upload_to_slack "$QR_LOCAL" "$SLACK_CHANNEL" "🍪 *XHS Cookie 刷新* — 请用小红书 APP 扫描此二维码登录。扫码后自动保存 cookie。"
if [ $? -eq 0 ]; then
  echo "QR code sent to Slack #rednote"
else
  echo "WARNING: Slack upload failed, trying HTTP fallback..."
  mkdir -p /tmp/qr_serve && cp "$QR_LOCAL" /tmp/qr_serve/index.png
  python3 -m http.server 9876 --directory /tmp/qr_serve &>/dev/null &
  HTTP_PID=$!
  QR_URL="http://34.63.188.198:9876/index.png"
  notify_slack "$SLACK_CHANNEL" "🍪 *XHS Cookie 刷新* — 请扫描二维码登录：\n$QR_URL\n(链接 3 分钟后失效)" "XHS Crawler" ":cookie:"
  echo "QR image available at: $QR_URL"
  (sleep 180 && kill $HTTP_PID 2>/dev/null && rm -rf /tmp/qr_serve) &
fi

# --- Step 6: 等待扫码完成 ---
echo ""
echo "--- Waiting for QR scan (timeout: ${TIMEOUT}s) ---"
echo "请打开 Slack 扫描二维码..."

START_TIME=$(date +%s)
FINAL_STATUS=""

while true; do
  ELAPSED=$(( $(date +%s) - START_TIME ))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    FINAL_STATUS="TIMEOUT"
    echo "TIMEOUT: 超过 ${TIMEOUT}s 未检测到登录"
    break
  fi

  sleep 5
  STATUS=$(ssh -o ConnectTimeout=5 "$ALIYUN" "cat $STATUS_REMOTE 2>/dev/null" 2>/dev/null || echo "")

  case "$STATUS" in
    SUCCESS)
      FINAL_STATUS="SUCCESS"
      echo "Login successful! Cookie saved."
      break
      ;;
    TIMEOUT)
      FINAL_STATUS="TIMEOUT"
      echo "Playwright reported timeout"
      break
      ;;
    ERROR*)
      FINAL_STATUS="$STATUS"
      echo "Error: $STATUS"
      break
      ;;
    QR_REFRESHED_*)
      REFRESH_SEC=$(echo "$STATUS" | grep -oP '\d+')
      echo "  QR refreshed at ${REFRESH_SEC}s, re-downloading..."
      scp -o ConnectTimeout=10 "$ALIYUN:$QR_REMOTE" "$QR_LOCAL" 2>/dev/null
      if [ -f "$QR_LOCAL" ]; then
        # 更新 HTTP server 的文件
        cp "$QR_LOCAL" /tmp/qr_serve/index.png 2>/dev/null
        notify_slack "$SLACK_CHANNEL" "🔄 QR 码已刷新（${REFRESH_SEC}s），请重新扫码\nhttp://34.63.188.198:9876/index.png" "XHS Crawler" ":cookie:"
      fi
      ;;
    *)
      echo "  waiting... ${ELAPSED}s ($STATUS)"
      ;;
  esac
done

# --- Step 7: 报告结果 ---
echo ""
echo "=== Result: $FINAL_STATUS ==="

if [ "$FINAL_STATUS" = "SUCCESS" ]; then
  echo ""
  echo "--- Verifying new cookie ---"
  "$HUB_DIR/skills/xhs-cookie-check.sh"
  CHECK_EXIT=$?

  if [ $CHECK_EXIT -eq 0 ]; then
    notify_slack "$SLACK_CHANNEL" "✅ *XHS Cookie 刷新成功* — 新 cookie 已保存并验证有效。" "XHS Crawler" ":white_check_mark:"
    log_event "xhs-crawler" "cookie-refresh" "end" "Cookie refreshed via QR code"
    echo ""
    echo "Cookie refresh complete!"
    exit 0
  else
    notify_slack "$SLACK_CHANNEL" "⚠️ *XHS Cookie 已保存但验证失败* — 请检查是否正确扫码。" "XHS Crawler" ":warning:"
    echo "WARNING: Cookie saved but verification failed"
    exit 1
  fi
else
  notify_slack "$SLACK_CHANNEL" "❌ *XHS Cookie 刷新失败* — $FINAL_STATUS" "XHS Crawler" ":x:"
  echo "DEBUG log:"
  ssh "$ALIYUN" "cat /tmp/xhs_login.log 2>/dev/null" 2>/dev/null | tail -20
  exit 1
fi
