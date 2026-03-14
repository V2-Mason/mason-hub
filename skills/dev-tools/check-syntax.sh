#!/bin/bash
# check-syntax.sh — Check Python file syntax using ast.parse
# Usage: check-syntax.sh file1.py file2.py ...
# Exit: 0=all pass, 1=syntax error found

if [ $# -eq 0 ]; then
  echo "Usage: check-syntax.sh file1.py [file2.py ...]"
  exit 0
fi

FAILED=0
for f in "$@"; do
  if [ ! -f "$f" ]; then
    echo "WARN: File not found: $f (skipped)"
    continue
  fi
  if python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null; then
    echo "  ✓ $f"
  else
    # Re-run to show the actual error
    echo "  ✗ $f"
    python3 -c "
import ast, sys
try:
    ast.parse(open('$f').read())
except SyntaxError as e:
    print(f'    SyntaxError: {e.msg} (line {e.lineno})', file=sys.stderr)
" 2>&1
    FAILED=1
  fi
done

if [ $FAILED -ne 0 ]; then
  echo ""
  echo "Syntax check FAILED"
  exit 1
fi

echo "Syntax check passed"
exit 0
