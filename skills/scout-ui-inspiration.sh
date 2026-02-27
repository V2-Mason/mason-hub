#!/bin/bash
# scout-ui-inspiration.sh — Search for UI/UX design inspiration and trends
# Usage: scout-ui-inspiration.sh [--category "dashboard"] [--competitors]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

CATEGORY="${1:-}"
COMPETITORS=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --category) CATEGORY="$2"; shift 2;;
    --competitors) COMPETITORS=true; shift;;
    --help) echo "Usage: scout-ui-inspiration.sh [--category \"dashboard\"] [--competitors]"; exit 0;;
    *) shift;;
  esac
done

CATEGORY="${CATEGORY:-social media management}"

echo "=== UI/UX Scout Report ==="
echo "Category: $CATEGORY"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

# 1. Search GitHub for trending UI component libraries and templates
echo "--- Trending UI Libraries & Templates ---"
QUERIES=(
  "social+media+dashboard+react+tailwind"
  "saas+dashboard+template+react"
  "content+management+ui+react"
)

for Q in "${QUERIES[@]}"; do
  RESULTS=$(gh search repos "$Q" --sort stars --limit 5 --json name,owner,description,stargazersCount,updatedAt 2>/dev/null)
  if [[ -n "$RESULTS" && "$RESULTS" != "[]" ]]; then
    echo "$RESULTS" | python3 -c "
import sys, json
repos = json.load(sys.stdin)
for r in repos:
    stars = r.get('stargazersCount', 0)
    if stars > 50:
        print(f\"  [{stars}★] {r['owner']['login']}/{r['name']}: {r.get('description','')[:100]}\")
" 2>/dev/null && HAS_RESULTS=true
  fi
done

echo ""

# 2. Search for competitor UI patterns
if [[ "$COMPETITORS" == true ]]; then
  echo "--- Competitor UI Analysis ---"
  COMPETITORS_LIST=(
    "buffer" "hootsuite" "later" "typefully"
    "publer" "socialchamp" "contentstudio"
  )
  for COMP in "${COMPETITORS_LIST[@]}"; do
    echo "  Competitor: $COMP"
    gh search repos "$COMP social media" --sort stars --limit 2 --json name,owner,stargazersCount,description 2>/dev/null | python3 -c "
import sys, json
repos = json.load(sys.stdin)
for r in repos:
    print(f\"    [{r.get('stargazersCount',0)}★] {r['owner']['login']}/{r['name']}: {r.get('description','')[:80]}\")
" 2>/dev/null
  done
  HAS_RESULTS=true
  echo ""
fi

# 3. Search for design system / component library updates
echo "--- Design System Updates ---"
DESIGN_REPOS=(
  "shadcn-ui/ui"
  "radix-ui/primitives"
  "tailwindlabs/headlessui"
  "tremor-so/tremor"
  "nextui-org/nextui"
)

for REPO in "${DESIGN_REPOS[@]}"; do
  LATEST=$(gh release list --repo "$REPO" --limit 1 --json tagName,publishedAt,name 2>/dev/null)
  if [[ -n "$LATEST" && "$LATEST" != "[]" ]]; then
    echo "$LATEST" | python3 -c "
import sys, json
releases = json.load(sys.stdin)
if releases:
    r = releases[0]
    print(f\"  {sys.argv[1]}: {r.get('tagName','')} ({r.get('publishedAt','')[:10]}) — {r.get('name','')[:60]}\")
" "$REPO" 2>/dev/null && HAS_RESULTS=true
  fi
done

echo ""
echo "=== End UI/UX Scout Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
