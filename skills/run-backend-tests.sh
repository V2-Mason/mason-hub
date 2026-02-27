#!/bin/bash
# run-backend-tests.sh — Run pytest for surenxuan backend
# Auto-starts backend if not running, kills it after tests if self-started.
# Usage: run-backend-tests.sh [--module <name>] [--mark <marker>]
# Exit: 0=all pass, 1=some fail, 2=infrastructure error
set -uo pipefail

PROJECT_DIR="$HOME/surenxuan"
TESTS_DIR="$PROJECT_DIR/backend/tests"
TIMEOUT=120
STARTUP_TIMEOUT=15
SELF_STARTED=false
SERVER_PID=""

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

# --- Auto-manage backend service ---
PID_FILE="/tmp/surenxuan-test-backend.pid"

start_backend() {
  echo "[service] Starting backend..."
  STARTUP_LOG=$(mktemp)
  cd "$PROJECT_DIR" && DEV_MODE=true setsid python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level warning > "$STARTUP_LOG" 2>&1 &
  SERVER_PID=$!
  echo "$SERVER_PID" > "$PID_FILE"
  SELF_STARTED=true

  for i in $(seq 1 "$STARTUP_TIMEOUT"); do
    if curl -s -o /dev/null http://localhost:8000/ 2>/dev/null; then
      echo "[service] Backend ready (${i}s, PID=$SERVER_PID)"
      rm -f "$STARTUP_LOG"
      return 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "ERROR: Backend process died during startup"
      cat "$STARTUP_LOG"
      rm -f "$STARTUP_LOG" "$PID_FILE"
      return 1
    fi
    sleep 1
  done
  echo "ERROR: Backend failed to start within ${STARTUP_TIMEOUT}s"
  rm -f "$STARTUP_LOG"
  kill "$SERVER_PID" 2>/dev/null
  rm -f "$PID_FILE"
  return 1
}

stop_backend() {
  if [ "$SELF_STARTED" = true ] && [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE")
    # Kill entire process group (setsid makes it a group leader)
    kill -- -"$pid" 2>/dev/null || true
    sleep 1
    # Fallback: kill anything still on port 8000
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    echo "[service] Backend stopped (PGID=$pid)"
    rm -f "$PID_FILE"
  fi
}

if curl -s -o /dev/null -w "" http://localhost:8000/ 2>/dev/null; then
  echo "[service] Backend already running on :8000"
else
  start_backend || exit 2
fi

# --- Build pytest command ---
PYTEST_ARGS="-v --tb=short --no-header -q"
TARGET="$TESTS_DIR"

if [ -n "$MODULE" ]; then
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

# --- Run pytest ---
echo "=== BACKEND TESTS ==="
echo "Target: $TARGET"
echo "Marker: ${MARKER:-none}"
echo "---"

EXIT_CODE=0
OUTPUT=$(cd "$PROJECT_DIR" && timeout "$TIMEOUT" python3 -m pytest "$TARGET" $PYTEST_ARGS 2>&1) || EXIT_CODE=$?

echo "$OUTPUT"
echo "---"

# Parse results
PASSED=$(echo "$OUTPUT" | grep -oP '\d+ passed' | grep -oP '\d+' || echo "0")
FAILED=$(echo "$OUTPUT" | grep -oP '\d+ failed' | grep -oP '\d+' || echo "0")
TEST_ERRORS=$(echo "$OUTPUT" | grep -oP '\d+ error' | grep -oP '\d+' || echo "0")

echo "=== SUMMARY ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Errors: $TEST_ERRORS"
echo "Exit code: $EXIT_CODE"

# Explicit cleanup
stop_backend

if [ "$EXIT_CODE" -eq 124 ]; then
  echo "TIMEOUT: Tests exceeded ${TIMEOUT}s limit"
  exit 2
elif [ "$EXIT_CODE" -ne 0 ]; then
  exit 1
fi
exit 0
