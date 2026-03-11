#!/bin/bash
# run-acceptance-tests.sh — PM acceptance tests by marker or FIX ID
# Usage: run-acceptance-tests.sh [--fix <FIX_ID>] [--mark <marker>]
# Exit: 0=all pass, 1=some fail, 2=infrastructure error
set -uo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)"

FIX_ID=""
MARKER="acceptance"

while [[ $# -gt 0 ]]; do
  case $1 in
    --fix) FIX_ID="$2"; shift 2;;
    --mark) MARKER="$2"; shift 2;;
    --help) echo "Usage: run-acceptance-tests.sh [--fix <FIX_ID>] [--mark <marker>]"; exit 0;;
    *) shift;;
  esac
done

echo "=== ACCEPTANCE TESTS ==="

if [ -n "$FIX_ID" ]; then
  # Run tests matching the FIX ID keyword
  echo "FIX ID: $FIX_ID"
  "$SKILLS_DIR/run-backend-tests.sh" --mark "$FIX_ID"
else
  echo "Marker: $MARKER"
  "$SKILLS_DIR/run-backend-tests.sh" --mark "$MARKER"
fi

exit $?
