#!/bin/bash
# session-bootstrap.sh — Interactive session 启动时注入轻量系统状态 + vault feedback
#
# 只在 interactive mode 下执行（不是 run-agent.sh 触发的 agent session）
# stdout 会被 Claude Code 自动注入到上下文

HUB_DIR="$HOME/projects/mason-hub"
VAULT_DIR="$HOME/vault"

# Agent session 由 run-agent.sh 管理，跳过
if [ -n "${AGENT_SESSION:-}" ] || [ -n "${CLAUDECODE:-}" ]; then
  exit 0
fi

# ========== VAULT FEEDBACK 注入（最重要，放最前面）==========
FEEDBACK_DIR="$VAULT_DIR/_claude/feedback"
if [ -d "$FEEDBACK_DIR" ]; then
  echo "## Vault Feedback Rules (auto-injected)"
  echo ""
  for f in "$FEEDBACK_DIR"/*.md; do
    [ -f "$f" ] || continue
    # 跳过 frontmatter，只输出正文
    awk 'BEGIN{skip=0} /^---$/{skip++; next} skip>=2{print}' "$f"
    echo ""
  done
  echo "---"
  echo ""
fi

# ========== Session INDEX 注入 ==========
SESSION_INDEX="$VAULT_DIR/_claude/session/INDEX.md"
if [ -f "$SESSION_INDEX" ]; then
  echo "## Session INDEX (auto-injected)"
  cat "$SESSION_INDEX"
  echo ""
  echo "---"
  echo ""
fi

# ========== 系统快照 ==========
echo "## 系统快照 ($(TZ=America/New_York date '+%Y-%m-%d %H:%M ET'))"
echo ""

# 1. System state from YAML (machine-readable)
STATE_FILE="$HUB_DIR/system-state.yaml"
if [ -f "$STATE_FILE" ]; then
  echo "**Capability Lines**:"
  # Extract line statuses using grep (no python dependency)
  for line in data content commerce; do
    status=$(grep -A1 "^  $line:" "$STATE_FILE" | grep "status:" | head -1 | sed 's/.*status: //')
    action=$(grep -A6 "^  $line:" "$STATE_FILE" | grep "next_action:" | head -1 | sed 's/.*next_action: //')
    if [ -n "$status" ]; then
      echo "  $line: $status $([ "$action" != "null" ] && [ -n "$action" ] && echo "-> $action")"
    fi
  done
  echo ""

  # Stale action check
  echo "**Alerts**:"
  python3 "$HUB_DIR/scripts/update-system-state.py" 2>/dev/null | grep -E '^\s+[!?]' | head -5
  if [ $? -ne 0 ]; then
    echo "  (none)"
  fi
  echo ""
fi

# 3. CC Native Agents
AGENTS_DIR="$HUB_DIR/.claude/agents"
if [ -d "$AGENTS_DIR" ]; then
  echo "**CC Agents**:"
  for f in "$AGENTS_DIR"/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .md)
    desc=$(grep "^description:" "$f" | head -1 | sed 's/^description: *"//;s/"$//')
    echo "  - $name: $desc"
  done
  echo ""
fi

# 4. 最近 5 个 commits（让 Claude 知道最近在做什么）
echo "**最近工作**:"
git -C "$HUB_DIR" log --oneline -5 2>/dev/null | sed 's/^/  /'

echo ""
echo "---"
echo "提示: 读 \`tasks/NOW.md\` 看待办 | \`system-state.yaml\` 看状态 | \`SYSTEM_MAP.md\` 看架构概览"
