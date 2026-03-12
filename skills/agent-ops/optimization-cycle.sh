#!/bin/bash
# =============================================================================
export PATH="/home/hangn/.local/bin:$PATH"
# 自优化周期 — 每周自动运行
#
# 流程（Mason 修正版顺序）：
#   1. 通过数据中台 SDK 装配数据（Radar + Scout + XHS + TrendRadar）
#   2. Gate 1：数据完整性检查（SDK 内置判定）
#   3. 分析数据 → 生成优化建议
#   4. Gate 2：建议合理性检查（违反规则/超出边界 → 打回重生成，最多 2 次）
#   5. 发 Slack 给 Mason，附：建议 + 数据来源 + Gate 检查结果
#
# 用法：
#   ./optimization-cycle.sh              # 手动运行
#   cron: 0 6 * * 3  (周三 02:00 ET = 06:00 UTC)
#
# 2026-03-12 改造：Step 1 + Gate 1 统一走 data/tools/pipeline.py SDK 接口
#   不再手工 ls -t / cat / SSH 读文件
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HUB_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$HUB_DIR/logs/optimization-cycle.log"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SLACK_CHANNEL="C0AKN4T1JBW"  # #optimization
DATE=$(date +%Y-%m-%d)
REPORT_DIR="$HUB_DIR/intel/optimization-reports"
REPORT_FILE="$REPORT_DIR/$DATE.md"
PYTHON="$HUB_DIR/.venv/bin/python3"

mkdir -p "$REPORT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# Step 1 + Gate 1: 通过数据中台 SDK 装配数据并检查完整性
# =============================================================================
log "=== 自优化周期开始 ==="
log "Step 1: 通过 SDK 装配数据..."

# 调用 assemble-data.py --json 一次性获取所有数据 + Gate 1 判定
ASSEMBLED=$("$PYTHON" "$HUB_DIR/data/pipelines/assemble-data.py" --json 2>/dev/null) || true

if [ -z "$ASSEMBLED" ]; then
    log "ERROR: assemble-data.py 调用失败，fallback 到空数据"
    ASSEMBLED='{"sources":[],"issues":["assemble-data.py 调用失败"],"source_count":0,"issue_count":1,"radar_report":"","scout_digest":"","xhs_briefing":"","trendradar_ok":false,"gate1_pass":false,"gate1_result":"FAIL — assemble-data.py 调用失败"}'
fi

# 从 JSON 提取各字段
_field() {
    echo "$ASSEMBLED" | "$PYTHON" -c "import json,sys; d=json.load(sys.stdin); v=d.get('$1',''); print(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False))" 2>/dev/null || echo ""
}

GATE1_RESULT=$(_field gate1_result)
GATE1_PASS=$(_field gate1_pass)
RADAR_REPORT=$(_field radar_report)
LATEST_DIGEST=$(_field scout_digest)
XHS_BRIEFING=$(_field xhs_briefing)
DATA_SOURCE_COUNT=$(_field source_count)
DATA_ISSUE_COUNT=$(_field issue_count)

# 格式化数据源和问题列表
DATA_SOURCES=$(echo "$ASSEMBLED" | "$PYTHON" -c "
import json,sys
d=json.load(sys.stdin)
for s in d.get('sources',[]): print(f'- {s}')
" 2>/dev/null) || true

DATA_ISSUES=$(echo "$ASSEMBLED" | "$PYTHON" -c "
import json,sys
d=json.load(sys.stdin)
for i in d.get('issues',[]): print(f'- {i}')
" 2>/dev/null) || true

log "  数据源: $DATA_SOURCE_COUNT/4, Gate 1: $GATE1_RESULT"

# Gate 1 失败 → 通知 Mason 并退出
if [ "$GATE1_PASS" = "False" ] || [ "$GATE1_PASS" = "false" ]; then
    log "Gate 1 FAIL — 通知 Mason 并跳过本周"
    FAIL_MSG="⚠️ 自优化周期 — Gate 1 数据检查失败

本周跳过优化建议生成。
原因：$GATE1_RESULT

数据问题：
$DATA_ISSUES

需要检查：cron 任务是否正常运行、阿里云是否可连接"

    "$SLACK_NOTIFY" "$SLACK_CHANNEL" "$FAIL_MSG" "Optimization Bot" ":warning:" 2>/dev/null || true
    log "=== 自优化周期结束（Gate 1 失败）==="
    exit 0
fi

# =============================================================================
# Step 3: 分析 → 生成优化建议
# =============================================================================
log "Step 3: 生成优化建议..."

# 组装数据给 EMP_0008 分析
ANALYSIS_PROMPT="你是 SocialMesh 内容运营总监（EMP_0008），正在执行每周自优化周期。

## 你的任务
基于以下数据，生成 3-5 条可执行的优化建议。

## 规则
- 你只能建议"怎么做"的优化（参数/文案/排程），不能改"做什么"（产品定位/平台优先级）
- 每条建议必须有：问题描述、数据依据、具体行动、预期效果
- 建议必须多维考虑（完播率 × 互动率 × 转化率），不能只优化单一指标
- 反馈是症状不是诊断：先定位根因再给方案
- 参照 shared/qa/optimization_loop.md 的反馈解析规则

## 因果推理要求（必须遵守）
- 区分相关性和因果性：数据显示 A 和 B 共现，不等于 A 导致 B
- 标注幸存者偏差：采集数据只含"被推荐的内容"，失败内容不在样本中，预期效果必须注明置信度
- 考虑混淆变量：比如"含数字标题互动高"可能是因为清单/教程类内容本身互动高，而非数字的功劳
- 预期效果的数字来源：如果来自竞品均值而非自身历史数据，必须标注"基于市场均值推算，置信度中等"
- Owner 只能从 Gate 2 审核时提供的合法 Agent 清单中选择，不要编造不存在的 EMP 编号

## 数据输入

### Radar 关注率
\`\`\`
${RADAR_REPORT:-无数据}
\`\`\`

### Scout 最新情报（摘要）
\`\`\`
$(echo "$LATEST_DIGEST" | head -50)
${LATEST_DIGEST:+...}
${LATEST_DIGEST:-无数据}
\`\`\`

### XHS 策略简报
\`\`\`
$(echo "$XHS_BRIEFING" | head -80)
${XHS_BRIEFING:+...}
${XHS_BRIEFING:-无数据}
\`\`\`

## 输出格式（严格遵守）
用以下 markdown 格式输出，不要加额外的解释：

### 优化建议 1：[标题]
- **问题**：[当前状态，用数据说明]
- **根因**：[为什么会这样]
- **行动**：[具体做什么]
- **预期**：[做了之后期望什么效果]
- **Owner**：[EMP_XXXX]
- **风险**：[可能的副作用]

（重复 3-5 条）

### 数据盲点
- [这些数据没告诉你什么，至少列 2 条]"

# 调用 Claude 生成建议（不走 run-agent.sh，直接用 claude -p 减少开销）
SUGGESTIONS=""
RETRY=0
MAX_RETRY=2

while [ "$RETRY" -lt "$MAX_RETRY" ]; do
    log "  生成建议（第 $((RETRY+1)) 轮）..."
    SUGGESTIONS=$(echo "$ANALYSIS_PROMPT" | claude -p --output-format text 2>/dev/null) || true

    if [ -z "$SUGGESTIONS" ]; then
        log "  Claude 调用失败，重试..."
        RETRY=$((RETRY + 1))
        continue
    fi

    # Gate 2 检查在下一步
    break
done

if [ -z "$SUGGESTIONS" ]; then
    log "生成建议失败（$MAX_RETRY 次重试后），通知 Mason"
    "$SLACK_NOTIFY" "$SLACK_CHANNEL" "⚠️ 自优化周期 — 建议生成失败（Claude 调用 $MAX_RETRY 次均失败）" "Optimization Bot" ":warning:" 2>/dev/null || true
    exit 0
fi

# =============================================================================
# Step 4: Gate 2 — 建议合理性检查
# =============================================================================
log "Step 4: Gate 2 建议合理性检查..."

# 动态获取 backlog 待办数量
BACKLOG_SUMMARY=""
if [ -f "$HUB_DIR/tasks/backlog.md" ]; then
    OPEN_TASKS=$(grep -c '^\- \[ \]' "$HUB_DIR/tasks/backlog.md" || true)
    BACKLOG_SUMMARY="当前 backlog 有 ${OPEN_TASKS} 个未完成任务。新建议要考虑执行容量，避免积压。"
fi

# 动态读取合法 Agent 清单（Single Source of Truth: docs/system/agents.yaml）
AGENTS_YAML="$HUB_DIR/docs/system/agents.yaml"
AGENT_ROSTER=""
if [ -f "$AGENTS_YAML" ]; then
    # 提取 status=active 且 can_own_tasks=true 的 agent 作为合法 Owner
    AGENT_ROSTER=$("$HUB_DIR/.venv/bin/python3" -c "
import yaml, sys
with open('$AGENTS_YAML') as f:
    data = yaml.safe_load(f)
active = []
deprecated = []
non_owners = []
for a in data.get('agents', []):
    if a['status'] == 'deprecated':
        deprecated.append(f\"- ~~{a['id']} {a['name']}~~ — 已废弃（{a.get('deprecated_reason', '')}）\")
    elif a.get('can_own_tasks'):
        active.append(f\"- {a['id']} {a['name']} — {a['role']}\")
    else:
        non_owners.append(f\"- {a['id']} {a['name']} — {a['role']}（不可作为 Owner）\")
print('### 可作为 Owner 的 Agent')
print('\n'.join(active))
print()
print('### 非执行角色（不可作为 Owner）')
print('\n'.join(non_owners))
if deprecated:
    print()
    print('### 已废弃（历史记录）')
    print('\n'.join(deprecated))
" 2>/dev/null) || true
fi

if [ -z "$AGENT_ROSTER" ]; then
    log "  WARN: 无法读取 agents.yaml，使用硬编码 fallback"
    AGENT_ROSTER="### 可作为 Owner 的 Agent
- EMP_0002 Platform Dev — 平台基础设施开发（mason-hub 专属）
- EMP_0004 SRE — 全局基础设施运维
- EMP_0008 SocialMesh 内容运营总监 — 内容策略 + 排程 + 复盘
- EMP_0009 Content-Tech Dev — 内容技术开发（socialmesh 专属）
- EMP_0010 Content Creator — 内容生产 + 社区互动
- EMP_0013 店铺运营 — XHS 店铺日常运营"
fi

GATE2_PROMPT="你是质量审核员。检查以下优化建议是否合理。

## 系统上下文（审查时必须参考）

### 合法 Agent 清单（Owner 只能从这里选）
$AGENT_ROSTER

### 本次建议的数据来源限制
- 所有 XHS 互动数据来自竞品采集（搜索 API），不含素仁轩自身账号数据
- 采集样本只含"被推荐的内容"——失败帖子不在样本中（幸存者偏差）
- 趋势数据如果两期相同，可能是采集缓存重复，"趋势"结论的置信度应降低
- 视频 vs 图文的互动差距中，制作成本维度缺失

### 执行容量
$BACKLOG_SUMMARY

## 硬性检查项（任何一条 FAIL → 整体 FAIL）
1. **Owner 合法性**：Owner 必须在上方合法 Agent 清单中。不存在的 EMP 编号 = 立即 FAIL
2. **越界检查**：改产品定位/平台优先级/品牌调性 = 越界 FAIL
3. **数据盲点声明**：必须有，且不能为空话套话

## 软性检查项（标注警告，不一定 FAIL）
4. 每条建议是否有数据依据（不能凭空建议）
5. 是否有单指标优化风险（只看完播率而忽略互动 = 有风险）
6. **幸存者偏差**：如果建议的数据依据来自竞品采集，预期效果是否标注了置信度？未标注 → 警告
7. **因果 vs 相关**：建议是否把相关性当因果（如"含数字标题互动高"→"用数字就能提高互动"）？有此问题 → 警告
8. **执行可行性**：建议的行动是否超出 Owner 的能力范围？当前 backlog 是否能承受新增任务？

## 待审核的建议
$SUGGESTIONS

## 输出格式
逐条给出 PASS / FAIL / WARN + 原因。
最后给总结论：PASS（可以发给 Mason）或 FAIL（需要修改）+ 原因。
如果有 WARN，在总结论中列出所有警告供 Mason 参考。
如果 FAIL，列出具体哪条建议有什么问题。"

GATE2_RESULT=$(echo "$GATE2_PROMPT" | claude -p --output-format text 2>/dev/null) || true
GATE2_PASS=true

if echo "$GATE2_RESULT" | grep -qi "总.*结论.*FAIL\|FAIL.*需要修改"; then
    GATE2_PASS=false
    log "  Gate 2 第 1 轮 FAIL，尝试修正..."

    # 第 2 轮：让 Claude 基于 Gate 2 反馈修正建议
    FIX_PROMPT="你是 SocialMesh 内容运营总监。你的优化建议被 Gate 2 审核打回了。

## Gate 2 审核反馈
$GATE2_RESULT

## 原始建议
$SUGGESTIONS

## 要求
根据审核反馈修正建议。删掉越界的建议，补充缺失的数据依据，修正 Owner。
输出修正后的完整建议（格式同之前）。"

    SUGGESTIONS_V2=$(echo "$FIX_PROMPT" | claude -p --output-format text 2>/dev/null) || true
    if [ -n "$SUGGESTIONS_V2" ]; then
        SUGGESTIONS="$SUGGESTIONS_V2"
        GATE2_PASS=true
        GATE2_RESULT="PASS（第 2 轮修正后通过）"
        log "  Gate 2 第 2 轮 PASS"
    else
        log "  Gate 2 第 2 轮修正失败"
        GATE2_RESULT="FAIL（2 轮均未通过）— $GATE2_RESULT"
    fi
else
    GATE2_RESULT="PASS（第 1 轮通过）"
    log "  Gate 2 PASS"
fi

# =============================================================================
# Step 5: 打包结果 + 发 Slack
# =============================================================================
log "Step 5: 打包结果..."

# 保存完整报告到文件
cat > "$REPORT_FILE" << REPORT_EOF
# 自优化周期报告 — $DATE

## Gate 检查结果
- **Gate 1（数据完整性）**：$GATE1_RESULT
- **Gate 2（建议合理性）**：$GATE2_RESULT

## 数据来源
$(echo -e "$DATA_SOURCES")

## 数据问题
$(echo -e "${DATA_ISSUES:-无}")

## 优化建议
$SUGGESTIONS

---
*自动生成于 $(TZ='America/New_York' date '+%Y-%m-%d %H:%M ET')，等待 Mason Gate 3 确认*
REPORT_EOF

log "  报告已保存: $REPORT_FILE"

# 上传到 Google Drive
log "  上传到 Google Drive..."
DRIVE_RESULT=$("$HUB_DIR/.venv/bin/python3" "$HUB_DIR/skills/analysis/gdrive_upload_report.py" "$REPORT_FILE" 2>/dev/null) || true
DRIVE_LINK=$(echo "$DRIVE_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('link',''))" 2>/dev/null) || true

if [ -n "$DRIVE_LINK" ]; then
    log "  Drive 上传成功: $DRIVE_LINK"
    REPORT_LINK="$DRIVE_LINK"
else
    log "  Drive 上传失败，使用本地路径"
    REPORT_LINK="intel/optimization-reports/$DATE.md"
fi

# 构建 Slack 消息（精简版，完整版在 Drive）
SUGGESTION_SUMMARY=$(echo "$SUGGESTIONS" | grep -E "^### 优化建议" | head -5)
SUGGESTION_COUNT=$(echo "$SUGGESTION_SUMMARY" | grep -c "优化建议" || true)

if [ "$GATE2_PASS" = true ]; then
    SLACK_MSG="📊 自优化周期 — $DATE

Gate 1（数据）：$GATE1_RESULT
Gate 2（合理性）：$GATE2_RESULT

本周 ${SUGGESTION_COUNT} 条优化建议：
$(echo "$SUGGESTION_SUMMARY" | sed 's/### /• /g')

完整报告：$REPORT_LINK
请确认是否执行 ✅ / 跳过 ⏭️ / 需要讨论 💬"
else
    SLACK_MSG="⚠️ 自优化周期 — $DATE

Gate 1（数据）：$GATE1_RESULT
Gate 2（合理性）：$GATE2_RESULT

本周建议未通过 Gate 2 审核，已跳过。
详见：$REPORT_LINK"
fi

"$SLACK_NOTIFY" "$SLACK_CHANNEL" "$SLACK_MSG" "Optimization Bot" ":gear:" 2>/dev/null || true
log "  Slack 通知已发送"

log "=== 自优化周期结束 ==="

# 发射事件: 自优化周期完成
"$HUB_DIR/scripts/emit_event.sh" "optimization-cycle-complete" "optimization-cycle.sh" "ok" 1 \
  "{\"gate1\":\"$GATE1_PASS\",\"gate2\":\"$GATE2_PASS\",\"suggestions\":$SUGGESTION_COUNT}" 2>/dev/null || true
