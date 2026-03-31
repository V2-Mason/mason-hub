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

# 1. 当前系统焦点（SYSTEM_MAP 前几行）
if [ -f "$HUB_DIR/SYSTEM_MAP.md" ]; then
  # 提取全局状态段落
  state=$(sed -n '/^## 全局状态/,/^##/p' "$HUB_DIR/SYSTEM_MAP.md" | head -5 | tail -3)
  if [ -n "$state" ]; then
    echo "**系统焦点**: $state"
    echo ""
  fi
fi

# 2. 能力线一行状态（名称+状态）
if [ -f "$HUB_DIR/SYSTEM_MAP.md" ]; then
  echo "**能力线**:"
  grep -B5 "^状态:" "$HUB_DIR/SYSTEM_MAP.md" | grep -E "^###|^状态:" | paste - - 2>/dev/null | \
    sed 's/### [0-9]*\. /  /; s/\t/ → /' | head -5
  echo ""
fi

# 3. Dispatcher 状态
if [ -f "$HUB_DIR/scripts/dispatcher_pause" ]; then
  echo "**Dispatcher**: ⏸️ PAUSED"
else
  echo "**Dispatcher**: ▶️ active"
fi

# 4. 今日 agent 活动摘要
DAILY_FILE="$HUB_DIR/memory/daily/$(date +%Y-%m-%d).md"
if [ -f "$DAILY_FILE" ]; then
  count=$(grep -c "^|" "$DAILY_FILE" 2>/dev/null || echo 0)
  count=$((count - 1))  # 减去表头
  if [ "$count" -gt 0 ]; then
    echo "**今日 agent 活动**: ${count} 条"
  fi
fi

# 5. 最近 3 个 session（让 Claude 知道最近在做什么）
echo ""
echo "**最近 session**:"
find "$HUB_DIR/agents"/*/memory/sessions -name "*.md" -type f 2>/dev/null | \
  xargs ls -t 2>/dev/null | head -3 | while read -r f; do
    agent=$(echo "$f" | grep -oP 'EMP_\d+')
    task=$(grep "^- 任务：" "$f" 2>/dev/null | head -1 | sed 's/^- 任务：//' | head -c 60)
    status=$(grep "^status:" "$f" 2>/dev/null | head -1 | sed 's/^status: //')
    if [ -n "$task" ]; then
      echo "  - $agent: $task ($status)"
    fi
  done

# 6. v2 路线图进度
PROGRESS_FILE="$HUB_DIR/data/v2-progress.yaml"
if [ -f "$PROGRESS_FILE" ]; then
  echo ""
  echo "**v2 路线图进度**:"
  # 提取下一个 pending session
  next_session=$(grep -B1 "status: pending" "$PROGRESS_FILE" | grep "S[0-9]:" | head -1 | tr -d ' :')
  completed=$(grep "status: done" "$PROGRESS_FILE" 2>/dev/null | grep -c "done" || echo 0)
  total=$(grep -E "^\s+- id:" "$PROGRESS_FILE" 2>/dev/null | wc -l || echo 0)
  if [ -n "$next_session" ]; then
    content=$(grep -A2 "$next_session:" "$PROGRESS_FILE" | grep "content:" | sed 's/.*content: "//' | tr -d '"')
    echo "  下一步: $next_session — $content"
    echo "  进度: ${completed}/${total} 交付物完成"
    echo "  路线图: docs/plans/2026-03-14-agent-os-v2-90-percent.md"
  fi
fi

echo ""
echo "---"
echo "提示: 读 \`tasks/backlog.md\` 看完整待办，读 \`SYSTEM_MAP.md\` 看详细状态"
