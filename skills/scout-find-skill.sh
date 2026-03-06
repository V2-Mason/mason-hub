#!/bin/bash
# scout-find-skill.sh — Search for tools, libraries, and MCP servers
# Usage: scout-find-skill.sh --query "image generator" [--domain "content"] [--sources "github,mcp,npm"]
# Exit: 0=results found, 1=no results, 2=error
set -uo pipefail

QUERY=""
DOMAIN=""
SOURCES="github,npm,pypi"

while [[ $# -gt 0 ]]; do
  case $1 in
    --query) QUERY="$2"; shift 2;;
    --domain) DOMAIN="$2"; shift 2;;
    --sources) SOURCES="$2"; shift 2;;
    --help) echo "Usage: scout-find-skill.sh --query \"keyword\" [--domain \"tech|content|ecom\"] [--sources \"github,npm,pypi\"]"; exit 0;;
    *) shift;;
  esac
done

if [[ -z "$QUERY" ]]; then
  echo "Error: --query is required"
  echo "Usage: scout-find-skill.sh --query \"keyword\" [--domain \"tech|content|ecom\"] [--sources \"github,npm,pypi\"]"
  exit 2
fi

# --- Dedup helper ---
DEDUP_SCRIPT="$(dirname "$0")/../scripts/scout-dedup.py"

echo "=== Find-Skill Scout Report ==="
echo "Query: $QUERY"
echo "Domain: ${DOMAIN:-all}"
echo "Sources: $SOURCES"
echo "Date: $(date +%Y-%m-%d)"
echo ""

HAS_RESULTS=false

github_search() {
  local query="$1"
  local encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")
  curl -s "https://api.github.com/search/repositories?q=${encoded}&sort=stars&per_page=10" 2>/dev/null
}

# --- GitHub Repos ---
if echo "$SOURCES" | grep -q "github"; then
  echo "--- GitHub Repositories ---"
  RESULT=$(github_search "$QUERY")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    items = data.get('items', [])
    if not items:
        print('  No results found.')
    for r in items[:10]:
        stars = r.get('stargazers_count', 0)
        name = r['full_name']; url = r['html_url']
        lang = r.get('language', '?')
        created = r.get('created_at', '')[:10]
        updated = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or 'No description')[:120]
        license = (r.get('license') or {}).get('spdx_id', '?')
        res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
        status = res.stdout.strip()
        if status == 'known': continue
        tag = '🆕' if status == 'new' else '📈'
        print(f'  {tag} [{name}]({url}) [{stars}★] ({lang}, {license})')
        print(f'    Created: {created} Updated: {updated} | {desc}')
        print()
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null && HAS_RESULTS=true
  echo ""
  sleep 2
fi

# --- GitHub MCP Servers ---
if echo "$SOURCES" | grep -q "mcp"; then
  echo "--- MCP Servers (GitHub) ---"
  RESULT=$(github_search "mcp server $QUERY")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    items = data.get('items', [])
    if not items:
        print('  No results found.')
    for r in items[:5]:
        stars = r.get('stargazers_count', 0)
        name = r['full_name']; url = r['html_url']
        lang = r.get('language', '?')
        created = r.get('created_at', '')[:10]
        updated = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or 'No description')[:120]
        res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
        status = res.stdout.strip()
        if status == 'known': continue
        tag = '🆕' if status == 'new' else '📈'
        print(f'  {tag} [{name}]({url}) [{stars}★] ({lang})')
        print(f'    Created: {created} Updated: {updated} | {desc}')
        print()
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null && HAS_RESULTS=true
  echo ""
  sleep 2
fi

# --- npm Packages ---
if echo "$SOURCES" | grep -q "npm"; then
  echo "--- npm Packages ---"
  ENCODED_Q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")
  NPM_RESULT=$(curl -s "https://registry.npmjs.org/-/v1/search?text=${ENCODED_Q}&size=5" 2>/dev/null)
  echo "$NPM_RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    objects = data.get('objects', [])
    if not objects:
        print('  No results found.')
    for obj in objects[:5]:
        pkg = obj.get('package', {})
        name = pkg.get('name', '?')
        desc = (pkg.get('description') or 'No description')[:120]
        version = pkg.get('version', '?')
        date = obj.get('package', {}).get('date', '?')[:10] if obj.get('package', {}).get('date') else '?'
        link = pkg.get('links', {}).get('npm', '')
        if link:
            print(f'  [{name}@{version}]({link}) updated {date}')
        else:
            print(f'  {name}@{version} updated {date}')
        print(f'    {desc}')
        print()
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null && HAS_RESULTS=true
  echo ""
  sleep 2
fi

# --- PyPI Packages ---
if echo "$SOURCES" | grep -q "pypi"; then
  echo "--- PyPI Packages ---"
  ENCODED_Q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")
  PYPI_RESULT=$(curl -s "https://pypi.org/search/?q=${ENCODED_Q}&o=" 2>/dev/null)
  # PyPI search doesn't have a JSON API, use GitHub search for Python packages instead
  RESULT=$(github_search "$QUERY language:python")
  echo "$RESULT" | python3 -c "
import sys, json, subprocess
try:
    data = json.load(sys.stdin)
    dedup = '${DEDUP_SCRIPT}'
    items = [r for r in data.get('items', []) if r.get('language') == 'Python']
    if not items:
        print('  No results found.')
    for r in items[:5]:
        stars = r.get('stargazers_count', 0)
        name = r['full_name']; url = r['html_url']
        created = r.get('created_at', '')[:10]
        updated = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or 'No description')[:120]
        res = subprocess.run(['python3', dedup, '--check', name, str(stars)], capture_output=True, text=True)
        status = res.stdout.strip()
        if status == 'known': continue
        tag = '🆕' if status == 'new' else '📈'
        print(f'  {tag} [{name}]({url}) [{stars}★]')
        print(f'    Created: {created} Updated: {updated} | {desc}')
        print()
except Exception as e:
    print(f'  Parse error: {e}')
" 2>/dev/null && HAS_RESULTS=true
  echo ""
fi

echo "=== End Find-Skill Report ==="

if [[ "$HAS_RESULTS" == true ]]; then
  exit 0
else
  exit 1
fi
