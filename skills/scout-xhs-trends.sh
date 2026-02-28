#!/bin/bash
# scout-xhs-trends.sh — Search for Xiaohongshu/RED topic trends and viral content
# Usage: scout-xhs-trends.sh --keyword "K-Beauty" [--since 7]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

KEYWORD="K-Beauty"
SINCE_DAYS=7

while [[ $# -gt 0 ]]; do
  case $1 in
    --keyword) KEYWORD="$2"; shift 2;;
    --since) SINCE_DAYS="$2"; shift 2;;
    --help) echo "Usage: scout-xhs-trends.sh --keyword \"K-Beauty\" [--since 7]"; exit 0;;
    *) shift;;
  esac
done

SINCE=$(date -d "$SINCE_DAYS days ago" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)

echo "=== Xiaohongshu Trends Scout Report ==="
echo "Keyword: $KEYWORD"
echo "Since: $SINCE"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

github_search() {
  local query="$1"
  local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")
  curl -s "https://api.github.com/search/repositories?q=${encoded}&sort=stars&per_page=5" 2>/dev/null
}

# 1. Xiaohongshu tools and scrapers
echo "--- Xiaohongshu Tools & APIs ---"
XHS_QUERIES=(
  "xiaohongshu"
  "小红书 api"
  "xhs scraper"
  "red note api"
)

for Q in "${XHS_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 10:
            lang = r.get('language', '?')
            updated = r.get('pushed_at', '')[:10]
            desc = (r.get('description') or 'No description')[:100]
            print(f'  [{stars}★] {r[\"full_name\"]} ({lang}, updated {updated})')
            print(f'    {desc}')
            print()
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 2. Content trend analysis tools
echo "--- Content Trend Analysis Tools ---"
TREND_QUERIES=(
  "social media trend analysis $KEYWORD"
  "content analytics $KEYWORD"
  "viral content analysis"
)

for Q in "${TREND_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 20:
            lang = r.get('language', '?')
            desc = (r.get('description') or 'No description')[:100]
            print(f'  [{stars}★] {r[\"full_name\"]} ({lang}): {desc}')
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 3. K-Beauty / beauty industry related tools
echo "--- Beauty Industry Tools ---"
BEAUTY_QUERIES=(
  "beauty product analysis"
  "cosmetics review scraper"
  "$KEYWORD trend"
)

for Q in "${BEAUTY_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 10:
            lang = r.get('language', '?')
            desc = (r.get('description') or 'No description')[:100]
            print(f'  [{stars}★] {r[\"full_name\"]} ({lang}): {desc}')
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""
echo "=== End Xiaohongshu Trends Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
