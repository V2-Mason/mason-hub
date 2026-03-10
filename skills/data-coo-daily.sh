#!/bin/bash
# data-coo-daily.sh — Agent #0 数据COO 每日巡检
# 用法: data-coo-daily.sh [--slack <channel_id>]
#
# 调用 surenxuan 现有 API 获取库存告警 + 销售摘要，汇总发 Slack
# API 端点:
#   GET /api/intelligence/risk-alerts  (临期/低库存/滞销)
#   GET /api/sales/summary             (销售摘要)
#   GET /api/dashboard/overview        (仪表盘概览)

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SRX_API="http://106.14.44.68:8000"
TIMEOUT=15

# 加载凭证
if [ -f "$HUB_DIR/.env" ]; then
  # shellcheck disable=SC1091
  set -a; source "$HUB_DIR/.env"; set +a
fi

SLACK_CHANNEL=""
if [ "${1:-}" = "--slack" ] && [ -n "${2:-}" ]; then
  SLACK_CHANNEL="$2"
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "=== DATA COO DAILY CHECK ==="
echo "Generated: $NOW"
echo ""

REPORT=""
HAS_ALERT=false

# --- 0. Login to get JWT token ---
AUTH_HEADER=""
if [ -n "${SRX_API_EMAIL:-}" ] && [ -n "${SRX_API_PASSWORD:-}" ]; then
  LOGIN_RESP=$(timeout "$TIMEOUT" curl -s -X POST "$SRX_API/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$SRX_API_EMAIL\",\"password\":\"$SRX_API_PASSWORD\"}" 2>/dev/null || echo "ERROR")
  TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
  if [ -n "$TOKEN" ]; then
    AUTH_HEADER="Authorization: Bearer $TOKEN"
    echo "Login: OK"
  else
    echo "WARNING: Login failed, API calls may return 401"
  fi
else
  echo "WARNING: SRX_API_EMAIL/PASSWORD not set, skipping auth"
fi
echo ""

# --- 1. Risk Alerts (临期/低库存/滞销) ---
echo "--- 1. Risk Alerts ---"
RISK_RESPONSE=$(timeout "$TIMEOUT" curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$SRX_API/api/intelligence/risk-alerts" 2>/dev/null || echo "ERROR")

if [ "$RISK_RESPONSE" = "ERROR" ] || [ -z "$RISK_RESPONSE" ]; then
  echo "WARNING: Cannot reach risk-alerts API"
  REPORT="${REPORT}*Risk Alerts*: API 不可达\n"
else
  # Parse risk alerts using python
  RISK_SUMMARY=$(python3 -c "
import json, sys
try:
    data = json.loads('''$RISK_RESPONSE''')
    alerts = data if isinstance(data, list) else data.get('alerts', data.get('data', []))
    if not alerts:
        print('No alerts')
    else:
        # Group by type
        by_type = {}
        for a in (alerts if isinstance(alerts, list) else [alerts]):
            t = a.get('type', a.get('alert_type', 'unknown'))
            by_type.setdefault(t, []).append(a)
        parts = []
        for t, items in by_type.items():
            parts.append(f'{t}: {len(items)} items')
        print(', '.join(parts))
        print(f'Total: {len(alerts if isinstance(alerts, list) else [alerts])} alerts')
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null || echo "Parse error")

  echo "$RISK_SUMMARY"
  REPORT="${REPORT}*Risk Alerts*: ${RISK_SUMMARY}\n"
  if echo "$RISK_SUMMARY" | grep -qv "No alerts"; then
    HAS_ALERT=true
  fi
fi
echo ""

# --- 2. Sales Summary ---
echo "--- 2. Sales Summary ---"
SALES_RESPONSE=$(timeout "$TIMEOUT" curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$SRX_API/api/sales/summary" 2>/dev/null || echo "ERROR")

if [ "$SALES_RESPONSE" = "ERROR" ] || [ -z "$SALES_RESPONSE" ]; then
  echo "WARNING: Cannot reach sales summary API"
  REPORT="${REPORT}*Sales Summary*: API 不可达\n"
else
  SALES_SUMMARY=$(python3 -c "
import json, sys
try:
    data = json.loads('''$SALES_RESPONSE''')
    total = data.get('total_revenue', data.get('total', 'N/A'))
    count = data.get('total_orders', data.get('count', 'N/A'))
    print(f'Revenue: {total}, Orders: {count}')
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null || echo "Parse error")

  echo "$SALES_SUMMARY"
  REPORT="${REPORT}*Sales Summary*: ${SALES_SUMMARY}\n"
fi
echo ""

# --- 3. Dashboard Overview ---
echo "--- 3. Dashboard Overview ---"
DASH_RESPONSE=$(timeout "$TIMEOUT" curl -s ${AUTH_HEADER:+-H "$AUTH_HEADER"} "$SRX_API/api/dashboard/overview" 2>/dev/null || echo "ERROR")

if [ "$DASH_RESPONSE" = "ERROR" ] || [ -z "$DASH_RESPONSE" ]; then
  echo "WARNING: Cannot reach dashboard API"
  REPORT="${REPORT}*Dashboard*: API 不可达\n"
else
  DASH_SUMMARY=$(python3 -c "
import json, sys
try:
    data = json.loads('''$DASH_RESPONSE''')
    inv = data.get('total_inventory', data.get('inventory_count', 'N/A'))
    products = data.get('total_products', data.get('product_count', 'N/A'))
    print(f'Products: {products}, Inventory: {inv}')
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null || echo "Parse error")

  echo "$DASH_SUMMARY"
  REPORT="${REPORT}*Dashboard*: ${DASH_SUMMARY}\n"
fi
echo ""

# --- Send to Slack ---
if [ -n "$SLACK_CHANNEL" ] && [ -x "$SLACK_NOTIFY" ]; then
  EMOJI=":chart_with_upwards_trend:"
  if [ "$HAS_ALERT" = true ]; then
    EMOJI=":warning:"
  fi

  SLACK_MSG="📊 *数据COO 每日巡检* ($(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M'))
$(echo -e "$REPORT")"

  "$SLACK_NOTIFY" "$SLACK_CHANNEL" "$SLACK_MSG" "Data COO" "$EMOJI" 2>/dev/null || true
  echo "Slack notification sent to $SLACK_CHANNEL"
fi

echo ""
echo "=== DATA COO DAILY CHECK COMPLETE ==="
