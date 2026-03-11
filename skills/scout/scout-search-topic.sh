#!/bin/bash
# scout-search-topic.sh — Search GitHub for a specific topic/keyword
# Usage: scout-search-topic.sh --query "keyword" [--min-stars 50] [--since "30 days ago"]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

QUERY=""
MIN_STARS=50
SINCE_ARG="30 days ago"

while [[ $# -gt 0 ]]; do
  case $1 in
    --query) QUERY="$2"; shift 2;;
    --min-stars) MIN_STARS="$2"; shift 2;;
    --since) SINCE_ARG="$2"; shift 2;;
    --help) echo "Usage: scout-search-topic.sh --query \"keyword\" [--min-stars 50] [--since \"30 days ago\"]"; exit 0;;
    *) shift;;
  esac
done

if [ -z "$QUERY" ]; then
  echo "ERROR: --query is required"
  echo "Usage: scout-search-topic.sh --query \"keyword\""
  exit 2
fi

SINCE=$(date -d "$SINCE_ARG" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
ENCODED_QUERY=$(echo "$QUERY" | sed 's/ /+/g')

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

echo "=== Topic Search Report ==="
echo "Query: $QUERY"
echo "Since: $SINCE"
echo "Min stars: $MIN_STARS"
echo "Date: $(date +%Y-%m-%d)"
echo ""

# Search repos
echo "### Repositories"
REPOS=$(curl -s "https://api.github.com/search/repositories?q=${ENCODED_QUERY}+stars:>${MIN_STARS}+pushed:>$SINCE&sort=stars&per_page=15" 2>/dev/null)
REPO_COUNT=$(echo "$REPOS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

if [ "$REPO_COUNT" -gt 0 ]; then
  echo "Found $REPO_COUNT repos (showing top 15):"
  echo ""
  echo "$REPOS" | python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
dedup = '${DEDUP_SCRIPT}'
for item in data.get('items', [])[:15]:
    name = item['full_name']
    url = item['html_url']
    stars = item['stargazers_count']
    lang = item.get('language') or '?'
    created = item.get('created_at', '')[:10]
    pushed = item.get('pushed_at', '')[:10]
    desc = (item.get('description') or 'No description')[:120]
    r = subprocess.run(['python3', dedup, '--check', name, str(stars)],
                       capture_output=True, text=True)
    status = r.stdout.strip()
    if status == 'known':
        continue
    tag = '🆕' if status == 'new' else '📈'
    print(f'- {tag} [{name}]({url})')
    print(f'  ⭐{stars} [{lang}] created {created} updated {pushed}')
    print(f'  {desc}')
    print()
" 2>/dev/null
  exit 0
else
  echo "No repositories found matching \"$QUERY\" with $MIN_STARS+ stars since $SINCE."
  exit 1
fi
