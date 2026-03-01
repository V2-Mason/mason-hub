#!/bin/bash
# xhs-cookie-check.sh — XHS Cookie 有效性检测（多账号）
# 用法: xhs-cookie-check.sh [--notify] [--account A]
#   --notify   过期时发 Slack 通知
#   --account  只检测指定账号（不传则检测所有账号）
# Exit code: 0=全部有效, 1=有过期的

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHTA97EAY"
DO_NOTIFY=false
CHECK_ACCOUNT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --notify) DO_NOTIFY=true; shift ;;
    --account) CHECK_ACCOUNT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "=== XHS Cookie Check ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

# SCP check script to Aliyun (避免 SSH heredoc 转义问题)
cat > /tmp/_xhs_cookie_check.py << 'PYEOF'
import json, sys, os

accounts_file = '/opt/mediacrawler/accounts.json'
if not os.path.exists(accounts_file):
    print("NO_ACCOUNTS_FILE")
    sys.exit(1)

with open(accounts_file) as f:
    accounts = json.load(f)

check_id = sys.argv[1] if len(sys.argv) > 1 else ""

results = []
for aid, acct in accounts.items():
    if check_id and aid != check_id:
        continue
    cookie = acct.get("cookie", "")
    name = acct.get("name", "?")
    if not cookie:
        results.append(f"{aid}|{name}|NO_COOKIE")
    elif len(cookie) < 50:
        results.append(f"{aid}|{name}|TOO_SHORT")
    else:
        # 简单检测: cookie 包含关键字段
        has_session = "web_session" in cookie
        has_a1 = "a1=" in cookie
        if has_session and has_a1:
            results.append(f"{aid}|{name}|HAS_COOKIE")
        else:
            results.append(f"{aid}|{name}|INCOMPLETE")

for r in results:
    print(r)
PYEOF

scp -o ConnectTimeout=10 -q /tmp/_xhs_cookie_check.py "$ALIYUN:$MC_DIR/_cookie_check.py"

CHECK_OUTPUT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "cd $MC_DIR && python3 _cookie_check.py '$CHECK_ACCOUNT'" 2>/dev/null)

SSH_EXIT=$?
if [ $SSH_EXIT -ne 0 ]; then
  echo "ERROR: SSH failed (exit $SSH_EXIT)"
  exit 1
fi

if [ -z "$CHECK_OUTPUT" ] || echo "$CHECK_OUTPUT" | grep -q "NO_ACCOUNTS_FILE"; then
  echo "accounts.json not found on Aliyun"
  echo "Run: scp shared/accounts.template.json $ALIYUN:$MC_DIR/accounts.json"
  exit 1
fi

# Parse results
ANY_BAD=false
EXPIRED_LIST=""

while IFS='|' read -r aid name status; do
  case "$status" in
    HAS_COOKIE)
      echo "  $aid ($name): ✓ cookie present"
      log_event "xhs-crawler" "cookie-check" "info" "Account $aid cookie present"
      ;;
    NO_COOKIE)
      echo "  $aid ($name): ✗ no cookie configured"
      ANY_BAD=true
      EXPIRED_LIST="${EXPIRED_LIST}• 账号 $aid ($name): 未配置 cookie\n"
      ;;
    INCOMPLETE)
      echo "  $aid ($name): ✗ cookie incomplete (missing web_session or a1)"
      ANY_BAD=true
      EXPIRED_LIST="${EXPIRED_LIST}• 账号 $aid ($name): cookie 不完整\n"
      ;;
    TOO_SHORT)
      echo "  $aid ($name): ✗ cookie too short"
      ANY_BAD=true
      EXPIRED_LIST="${EXPIRED_LIST}• 账号 $aid ($name): cookie 太短\n"
      ;;
    *)
      echo "  $aid ($name): ? unknown status: $status"
      ;;
  esac
done <<< "$CHECK_OUTPUT"

if [ "$ANY_BAD" = true ]; then
  log_event "xhs-crawler" "cookie-check" "error" "Some accounts have invalid cookies"

  if [ "$DO_NOTIFY" = true ]; then
    MSG="🍪 *XHS Cookie 需要更新*\n${EXPIRED_LIST}请登录对应账号的小红书网页版 → F12 → Cookies → 复制整串 cookie，然后告诉我更新。"
    notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Crawler" ":cookie:"
    echo "Slack notification sent"
  fi

  exit 1
else
  echo "All accounts OK"
  exit 0
fi
