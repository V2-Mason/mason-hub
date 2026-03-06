#!/bin/bash
# scout-anthropic.sh — Check Anthropic/Claude ecosystem updates
# Usage: scout-anthropic.sh
# Exit: 0=results found, 1=no new updates, 2=error
set -uo pipefail

WEEK_AGO=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

echo "=== Anthropic / Claude Ecosystem Scout ==="
echo "Date: $(date +%Y-%m-%d)"
echo "Checking since: $WEEK_AGO"
echo ""

# 1. Check anthropic org repos for updates
echo "### Anthropic Official Repos (pushed since $WEEK_AGO)"
ANTHROPIC_REPOS=$(curl -s "https://api.github.com/search/repositories?q=org:anthropics+pushed:>$WEEK_AGO&sort=updated&per_page=10" 2>/dev/null)
A_COUNT=$(echo "$ANTHROPIC_REPOS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

if [ "$A_COUNT" -gt 0 ]; then
  echo "$ANTHROPIC_REPOS" | python3 -c "
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
else
  echo "  No updates since $WEEK_AGO."
fi
echo ""

# 2. Check claude-code related repos
echo "### Claude Code Ecosystem (new/updated)"
CC_REPOS=$(curl -s "https://api.github.com/search/repositories?q=claude-code+pushed:>$WEEK_AGO&sort=updated&per_page=10" 2>/dev/null)
CC_COUNT=$(echo "$CC_REPOS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

if [ "$CC_COUNT" -gt 0 ]; then
  echo "$CC_REPOS" | python3 -c "
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
else
  echo "  No updates since $WEEK_AGO."
fi
echo ""

# 3. Check MCP server repos
echo "### MCP Server Ecosystem (new/updated)"
MCP_REPOS=$(curl -s "https://api.github.com/search/repositories?q=mcp+server+pushed:>$WEEK_AGO+stars:>10&sort=stars&per_page=10" 2>/dev/null)
MCP_COUNT=$(echo "$MCP_REPOS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null || echo "0")

if [ "$MCP_COUNT" -gt 0 ]; then
  echo "$MCP_REPOS" | python3 -c "
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
else
  echo "  No updates since $WEEK_AGO."
fi

echo ""
echo "=== End Anthropic Ecosystem Report ==="
exit 0
