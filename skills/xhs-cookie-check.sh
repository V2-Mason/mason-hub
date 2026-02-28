#!/bin/bash
# xhs-cookie-check.sh — XHS Cookie 有效性检测
# 用法: xhs-cookie-check.sh [--notify]
#   --notify  过期时发 Slack 通知 Mason 更换 cookie
# Exit code: 0=有效, 1=过期/无效

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
SLACK_CHANNEL_SOCIALMESH="C0AHTA97EAY"
DO_NOTIFY=false

if [ "${1:-}" = "--notify" ]; then
  DO_NOTIFY=true
fi

echo "=== XHS Cookie Check ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

# SSH 到阿里云，用 cookie 请求 XHS 主站检测有效性
# 注意：创作者中心和主站 session 分开，MediaCrawler 用主站 cookie，所以检测主站
RESULT=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$ALIYUN" bash -s << 'REMOTE_EOF'
# 直接从 base_config.py 用 grep 提取 cookie（不依赖 venv python）
COOKIE=$(grep -oP "^COOKIES\s*=\s*['\"](.+)['\"]" /opt/mediacrawler/config/base_config.py | sed "s/^COOKIES\s*=\s*['\"]//;s/['\"]$//")

if [ -z "$COOKIE" ]; then
  echo "NO_COOKIE"
  exit 1
fi

# 检测方式：请求用户主页，检查返回 HTML 是否包含登录态标志
# web_session 有效时页面包含用户昵称等数据；过期时会跳转登录页
RESP=$(curl -s \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Cookie: $COOKIE" \
  --connect-timeout 10 \
  --max-time 15 \
  "https://www.xiaohongshu.com/user/profile/5d42d8820000000012030bd6" 2>/dev/null)

HTTP_LEN=${#RESP}

# 有效 cookie: 返回完整页面 (>5000 字符，包含用户数据)
# 过期 cookie: 返回短页面或跳转登录 (<2000 字符)
if [ "$HTTP_LEN" -gt 5000 ]; then
  # 二次确认：页面是否包含用户ID或个人资料标志
  if echo "$RESP" | grep -q 'user-id\|userPageData\|"nickname"'; then
    echo "VALID"
  else
    echo "EXPIRED"
  fi
elif [ "$HTTP_LEN" -gt 0 ]; then
  echo "EXPIRED"
else
  echo "NETWORK_ERROR"
fi
REMOTE_EOF
)

SSH_EXIT=$?

if [ $SSH_EXIT -ne 0 ]; then
  echo "ERROR: SSH connection failed (exit $SSH_EXIT)"
  exit 1
fi

echo "Cookie status: $RESULT"

if [ "$RESULT" = "VALID" ]; then
  echo "Cookie is valid"
  log_event "xhs-crawler" "cookie-check" "info" "XHS cookie valid"
  exit 0
else
  echo "Cookie expired or invalid"
  log_event "xhs-crawler" "cookie-check" "error" "XHS cookie status: $RESULT"

  if [ "$DO_NOTIFY" = true ]; then
    MSG="🍪 *XHS Cookie 已过期*
采集脚本检测到 cookie 失效 (HTTP $RESULT)。
请在电脑浏览器登录 web.xiaohongshu.com → F12 → Application → Cookies → 复制整串 cookie。
然后更新阿里云 /opt/mediacrawler/config/base_config.py 中的 COOKIES 值。
手机 APP 正常使用不影响。"
    notify_slack "$SLACK_CHANNEL_SOCIALMESH" "$MSG" "XHS Crawler" ":cookie:"
    echo "Slack notification sent"
  fi

  exit 1
fi
