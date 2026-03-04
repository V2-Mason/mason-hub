#!/bin/bash
# scout-github.sh — Search GitHub for new AI agent / Claude related repos
# Usage: scout-github.sh [--topic "keyword"] [--since "7 days ago"]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

TOPIC="${1:-}"
SINCE_ARG="${2:-7 days ago}"

# Parse named args
while [[ $# -gt 0 ]]; do
  case $1 in
    --topic) TOPIC="$2"; shift 2;;
    --since) SINCE_ARG="$2"; shift 2;;
    --help) echo "Usage: scout-github.sh [--topic \"keyword\"] [--since \"7 days ago\"]"; exit 0;;
    *) shift;;
  esac
done

TOPIC="${TOPIC:-claude code agent}"
SINCE=$(date -d "$SINCE_ARG" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
ENCODED_TOPIC=$(echo "$TOPIC" | sed 's/ /+/g')

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"
scout_dedup_check() {
  local repo="$1" stars="$2"
  if [ -x "$DEDUP_SCRIPT" ] || [ -f "$DEDUP_SCRIPT" ]; then
    python3 "$DEDUP_SCRIPT" --check "$repo" "$stars" 2>/dev/null
    return $?
  fi
  echo "new"
  return 0
}

echo "=== GitHub Scout Report ==="
echo "Topic: $TOPIC"
echo "Since: $SINCE"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

# Search new repos
echo "### New Repositories (created since $SINCE)"
NEW_REPOS=$(curl -s "https://api.github.com/search/repositories?q=${ENCODED_TOPIC}+created:>$SINCE&sort=stars&per_page=10" 2>/dev/null)
NEW_COUNT=$(echo "$NEW_REPOS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

if [ "$NEW_COUNT" -gt 0 ]; then
  echo "$NEW_REPOS" | python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
dedup = '${DEDUP_SCRIPT}'
for item in data.get('items', [])[:10]:
    name = item['full_name']
    url = item['html_url']
    stars = item['stargazers_count']
    desc = (item.get('description') or 'No description')[:100]
    lang = item.get('language') or '?'
    created = item.get('created_at', '')[:10]
    # dedup check
    r = subprocess.run(['python3', dedup, '--check', name, str(stars)],
                       capture_output=True, text=True)
    status = r.stdout.strip()
    if status == 'known':
        continue
    tag = '🆕' if status == 'new' else '📈'
    print(f'- {tag} [{name}]({url}) ⭐{stars} [{lang}] created {created} — {desc}')
" 2>/dev/null
  HAS_RESULTS=true
else
  echo "No new repositories found."
fi

echo ""

# Search recently updated high-star repos
echo "### Recently Updated (100+ stars, pushed since $SINCE)"
UPDATED_REPOS=$(curl -s "https://api.github.com/search/repositories?q=${ENCODED_TOPIC}+stars:>100+pushed:>$SINCE&sort=updated&per_page=10" 2>/dev/null)
UPD_COUNT=$(echo "$UPDATED_REPOS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

if [ "$UPD_COUNT" -gt 0 ]; then
  echo "$UPDATED_REPOS" | python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
dedup = '${DEDUP_SCRIPT}'
for item in data.get('items', [])[:10]:
    name = item['full_name']
    url = item['html_url']
    stars = item['stargazers_count']
    pushed = item.get('pushed_at', '')[:10]
    desc = (item.get('description') or 'No description')[:100]
    r = subprocess.run(['python3', dedup, '--check', name, str(stars)],
                       capture_output=True, text=True)
    status = r.stdout.strip()
    if status == 'known':
        continue
    tag = '🆕' if status == 'new' else '📈'
    print(f'- {tag} [{name}]({url}) ⭐{stars} updated {pushed} — {desc}')
" 2>/dev/null
  HAS_RESULTS=true
else
  echo "No recently updated repositories found."
fi

echo ""
echo "Total new repos: $NEW_COUNT"
echo "=== End Report ==="

if [ "$HAS_RESULTS" = true ]; then
  exit 0
else
  exit 1
fi
