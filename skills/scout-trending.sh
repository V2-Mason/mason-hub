#!/bin/bash
# scout-trending.sh — Check GitHub trending repos and high-growth projects
# Usage: scout-trending.sh [--language python] [--min-stars 500]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

LANGUAGE=""
MIN_STARS=500

while [[ $# -gt 0 ]]; do
  case $1 in
    --language) LANGUAGE="$2"; shift 2;;
    --min-stars) MIN_STARS="$2"; shift 2;;
    --help) echo "Usage: scout-trending.sh [--language python] [--min-stars 500]"; exit 0;;
    *) shift;;
  esac
done

WEEK_AGO=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

echo "=== GitHub Trending Scout ==="
echo "Date: $(date +%Y-%m-%d)"
echo "Min stars: $MIN_STARS"
echo "Language: ${LANGUAGE:-any}"
echo ""

# AI/Agent related trending topics
TOPICS=("ai+agent" "claude+code" "mcp+server" "llm+tool" "ai+automation")

for topic in "${TOPICS[@]}"; do
  echo "### Topic: ${topic//+/ }"

  LANG_FILTER=""
  if [ -n "$LANGUAGE" ]; then
    LANG_FILTER="+language:$LANGUAGE"
  fi

  RESULT=$(curl -s "https://api.github.com/search/repositories?q=${topic}+stars:>${MIN_STARS}+pushed:>$WEEK_AGO${LANG_FILTER}&sort=stars&order=desc&per_page=5" 2>/dev/null)
  COUNT=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

  if [ "$COUNT" -gt 0 ]; then
    echo "$RESULT" | python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
dedup = '${DEDUP_SCRIPT}'
for item in data.get('items', [])[:5]:
    name = item['full_name']
    url = item['html_url']
    stars = item['stargazers_count']
    desc = (item.get('description') or 'No description')[:80]
    created = item.get('created_at', '')[:10]
    r = subprocess.run(['python3', dedup, '--check', name, str(stars)],
                       capture_output=True, text=True)
    status = r.stdout.strip()
    if status == 'known':
        continue
    tag = '🆕' if status == 'new' else '📈'
    print(f'- {tag} [{name}]({url}) ⭐{stars} created {created} — {desc}')
" 2>/dev/null
  else
    echo "  No results."
  fi
  echo ""
done

echo "=== End Trending Report ==="
exit 0
