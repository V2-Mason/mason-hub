#!/bin/bash
# =============================================================================
# 自优化周期 — 每周自动运行
#
# 流程（Mason 修正版顺序）：
#   1. 读数据（Radar 关注率 + Scout 情报 + XHS 互动数据）
#   2. Gate 1：数据完整性检查（缺失/异常 → 告知 Mason，本周跳过）
#   3. 分析数据 → 生成优化建议
#   4. Gate 2：建议合理性检查（违反规则/超出边界 → 打回重生成，最多 2 次）
#   5. 发 Slack 给 Mason，附：建议 + 数据来源 + Gate 检查结果
#
# 用法：
#   ./optimization-cycle.sh              # 手动运行
#   cron: 0 6 * * 3  (周三 14:00 CST = 06:00 UTC)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HUB_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$HUB_DIR/logs/optimization-cycle.log"
SLACK_NOTIFY="/home/hangn/slack-bot/slack_notify.sh"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh
DATE=$(date +%Y-%m-%d)
REPORT_DIR="$HUB_DIR/intel/optimization-reports"
REPORT_FILE="$REPORT_DIR/$DATE.md"

mkdir -p "$REPORT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# Step 1: 读数据
# =============================================================================
log "=== 自优化周期开始 ==="

DATA_ISSUES=""
DATA_SOURCES=""

# 1a. Radar 关注率
log "Step 1a: 读取 Radar 关注率..."
RADAR_REPORT=""
if [ -f "$HUB_DIR/tools/radar-tracker/tracker.db" ]; then
    RADAR_REPORT=$("$HUB_DIR/.venv/bin/python3" "$HUB_DIR/tools/radar-tracker/weekly_report.py" --weeks 2 2>&1) || true
    if [ -n "$RADAR_REPORT" ]; then
        DATA_SOURCES="$DATA_SOURCES\n- Radar 关注率周报 ✅"
        log "  Radar 数据获取成功"
    else
        DATA_ISSUES="$DATA_ISSUES\n- Radar 周报为空（可能 dismiss 数据不足）"
        log "  Radar 数据为空"
    fi
else
    DATA_ISSUES="$DATA_ISSUES\n- tracker.db 不存在，无 Radar 数据"
    log "  tracker.db 不存在"
fi

# 1b. Scout 最新情报
log "Step 1b: 读取 Scout 最新情报..."
LATEST_DIGEST=""
DIGEST_DIR="$HUB_DIR/intel/digests"
if [ -d "$DIGEST_DIR" ]; then
    LATEST_DIGEST_FILE=$(ls -t "$DIGEST_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_DIGEST_FILE" ]; then
        DIGEST_AGE_DAYS=$(( ($(date +%s) - $(stat -c %Y "$LATEST_DIGEST_FILE")) / 86400 ))
        if [ "$DIGEST_AGE_DAYS" -le 14 ]; then
            LATEST_DIGEST=$(head -100 "$LATEST_DIGEST_FILE")
            DATA_SOURCES="$DATA_SOURCES\n- Scout 情报简报 ✅ ($(basename "$LATEST_DIGEST_FILE"), ${DIGEST_AGE_DAYS}天前)"
            log "  Scout 情报获取成功: $(basename "$LATEST_DIGEST_FILE")"
        else
            DATA_ISSUES="$DATA_ISSUES\n- Scout 最新情报已过期（${DIGEST_AGE_DAYS}天前），数据时效性低"
            log "  Scout 情报过期: ${DIGEST_AGE_DAYS}天"
        fi
    else
        DATA_ISSUES="$DATA_ISSUES\n- 无 Scout 情报简报文件"
    fi
else
    DATA_ISSUES="$DATA_ISSUES\n- intel/digests/ 目录不存在"
fi

# 1c. XHS 最新分析/策略简报
log "Step 1c: 读取 XHS 互动数据..."
XHS_BRIEFING=""
# 尝试从阿里云获取最新简报
XHS_BRIEFING_FILE=$(ssh -o ConnectTimeout=5 root@106.14.44.68 \
    "ls -t /opt/mediacrawler/analysis/briefings/*.json 2>/dev/null | head -1" 2>/dev/null) || true
if [ -n "$XHS_BRIEFING_FILE" ]; then
    XHS_BRIEFING=$(ssh root@106.14.44.68 "cat '$XHS_BRIEFING_FILE'" 2>/dev/null) || true
    if [ -n "$XHS_BRIEFING" ]; then
        DATA_SOURCES="$DATA_SOURCES\n- XHS 策略简报 ✅ ($(basename "$XHS_BRIEFING_FILE"))"
        log "  XHS 简报获取成功: $(basename "$XHS_BRIEFING_FILE")"
    else
        DATA_ISSUES="$DATA_ISSUES\n- XHS 简报文件存在但读取失败"
    fi
else
    DATA_ISSUES="$DATA_ISSUES\n- 阿里云无 XHS 策略简报（可能采集未运行或连接失败）"
    log "  XHS 简报获取失败（阿里云连接或文件不存在）"
fi

# 1d. TrendRadar 最新数据
log "Step 1d: 读取 TrendRadar 数据..."
TR_REPORT="$HUB_DIR/tools/trendradar/output/index.html"
if [ -f "$TR_REPORT" ]; then
    TR_AGE_HOURS=$(( ($(date +%s) - $(stat -c %Y "$TR_REPORT")) / 3600 ))
    if [ "$TR_AGE_HOURS" -le 24 ]; then
        DATA_SOURCES="$DATA_SOURCES\n- TrendRadar 热榜 ✅ (${TR_AGE_HOURS}h 前更新)"
        log "  TrendRadar 数据正常: ${TR_AGE_HOURS}h 前"
    else
        DATA_ISSUES="$DATA_ISSUES\n- TrendRadar 数据陈旧（${TR_AGE_HOURS}h 未更新，cron 可能停了）"
        log "  TrendRadar 数据陈旧: ${TR_AGE_HOURS}h"
    fi
else
    DATA_ISSUES="$DATA_ISSUES\n- TrendRadar 输出文件不存在"
fi

# =============================================================================
# Step 2: Gate 1 — 数据完整性检查
# =============================================================================
log "Step 2: Gate 1 数据完整性检查..."

GATE1_PASS=true
GATE1_RESULT=""
DATA_SOURCE_COUNT=$(echo -e "$DATA_SOURCES" | grep -c "✅" || true)
DATA_ISSUE_COUNT=$(echo -e "$DATA_ISSUES" | grep -c "^-" || true)

if [ "$DATA_SOURCE_COUNT" -eq 0 ]; then
    GATE1_PASS=false
    GATE1_RESULT="FAIL — 没有任何数据源可用，无法生成优化建议"
    log "  Gate 1 FAIL: 无可用数据源"
elif [ "$DATA_SOURCE_COUNT" -lt 2 ]; then
    GATE1_RESULT="WARN — 仅 ${DATA_SOURCE_COUNT}/4 个数据源可用，建议质量有限"
    log "  Gate 1 WARN: 仅 ${DATA_SOURCE_COUNT} 个数据源"
else
    GATE1_RESULT="PASS — ${DATA_SOURCE_COUNT}/4 个数据源可用"
    log "  Gate 1 PASS: ${DATA_SOURCE_COUNT} 个数据源"
fi

# Gate 1 失败 → 通知 Mason 并退出
if [ "$GATE1_PASS" = false ]; then
    log "Gate 1 FAIL — 通知 Mason 并跳过本周"
    FAIL_MSG="⚠️ 自优化周期 — Gate 1 数据检查失败

本周跳过优化建议生成。
原因：$GATE1_RESULT

数据问题：$(echo -e "$DATA_ISSUES")

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

GATE2_PROMPT="你是质量审核员。检查以下优化建议是否合理。

## 检查项（逐条过）
1. 每条建议是否有数据依据（不能凭空建议）
2. 是否有越界建议（改产品定位/平台优先级/品牌调性 = 越界）
3. 是否有单指标优化风险（只看完播率而忽略互动 = 有风险）
4. Owner 是否合理（EMP_0002 不做内容，EMP_0010 不做代码）
5. 是否有数据盲点声明

## 待审核的建议
$SUGGESTIONS

## 输出格式
逐条给出 PASS 或 FAIL + 原因。最后给总结论：PASS（可以发给 Mason）或 FAIL（需要修改）+ 原因。
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
*自动生成于 $(date '+%Y-%m-%d %H:%M CST')，等待 Mason Gate 3 确认*
REPORT_EOF

log "  报告已保存: $REPORT_FILE"

# 构建 Slack 消息（精简版，完整版在文件里）
SUGGESTION_SUMMARY=$(echo "$SUGGESTIONS" | grep -E "^### 优化建议" | head -5)
SUGGESTION_COUNT=$(echo "$SUGGESTION_SUMMARY" | grep -c "优化建议" || true)

if [ "$GATE2_PASS" = true ]; then
    SLACK_MSG="📊 自优化周期 — $DATE

Gate 1（数据）：$GATE1_RESULT
Gate 2（合理性）：$GATE2_RESULT

本周 ${SUGGESTION_COUNT} 条优化建议：
$(echo "$SUGGESTION_SUMMARY" | sed 's/### /• /g')

完整报告：intel/optimization-reports/$DATE.md
请确认是否执行 ✅ / 跳过 ⏭️ / 需要讨论 💬"
else
    SLACK_MSG="⚠️ 自优化周期 — $DATE

Gate 1（数据）：$GATE1_RESULT
Gate 2（合理性）：$GATE2_RESULT

本周建议未通过 Gate 2 审核，已跳过。
详见：intel/optimization-reports/$DATE.md"
fi

"$SLACK_NOTIFY" "$SLACK_CHANNEL" "$SLACK_MSG" "Optimization Bot" ":gear:" 2>/dev/null || true
log "  Slack 通知已发送"

log "=== 自优化周期结束 ==="
