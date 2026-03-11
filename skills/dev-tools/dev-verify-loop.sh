#!/bin/bash
# dev-verify-loop.sh — Three-layer verification: syntax → module tests → regression
# Usage: dev-verify-loop.sh <modified_files> [test_module]
#   modified_files: comma-separated list of modified .py files
#   test_module: pytest module to run (e.g., "sales", "selection")
# Exit: 0=all pass, 1=some fail, 2=infrastructure error
set -uo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)"
OVERALL_TIMEOUT=180

if [ $# -lt 1 ]; then
  echo "Usage: dev-verify-loop.sh <modified_files> [test_module]"
  echo "  modified_files: comma-separated .py file paths"
  echo "  test_module: optional pytest module name (e.g., sales)"
  exit 2
fi

MODIFIED_FILES="$1"
TEST_MODULE="${2:-}"

echo "=== DEV VERIFY LOOP ==="
echo "Modified files: $MODIFIED_FILES"
echo "Test module: ${TEST_MODULE:-auto}"
echo ""

# --- Step 1: Syntax Check ---
echo "--- Step 1: Syntax Check ---"
IFS=',' read -ra FILES <<< "$MODIFIED_FILES"
PY_FILES=()
for f in "${FILES[@]}"; do
  f=$(echo "$f" | xargs)  # trim whitespace
  [[ "$f" == *.py ]] && PY_FILES+=("$f")
done

if [ ${#PY_FILES[@]} -eq 0 ]; then
  echo "No .py files to check, skipping syntax check"
else
  "$SKILLS_DIR/check-syntax.sh" "${PY_FILES[@]}"
  SYNTAX_EXIT=$?
  if [ $SYNTAX_EXIT -ne 0 ]; then
    echo ""
    echo "=== VERIFY LOOP FAILED at Step 1 (Syntax) ==="
    exit 1
  fi
fi
echo ""

# --- Step 2: Module Tests ---
if [ -n "$TEST_MODULE" ]; then
  echo "--- Step 2: Module Tests ($TEST_MODULE) ---"
  "$SKILLS_DIR/run-backend-tests.sh" --module "$TEST_MODULE"
  MODULE_EXIT=$?
  if [ $MODULE_EXIT -ne 0 ]; then
    echo ""
    echo "=== VERIFY LOOP FAILED at Step 2 (Module Tests: $TEST_MODULE) ==="
    exit 1
  fi
  echo ""
else
  echo "--- Step 2: Skipped (no test module specified) ---"
  echo ""
fi

# --- Step 3: Full Regression ---
echo "--- Step 3: Full Regression ---"
"$SKILLS_DIR/run-backend-tests.sh"
REGRESSION_EXIT=$?
if [ $REGRESSION_EXIT -ne 0 ]; then
  echo ""
  echo "=== VERIFY LOOP FAILED at Step 3 (Full Regression) ==="
  exit 1
fi

echo ""
echo "=== ALL VERIFICATION PASSED ==="
exit 0
