#!/bin/bash
# migrate-memory-v1.1.sh — 一次性迁移脚本
#
# 将现有记忆系统迁移到 v1.1 三温度模型：
#   1. long_term.md → 保持为 cold 层（不动）
#   2. 从最近 task logs 回填 sessions/ 文件
#   3. short_term.json → 标记 deprecated
#   4. lessons.md → 内容不删，新 session 不再往里写
#
# 用法:
#   ./migrate-memory-v1.1.sh              # 执行迁移
#   ./migrate-memory-v1.1.sh --dry-run    # 只检查不执行
#   ./migrate-memory-v1.1.sh --status     # 显示迁移状态

set -euo pipefail

HUB_DIR="$HOME/mason-hub"
AGENTS_DIR="$HUB_DIR/agents"
TASK_LOG_DIR="$HUB_DIR/logs/tasks"
AUDIT_LOG="$HUB_DIR/logs/audit.jsonl"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

if [[ "${1:-}" == "--status" ]]; then
    echo "=== v1.1 迁移状态 ==="
    for d in "$AGENTS_DIR"/EMP_*/memory/; do
        agent=$(basename "$(dirname "$d")")
        [[ "$agent" == "EMP_0007" ]] && continue
        sessions_count=$(ls "$d/sessions/"*.md 2>/dev/null | grep -v .gitkeep | wc -l || echo 0)
        has_warm=$([[ -f "$d/warm.md" ]] && echo "✅" || echo "❌")
        has_deprecated=$([[ -f "$d/short_term.json.deprecated" ]] && echo "✅" || echo "—")
        lt_lines=$(wc -l < "$d/long_term.md" 2>/dev/null || echo 0)
        echo "  $agent: sessions=$sessions_count warm=$has_warm deprecated=$has_deprecated cold=${lt_lines}行"
    done
    exit 0
fi

echo "=== v1.1 MEMORY MIGRATION ==="
echo "Dry run: $DRY_RUN"
echo ""

migrated=0
skipped=0

for d in "$AGENTS_DIR"/EMP_*/memory/; do
    agent=$(basename "$(dirname "$d")")
    [[ "$agent" == "EMP_0007" ]] && continue

    echo "--- $agent ---"

    # 1. sessions/ 目录确保存在
    mkdir -p "$d/sessions"

    # 2. 从 task logs 回填 sessions/
    # 找到该 agent 最近 10 个 summary.json
    summaries=$(ls -t "$TASK_LOG_DIR"/task_${agent}_*_summary.json 2>/dev/null | head -10 || true)
    backfill_count=0

    for sf in $summaries; do
        [[ -f "$sf" ]] || continue
        # 提取 task_id 和时间
        task_id=$(python3 -c "import json; print(json.load(open('$sf')).get('task_id','unknown'))" 2>/dev/null || echo "unknown")
        start_time=$(python3 -c "import json; print(json.load(open('$sf')).get('start_time',''))" 2>/dev/null || echo "")
        end_time=$(python3 -c "import json; print(json.load(open('$sf')).get('end_time',''))" 2>/dev/null || echo "")
        status=$(python3 -c "import json; print(json.load(open('$sf')).get('final_status','completed'))" 2>/dev/null || echo "completed")
        rounds=$(python3 -c "import json; print(json.load(open('$sf')).get('total_rounds',1))" 2>/dev/null || echo "1")

        # 生成 instance_id
        date_part=$(echo "$start_time" | grep -oP '\d{4}-\d{2}-\d{2}' | tr -d '-' || echo "00000000")
        rand_hex=$(echo "$task_id" | md5sum | head -c 8)
        instance_id="session-${date_part}-${agent}-${rand_hex}"
        session_file="$d/sessions/${instance_id}.md"

        # 跳过已存在的
        if [[ -f "$session_file" ]]; then
            continue
        fi

        if $DRY_RUN; then
            echo "  [DRY-RUN] would create $session_file"
            backfill_count=$((backfill_count + 1))
            continue
        fi

        {
            echo "---"
            echo "instance_id: $instance_id"
            echo "role_id: $agent"
            echo "task_id: $task_id"
            echo "status: $status"
            echo "started_at: $start_time"
            echo "ended_at: $end_time"
            echo "rounds: $rounds"
            echo "schema_version: 1"
            echo "source: migration-v1.1"
            echo "---"
            echo ""
            echo "## $(echo "$start_time" | grep -oP '\d{4}-\d{2}-\d{2}' || date +%Y-%m-%d): $task_id"
            echo "- 状态: $status"
            echo "- 来源: 迁移自 task logs"
        } > "$session_file"
        backfill_count=$((backfill_count + 1))
    done

    echo "  sessions 回填: $backfill_count 个"

    # 3. short_term.json → deprecated
    if [[ -f "$d/short_term.json" ]]; then
        if $DRY_RUN; then
            echo "  [DRY-RUN] would rename short_term.json → short_term.json.deprecated"
        else
            mv "$d/short_term.json" "$d/short_term.json.deprecated"
            echo "  short_term.json → deprecated"
        fi
    else
        echo "  short_term.json: 不存在或已处理"
    fi

    # 4. long_term.md 保持不动
    if [[ -f "$d/long_term.md" ]]; then
        lt_lines=$(wc -l < "$d/long_term.md")
        echo "  long_term.md: ${lt_lines} 行（保持为 cold 层，不动）"
    fi

    # 5. lessons.md 保持不动（新 session 不再写入，但历史保留）
    if [[ -f "$d/lessons.md" ]]; then
        ls_lines=$(wc -l < "$d/lessons.md")
        echo "  lessons.md: ${ls_lines} 行（历史保留，新 session 写 sessions/）"
    fi

    migrated=$((migrated + 1))
    echo ""
done

echo "=== 迁移完成: $migrated 个 agent ==="
echo ""
echo "后续步骤："
echo "  1. 运行 compact-memory.sh all 生成 warm.md"
echo "  2. 验证 run-agent.sh 新 session 写入 sessions/"
echo "  3. 下次 dispatcher 运行时观察 session 文件生成"
