#!/bin/bash
# compact-memory.sh — 记忆衰减脚本
# 用法: compact-memory.sh [agent_id] [--dry-run]
# 规则:
#   7 天内：完整保留
#   7-30 天：保留关键信息（AI 压缩）
#   30 天+：单行总结，标记 [COMPACTED]
#
# 同时归档 logs/tasks/ 中超过 30 天的任务日志

set -euo pipefail

HUB_DIR="$HOME/mason-hub"
MEMORY_DIR="$HUB_DIR/memory"
TASK_LOG_DIR="$HUB_DIR/logs/tasks"
ARCHIVE_DIR="$HUB_DIR/logs/archive"
DRY_RUN=false

# --- 参数解析 ---
AGENT_ID="${1:-all}"
if [ "${2:-}" = "--dry-run" ] || [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=true
  [ "${1:-}" = "--dry-run" ] && AGENT_ID="all"
fi

mkdir -p "$ARCHIVE_DIR"

# --- 加载 API key ---
source ~/slack-bot/.env 2>/dev/null || true
export ANTHROPIC_API_KEY

NOW_EPOCH=$(date +%s)
SEVEN_DAYS=$((7 * 86400))
THIRTY_DAYS=$((30 * 86400))

echo "=== MEMORY COMPACTION ==="
echo "Agent: $AGENT_ID"
echo "Dry run: $DRY_RUN"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# --- Part 1: Compact lessons.md files ---
compact_lessons() {
  local file="$1"
  local agent="$2"

  if [ ! -f "$file" ] || [ ! -s "$file" ]; then
    echo "[$agent] lessons file empty or missing, skip"
    return
  fi

  local file_size
  file_size=$(stat -c %s "$file")
  echo "[$agent] lessons file: $(( file_size / 1024 ))KB"

  # 如果文件小于 2KB，不需要压缩
  if [ "$file_size" -lt 2048 ]; then
    echo "[$agent] under 2KB, skip compaction"
    return
  fi

  # 提取所有日期标记的 section
  local temp_fresh="/tmp/compact_fresh_$$"
  local temp_mid="/tmp/compact_mid_$$"
  local temp_old="/tmp/compact_old_$$"
  local temp_header="/tmp/compact_header_$$"
  > "$temp_fresh"
  > "$temp_mid"
  > "$temp_old"
  > "$temp_header"

  local current_section=""
  local current_date=""
  local in_section=false

  while IFS= read -r line; do
    # 检测 section 头：## 2026-02-27: ... 或 ## [COMPACTED] ...
    if echo "$line" | grep -qP '^## \d{4}-\d{2}-\d{2}:'; then
      # 保存上一个 section
      if [ -n "$current_section" ] && [ -n "$current_date" ]; then
        local section_epoch
        section_epoch=$(date -d "$current_date" +%s 2>/dev/null || echo 0)
        local age=$(( NOW_EPOCH - section_epoch ))
        if [ "$age" -lt "$SEVEN_DAYS" ]; then
          echo "$current_section" >> "$temp_fresh"
        elif [ "$age" -lt "$THIRTY_DAYS" ]; then
          echo "$current_section" >> "$temp_mid"
        else
          echo "$current_section" >> "$temp_old"
        fi
      fi
      current_date=$(echo "$line" | grep -oP '\d{4}-\d{2}-\d{2}')
      current_section="$line"
      in_section=true
    elif echo "$line" | grep -qP '^## \[COMPACTED\]'; then
      # 已压缩的 section 直接保留
      if [ -n "$current_section" ] && [ -n "$current_date" ]; then
        local section_epoch
        section_epoch=$(date -d "$current_date" +%s 2>/dev/null || echo 0)
        local age=$(( NOW_EPOCH - section_epoch ))
        if [ "$age" -lt "$SEVEN_DAYS" ]; then
          echo "$current_section" >> "$temp_fresh"
        elif [ "$age" -lt "$THIRTY_DAYS" ]; then
          echo "$current_section" >> "$temp_mid"
        else
          echo "$current_section" >> "$temp_old"
        fi
      fi
      current_date=""
      current_section="$line"
      in_section=true
    elif [ "$in_section" = true ]; then
      current_section="${current_section}
${line}"
    else
      # Header content (before first section)
      echo "$line" >> "$temp_header"
    fi
  done < "$file"

  # 处理最后一个 section
  if [ -n "$current_section" ] && [ -n "$current_date" ]; then
    local section_epoch
    section_epoch=$(date -d "$current_date" +%s 2>/dev/null || echo 0)
    local age=$(( NOW_EPOCH - section_epoch ))
    if [ "$age" -lt "$SEVEN_DAYS" ]; then
      echo "$current_section" >> "$temp_fresh"
    elif [ "$age" -lt "$THIRTY_DAYS" ]; then
      echo "$current_section" >> "$temp_mid"
    else
      echo "$current_section" >> "$temp_old"
    fi
  fi

  local fresh_count mid_count old_count
  fresh_count=$(grep -c '^## ' "$temp_fresh" 2>/dev/null || echo 0)
  mid_count=$(grep -c '^## ' "$temp_mid" 2>/dev/null || echo 0)
  old_count=$(grep -c '^## ' "$temp_old" 2>/dev/null || echo 0)

  echo "[$agent] sections: fresh=$fresh_count, mid-term=$mid_count, old=$old_count"

  # 只在有 mid-term 或 old 内容时才压缩
  if [ "$mid_count" -eq 0 ] && [ "$old_count" -eq 0 ]; then
    echo "[$agent] nothing to compact"
    rm -f "$temp_fresh" "$temp_mid" "$temp_old" "$temp_header"
    return
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "[$agent] DRY RUN: would compact $mid_count mid-term + $old_count old sections"
    rm -f "$temp_fresh" "$temp_mid" "$temp_old" "$temp_header"
    return
  fi

  # AI 压缩中期内容
  local compacted_mid=""
  if [ "$mid_count" -gt 0 ] && [ -s "$temp_mid" ]; then
    local mid_content
    mid_content=$(cat "$temp_mid")
    compacted_mid=$(unset CLAUDECODE 2>/dev/null; claude -p \
      --output-format text \
      --system-prompt "你是一个记忆压缩助手。将以下 Agent 经验记录压缩为关键信息。保留：具体的文件名、函数名、错误类型、解决方案。删除：详细的调试过程描述、重复信息。每条经验压缩为 1-2 行。保持 ## 日期: 模块 格式。" \
      "压缩以下中期经验（7-30天前）：

$mid_content" 2>/dev/null) || compacted_mid="$mid_content"
  fi

  # AI 压缩远期内容为单行
  local compacted_old=""
  if [ "$old_count" -gt 0 ] && [ -s "$temp_old" ]; then
    local old_content
    old_content=$(cat "$temp_old")
    compacted_old=$(unset CLAUDECODE 2>/dev/null; claude -p \
      --output-format text \
      --system-prompt "你是一个记忆压缩助手。将以下旧经验记录压缩为单行总结，格式为：## [COMPACTED] 模块1: 要点; 模块2: 要点。只保留最核心的教训，每条不超过 15 个字。" \
      "压缩以下远期经验（30天+）为单行总结：

$old_content" 2>/dev/null) || compacted_old=""
  fi

  # 重组文件
  {
    cat "$temp_header"
    [ -n "$compacted_old" ] && echo -e "\n$compacted_old"
    [ -n "$compacted_mid" ] && echo -e "\n$compacted_mid"
    [ -s "$temp_fresh" ] && echo "" && cat "$temp_fresh"
  } > "${file}.new"

  # 备份原文件
  cp "$file" "${file}.bak.$(date +%Y%m%d)"
  mv "${file}.new" "$file"

  local new_size
  new_size=$(stat -c %s "$file")
  echo "[$agent] compacted: $(( file_size / 1024 ))KB → $(( new_size / 1024 ))KB"

  rm -f "$temp_fresh" "$temp_mid" "$temp_old" "$temp_header"
}

# --- Part 2: 归档旧 task logs ---
archive_task_logs() {
  echo ""
  echo "=== TASK LOG ARCHIVAL ==="

  if [ ! -d "$TASK_LOG_DIR" ]; then
    echo "No task log dir, skip"
    return
  fi

  local archived=0
  local total=0

  for f in "$TASK_LOG_DIR"/*; do
    [ -f "$f" ] || continue
    total=$((total + 1))

    local file_age
    file_age=$(( NOW_EPOCH - $(stat -c %Y "$f") ))

    if [ "$file_age" -gt "$THIRTY_DAYS" ]; then
      if [ "$DRY_RUN" = true ]; then
        echo "  DRY RUN: would archive $(basename "$f")"
      else
        mv "$f" "$ARCHIVE_DIR/"
      fi
      archived=$((archived + 1))
    fi
  done

  echo "Task logs: $total total, $archived archived (>30 days)"
}

# --- Part 3: Compact audit.jsonl ---
compact_audit() {
  local audit_file="$HUB_DIR/logs/audit.jsonl"
  echo ""
  echo "=== AUDIT LOG COMPACTION ==="

  if [ ! -f "$audit_file" ] || [ ! -s "$audit_file" ]; then
    echo "Audit log empty, skip"
    return
  fi

  local lines
  lines=$(wc -l < "$audit_file")
  echo "Audit log: $lines entries"

  # 只在超过 500 行时才压缩
  if [ "$lines" -lt 500 ]; then
    echo "Under 500 lines, skip compaction"
    return
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: would compact entries older than 30 days"
    return
  fi

  # 分离：30天内保留，30天前归档
  local archive_file="$ARCHIVE_DIR/audit_$(date +%Y%m%d).jsonl"
  python3 -c "
import json, time, sys
cutoff = time.time() - (30 * 86400)
recent = []
old = []
with open('$audit_file') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            r = json.loads(line)
            ts = r.get('timestamp', '')
            # Parse ISO timestamp
            from datetime import datetime
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            epoch = dt.timestamp()
            if epoch >= cutoff:
                recent.append(line)
            else:
                old.append(line)
        except:
            recent.append(line)  # keep unparseable lines

with open('$archive_file', 'w') as f:
    f.write('\n'.join(old) + '\n')
with open('$audit_file', 'w') as f:
    f.write('\n'.join(recent) + '\n')
print(f'Kept {len(recent)} recent, archived {len(old)} old entries')
" 2>/dev/null || echo "Audit compaction failed (non-critical)"
}

# --- 执行 ---
if [ "$AGENT_ID" = "all" ]; then
  for f in "$MEMORY_DIR"/*_lessons.md; do
    [ -f "$f" ] || continue
    agent=$(basename "$f" _lessons.md)
    compact_lessons "$f" "$agent"
  done
else
  compact_lessons "$MEMORY_DIR/${AGENT_ID}_lessons.md" "$AGENT_ID"
fi

archive_task_logs
compact_audit

echo ""
echo "=== COMPACTION COMPLETE ==="
