---
name: pattern-extract
description: 跨任务规律提炼 — 从审计日志和 agent 记忆中自动识别重复模式、失败规律、成功因子。五维 Gap #5 学习-模式识别。
user_invocable: false
---

# pattern-extract — 跨任务模式提炼

> **触发时机**：/standup 聚合、周报生成、PM 分析失败趋势、手动调用
> **类型**：Stateless 分析工具，无副作用

## 用法

```bash
# 全量分析（近 7 天）
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py

# 指定天数
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py --days 14

# 只分析特定 agent
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py --agent EMP_0002

# JSON 输出（供下游消费）
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py --format json

# 只跑某个分析器
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py --analyzer failure
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py --analyzer efficiency
python3 ~/mason-hub/.claude/skills/pattern-extract/pattern-extract.py --analyzer lesson
```

## 输出

脚本输出 3 类模式：

1. **Failure Patterns** — 重复失败的错误类型、agent、任务类型聚类
2. **Efficiency Patterns** — 成本/时长异常、token 使用趋势、成功率变化
3. **Lesson Patterns** — agent 记忆中的重复主题、Gap 类型分布、知识覆盖盲区

## 下游集成

- `/standup` 可调用获取趋势摘要
- `dispatcher.sh` 可读 JSON 输出调整任务分配
- PM 可用于周报素材
