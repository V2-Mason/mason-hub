#!/bin/bash
# scout-ecom-compete.sh — Search for e-commerce competitor intelligence tools
# Usage: scout-ecom-compete.sh --keyword "COSRX" [--market "cross-border"]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

KEYWORD="COSRX"
MARKET="cross-border"

while [[ $# -gt 0 ]]; do
  case $1 in
    --keyword) KEYWORD="$2"; shift 2;;
    --market) MARKET="$2"; shift 2;;
    --help) echo "Usage: scout-ecom-compete.sh --keyword \"COSRX\" [--market \"cross-border\"]"; exit 0;;
    *) shift;;
  esac
done

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

REPORT_DATE=$(date +%Y-%m-%d)

echo "=== E-Commerce Competitor Scout Report ==="
echo "Keyword: $KEYWORD"
echo "Market: $MARKET"
echo "Date: $REPORT_DATE"
echo ""

HAS_RESULTS=false

github_search() {
  local query="$1"
  local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")
  curl -s "https://api.github.com/search/repositories?q=${encoded}&sort=stars&per_page=5" 2>/dev/null
}

# 1. Price monitoring & comparison tools
echo "--- Price Monitoring Tools ---"
PRICE_QUERIES=(
  "price monitor ecommerce"
  "price tracker scraper"
  "price comparison tool"
)

for Q in "${PRICE_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 20:
            name = r['full_name']; url = r['html_url']; lang = r.get('language', '?')
            created = r.get('created_at', '')[:10]; updated = r.get('pushed_at', '')[:10]
            desc = (r.get('description') or 'No description')[:100]
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            print(f'  {tag} [{name}]({url}) [{stars}★] ({lang}) created {created} updated {updated}')
            print(f'    {desc}')
            print()
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 2. Cross-border e-commerce tools
echo "--- Cross-Border E-Commerce Tools ---"
XBORDER_QUERIES=(
  "cross border ecommerce tool"
  "跨境电商"
  "ecommerce $MARKET scraper"
)

for Q in "${XBORDER_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 10:
            name = r['full_name']; url = r['html_url']; lang = r.get('language', '?')
            created = r.get('created_at', '')[:10]
            desc = (r.get('description') or 'No description')[:100]
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            print(f'  {tag} [{name}]({url}) [{stars}★] ({lang}) created {created}: {desc}')
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 3. Product research & trend tools
echo "--- Product Research & Trend Tools ---"
PRODUCT_QUERIES=(
  "product research ecommerce"
  "ecommerce analytics"
  "beauty cosmetics $KEYWORD"
)

for Q in "${PRODUCT_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 10:
            name = r['full_name']; url = r['html_url']; lang = r.get('language', '?')
            created = r.get('created_at', '')[:10]
            desc = (r.get('description') or 'No description')[:100]
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            print(f'  {tag} [{name}]({url}) [{stars}★] ({lang}) created {created}: {desc}')
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 4. E-commerce platform scrapers
echo "--- E-Commerce Platform Scrapers ---"
PLATFORM_QUERIES=(
  "taobao scraper"
  "shopee scraper"
  "amazon product scraper"
)

for Q in "${PLATFORM_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 50:
            name = r['full_name']; url = r['html_url']; lang = r.get('language', '?')
            created = r.get('created_at', '')[:10]; updated = r.get('pushed_at', '')[:10]
            desc = (r.get('description') or 'No description')[:100]
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            print(f'  {tag} [{name}]({url}) [{stars}★] ({lang}) created {created} updated {updated}')
            print(f'    {desc}')
            print()
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""
echo "=== End E-Commerce Competitor Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
