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
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('items', [])[:5]:
        stars = r.get('stargazers_count', 0)
        if stars > 100:
            print(f\"  [{stars}★] {r['full_name']}: {(r.get('description') or '')[:100]}\")
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
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get('items', [])[:2]:
        stars = r.get('stargazers_count', 0)
        if stars > 20:
            print(f\"  [{stars}★] {r['full_name']}: {(r.get('description') or '')[:100]}\")
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
import sys, json
try:
    r = json.load(sys.stdin)
    stars = r.get('stargazers_count', 0)
    pushed = r.get('pushed_at', '')[:10]
    desc = (r.get('description') or '')[:80]
    print(f\"  [{stars}★] {r['full_name']} (updated {pushed}): {desc}\")
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
