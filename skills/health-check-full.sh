#!/bin/bash
# health-check-full.sh — System + application health check
# Usage: health-check-full.sh
# Exit: 0=healthy, 1=warnings, 2=critical
set -uo pipefail

WARN=0
CRIT=0

echo "=== HEALTH CHECK ==="
echo "Host: $(hostname)"
echo "Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# --- Disk ---
echo "--- Disk Usage ---"
DISK_PCT=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
echo "Root partition: ${DISK_PCT}%"
if [ "$DISK_PCT" -ge 90 ]; then
  echo "CRITICAL: Disk usage >= 90%"
  CRIT=$((CRIT + 1))
elif [ "$DISK_PCT" -ge 80 ]; then
  echo "WARNING: Disk usage >= 80%"
  WARN=$((WARN + 1))
else
  echo "OK"
fi
echo ""

# --- Memory ---
echo "--- Memory Usage ---"
MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
MEM_USED=$(free -m | awk 'NR==2{print $3}')
MEM_PCT=$((MEM_USED * 100 / MEM_TOTAL))
echo "Used: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PCT}%)"
if [ "$MEM_PCT" -ge 90 ]; then
  echo "CRITICAL: Memory usage >= 90%"
  CRIT=$((CRIT + 1))
elif [ "$MEM_PCT" -ge 80 ]; then
  echo "WARNING: Memory usage >= 80%"
  WARN=$((WARN + 1))
else
  echo "OK"
fi
echo ""

# --- Key Processes ---
echo "--- Key Processes ---"
for proc in "python" "node"; do
  COUNT=$(pgrep -c "$proc" 2>/dev/null || echo "0")
  COUNT=$(echo "$COUNT" | head -1 | tr -d '[:space:]')
  echo "$proc: $COUNT processes"
done
echo ""

# --- Slack Bot Service ---
echo "--- Slack Bot Service ---"
if systemctl is-active --quiet slack-bot 2>/dev/null; then
  echo "slack-bot: active"
else
  STATUS=$(systemctl is-active slack-bot 2>/dev/null || echo "not found")
  echo "slack-bot: $STATUS"
  WARN=$((WARN + 1))
fi
echo ""

# --- Aliyun API Reachability ---
echo "--- Aliyun Production API ---"
HTTP_CODE=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" "http://106.14.44.68:8000/api/dashboard/overview" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "000" ]]; then
  echo "CRITICAL: Cannot reach Aliyun API"
  CRIT=$((CRIT + 1))
elif [[ "$HTTP_CODE" == "502" ]] || [[ "$HTTP_CODE" == "503" ]]; then
  echo "CRITICAL: Aliyun API returning $HTTP_CODE"
  CRIT=$((CRIT + 1))
else
  echo "OK: Aliyun API reachable (HTTP $HTTP_CODE)"
fi
echo ""

# --- Recent Errors in Logs ---
echo "--- Recent Errors (last 30 min) ---"
ERROR_COUNT=$(journalctl -u slack-bot --since "30 min ago" --no-pager 2>/dev/null | grep -ci "error" || true)
ERROR_COUNT=${ERROR_COUNT:-0}
ERROR_COUNT=$(echo "$ERROR_COUNT" | tr -d '[:space:]')
echo "Errors in slack-bot log: $ERROR_COUNT"
if [ "$ERROR_COUNT" -gt 10 ] 2>/dev/null; then
  echo "WARNING: High error count"
  WARN=$((WARN + 1))
fi
echo ""

# --- Summary ---
echo "=== SUMMARY ==="
echo "Warnings: $WARN"
echo "Critical: $CRIT"

if [ $CRIT -gt 0 ]; then
  echo "STATUS: CRITICAL"
  exit 2
elif [ $WARN -gt 0 ]; then
  echo "STATUS: WARNING"
  exit 1
fi
echo "STATUS: HEALTHY"
exit 0
