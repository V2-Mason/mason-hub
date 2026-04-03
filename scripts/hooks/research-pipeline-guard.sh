#!/bin/bash
# research-pipeline-guard.sh
# UserPromptSubmit hook: 当 Mason 说"执行"且上下文是调研时，
# 注入 system message 强制 Claude 按 6 步跑完不停顿。

# 读 stdin JSON
INPUT=$(cat)

# 提取用户消息
USER_MSG=$(echo "$INPUT" | jq -r '.user_prompt // .message // ""' 2>/dev/null)

# 检测是否是调研执行指令
if echo "$USER_MSG" | grep -qiE '执行|按这个跑|全跑|开始调研|run research|execute'; then
  # 注入流程提醒
  cat <<'HOOKJSON'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "【调研管线自动执行模式已激活】你正在执行 /research 调研管线。必须按以下顺序连续完成所有步骤，不停顿、不问 Mason、不跳步：\n\nStep A: /research-keywords → 关键词池 + 搜索量验证\nStep B: /research-collect → 多平台原始数据采集（不合成指标）\nStep C: /research-score Step 1 → 原始字段提取 + trimmed mean\nStep D: /research-score Step 2 → statsmodels 维度验证（VIF+CV）\nStep E: /research-score Step 3 → pymoo Pareto 排名\nStep F: /research-score Step 4 → 代理指标抽检（Top 3 各看 5 条）\nStep G: /research-score Step 5 → SHAP 归因解释（严谨精度时）\nStep H: 归档 GCS + 更新 INDEX.md\n\n完成后一次性输出完整调研报告。中间步骤日志附在报告末尾。遇到障碍自动降级，不停顿。"
  }
}
HOOKJSON
fi
