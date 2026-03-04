#!/bin/bash
# scout-products.sh — Search for trending products, tools, and market movements
# Usage: scout-products.sh [--track "social media"] [--since "30"]
# Uses GitHub REST API (no auth needed for basic search)
set -uo pipefail

TRACK="social media management"
SINCE_DAYS=30

while [[ $# -gt 0 ]]; do
  case $1 in
    --track) TRACK="$2"; shift 2;;
    --since) SINCE_DAYS="$2"; shift 2;;
    --help) echo "Usage: scout-products.sh [--track \"social media\"] [--since 30]"; exit 0;;
    *) shift;;
  esac
done

SINCE=$(date -d "$SINCE_DAYS days ago" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

echo "=== Product Scout Report ==="
echo "Track: $TRACK"
echo "Since: $SINCE"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

github_search() {
  local query="$1"
  local extra="${2:-}"
  local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query $extra'))")
  curl -s "https://api.github.com/search/repositories?q=${encoded}&sort=stars&per_page=5" 2>/dev/null
}

# 1. New & trending tools in the space
echo "--- Social Media Management Tools ---"
QUERIES=(
  "social media management tool"
  "social media scheduler open source"
  "content publishing platform"
  "multi platform posting"
)

for Q in "${QUERIES[@]}"; do
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
            created = r.get('created_at', '')[:10]
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            print(f\"  {tag} [{name}]({url}) [{stars}★] ({lang}) created {created}: {(r.get('description') or '')[:100]}\")
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 2. GEO / AI SEO tools
echo "--- GEO & AI SEO Tools ---"
GEO_QUERIES=(
  "generative engine optimization"
  "ai seo tool"
  "llm search optimization"
  "ai content optimization"
)

for Q in "${GEO_QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:3]:
        stars = r.get('stargazers_count', 0)
        if stars > 20:
            name = r['full_name']; url = r['html_url']
            created = r.get('created_at', '')[:10]
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            print(f\"  {tag} [{name}]({url}) [{stars}★] created {created}: {(r.get('description') or '')[:100]}\")
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 2
done

echo ""

# 3. Key competitors — direct stats
echo "--- Key Competitor Repos ---"
COMP_REPOS=(
  "inovector/mixpost"
  "postiz-app/postiz"
  "typefully/typefully"
  "giso-official/giso"
)

for REPO in "${COMP_REPOS[@]}"; do
  RESULT=$(curl -s "https://api.github.com/repos/$REPO" 2>/dev/null)
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    r = json.load(sys.stdin)
    if 'stargazers_count' in r:
        stars = r['stargazers_count']
        pushed = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or '')[:80]
        name = r['full_name']; url = r.get('html_url', '')
        dedup = '${DEDUP_SCRIPT}'
        res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
        status = res.stdout.strip()
        if status != 'known':
            tag = '🆕' if status == 'new' else '📈'
            print(f\"  {tag} [{name}]({url}) [{stars}★] updated {pushed}: {desc}\")
except: pass
" 2>/dev/null && HAS_RESULTS=true
  sleep 1
done

echo ""
echo "=== End Product Scout Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
