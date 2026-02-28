#!/bin/bash
# Cookie 过期提醒 — 每周随机一天提醒 Mason 更换 XHS cookie
# cron: 每天 10:00 CST 运行，脚本内部控制每周只发一次

LOCK_FILE="/tmp/.cookie_reminder_week"
CURRENT_WEEK=$(date +%Y-%W)
DAY_OF_WEEK=$(date +%u)  # 1=周一, 7=周日

# 如果本周已经提醒过，跳过
if [ -f "$LOCK_FILE" ] && [ "$(cat $LOCK_FILE)" = "$CURRENT_WEEK" ]; then
    exit 0
fi

# 剩余天数（含今天）：8 - 当前星期几
REMAINING=$((8 - DAY_OF_WEEK))

# 1/剩余天数 的概率触发（周日 100% 兜底）
ROLL=$((RANDOM % REMAINING))
if [ "$ROLL" -ne 0 ]; then
    exit 0
fi

# 发 Slack 提醒
WEBHOOK_URL="${SLACK_WEBHOOK_URL}"
if [ -z "$WEBHOOK_URL" ]; then
    echo "ERROR: SLACK_WEBHOOK_URL not set"
    exit 1
fi

curl -s -X POST "$WEBHOOK_URL" \
    -H 'Content-type: application/json' \
    -d '{
        "text": "🍪 *Cookie 更换提醒*\nXHS 采集 cookie 可能快过期了。\n请在电脑浏览器登录 web.xiaohongshu.com → F12 → Application → Cookies → 复制整串 cookie 发给我。\n手机 APP 正常用不影响。"
    }'

# 标记本周已提醒
echo "$CURRENT_WEEK" > "$LOCK_FILE"
echo "Cookie reminder sent for week $CURRENT_WEEK"
