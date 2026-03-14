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
MEMORY_DIR="$HUB_DIR/agents"
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

# --- Part 3.5: Lesson 质量评分（压缩后运行）---
score_lesson_quality() {
  local agent_id="$1"
  local lt_file="$MEMORY_DIR/${agent_id}/memory/long_term.md"
  [ -f "$lt_file" ] || return

  echo "[$agent_id] Scoring lesson quality..."

  python3 -c "
import sys

filepath = '$lt_file'
agent = '$agent_id'
issues = []
total_lessons = 0
has_gap = 0
too_short = 0
duplicates = {}

with open(filepath, 'r') as f:
    lines = f.readlines()

seen_texts = set()
for line in lines:
    stripped = line.strip()
    if not stripped.startswith('- '):
        continue
    text = stripped[2:].strip()
    if len(text) < 5:
        continue
    total_lessons += 1

    # Check 1: has gap classification
    if 'Gap' in text and '类型' in text:
        has_gap += 1

    # Check 2: too short (< 15 chars = likely not actionable)
    if len(text) < 15:
        too_short += 1

    # Check 3: near-duplicate detection (first 30 chars)
    key = text[:30].lower()
    if key in seen_texts:
        dup_key = key[:20]
        duplicates[dup_key] = duplicates.get(dup_key, 1) + 1
    seen_texts.add(key)

gap_rate = has_gap / total_lessons * 100 if total_lessons else 0
short_rate = too_short / total_lessons * 100 if total_lessons else 0

print(f'  总 lesson: {total_lessons}')
print(f'  有 Gap 分类: {has_gap} ({gap_rate:.0f}%)')
print(f'  过短(<15字): {too_short} ({short_rate:.0f}%)')
print(f'  疑似重复: {len(duplicates)}')

if gap_rate < 30 and total_lessons > 10:
    print(f'  ⚠️ Gap 分类率低 ({gap_rate:.0f}%)，建议补充 Gap 类型标注')
if short_rate > 30:
    print(f'  ⚠️ {short_rate:.0f}% lesson 过短，可操作性不足')
if len(duplicates) > 3:
    print(f'  ⚠️ 疑似重复 {len(duplicates)} 组，建议合并')
" 2>/dev/null || echo "[$agent_id] Quality scoring skipped (python error)"
}

# --- Part 4: 生成 warm.md（最近任务的滚动摘要，~3K tokens）---
generate_warm_memory() {
  local agent_id="$1"
  local agent_mem_dir="$MEMORY_DIR/${agent_id}/memory"
  local warm_file="$agent_mem_dir/warm.md"
  local long_term_file="$agent_mem_dir/long_term.md"
  local lessons_file="$agent_mem_dir/lessons.md"
  local sessions_dir="$agent_mem_dir/sessions"

  # v1.1 Merge 锁：防止并发 merge 冲突
  local lock_file="/tmp/merge-${agent_id}.lock"
  exec 9>"$lock_file"
  if ! flock -n 9; then
    echo "[$agent_id] merge lock held by another process, skip"
    return
  fi

  # 收集最近素材：sessions/ + task logs + lessons + long_term 最新部分
  local recent_content=""
  local task_count=0

  # v1.1: 优先从 sessions/ 读取（隔离写入的产出）
  local session_content=""
  if [ -d "$sessions_dir" ]; then
    local session_files
    session_files=$(ls -t "$sessions_dir"/*.md 2>/dev/null | grep -v .gitkeep | head -10)
    for sf in $session_files; do
      [ -f "$sf" ] && session_content="${session_content}
$(cat "$sf")"
      task_count=$((task_count + 1))
    done
  fi

  # 回退：从 task logs 提取 summary（sessions/ 不足时补充）
  if [ "$task_count" -lt 5 ] && [ -d "$TASK_LOG_DIR" ]; then
    local summaries
    summaries=$(ls -t "$TASK_LOG_DIR"/task_${agent_id}_*_summary.json 2>/dev/null | head -$((10 - task_count)))
    for sf in $summaries; do
      [ -f "$sf" ] && recent_content="${recent_content}
$(cat "$sf")"
      task_count=$((task_count + 1))
    done
  fi

  # 从 audit.jsonl 提取该 agent 最近 7 天的记录
  local audit_entries=""
  if [ -f "$HUB_DIR/logs/audit.jsonl" ]; then
    local cutoff_date
    cutoff_date=$(date -d '7 days ago' +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
    audit_entries=$(python3 -c "
import json, sys
with open('$HUB_DIR/logs/audit.jsonl', encoding='utf-8', errors='replace') as f:
    for line in f:
        try:
            r = json.loads(line.strip())
            if r.get('agent') == '$agent_id' and r.get('timestamp','') >= '$cutoff_date':
                status = r.get('status','')
                task = r.get('task','')[:60]
                cost = r.get('cost_usd', 0)
                print(f'- {status}: {task} (\${cost:.2f})')
        except: pass
" 2>/dev/null) || audit_entries=""
  fi

  # 从 lessons.md 取最近 7 天的 section
  local recent_lessons=""
  if [ -f "$lessons_file" ]; then
    recent_lessons=$(python3 -c "
import re, sys
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(days=7)
content = open('$lessons_file').read()
sections = re.split(r'(?=^## \d{4}-\d{2}-\d{2})', content, flags=re.MULTILINE)
for s in sections:
    m = re.match(r'## (\d{4}-\d{2}-\d{2})', s)
    if m:
        try:
            d = datetime.strptime(m.group(1), '%Y-%m-%d')
            if d >= cutoff:
                print(s.strip())
        except: pass
" 2>/dev/null) || recent_lessons=""
  fi

  # 从 long_term.md 取最后 30 行作为参考
  local lt_tail=""
  if [ -f "$long_term_file" ]; then
    lt_tail=$(tail -30 "$long_term_file")
  fi

  # 如果没有任何素材，跳过
  if [ -z "$recent_content" ] && [ -z "$audit_entries" ] && [ -z "$recent_lessons" ]; then
    echo "[$agent_id] no recent data for warm.md, skip"
    return
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "[$agent_id] DRY RUN: would generate warm.md from $task_count tasks + audit + lessons"
    return
  fi

  echo "[$agent_id] generating warm.md from $task_count tasks..."

  # 用 LLM 生成摘要（限制 3K tokens ≈ 12K chars）
  local warm_content
  warm_content=$(unset CLAUDECODE 2>/dev/null; claude -p \
    --output-format text \
    --max-budget-usd 0.05 \
    --system-prompt "你是记忆摘要助手。将以下 Agent 最近 7 天的活动数据压缩为一份滚动摘要。

要求：
- 输出不超过 80 行
- 保留：关键决策、发现的问题、解决方案、待跟进事项
- 删除：重复信息、调试过程细节
- 格式：## 最近活动摘要 (生成日期)，然后分类列出
- 用中文" \
    "Agent: $agent_id

最近 session 记录（v1.1 隔离写入）：
$session_content

最近任务执行记录：
$audit_entries

最近经验教训：
$recent_lessons

长期记忆末尾（上下文参考）：
$lt_tail" 2>/dev/null) || warm_content=""

  if [ -n "$warm_content" ] && [ ${#warm_content} -gt 50 ]; then
    # 备份旧版本
    [ -f "$warm_file" ] && cp "$warm_file" "${warm_file}.bak.$(date +%Y%m%d)" 2>/dev/null || true
    echo "$warm_content" > "$warm_file"
    local warm_size
    warm_size=$(stat -c %s "$warm_file")
    echo "[$agent_id] warm.md generated: $(( warm_size / 1024 ))KB"
  else
    echo "[$agent_id] warm.md generation failed or empty output"
  fi

  # v1.1 §5.1: warm→cold 蒸馏（周度执行）
  # 条件：long_term.md 最后修改超过 7 天 + warm.md 存在
  if [ -f "$warm_file" ] && [ -f "$long_term_file" ]; then
    local lt_age
    lt_age=$(( NOW_EPOCH - $(stat -c %Y "$long_term_file") ))
    local lt_lines
    lt_lines=$(wc -l < "$long_term_file")

    if [ "$lt_age" -gt "$SEVEN_DAYS" ] && [ "$lt_lines" -lt 300 ]; then
      echo "[$agent_id] warm→cold distillation candidate (lt_age=${lt_age}s, lt_lines=${lt_lines})"
      if [ "$DRY_RUN" = true ]; then
        echo "[$agent_id] DRY RUN: would distill warm.md highlights into long_term.md"
      else
        # 从 warm.md 提取关键条目追加到 long_term.md
        local distilled
        distilled=$(unset CLAUDECODE 2>/dev/null; claude -p \
          --output-format text \
          --max-budget-usd 0.03 \
          --system-prompt "你是记忆蒸馏助手。从以下 warm memory 中提取值得永久保存的关键教训（不超过 5 条）。跳过临时状态和已过时信息。每条格式：- [日期] 要点。只输出要点列表，无其他内容。" \
          "$(cat "$warm_file")" 2>/dev/null) || distilled=""
        if [ -n "$distilled" ] && [ ${#distilled} -gt 20 ]; then
          {
            echo ""
            echo "## [DISTILLED $(date +%Y-%m-%d)] from warm.md"
            echo "$distilled"
          } >> "$long_term_file"
          echo "[$agent_id] distilled $(echo "$distilled" | wc -l) entries to long_term.md"
        fi
      fi
    fi
  fi

  # 释放 flock
  exec 9>&-
}

# --- 执行 ---
if [ "$AGENT_ID" = "all" ]; then
  for f in "$MEMORY_DIR"/EMP_*/memory/lessons.md; do
    [ -f "$f" ] || continue
    agent=$(basename "$(dirname "$(dirname "$f")")")
    compact_lessons "$f" "$agent"
  done
  # 为所有 active agent 生成 warm.md
  for d in "$MEMORY_DIR"/EMP_*/memory/; do
    [ -d "$d" ] || continue
    agent=$(basename "$(dirname "$d")")
    # 跳过 deprecated agent
    [ "$agent" = "EMP_0007" ] && continue
    score_lesson_quality "$agent"
    generate_warm_memory "$agent"
  done
else
  compact_lessons "$MEMORY_DIR/${AGENT_ID}/memory/lessons.md" "$AGENT_ID"
  score_lesson_quality "$AGENT_ID"
  generate_warm_memory "$AGENT_ID"
fi

# --- Part 5: 归档旧 session 文件（30天+）---
archive_old_sessions() {
  echo ""
  echo "=== SESSION ARCHIVAL ==="

  local archived_total=0
  for d in "$MEMORY_DIR"/EMP_*/memory/sessions/; do
    [ -d "$d" ] || continue
    local agent
    agent=$(basename "$(dirname "$(dirname "$d")")")
    [ "$agent" = "EMP_0007" ] && continue

    local archived=0
    for sf in "$d"session-*.md; do
      [ -f "$sf" ] || continue
      local file_age
      file_age=$(( NOW_EPOCH - $(stat -c %Y "$sf") ))
      if [ "$file_age" -gt "$THIRTY_DAYS" ]; then
        # 提取月份用于归档目录
        local file_month
        file_month=$(stat -c %Y "$sf" | xargs -I{} date -d @{} +%Y-%m 2>/dev/null || date +%Y-%m)
        local archive_dir="$MEMORY_DIR/$agent/memory/archive/$file_month"

        if [ "$DRY_RUN" = true ]; then
          echo "  [$agent] DRY RUN: would archive $(basename "$sf")"
        else
          mkdir -p "$archive_dir"
          mv "$sf" "$archive_dir/"
        fi
        archived=$((archived + 1))
      fi
    done
    [ "$archived" -gt 0 ] && echo "  [$agent] archived $archived session files"
    archived_total=$((archived_total + archived))
  done
  echo "Session archival: $archived_total total"
}

archive_task_logs
archive_old_sessions
compact_audit

# --- Part 6: v2 四管分别压缩（Pipe 2+3）---
echo ""
echo "=== PIPE 2+3 COMPACTION ==="

compact_account_memory() {
  local accounts_dir="$HUB_DIR/accounts"
  [ -d "$accounts_dir" ] || return

  for account_dir in "$accounts_dir"/*/; do
    [ -d "$account_dir" ] || continue
    local account_name
    account_name=$(basename "$account_dir")
    [ "$account_name" = "_test" ] && continue

    # Pipe 2: shared.md (阈值 200 行)
    local shared="$account_dir/shared.md"
    if [ -f "$shared" ]; then
      local lines
      lines=$(wc -l < "$shared")
      if [ "$lines" -gt 200 ]; then
        echo "[$account_name] Pipe 2 shared.md: ${lines} lines (>200 threshold)"
        # 保留前 50 行（核心）+ 最近 100 行
        local temp="/tmp/compact_shared_$$"
        head -50 "$shared" > "$temp"
        echo "" >> "$temp"
        echo "## [COMPACTED $(date +%Y-%m-%d)] 中间 $((lines - 150)) 行已压缩" >> "$temp"
        echo "" >> "$temp"
        tail -100 "$shared" >> "$temp"
        mv "$temp" "$shared"
        echo "[$account_name] Pipe 2 compacted: ${lines} → $(wc -l < "$shared") lines"
      fi
    fi

    # Pipe 3: memory/EMP_*.md (阈值 100 行/agent)
    for pipe3 in "$account_dir"/memory/EMP_*.md; do
      [ -f "$pipe3" ] || continue
      local agent_name
      agent_name=$(basename "$pipe3" .md)
      local lines
      lines=$(wc -l < "$pipe3")
      if [ "$lines" -gt 100 ]; then
        echo "[$account_name] Pipe 3 ${agent_name}: ${lines} lines (>100 threshold)"
        local temp="/tmp/compact_pipe3_$$"
        head -20 "$pipe3" > "$temp"
        echo "" >> "$temp"
        echo "## [COMPACTED $(date +%Y-%m-%d)] 中间 $((lines - 50)) 行已压缩" >> "$temp"
        echo "" >> "$temp"
        tail -30 "$pipe3" >> "$temp"
        mv "$temp" "$pipe3"
        echo "[$account_name] Pipe 3 ${agent_name} compacted: ${lines} → $(wc -l < "$pipe3") lines"
      fi
    done
  done
}

compact_account_memory

echo ""
echo "=== RE-INDEX CHROMADB ==="
"$HOME/mason-hub/.venv/bin/python3" "$HOME/mason-hub/scripts/memory-store.py" --incremental 2>&1 || echo "ChromaDB re-index failed (non-critical)"

echo ""
echo "=== COMPACTION COMPLETE ==="
