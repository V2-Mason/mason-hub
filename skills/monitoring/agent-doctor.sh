#!/bin/bash
# agent-doctor.sh — Comprehensive agent system health check
# Exit: 0=healthy (maybe warnings), 1=serious issues, 2=script error
set -uo pipefail

HUB_DIR="$HOME/mason-hub"
AGENTS_DIR="$HUB_DIR/agents"
SKILLS_DIR="$HUB_DIR/skills"
AUDIT_LOG="$HUB_DIR/logs/audit.jsonl"
TASK_LOG_DIR="$HUB_DIR/logs/tasks"
MEMORY_DIR="$HUB_DIR/memory"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
TIMEOUT_LIMIT=60

mark_pass() { echo "[PASS] $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
mark_warn() { echo "[WARN] $1"; WARN_COUNT=$((WARN_COUNT + 1)); }
mark_fail() { echo "[FAIL] $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

echo "=== Agent Doctor Report ==="
echo ""

# --- 1. Agent role file integrity ---
AGENT_FILES=$(ls "$AGENTS_DIR"/EMP_*.md 2>/dev/null)
AGENT_TOTAL=$(echo "$AGENT_FILES" | grep -c '.' || echo 0)
AGENT_VALID=0
for af in $AGENT_FILES; do
  # Check frontmatter parseable (has opening and closing ---)
  FM_COUNT=$(grep -c '^---$' "$af" 2>/dev/null || echo 0)
  if [ "$FM_COUNT" -ge 2 ]; then
    AGENT_VALID=$((AGENT_VALID + 1))
  fi
done
if [ "$AGENT_VALID" -eq "$AGENT_TOTAL" ] && [ "$AGENT_TOTAL" -gt 0 ]; then
  mark_pass "Agent files: $AGENT_VALID/$AGENT_TOTAL valid"
else
  mark_fail "Agent files: $AGENT_VALID/$AGENT_TOTAL valid"
fi

# --- 2. Skills array consistency ---
SKILL_MISSING=0
SKILL_TOTAL=0
for af in $AGENT_FILES; do
  SKILLS=$(awk 'BEGIN{c=0; in_skills=0} /^---$/{c++; next} c>=2{exit} c==1{
    if(/^skills:/){in_skills=1; if(/\[\]/){in_skills=0}; next}
    if(in_skills && /^  - /){gsub(/^  - /,""); print; next}
    if(in_skills && !/^  /){in_skills=0}
  }' "$af")
  for skill in $SKILLS; do
    SKILL_TOTAL=$((SKILL_TOTAL + 1))
    if [ ! -f "$SKILLS_DIR/${skill}.sh" ]; then
      SKILL_MISSING=$((SKILL_MISSING + 1))
      echo "       Missing: $skill.sh (referenced by $(basename "$af"))"
    fi
  done
done
SKILL_FOUND=$((SKILL_TOTAL - SKILL_MISSING))
if [ "$SKILL_MISSING" -eq 0 ]; then
  mark_pass "Skills refs: $SKILL_FOUND/$SKILL_TOTAL have matching .sh files"
else
  mark_fail "Skills refs: $SKILL_FOUND/$SKILL_TOTAL have matching .sh files ($SKILL_MISSING missing)"
fi

# --- 3. Skills scripts health ---
SCRIPT_TOTAL=0
SCRIPT_OK=0
for sf in "$SKILLS_DIR"/*.sh; do
  [ ! -f "$sf" ] && continue
  SCRIPT_TOTAL=$((SCRIPT_TOTAL + 1))
  if [ -x "$sf" ] && bash -n "$sf" 2>/dev/null; then
    SCRIPT_OK=$((SCRIPT_OK + 1))
  else
    echo "       Problem: $(basename "$sf") (not executable or syntax error)"
  fi
done
if [ "$SCRIPT_OK" -eq "$SCRIPT_TOTAL" ] && [ "$SCRIPT_TOTAL" -gt 0 ]; then
  mark_pass "Skills scripts: $SCRIPT_OK/$SCRIPT_TOTAL executable + syntax OK"
else
  mark_fail "Skills scripts: $SCRIPT_OK/$SCRIPT_TOTAL OK"
fi

# --- 4. Log system ---
LOG_OK=true
if [ -f "$AUDIT_LOG" ] && [ -w "$AUDIT_LOG" ]; then
  LAST_ENTRY_AGE=""
  LAST_TS=$(tail -1 "$AUDIT_LOG" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('timestamp',''))" 2>/dev/null || echo "")
  if [ -n "$LAST_TS" ]; then
    LAST_ENTRY_AGE="last entry: $LAST_TS"
  else
    LAST_ENTRY_AGE="no valid entries"
  fi
  mark_pass "Audit log: healthy ($LAST_ENTRY_AGE)"
else
  mark_fail "Audit log: missing or not writable"
  LOG_OK=false
fi

if [ -d "$TASK_LOG_DIR" ] && [ -w "$TASK_LOG_DIR" ]; then
  TASK_LOG_COUNT=$(ls "$TASK_LOG_DIR"/*_summary.json 2>/dev/null | wc -l | tr -d '[:space:]' || echo 0)
  mark_pass "Task logs dir: exists ($TASK_LOG_COUNT summaries)"
else
  mark_warn "Task logs dir: missing or not writable ($TASK_LOG_DIR)"
fi

# --- 5. Working directories ---
WORK_DIRS=("$HOME/surenxuan" "$HUB_DIR")
for wd in "${WORK_DIRS[@]}"; do
  if [ -d "$wd" ]; then
    UNCOMMITTED=$(cd "$wd" && git status --porcelain 2>/dev/null | wc -l || echo "N/A")
    if [ "$UNCOMMITTED" = "0" ]; then
      mark_pass "Working dir: $wd (git clean)"
    else
      mark_warn "Working dir: $wd has $UNCOMMITTED uncommitted changes"
    fi
  else
    mark_fail "Working dir: $wd does not exist"
  fi
done

# --- 6. Dependencies ---
DEPS_OK=true
for dep in python3 pytest curl; do
  if ! command -v "$dep" &>/dev/null; then
    mark_fail "Dependency: $dep not found"
    DEPS_OK=false
  fi
done
# jq is optional but useful
if ! command -v jq &>/dev/null; then
  mark_warn "Dependency: jq not found (optional but recommended)"
else
  if [ "$DEPS_OK" = true ]; then
    mark_pass "Dependencies: python3, pytest, curl, jq all present"
  fi
fi

# --- 7. test-map.json ---
MAP_FILE="$SKILLS_DIR/test-map.json"
if [ -f "$MAP_FILE" ]; then
  MAP_VALID=$(python3 -c "
import json
with open('$MAP_FILE') as f:
    m = json.load(f)
print(len(m))
" 2>/dev/null || echo "0")
  if [ "$MAP_VALID" -gt 0 ]; then
    mark_pass "Test map: $MAP_VALID mappings"
  else
    mark_fail "Test map: invalid JSON or empty"
  fi
else
  mark_warn "Test map: $MAP_FILE not found"
fi

# --- 8. Backend startup test (quick, 10s max) ---
if lsof -ti:8000 &>/dev/null; then
  mark_warn "Backend test: port 8000 already in use, skipping startup test"
else
  BACKEND_DIR="$HOME/surenxuan"
  if [ -d "$BACKEND_DIR" ]; then
    STARTUP_LOG=$(mktemp)
    cd "$BACKEND_DIR" && DEV_MODE=true setsid python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level warning > "$STARTUP_LOG" 2>&1 &
    BG_PID=$!
    BACKEND_OK=false
    for i in $(seq 1 10); do
      if curl -s -o /dev/null http://localhost:8000/ 2>/dev/null; then
        mark_pass "Backend startup: OK (port 8000 responsive in ${i}s)"
        BACKEND_OK=true
        break
      fi
      sleep 1
    done
    if [ "$BACKEND_OK" = false ]; then
      mark_fail "Backend startup: failed within 10s"
    fi
    # Cleanup
    kill -- -"$BG_PID" 2>/dev/null || true
    sleep 1
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    rm -f "$STARTUP_LOG"
  else
    mark_warn "Backend test: $BACKEND_DIR not found, skipping"
  fi
fi

# --- 9. Memory layer ---
if [ -d "$MEMORY_DIR" ]; then
  LESSON_FILES=$(ls "$MEMORY_DIR"/*_lessons.md 2>/dev/null | wc -l || echo 0)
  mark_pass "Memory layer: $LESSON_FILES lesson files"
else
  mark_warn "Memory layer: $MEMORY_DIR not found"
fi

# --- Summary ---
echo ""
TOTAL=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
if [ "$FAIL_COUNT" -eq 0 ]; then
  if [ "$WARN_COUNT" -eq 0 ]; then
    echo "STATUS: HEALTHY ($PASS_COUNT checks passed)"
    exit 0
  else
    echo "STATUS: HEALTHY ($WARN_COUNT warning(s))"
    exit 0
  fi
else
  echo "STATUS: UNHEALTHY ($FAIL_COUNT failure(s), $WARN_COUNT warning(s))"
  exit 1
fi
