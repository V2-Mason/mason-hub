#!/bin/bash
# scout-ui-inspiration.sh — Search for UI/UX design inspiration and trends
# Usage: scout-ui-inspiration.sh [--category "dashboard"] [--competitors]
# Uses GitHub REST API (no auth needed for basic search)
set -uo pipefail

CATEGORY="social media management"
COMPETITORS=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --category) CATEGORY="$2"; shift 2;;
    --competitors) COMPETITORS=true; shift;;
    --help) echo "Usage: scout-ui-inspiration.sh [--category \"dashboard\"] [--competitors]"; exit 0;;
    *) shift;;
  esac
done

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

echo "=== UI/UX Scout Report ==="
echo "Category: $CATEGORY"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

github_search() {
  local query="$1"
  local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")
  curl -s "https://api.github.com/search/repositories?q=${encoded}&sort=stars&per_page=5" 2>/dev/null
}

# 1. Trending UI Libraries & Templates
echo "--- Trending UI Libraries & Templates ---"
QUERIES=(
  "social media dashboard react tailwind"
  "saas dashboard template react"
  "admin dashboard react tailwind"
  "content management ui react"
)

for Q in "${QUERIES[@]}"; do
  RESULT=$(github_search "$Q")
  if [[ -n "$RESULT" ]]; then
    echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:5]:
        stars = r.get('stargazers_count', 0)
        if stars > 100:
            name = r['full_name']
            url = r['html_url']
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            created = r.get('created_at', '')[:10]
            print(f\"  {tag} [{name}]({url}) [{stars}★] created {created}: {(r.get('description') or '')[:100]}\")
except: pass
" 2>/dev/null && HAS_RESULTS=true
  fi
  sleep 2  # Rate limit courtesy
done

echo ""

# 2. Competitor UI patterns
if [[ "$COMPETITORS" == true ]]; then
  echo "--- Competitor Open-Source Projects ---"
  COMPETITORS_LIST=(
    "buffer social media"
    "hootsuite open source"
    "typefully twitter thread"
    "postiz social media scheduler"
    "mixpost social media management"
  )
  for COMP in "${COMPETITORS_LIST[@]}"; do
    RESULT=$(github_search "$COMP")
    echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    for r in data.get('items', [])[:2]:
        stars = r.get('stargazers_count', 0)
        if stars > 20:
            name = r['full_name']
            url = r['html_url']
            res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
            status = res.stdout.strip()
            if status == 'known': continue
            tag = '🆕' if status == 'new' else '📈'
            created = r.get('created_at', '')[:10]
            print(f\"  {tag} [{name}]({url}) [{stars}★] created {created}: {(r.get('description') or '')[:100]}\")
except: pass
" 2>/dev/null && HAS_RESULTS=true
    sleep 2
  done
  echo ""
fi

# 3. Design system / component library stats
echo "--- Design System Stats ---"
DESIGN_REPOS=(
  "shadcn-ui/ui"
  "radix-ui/primitives"
  "tailwindlabs/headlessui"
  "tremor-so/tremor"
  "nextui-org/nextui"
  "saadeghi/daisyui"
)

for REPO in "${DESIGN_REPOS[@]}"; do
  RESULT=$(curl -s "https://api.github.com/repos/$REPO" 2>/dev/null)
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    r = json.load(sys.stdin)
    stars = r.get('stargazers_count', 0)
    pushed = r.get('pushed_at', '')[:10]
    desc = (r.get('description') or '')[:80]
    name = r['full_name']
    url = r.get('html_url', '')
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
echo "=== End UI/UX Scout Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
