#!/bin/bash
# PreToolUse Hook: 硬红线拦截
# 拦截所有 agent 都不该做的危险操作
# exit 2 = 阻断执行，stderr 信息会展示给 Claude
#
# Layer 2: 不需要身份识别，任何 agent 都适用
# 误拦率极低，自动执行安全

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

# === Bash 命令红线 ===
if [[ "$TOOL_NAME" == "Bash" ]]; then
  COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

  # 提取实际命令部分（去掉 heredoc/引号内的文本，只看命令结构）
  # git commit -m "..." / echo "..." / cat <<EOF 这些的引号内容不应被扫描
  COMMAND_CORE=$(echo "$COMMAND" | python3 -c "
import sys, re
cmd = sys.stdin.read()
# 跳过 git commit（消息体可能包含任何文本）
if re.match(r'^\s*(cd\s+\S+\s*&&\s*)?git\s+commit\b', cmd):
    sys.exit(0)
# 跳过 echo/printf（输出文本不是命令）
if re.match(r'^\s*echo\s', cmd):
    sys.exit(0)
# 去掉 heredoc 内容
cmd = re.sub(r\"<<'?EOF'?.*?EOF\", '', cmd, flags=re.DOTALL)
# 去掉双引号内的内容（保守：只去掉 \$(cat <<...EOF) 格式）
cmd = re.sub(r'\\\$\(cat\s+<<.*?\)', '', cmd, flags=re.DOTALL)
print(cmd)
" 2>/dev/null) || COMMAND_CORE=""

  # 如果 python 退出 0 但无输出（git commit 等安全命令），跳过检查
  if [[ -n "$COMMAND_CORE" ]]; then
    # 硬拦截：破坏性操作
    if echo "$COMMAND_CORE" | grep -qE '(rm\s+-rf\s+[/~]|rm\s+-rf\s+\.\s|git\s+push\s+--force|git\s+push\s+-f\b|git\s+reset\s+--hard|DROP\s+TABLE|DROP\s+DATABASE|mkfs\.|dd\s+if=.*of=/dev/)'; then
      echo "🚫 硬红线：检测到破坏性命令，已拦截" >&2
      echo "命令: $COMMAND" >&2
      exit 2
    fi

    # 硬拦截：敏感文件操作
    if echo "$COMMAND_CORE" | grep -qE '(cat\s+.*\.env\b|cat\s+.*credentials|cat\s+.*secret|curl.*\.env)'; then
      echo "🚫 硬红线：检测到敏感文件读取，已拦截" >&2
      exit 2
    fi
  fi
fi

# === Write/Edit 敏感文件红线 ===
if [[ "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "Edit" ]]; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ti.get('path', '')))
" 2>/dev/null || echo "")

  # 硬拦截：不允许写 .env / credentials / 密钥文件
  if echo "$FILE_PATH" | grep -qE '(\.env$|credentials\.json|\.pem$|\.key$|id_rsa)'; then
    echo "🚫 硬红线：不允许写入敏感文件 ($FILE_PATH)" >&2
    exit 2
  fi
fi

# 通过 — 返回 allow（JSON 格式让 Claude Code 解析）
echo '{}'
exit 0
