#!/bin/bash
# PostToolUse Hook: 文件格式校验
# 写完文件后自动检查 JSON/YAML/Python/Shell 语法
# 不阻断执行（PostToolUse 无法阻断），但把错误信息反馈给 Claude 让它修复
#
# 输入：stdin JSON（tool_name, tool_input）
# 输出：stdout 错误信息（Claude 会看到）

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

# 只处理 Write 和 Edit
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" ]]; then
  exit 0
fi

# 提取文件路径
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ti.get('path', '')))
" 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]] || [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"
ERROR=""

case "$EXT" in
  json)
    ERROR=$(python3 -c "import json; json.load(open('$FILE_PATH'))" 2>&1) || true
    if [[ -n "$ERROR" ]]; then
      echo "⚠️ JSON 语法错误 ($FILE_PATH): $ERROR"
    fi
    ;;
  yaml|yml)
    ERROR=$(python3 -c "import yaml; yaml.safe_load(open('$FILE_PATH'))" 2>&1) || true
    if [[ -n "$ERROR" ]]; then
      echo "⚠️ YAML 语法错误 ($FILE_PATH): $ERROR"
    fi
    ;;
  py)
    ERROR=$(python3 -c "import ast; ast.parse(open('$FILE_PATH').read())" 2>&1) || true
    if [[ -n "$ERROR" ]]; then
      echo "⚠️ Python 语法错误 ($FILE_PATH): $ERROR"
    fi
    ;;
  sh|bash)
    ERROR=$(bash -n "$FILE_PATH" 2>&1) || true
    if [[ -n "$ERROR" ]]; then
      echo "⚠️ Shell 语法错误 ($FILE_PATH): $ERROR"
    fi
    ;;
esac

exit 0
