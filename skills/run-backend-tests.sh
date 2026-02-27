#!/bin/bash
# run-backend-tests.sh — Run pytest for surenxuan backend
# Usage: run-backend-tests.sh [--module <name>] [--mark <marker>]
# Exit: 0=all pass, 1=some fail, 2=infrastructure error
set -uo pipefail

PROJECT_DIR="$HOME/surenxuan"
TESTS_DIR="$PROJECT_DIR/backend/tests"
TIMEOUT=120

if [ ! -d "$TESTS_DIR" ]; then
  echo "ERROR: Tests directory not found: $TESTS_DIR"
  exit 2
fi

# Parse arguments
MODULE=""
MARKER=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --module) MODULE="$2"; shift 2;;
    --mark) MARKER="$2"; shift 2;;
    --help) echo "Usage: run-backend-tests.sh [--module <name>] [--mark <marker>]"; exit 0;;
    *) shift;;
  esac
done

# Build pytest command
PYTEST_ARGS="-v --tb=short --no-header -q"
TARGET="$TESTS_DIR"

if [ -n "$MODULE" ]; then
  # Support both "sales" and "test_sales" formats
  MOD_NAME="$MODULE"
  [[ "$MOD_NAME" != test_* ]] && MOD_NAME="test_${MOD_NAME}"
  TARGET="$TESTS_DIR/${MOD_NAME}.py"
  if [ ! -f "$TARGET" ]; then
    echo "ERROR: Test file not found: $TARGET"
    echo "Available test files:"
    ls "$TESTS_DIR"/test_*.py 2>/dev/null | xargs -I{} basename {}
    exit 2
  fi
fi

if [ -n "$MARKER" ]; then
  PYTEST_ARGS="$PYTEST_ARGS -m $MARKER"
fi

# Run pytest with timeout
echo "=== BACKEND TESTS ==="
echo "Target: $TARGET"
echo "Marker: ${MARKER:-none}"
echo "---"

OUTPUT=$(cd "$PROJECT_DIR" && timeout "$TIMEOUT" python3 -m pytest "$TARGET" $PYTEST_ARGS 2>&1) || true
EXIT_CODE=$?

echo "$OUTPUT"
echo "---"

# Parse results
PASSED=$(echo "$OUTPUT" | grep -oP '\d+ passed' | grep -oP '\d+' || echo "0")
FAILED=$(echo "$OUTPUT" | grep -oP '\d+ failed' | grep -oP '\d+' || echo "0")
ERRORS=$(echo "$OUTPUT" | grep -oP '\d+ error' | grep -oP '\d+' || echo "0")

echo "=== SUMMARY ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Errors: $ERRORS"
echo "Exit code: $EXIT_CODE"

if [ "$EXIT_CODE" -eq 124 ]; then
  echo "TIMEOUT: Tests exceeded ${TIMEOUT}s limit"
  exit 2
elif [ "$EXIT_CODE" -ne 0 ]; then
  exit 1
fi
exit 0
