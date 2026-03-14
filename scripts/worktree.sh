#!/bin/bash
# worktree.sh — mason-hub git worktree 管理工具
# 用法:
#   worktree.sh create <agent_id> <task_id> [description]  — 创建 worktree + 分支
#   worktree.sh list                                        — 列出所有活跃 worktree
#   worktree.sh merge <branch_name>                         — 合并分支回 main（fast-forward only）
#   worktree.sh cleanup <branch_name>                       — 删除 worktree + 分支
#   worktree.sh cleanup-all                                 — 清理所有已合并的 worktree
#   worktree.sh dir <branch_name>                           — 输出 worktree 目录路径

set -euo pipefail

HUB_DIR="$HOME/mason-hub"
WORKTREE_BASE="$HUB_DIR/.worktrees"

# --- 子命令 ---
cmd="${1:-help}"
shift || true

case "$cmd" in

  create)
    # create <agent_id> <task_id> [description]
    AGENT_ID="${1:?用法: worktree.sh create <agent_id> <task_id> [description]}"
    TASK_ID="${2:?用法: worktree.sh create <agent_id> <task_id> [description]}"
    DESC="${3:-}"
    shift 2; shift || true

    # 分支名: agent/EMP_XXXX/<task_id>
    # 清理非法字符
    SAFE_TASK=$(echo "$TASK_ID" | tr ' /:' '---' | head -c 60)
    BRANCH="agent/${AGENT_ID}/${SAFE_TASK}"
    WT_DIR="$WORKTREE_BASE/${AGENT_ID}_${SAFE_TASK}"

    # 确保 worktree 基目录存在
    mkdir -p "$WORKTREE_BASE"

    # 检查是否已存在
    if [ -d "$WT_DIR" ]; then
      echo "⚠️  Worktree 已存在: $WT_DIR (branch: $BRANCH)"
      echo "$WT_DIR"
      exit 0
    fi

    # 确保 main 是最新的
    cd "$HUB_DIR"
    git fetch origin main 2>/dev/null || true

    # 创建分支 + worktree
    git worktree add -b "$BRANCH" "$WT_DIR" main 2>/dev/null || {
      # 分支可能已存在（之前创建但 worktree 被删了）
      git worktree add "$WT_DIR" "$BRANCH" 2>/dev/null || {
        echo "❌ 无法创建 worktree: branch=$BRANCH dir=$WT_DIR"
        exit 1
      }
    }

    echo "✅ Worktree 已创建"
    echo "   分支: $BRANCH"
    echo "   目录: $WT_DIR"
    [ -n "$DESC" ] && echo "   描述: $DESC"
    echo "$WT_DIR"
    ;;

  list)
    cd "$HUB_DIR"
    echo "=== 活跃 Worktrees ==="
    git worktree list
    echo ""
    # 额外显示哪些 agent 分支存在
    echo "=== Agent 分支 ==="
    git branch --list 'agent/*' 2>/dev/null || echo "(无)"
    ;;

  dir)
    # dir <branch_name> — 输出 worktree 路径
    BRANCH="${1:?用法: worktree.sh dir <branch_name>}"
    cd "$HUB_DIR"
    WT_PATH=$(git worktree list --porcelain | awk -v b="$BRANCH" '
      /^worktree /{path=$2}
      /^branch refs\/heads\//{
        gsub("branch refs/heads/", "")
        if ($0 == b) print path
      }
    ')
    if [ -n "$WT_PATH" ]; then
      echo "$WT_PATH"
    else
      echo "❌ 找不到分支 $BRANCH 的 worktree"
      exit 1
    fi
    ;;

  merge)
    # merge <branch_name> — 合并回 main
    BRANCH="${1:?用法: worktree.sh merge <branch_name>}"
    cd "$HUB_DIR"

    # 确保当前在 main
    CURRENT=$(git branch --show-current)
    if [ "$CURRENT" != "main" ]; then
      echo "❌ 请在 main 分支上执行 merge（当前: $CURRENT）"
      exit 1
    fi

    # 检查分支是否存在
    if ! git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
      echo "❌ 分支不存在: $BRANCH"
      exit 1
    fi

    # 显示将要合并的内容
    COMMITS=$(git log --oneline main.."$BRANCH" 2>/dev/null | wc -l)
    echo "📋 分支 $BRANCH 有 $COMMITS 个新 commit:"
    git log --oneline main.."$BRANCH" 2>/dev/null | head -10
    echo ""

    # 尝试 fast-forward merge（安全）
    if git merge --ff-only "$BRANCH" 2>/dev/null; then
      echo "✅ Fast-forward merge 成功: $BRANCH → main"
    else
      # 非 fast-forward，用 --no-ff 创建 merge commit
      echo "⚠️  无法 fast-forward，创建 merge commit..."
      git merge --no-ff -m "merge: $BRANCH → main" "$BRANCH"
      echo "✅ Merge commit 已创建: $BRANCH → main"
    fi
    ;;

  cleanup)
    # cleanup <branch_name> — 删除 worktree + 分支
    BRANCH="${1:?用法: worktree.sh cleanup <branch_name>}"
    cd "$HUB_DIR"

    # 找到对应的 worktree 路径
    WT_PATH=$(git worktree list --porcelain 2>/dev/null | awk -v b="refs/heads/$BRANCH" '
      /^worktree /{path=$2}
      $0 == "branch " b {print path}
    ')

    if [ -n "$WT_PATH" ] && [ -d "$WT_PATH" ]; then
      git worktree remove "$WT_PATH" 2>/dev/null || {
        echo "⚠️  强制移除 worktree..."
        git worktree remove --force "$WT_PATH" 2>/dev/null || true
      }
      echo "🗑️  Worktree 已移除: $WT_PATH"
    fi

    # 检查分支是否已合并到 main
    if git branch --merged main | grep -q "$BRANCH"; then
      git branch -d "$BRANCH" 2>/dev/null && echo "🗑️  分支已删除: $BRANCH"
    else
      echo "⚠️  分支 $BRANCH 尚未合并到 main，保留分支（使用 git branch -D 强制删除）"
    fi
    ;;

  cleanup-all)
    # 清理所有已合并的 agent 分支
    cd "$HUB_DIR"
    MERGED=$(git branch --merged main --list 'agent/*' 2>/dev/null || true)
    if [ -z "$MERGED" ]; then
      echo "✅ 没有已合并的 agent 分支需要清理"
      exit 0
    fi
    echo "=== 清理已合并分支 ==="
    while IFS= read -r branch; do
      branch=$(echo "$branch" | xargs)  # trim whitespace
      [ -z "$branch" ] && continue
      bash "$0" cleanup "$branch"
    done <<< "$MERGED"
    # 清理可能残留的空目录
    if [ -d "$WORKTREE_BASE" ]; then
      find "$WORKTREE_BASE" -maxdepth 1 -type d -empty -delete 2>/dev/null || true
    fi
    echo "✅ 清理完成"
    ;;

  help|*)
    echo "worktree.sh — mason-hub git worktree 管理工具"
    echo ""
    echo "用法:"
    echo "  worktree.sh create <agent_id> <task_id> [desc]  创建 worktree + 分支"
    echo "  worktree.sh list                                 列出所有活跃 worktree"
    echo "  worktree.sh dir <branch>                         输出 worktree 目录路径"
    echo "  worktree.sh merge <branch>                       合并分支回 main"
    echo "  worktree.sh cleanup <branch>                     删除 worktree + 分支"
    echo "  worktree.sh cleanup-all                          清理所有已合并分支"
    echo ""
    echo "环境变量（run-agent.sh 集成）:"
    echo "  USE_WORKTREE=1  — agent 在独立 worktree 中执行任务"
    ;;

esac
