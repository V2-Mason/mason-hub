#!/bin/bash
# agent-loader.sh — v2 Agent 文件加载器
# 从 run-agent.sh 提取，适配 5 文件分层架构
#
# 用法：
#   source scripts/agent-loader.sh
#   load_agent_context <agent_dir> [layer]   # 组装 context 到 stdout
#   update_agent_state <agent_dir> <task_id> <status> [summary]
#
# Layer 说明：
#   0  = identity.md + state.md（T1 轻量任务）
#   01 = identity + state + soul + tools + memory.md（T3+ 完整任务，默认）

set -euo pipefail

# ============================================================
# load_agent_context — 组装 agent 上下文到 stdout
# ============================================================
load_agent_context() {
  local agent_dir="$1"
  local layer="${2:-01}"

  # --- 规范化路径 ---
  if [[ ! "$agent_dir" = /* ]]; then
    agent_dir="${HUB_DIR:-$HOME/mason-hub}/$agent_dir"
  fi

  if [ ! -d "$agent_dir" ]; then
    echo "❌ agent-loader: 目录不存在: $agent_dir" >&2
    return 1
  fi

  local identity="$agent_dir/identity.md"
  local state="$agent_dir/state.md"
  local soul="$agent_dir/soul.md"
  local tools="$agent_dir/tools.md"
  local memory="$agent_dir/memory/memory.md"
  local config_fallback="$agent_dir/config.md"

  # --- Layer 0: identity.md（必须存在，或 fallback 到 config.md）---
  if [ -f "$identity" ]; then
    echo "--- identity.md ---"
    # 跳过 YAML frontmatter，只输出 body
    awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$identity"
  elif [ -f "$config_fallback" ]; then
    echo "⚠️ agent-loader: identity.md 不存在，回退到 config.md" >&2
    echo "--- config.md (fallback) ---"
    awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$config_fallback"
    # fallback 模式下只输出 config.md，不继续加载其他 v2 文件
    return 0
  else
    echo "❌ agent-loader: 必须文件缺失: identity.md 和 config.md 都不存在" >&2
    return 1
  fi

  # --- Layer 0: state.md ---
  if [ -f "$state" ]; then
    echo ""
    echo "--- state.md ---"
    awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$state"
  else
    echo "⚠️ agent-loader: state.md 不存在，跳过" >&2
  fi

  # --- Layer 1（仅 layer=01 时加载）---
  if [ "$layer" = "01" ]; then
    if [ -f "$soul" ]; then
      echo ""
      echo "--- soul.md ---"
      cat "$soul"
    else
      echo "⚠️ agent-loader: soul.md 不存在，跳过" >&2
    fi

    if [ -f "$tools" ]; then
      echo ""
      echo "--- tools.md ---"
      cat "$tools"
    else
      echo "⚠️ agent-loader: tools.md 不存在，跳过" >&2
    fi

    if [ -f "$memory" ]; then
      echo ""
      echo "--- memory/memory.md ---"
      cat "$memory"
    else
      echo "⚠️ agent-loader: memory/memory.md 不存在，跳过" >&2
    fi
  fi
}

# ============================================================
# update_agent_state — 覆写 state.md
# ============================================================
update_agent_state() {
  local agent_dir="$1"
  local task_id="$2"
  local status="$3"  # completed / failed
  local summary="${4:-}"

  if [[ ! "$agent_dir" = /* ]]; then
    agent_dir="${HUB_DIR:-$HOME/mason-hub}/$agent_dir"
  fi

  local state_file="$agent_dir/state.md"
  local old_issues=""

  # 保留"已知未解决问题"字段
  if [ -f "$state_file" ]; then
    old_issues=$(awk '/^## 已知未解决问题/{found=1; next} found && /^## /{found=0} found{print}' "$state_file")
  fi

  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local today
  today=$(date +%Y-%m-%d)

  local status_label
  if [ "$status" = "completed" ]; then
    status_label="✅ completed"
  else
    status_label="❌ failed"
  fi

  cat > "$state_file" <<EOF
---
last_updated: $now
---

# $(basename "$agent_dir") 当前状态

## 活跃任务
（无 · 待派发）

## 最近完成
- $today: [$task_id] $status_label${summary:+ — $summary}

## 等待 / 阻塞
（无）

## 已知未解决问题
${old_issues:-（无）}
EOF
}

# ============================================================
# extract_frontmatter_field — 从 identity.md 提取 frontmatter 字段
# ============================================================
extract_frontmatter_field() {
  local file="$1"
  local field="$2"
  awk -v f="$field" 'BEGIN{c=0} /^---$/{c++; next} c>=2{exit} c==1{
    if($0 ~ "^"f":"){gsub("^"f":\\s*", ""); print; exit}
  }' "$file" 2>/dev/null
}

# ============================================================
# extract_launcher_args — 从 identity.md 的 launcher 行提取参数
# ============================================================
extract_launcher_args() {
  local agent_dir="$1"
  if [[ ! "$agent_dir" = /* ]]; then
    agent_dir="${HUB_DIR:-$HOME/mason-hub}/$agent_dir"
  fi

  local identity="$agent_dir/identity.md"
  if [ -f "$identity" ]; then
    # 从 body 中提取 **launcher**: claude --args 格式
    grep -oP '^\*\*launcher\*\*:\s*claude\s+\K.*' "$identity" 2>/dev/null || true
  fi
}
