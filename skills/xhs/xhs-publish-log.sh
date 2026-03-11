#!/bin/bash
# xhs-publish-log.sh — XHS 发布记录 CLI
#
# 用法:
#   xhs-publish-log.sh log --title "标题" --keywords "k1,k2" [--type video] [--expect high]
#   xhs-publish-log.sh check [--id 1] [--all]
#   xhs-publish-log.sh list
#   xhs-publish-log.sh review [--json-out /path/to/output.json]

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"

if [ $# -eq 0 ]; then
  echo "Usage: xhs-publish-log.sh <log|check|list|review> [options]"
  echo ""
  echo "Commands:"
  echo "  log      Record a new publish"
  echo "  check    Check actual performance (72h+ after publish)"
  echo "  list     List all publish records"
  echo "  review   Prediction accuracy review"
  exit 1
fi

# Sync script
scp -o ConnectTimeout=10 "$HUB_DIR/skills/xhs/_xhs_publish_log.py" "$ALIYUN:$MC_DIR/_publish_log.py" 2>/dev/null

# Pass all args through
ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python _publish_log.py $* 2>&1"

EXIT_CODE=$?

# Log event for tracking
CMD="$1"
if [ "$CMD" = "log" ]; then
  log_event "xhs-publish" "publish-log" "info" "Recorded publish: $*"
elif [ "$CMD" = "check" ]; then
  log_event "xhs-publish" "publish-log" "info" "Checked publish performance: $*"
fi

exit $EXIT_CODE
