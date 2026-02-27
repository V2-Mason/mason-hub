#!/bin/bash
# check-syntax.sh — Python syntax check via py_compile
# Usage: check-syntax.sh <file1.py> [file2.py ...]
# Exit: 0=all pass, 1=some fail, 2=infrastructure error
set -uo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: check-syntax.sh <file1.py> [file2.py ...]"
  exit 2
fi

PASS=0
FAIL=0
ERRORS=""

for f in "$@"; do
  if [[ "$f" != *.py ]]; then
    continue
  fi
  if [ ! -f "$f" ]; then
    ERRORS="${ERRORS}SKIP: $f (file not found)\n"
    continue
  fi
  OUTPUT=$(timeout 10 python3 -m py_compile "$f" 2>&1)
  if [ $? -eq 0 ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    ERRORS="${ERRORS}FAIL: $f\n  ${OUTPUT}\n"
  fi
done

echo "=== SYNTAX CHECK ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ $FAIL -gt 0 ]; then
  echo ""
  echo "--- Failures ---"
  echo -e "$ERRORS"
  exit 1
fi
echo "All files OK"
exit 0
