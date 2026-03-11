#!/bin/bash
# marketing-daily.sh — Agent #2 营销引擎 每日客户数据采集
# 用法: marketing-daily.sh [--slack <channel_id>]
#
# 调用 surenxuan 现有 API 获取客户列表，按跟进策略分组输出
# API 端点:
#   GET /api/customers  (客户列表，含最后购买日期)
#
# NOTE: 现有 crontab 已有"每日客户跟进" cron (0 2 * * *)，
#       通过 run-agent.sh 调用 EMP_0001 生成跟进话术。
#       本脚本提供数据采集层，可被 cron prompt 引用或独立运行。

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SRX_API="http://106.14.44.68:8000"
TIMEOUT=15

SLACK_CHANNEL=""
if [ "${1:-}" = "--slack" ] && [ -n "${2:-}" ]; then
  SLACK_CHANNEL="$2"
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "=== MARKETING DAILY CUSTOMER DATA ==="
echo "Generated: $NOW"
echo ""

# --- 1. Fetch customers ---
echo "--- 1. Customer List ---"
CUST_RESPONSE=$(timeout "$TIMEOUT" curl -s "$SRX_API/api/customers" 2>/dev/null || echo "ERROR")

if [ "$CUST_RESPONSE" = "ERROR" ] || [ -z "$CUST_RESPONSE" ]; then
  echo "WARNING: Cannot reach customers API"
  echo ""
  echo "=== MARKETING DAILY DATA INCOMPLETE ==="
  exit 1
fi

# --- 2. Segment customers ---
echo "--- 2. Customer Segmentation ---"
SEGMENT_RESULT=$(python3 -c "
import json, sys
from datetime import datetime, timedelta

try:
    data = json.loads('''$CUST_RESPONSE''')
    customers = data if isinstance(data, list) else data.get('customers', data.get('data', []))
    now = datetime.now()

    # Segmentation
    aftercare = []     # purchased within 3 days
    wakeup = []        # active but 7+ days no purchase
    total = len(customers)

    for c in customers:
        name = c.get('name', c.get('customer_name', 'Unknown'))
        last_buy = c.get('last_purchase_date', c.get('last_buy', ''))
        if not last_buy:
            continue
        try:
            last_dt = datetime.fromisoformat(last_buy.replace('Z', '+00:00').replace('+00:00', ''))
        except:
            try:
                last_dt = datetime.strptime(last_buy[:10], '%Y-%m-%d')
            except:
                continue

        days_ago = (now - last_dt).days
        if days_ago <= 3:
            aftercare.append({'name': name, 'days': days_ago})
        elif days_ago >= 7 and days_ago <= 30:
            wakeup.append({'name': name, 'days': days_ago})

    print(f'Total customers: {total}')
    print(f'Aftercare (<=3d): {len(aftercare)}')
    for c in aftercare[:5]:
        print(f'  - {c[\"name\"]} ({c[\"days\"]}d ago)')
    print(f'Wakeup (7-30d): {len(wakeup)}')
    for c in wakeup[:5]:
        print(f'  - {c[\"name\"]} ({c[\"days\"]}d ago)')
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null || echo "Parse error")

echo "$SEGMENT_RESULT"
echo ""

# --- Send to Slack ---
if [ -n "$SLACK_CHANNEL" ] && [ -x "$SLACK_NOTIFY" ]; then
  SLACK_MSG="💄 *营销引擎 每日客户数据* ($(TZ='America/New_York' date '+%Y-%m-%d %H:%M ET'))
${SEGMENT_RESULT}"

  "$SLACK_NOTIFY" "$SLACK_CHANNEL" "$SLACK_MSG" "Marketing Engine" ":lipstick:" 2>/dev/null || true
  echo "Slack notification sent to $SLACK_CHANNEL"
fi

echo ""
echo "=== MARKETING DAILY DATA COMPLETE ==="
