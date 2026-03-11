#!/bin/bash
# run-smoke-tests.sh — Endpoint smoke tests against production
# Usage: run-smoke-tests.sh [--target <base_url>]
# Exit: 0=all pass, 1=some fail, 2=infrastructure error
set -uo pipefail

# Default target: Aliyun production
TARGET="http://106.14.44.68:8000"
REQ_TIMEOUT=10
OVERALL_TIMEOUT=60

while [[ $# -gt 0 ]]; do
  case $1 in
    --target) TARGET="$2"; shift 2;;
    --help) echo "Usage: run-smoke-tests.sh [--target <base_url>]"; exit 0;;
    *) shift;;
  esac
done

# Endpoints to check (GET only, expect 200 or 401)
# 401 means the endpoint exists and auth is required (still healthy)
# 404 means the endpoint is missing (broken deployment)
# 502/503 means the service is down
ENDPOINTS=(
  "/api/dashboard/overview"
  "/api/inventory"
  "/api/sales?page_size=1"
  "/api/customers?page_size=1"
  "/api/products?page_size=1"
  "/api/selection/batches?page_size=1"
  "/api/purchases?page_size=1"
  "/api/settings"
  "/api/intelligence/replenishment"
  "/api/notifications?page_size=1"
)

echo "=== SMOKE TESTS ==="
echo "Target: $TARGET"
echo "Endpoints: ${#ENDPOINTS[@]}"
echo "---"

PASS=0
FAIL=0
ERRORS=""

for ep in "${ENDPOINTS[@]}"; do
  HTTP_CODE=$(timeout "$REQ_TIMEOUT" curl -s -o /dev/null -w "%{http_code}" "${TARGET}${ep}" 2>/dev/null || echo "000")

  if [[ "$HTTP_CODE" == "000" ]]; then
    FAIL=$((FAIL + 1))
    ERRORS="${ERRORS}FAIL: ${ep} — connection failed/timeout\n"
  elif [[ "$HTTP_CODE" == "404" ]]; then
    FAIL=$((FAIL + 1))
    ERRORS="${ERRORS}FAIL: ${ep} — 404 (endpoint missing)\n"
  elif [[ "$HTTP_CODE" == "502" ]] || [[ "$HTTP_CODE" == "503" ]]; then
    FAIL=$((FAIL + 1))
    ERRORS="${ERRORS}FAIL: ${ep} — ${HTTP_CODE} (service down)\n"
  else
    PASS=$((PASS + 1))
    echo "OK: ${ep} — ${HTTP_CODE}"
  fi
done

echo "---"
echo "=== SUMMARY ==="
echo "Passed: $PASS / ${#ENDPOINTS[@]}"
echo "Failed: $FAIL"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "--- Failures ---"
  echo -e "$ERRORS"
  exit 1
fi

echo "All endpoints healthy"
exit 0
