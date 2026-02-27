#!/bin/bash
# deploy-to-aliyun.sh — 一键部署 surenxuan 到阿里云生产环境
# 用法: deploy-to-aliyun.sh [--skip-build] [--skip-restart] [--git]
#
# 默认: tar+scp 方式（不依赖阿里云 git）
# --git: 使用 git pull（已配好 deploy key，推荐）
#
# 流程: preflight → sync → npm build → restart backend → verify

set -euo pipefail

REMOTE="root@106.14.44.68"
LOCAL_DIR="$HOME/surenxuan"
REMOTE_DIR="/opt/surenxuan"
TMP_FILE="/tmp/surenxuan-deploy-$(date +%s).tar.gz"
SKIP_BUILD=false
SKIP_RESTART=false
USE_GIT=false
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    --skip-restart) SKIP_RESTART=true ;;
    --git) USE_GIT=true ;;
  esac
done

echo "=== DEPLOY TO ALIYUN ==="
echo "Source: $LOCAL_DIR"
echo "Target: $REMOTE:$REMOTE_DIR"
echo ""

# --- Step 1: Pre-flight ---
echo "--- Step 1: Pre-flight Checks ---"

# SSH connectivity
if ! ssh -o ConnectTimeout=5 "$REMOTE" "echo OK" >/dev/null 2>&1; then
  echo "❌ SSH to $REMOTE failed"
  exit 1
fi
echo "  ✅ SSH connectivity"

# Local repo clean check
LOCAL_STATUS=$(cd "$LOCAL_DIR" && git status --porcelain 2>/dev/null | head -5)
if [ -n "$LOCAL_STATUS" ]; then
  echo "  ⚠️ Local repo has uncommitted changes (deploying anyway)"
fi

# Remote disk space
DISK_PCT=$(ssh "$REMOTE" "df / --output=pcent | tail -1 | tr -d ' %'" 2>/dev/null || echo "0")
if [ "$DISK_PCT" -gt 90 ]; then
  echo "  ❌ Remote disk ${DISK_PCT}% full (>90%)"
  exit 1
fi
echo "  ✅ Remote disk: ${DISK_PCT}%"

# Get local commit
LOCAL_COMMIT=$(cd "$LOCAL_DIR" && git log --oneline -1 2>/dev/null || echo "unknown")
echo "  📦 Deploying: $LOCAL_COMMIT"
echo ""

# --- Step 2-4: Sync Code ---
if [ "$USE_GIT" = true ]; then
  echo "--- Step 2: Git Pull (recommended) ---"
  GIT_OUTPUT=$(ssh "$REMOTE" "cd $REMOTE_DIR && git stash 2>/dev/null; git pull origin main 2>&1")
  echo "  $GIT_OUTPUT" | tail -5
  if echo "$GIT_OUTPUT" | grep -qE "Already up to date|files changed|Updating"; then
    echo "  ✅ Git sync complete"
  else
    echo "  ⚠️ Git pull may have issues, falling back to tar+scp"
    USE_GIT=false
  fi
fi

if [ "$USE_GIT" = false ]; then
  echo "--- Step 2: Package ---"
  cd "$LOCAL_DIR"
  tar czf "$TMP_FILE" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='uploads/*' \
    --exclude='data/*' \
    --exclude='assets/*' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='logs' \
    .
  SIZE=$(du -h "$TMP_FILE" | cut -f1)
  echo "  📦 Package: $SIZE"

  echo "--- Step 3: Transfer ---"
  scp -q "$TMP_FILE" "$REMOTE:/tmp/deploy.tar.gz"
  echo "  ✅ Transferred"

  echo "--- Step 4: Extract ---"
  ssh "$REMOTE" "cd $REMOTE_DIR && tar xzf /tmp/deploy.tar.gz --overwrite && rm /tmp/deploy.tar.gz"
  echo "  ✅ Extracted to $REMOTE_DIR"
fi

# --- Step 5: Frontend Build ---
if [ "$SKIP_BUILD" = false ]; then
  echo "--- Step 5: Frontend Build ---"
  BUILD_OUTPUT=$(ssh "$REMOTE" "cd $REMOTE_DIR/frontend && npm run build 2>&1 | tail -3")
  echo "  $BUILD_OUTPUT"
  if echo "$BUILD_OUTPUT" | grep -q "built in"; then
    echo "  ✅ Frontend built"
  else
    echo "  ⚠️ Frontend build may have issues"
  fi
else
  echo "--- Step 5: Frontend Build (skipped) ---"
fi

# --- Step 6: Restart Backend ---
if [ "$SKIP_RESTART" = false ]; then
  echo "--- Step 6: Restart Backend ---"
  # Find and kill current backend process
  BACKEND_PID=$(ssh "$REMOTE" "ps aux | grep 'python main.py' | grep -v grep | awk '{print \$2}'" 2>/dev/null || echo "")
  if [ -n "$BACKEND_PID" ]; then
    ssh "$REMOTE" "kill $BACKEND_PID" 2>/dev/null || true
    echo "  Killed old backend (PID $BACKEND_PID)"
    sleep 3
    # Check if auto-restarted
    NEW_PID=$(ssh "$REMOTE" "ps aux | grep 'python main.py' | grep -v grep | awk '{print \$2}'" 2>/dev/null || echo "")
    if [ -n "$NEW_PID" ]; then
      echo "  ✅ Backend auto-restarted (PID $NEW_PID)"
    else
      echo "  ⚠️ Backend did not auto-restart. Starting manually..."
      ssh "$REMOTE" "cd $REMOTE_DIR && nohup $REMOTE_DIR/venv/bin/python main.py > $REMOTE_DIR/logs/backend.log 2>&1 &"
      sleep 3
    fi
  else
    echo "  No running backend found, starting..."
    ssh "$REMOTE" "cd $REMOTE_DIR && nohup $REMOTE_DIR/venv/bin/python main.py > $REMOTE_DIR/logs/backend.log 2>&1 &"
    sleep 3
  fi
else
  echo "--- Step 6: Restart Backend (skipped) ---"
fi

# --- Step 7: Verify ---
echo "--- Step 7: Health Check ---"
sleep 2
HTTP_CODE=$(ssh "$REMOTE" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  echo "  ✅ /api/health → 200"
else
  echo "  ❌ /api/health → $HTTP_CODE"
fi

# External check
EXT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://106.14.44.68:8000/api/health 2>/dev/null || echo "000")
if [ "$EXT_CODE" = "200" ]; then
  echo "  ✅ External health check → 200"
else
  echo "  ⚠️ External health check → $EXT_CODE (may be firewall)"
fi

# --- Cleanup ---
rm -f "$TMP_FILE"

# --- Summary ---
echo ""
echo "=== DEPLOY COMPLETE ==="
echo "Commit: $LOCAL_COMMIT"
echo "Health: $HTTP_CODE (internal) / $EXT_CODE (external)"

# Slack notification
if [ -x "$SLACK_NOTIFY" ]; then
  "$SLACK_NOTIFY" "C0AHCMUC057" "🚀 *部署完成* | $LOCAL_COMMIT | Health: $HTTP_CODE" "Deploy Bot" ":rocket:" 2>/dev/null || true
fi
