#!/bin/bash
# config-health-check.sh — Agent 配置架构一致性检查
#
# 三项检查：
#   1. Config 膨胀检查 — config.md > 4KB 警告
#   2. 引用断裂检查 — config 里引用的文件是否存在
#   3. Protocol/Playbook 过时检查 — 超过 30 天未更新的文件
#
# 用法:
#   scripts/config-health-check.sh          # 全部检查
#   scripts/config-health-check.sh --brief  # 只输出有问题的行（适合 /commit 集成）
#
set -euo pipefail

HUB_DIR="$HOME/mason-hub"
MAX_CONFIG_BYTES=5120  # 5KB: ~4KB markdown body + ~1KB YAML frontmatter
STALE_DAYS=30
BRIEF="${1:-}"
ISSUES=0

warn() {
  echo "  ⚠️  $1"
  ISSUES=$((ISSUES + 1))
}

# === 1. Config 膨胀检查 ===
if [ "$BRIEF" != "--brief" ]; then
  echo "📏 Config 大小检查 (上限 ${MAX_CONFIG_BYTES} bytes)"
fi

for cfg in "$HUB_DIR"/agents/EMP_*/config.md; do
  agent=$(basename "$(dirname "$cfg")")
  # 跳过已归档 agent
  [ "$agent" = "EMP_0007" ] && continue
  size=$(wc -c < "$cfg")
  if [ "$size" -gt "$MAX_CONFIG_BYTES" ]; then
    warn "$agent config.md = ${size} bytes (超过 ${MAX_CONFIG_BYTES})，需要拆分操作细节到 playbook"
  fi
done

if [ "$BRIEF" != "--brief" ] && [ "$ISSUES" -eq 0 ]; then
  echo "  ✅ 所有 config 在 ${MAX_CONFIG_BYTES} bytes 以内"
fi

# === 2. 引用断裂检查 ===
SAVED_ISSUES=$ISSUES
if [ "$BRIEF" != "--brief" ]; then
  echo ""
  echo "🔗 引用完整性检查"
fi

for cfg in "$HUB_DIR"/agents/EMP_*/config.md; do
  agent=$(basename "$(dirname "$cfg")")
  [ "$agent" = "EMP_0007" ] && continue
  # 提取 config 中反引号内的 .md/.yaml/.json 文件引用
  refs=$(grep -oP '`([^`]+\.(?:md|yaml|json))`' "$cfg" | tr -d '`' | sort -u || true)
  for ref in $refs; do
    # 跳过模板路径、变量路径、config 自引用
    case "$ref" in
      *"<"*|*"{"*|*EMP_*config.md|*YYYY*) continue ;;
    esac
    # 解析路径（~ 展开）
    resolved=""
    expanded_ref="${ref/#\~/$HOME}"
    case "$expanded_ref" in
      /*) resolved="$expanded_ref" ;;
      *) resolved="$HUB_DIR/$expanded_ref" ;;
    esac
    if [ -n "$resolved" ] && [ ! -f "$resolved" ] && [ ! -d "$resolved" ]; then
      warn "$agent 引用 $ref → 文件不存在"
    fi
  done
done

if [ "$BRIEF" != "--brief" ] && [ "$ISSUES" -eq "$SAVED_ISSUES" ]; then
  echo "  ✅ 所有引用文件存在"
fi

# === 3. Protocol/Playbook 过时检查 ===
SAVED_ISSUES=$ISSUES
if [ "$BRIEF" != "--brief" ]; then
  echo ""
  echo "📅 过时检查 (>${STALE_DAYS} 天未更新)"
fi

for dir in "$HUB_DIR/shared/protocols" "$HUB_DIR/docs/playbooks"; do
  if [ ! -d "$dir" ]; then continue; fi
  while IFS= read -r -d '' file; do
    relpath="${file#$HUB_DIR/}"
    days_old=$(( ( $(date +%s) - $(stat -c %Y "$file") ) / 86400 ))
    if [ "$days_old" -gt "$STALE_DAYS" ]; then
      warn "$relpath 已 ${days_old} 天未更新，可能需要 review"
    fi
  done < <(find "$dir" -name "*.md" -print0)
done

if [ "$BRIEF" != "--brief" ] && [ "$ISSUES" -eq "$SAVED_ISSUES" ]; then
  echo "  ✅ 所有 protocol/playbook 在 ${STALE_DAYS} 天内更新过"
fi

# === 汇总 ===
if [ "$BRIEF" != "--brief" ]; then
  echo ""
  if [ "$ISSUES" -gt 0 ]; then
    echo "❌ 发现 $ISSUES 个问题"
  else
    echo "✅ 配置架构健康，无问题"
  fi
fi

exit $( [ "$ISSUES" -eq 0 ] && echo 0 || echo 0 )  # 警告不阻塞 commit
