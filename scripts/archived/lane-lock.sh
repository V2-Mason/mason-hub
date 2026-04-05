#!/bin/bash
# Lane Queue — serial execution lock per domain lane
# Uses atomic mkdir for file-based locking
#
# Usage:
#   lane-lock.sh get-lane <agent_id>
#   lane-lock.sh acquire <lane> <agent_id> <task_id> [--timeout <minutes>] [--wait <seconds>]
#   lane-lock.sh release <lane> <agent_id>
#   lane-lock.sh status [<lane>]
#   lane-lock.sh cleanup

set -euo pipefail

LOCK_DIR="${HOME}/mason-hub/locks"
mkdir -p "$LOCK_DIR"

# --- Subcommand: get-lane ---
cmd_get_lane() {
  local agent_id="${1:-}"
  case "$agent_id" in
    EMP_0001|EMP_0003|EMP_0005|EMP_0013|EMP_0015) echo "ecommerce" ;;
    EMP_0008|EMP_0009|EMP_0010)                    echo "socialmesh" ;;
    EMP_0002|EMP_0004|EMP_0014)                    echo "platform" ;;
    *)                                       echo "" ;;
  esac
}

# --- Helper: read info.json field ---
read_info() {
  local lock_path="$1"
  local info_file="${lock_path}/info.json"
  if [ -f "$info_file" ]; then
    cat "$info_file"
  else
    echo "{}"
  fi
}

# --- Helper: write info.json ---
write_info() {
  local lock_path="$1"
  local agent="$2"
  local task_id="$3"
  local timeout_minutes="$4"
  local now
  now=$(date -u +%s)
  local caller_pid=$PPID
  python3 -c "
import json
info = {
    'agent': '$agent',
    'pid': $caller_pid,
    'task_id': '$task_id',
    'acquired_at': $now,
    'timeout_minutes': $timeout_minutes
}
with open('${lock_path}/info.json', 'w') as f:
    json.dump(info, f, indent=2)
"
}

# --- Helper: check if lock is stale ---
is_stale() {
  local lock_path="$1"
  local info
  info=$(read_info "$lock_path")
  if [ "$info" = "{}" ]; then
    # No info.json means stale
    return 0
  fi
  python3 -c "
import json, sys, os
info = json.loads('''$info''')
import time
now = int(time.time())
acquired = info.get('acquired_at', 0)
timeout_min = info.get('timeout_minutes', 20)
# Check timeout
if (acquired + timeout_min * 60) < now:
    sys.exit(0)  # stale (timeout expired)
# Check if holder PID is alive (the shell that acquired the lock)
pid = info.get('pid', 0)
if pid > 0:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        sys.exit(0)  # stale (PID dead)
    except PermissionError:
        pass  # PID exists but we can't signal it
sys.exit(1)  # not stale
" 2>/dev/null
}

# --- Subcommand: acquire ---
cmd_acquire() {
  local lane="${1:-}"
  local agent_id="${2:-}"
  local task_id="${3:-unknown}"
  local timeout_minutes=20
  local wait_seconds=0

  if [ -z "$lane" ] || [ -z "$agent_id" ]; then
    echo "Usage: lane-lock.sh acquire <lane> <agent_id> <task_id> [--timeout <minutes>] [--wait <seconds>]" >&2
    return 1
  fi

  # Parse optional args
  shift 3 || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --timeout) timeout_minutes="${2:-20}"; shift 2 ;;
      --wait)    wait_seconds="${2:-0}"; shift 2 ;;
      *)         shift ;;
    esac
  done

  local lock_path="${LOCK_DIR}/${lane}.lock"
  local deadline
  deadline=$(( $(date -u +%s) + wait_seconds ))

  while true; do
    # Try atomic mkdir
    if mkdir "$lock_path" 2>/dev/null; then
      write_info "$lock_path" "$agent_id" "$task_id" "$timeout_minutes"
      echo "Lock acquired: lane=$lane agent=$agent_id task=$task_id timeout=${timeout_minutes}m"
      return 0
    fi

    # Lock exists — check staleness
    if is_stale "$lock_path"; then
      local old_info
      old_info=$(read_info "$lock_path")
      echo "Removing stale lock: $old_info" >&2
      rm -rf "$lock_path"
      # Retry immediately
      continue
    fi

    # Not stale — check if we should wait
    local now
    now=$(date -u +%s)
    if [ "$now" -ge "$deadline" ]; then
      local holder_info
      holder_info=$(read_info "$lock_path")
      echo "Cannot acquire lock: lane=$lane held by $(echo "$holder_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent','unknown'))" 2>/dev/null || echo unknown)" >&2
      return 1
    fi

    # Wait and retry
    sleep 5
  done
}

# --- Subcommand: release ---
cmd_release() {
  local lane="${1:-}"
  local agent_id="${2:-}"

  if [ -z "$lane" ] || [ -z "$agent_id" ]; then
    echo "Usage: lane-lock.sh release <lane> <agent_id>" >&2
    return 1
  fi

  local lock_path="${LOCK_DIR}/${lane}.lock"

  # Already released — idempotent
  if [ ! -d "$lock_path" ]; then
    return 0
  fi

  # Verify holder
  local info
  info=$(read_info "$lock_path")
  local holder
  holder=$(echo "$info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent',''))" 2>/dev/null || echo "")

  if [ "$holder" != "$agent_id" ]; then
    echo "Warning: lock held by $holder, not $agent_id. Not releasing." >&2
    return 1
  fi

  rm -rf "$lock_path"
  echo "Lock released: lane=$lane agent=$agent_id"
  return 0
}

# --- Subcommand: status ---
cmd_status() {
  local filter_lane="${1:-}"

  printf "%-14s %-12s %-20s %-8s %s\n" "LANE" "AGENT" "TASK_ID" "AGE" "STATUS"
  printf "%-14s %-12s %-20s %-8s %s\n" "----" "-----" "-------" "---" "------"

  local found=false
  for lock_path in "${LOCK_DIR}"/*.lock; do
    [ -d "$lock_path" ] || continue
    found=true

    local lane_name
    lane_name=$(basename "$lock_path" .lock)

    if [ -n "$filter_lane" ] && [ "$lane_name" != "$filter_lane" ]; then
      continue
    fi

    local info
    info=$(read_info "$lock_path")

    local agent task_id age_str status_str
    agent=$(echo "$info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent','?'))" 2>/dev/null || echo "?")
    task_id=$(echo "$info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id','?'))" 2>/dev/null || echo "?")

    local acquired_at
    acquired_at=$(echo "$info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('acquired_at',0))" 2>/dev/null || echo "0")
    local now
    now=$(date -u +%s)
    local age_sec=$(( now - acquired_at ))
    local age_min=$(( age_sec / 60 ))
    local age_rem=$(( age_sec % 60 ))
    age_str="${age_min}m${age_rem}s"

    if is_stale "$lock_path"; then
      status_str="[STALE]"
    else
      status_str="ACTIVE"
    fi

    printf "%-14s %-12s %-20s %-8s %s\n" "$lane_name" "$agent" "$task_id" "$age_str" "$status_str"
  done

  if [ "$found" = false ]; then
    echo "(no active locks)"
  fi
}

# --- Subcommand: cleanup ---
cmd_cleanup() {
  local cleaned=0
  for lock_path in "${LOCK_DIR}"/*.lock; do
    [ -d "$lock_path" ] || continue

    if is_stale "$lock_path"; then
      local info
      info=$(read_info "$lock_path")
      local lane_name
      lane_name=$(basename "$lock_path" .lock)
      echo "Cleaning stale lock: lane=$lane_name info=$info"
      rm -rf "$lock_path"
      cleaned=$((cleaned + 1))
    fi
  done

  if [ "$cleaned" -eq 0 ]; then
    echo "No stale locks found."
  else
    echo "Cleaned $cleaned stale lock(s)."
  fi
}

# --- Main dispatch ---
SUBCMD="${1:-}"
shift || true

case "$SUBCMD" in
  get-lane) cmd_get_lane "$@" ;;
  acquire)  cmd_acquire "$@" ;;
  release)  cmd_release "$@" ;;
  status)   cmd_status "$@" ;;
  cleanup)  cmd_cleanup "$@" ;;
  *)
    echo "Usage: lane-lock.sh {get-lane|acquire|release|status|cleanup} [args...]" >&2
    exit 1
    ;;
esac
