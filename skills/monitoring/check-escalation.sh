#!/bin/bash
# check-escalation.sh — Query escalation history for a task from audit.jsonl
# Usage: check-escalation.sh --task <task_id> | --task-pattern <keyword>
# Exit: 0=found, 1=not found, 2=infrastructure error
set -uo pipefail

AUDIT_LOG="$HOME/mason-hub/logs/audit.jsonl"
MAX_PM_RETRIES=2

if [ ! -f "$AUDIT_LOG" ]; then
  echo '{"error":"audit.jsonl not found","path":"'"$AUDIT_LOG"'"}'
  exit 2
fi

# Parse arguments
TASK_ID=""
TASK_PATTERN=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --task) TASK_ID="$2"; shift 2;;
    --task-pattern) TASK_PATTERN="$2"; shift 2;;
    --help) echo "Usage: check-escalation.sh --task <task_id> | --task-pattern <keyword>"; exit 0;;
    *) shift;;
  esac
done

if [ -z "$TASK_ID" ] && [ -z "$TASK_PATTERN" ]; then
  echo '{"error":"Must provide --task <task_id> or --task-pattern <keyword>"}'
  exit 2
fi

python3 -c "
import json, sys, re

audit_file = '$AUDIT_LOG'
task_id = '$TASK_ID'
task_pattern = '$TASK_PATTERN'
max_pm_retries = $MAX_PM_RETRIES

# Read all records
records = []
with open(audit_file) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

# Filter matching records
matched = []
for r in records:
    rid = r.get('task_id', '')
    if task_id and rid == task_id:
        matched.append(r)
    elif task_pattern and task_pattern.lower() in json.dumps(r).lower():
        matched.append(r)

if not matched:
    print(json.dumps({'error': 'no matching records found', 'task_id': task_id or task_pattern}))
    sys.exit(1)

# Determine task_id from first match if using pattern
effective_task_id = matched[0].get('task_id', 'unknown')

# Count metrics
dev_attempts = 0
pm_retries = 0
history = []

for r in matched:
    status = r.get('status', '')
    if status == 'repair_failed':
        attempts = r.get('attempts', [])
        dev_attempts += len(attempts)
        pm_retry = r.get('pm_retry_count', 0)
        pm_retries = max(pm_retries, pm_retry)
        history.append({
            'agent': r.get('agent', ''),
            'status': status,
            'dev_rounds': len(attempts),
            'pm_retry_count': pm_retry,
            'timestamp': r.get('timestamp', '')
        })
    elif status == 'completed':
        history.append({
            'agent': r.get('agent', ''),
            'status': status,
            'verify_rounds': r.get('verify_rounds', 0),
            'timestamp': r.get('timestamp', '')
        })

can_retry = pm_retries < max_pm_retries

result = {
    'task_id': effective_task_id,
    'dev_attempts': dev_attempts,
    'pm_retries': pm_retries,
    'max_pm_retries': max_pm_retries,
    'can_retry': can_retry,
    'history': history
}

print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0)
" 2>/dev/null

EXIT=$?
if [ $EXIT -eq 2 ] || [ $EXIT -gt 2 ]; then
  echo '{"error":"python3 execution failed"}'
  exit 2
fi
exit $EXIT
