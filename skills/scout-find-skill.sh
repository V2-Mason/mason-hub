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
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    if not items:
        print('  No results found.')
    for r in items[:10]:
        stars = r.get('stargazers_count', 0)
        lang = r.get('language', '?')
        updated = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or 'No description')[:120]
        license = (r.get('license') or {}).get('spdx_id', '?')
        print(f'  [{stars}★] {r[\"full_name\"]} ({lang}, {license})')
        print(f'    Updated: {updated} | {desc}')
        print(f'    URL: {r[\"html_url\"]}')
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
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    if not items:
        print('  No results found.')
    for r in items[:5]:
        stars = r.get('stargazers_count', 0)
        lang = r.get('language', '?')
        updated = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or 'No description')[:120]
        print(f'  [{stars}★] {r[\"full_name\"]} ({lang})')
        print(f'    Updated: {updated} | {desc}')
        print(f'    URL: {r[\"html_url\"]}')
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
        link = pkg.get('links', {}).get('npm', '')
        print(f'  {name}@{version}')
        print(f'    {desc}')
        if link:
            print(f'    URL: {link}')
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
import sys, json
try:
    data = json.load(sys.stdin)
    items = [r for r in data.get('items', []) if r.get('language') == 'Python']
    if not items:
        print('  No results found.')
    for r in items[:5]:
        stars = r.get('stargazers_count', 0)
        updated = r.get('pushed_at', '')[:10]
        desc = (r.get('description') or 'No description')[:120]
        print(f'  [{stars}★] {r[\"full_name\"]}')
        print(f'    Updated: {updated} | {desc}')
        print(f'    URL: {r[\"html_url\"]}')
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
