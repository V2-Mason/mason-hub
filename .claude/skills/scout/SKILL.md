---
name: scout
description: "技术情报巡逻：搜索 GitHub 趋势、分析技术动态、生成情报简报"
---

# /scout — 技术情报巡逻

执行技术情报搜集，聚焦与 Mason Hub agent 系统相关的技术动态。

## 1. 读取关注列表
```bash
cat ~/mason-hub/intel/watchlist.md
```
从中提取关注的关键词和主题。

## 2. GitHub 搜索
对 watchlist 中的高优先级和中优先级主题，运行 GitHub 搜索：
```bash
bash ~/mason-hub/skills/scout/scout-github.sh "claude code agent"
bash ~/mason-hub/skills/scout/scout-github.sh "MCP server tool"
bash ~/mason-hub/skills/scout/scout-github.sh "AI agent orchestration"
```
（根据 watchlist.md 的实际内容调整搜索词）

## 3. 技术趋势分析
基于你的知识和搜索结果，分析：
- Claude Code 最近有什么更新或新特性？
- MCP 生态有什么新的有用的 server？
- AI agent 编排领域有什么新方案值得关注？
- 有没有与 K-Beauty 跨境电商相关的技术方案？

## 4. 生成情报简报
将结果保存到 intel/digests/ 目录：
```bash
DATE=$(date +%Y-%m-%d)
OUTPUT="$HOME/mason-hub/intel/digests/${DATE}.md"
```

简报格式：
```markdown
# 情报简报 — {日期}

## 🔴 高优发现（需要关注）
- {重要发现，附链接}

## 🟡 值得了解
- {有意思但不紧急的发现}

## 📊 GitHub 趋势
- {相关项目的 star 变化、新 release}

## 💡 建议行动
- {基于情报的具体建议，比如"考虑升级 X"或"关注 Y 项目的 Z 特性"}
```

## 5. 汇报
输出简报的摘要（3-5 行），告诉 Mason 完整简报在哪个文件。

## 注意
- 搜索词要具体，不要太宽泛
- 只报告与 Mason Hub 系统或素仁轩业务相关的发现
- 如果某个搜索没有有价值的结果，跳过不报
- 情报简报是 append-only 的，不修改已有的简报文件
