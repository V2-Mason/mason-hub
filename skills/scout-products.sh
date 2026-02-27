#!/bin/bash
# scout-products.sh — Search for trending products, tools, and market movements
# Usage: scout-products.sh [--track "social media"] [--sources "github,hn"]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

TRACK="${1:-}"
SOURCES="${2:-all}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --track) TRACK="$2"; shift 2;;
    --sources) SOURCES="$2"; shift 2;;
    --help) echo "Usage: scout-products.sh [--track \"social media\"] [--sources \"github,hn\"]"; exit 0;;
    *) shift;;
  esac
done

TRACK="${TRACK:-social media management}"

echo "=== Product Scout Report ==="
echo "Track: $TRACK"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

# 1. GitHub — new tools in the space
echo "--- New Tools (GitHub, last 30 days) ---"
SINCE=$(date -d "30 days ago" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
SEARCH_QUERIES=(
  "social+media+management+tool"
  "social+media+scheduler"
  "content+publishing+platform"
  "geo+optimization+seo"
  "ai+content+creation+tool"
)

for Q in "${SEARCH_QUERIES[@]}"; do
  RESULTS=$(gh search repos "$Q" --sort stars --limit 3 --json name,owner,description,stargazersCount,createdAt 2>/dev/null)
  if [[ -n "$RESULTS" && "$RESULTS" != "[]" ]]; then
    echo "$RESULTS" | python3 -c "
import sys, json
repos = json.load(sys.stdin)
for r in repos:
    stars = r.get('stargazersCount', 0)
    if stars > 20:
        print(f\"  [{stars}★] {r['owner']['login']}/{r['name']}: {r.get('description','')[:100]}\")
" 2>/dev/null && HAS_RESULTS=true
  fi
done

echo ""

# 2. Search for GEO / AI SEO related tools
echo "--- GEO & AI SEO Tools ---"
GEO_QUERIES=(
  "generative+engine+optimization"
  "ai+seo+tool"
  "llm+citation+tracking"
  "ai+search+optimization"
)

for Q in "${GEO_QUERIES[@]}"; do
  RESULTS=$(gh search repos "$Q" --sort stars --limit 3 --json name,owner,description,stargazersCount 2>/dev/null)
  if [[ -n "$RESULTS" && "$RESULTS" != "[]" ]]; then
    echo "$RESULTS" | python3 -c "
import sys, json
repos = json.load(sys.stdin)
for r in repos:
    stars = r.get('stargazersCount', 0)
    if stars > 10:
        print(f\"  [{stars}★] {r['owner']['login']}/{r['name']}: {r.get('description','')[:100]}\")
" 2>/dev/null && HAS_RESULTS=true
  fi
done

echo ""

# 3. Competitor landscape — major players
echo "--- Competitor Landscape ---"
COMPETITORS=(
  "buffer/buffer:Buffer"
  "publer/publer:Publer"
  "typefully/typefully:Typefully"
)

for ENTRY in "${COMPETITORS[@]}"; do
  REPO="${ENTRY%%:*}"
  NAME="${ENTRY##*:}"
  STARS=$(gh repo view "$REPO" --json stargazersCount -q '.stargazersCount' 2>/dev/null)
  if [[ -n "$STARS" ]]; then
    echo "  $NAME: ${STARS}★"
    HAS_RESULTS=true
  fi
done

echo ""
echo "=== End Product Scout Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
