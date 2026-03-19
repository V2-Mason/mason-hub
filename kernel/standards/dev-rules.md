# 开发规范详细版

> CLAUDE.md 里只保留铁律摘要，完整规则在这里。按需读取。

## 反"自我合理化"清单

遇到以下想法时必须停下来：
- "这个太简单了不需要测试" → 简单的代码也会出 bug
- "我很有信心" → 信心不是证据，跑一遍验证
- "就这一次跳过" → 没有例外
- "已经改了代码应该没问题" → 改了 ≠ 对了
- "Linter 过了就行" → Linter 不是编译器也不是测试
- "之前跑过一次了" → 之前 ≠ 现在

## Code Review

- Team agent 写的代码 → 调 code-reviewer agent 做两阶段审查
- 第一阶段：功能是否符合需求（spec review）
- 第二阶段：代码质量（命名/结构/边界处理）
- 配置：`agents/code-reviewer/config.md`

## 设计文档

- 重要架构决策存档到 `docs/plans/YYYY-MM-DD-<topic>.md`
- 包含：背景、方案选择、最终决策、关键约束

## Token 消耗记录

- Claude API 调用经过 `api_logger.log_api_call()` 记录
- 日志：`~/mason-hub/logs/api_usage.jsonl`
- 子进程 agent 通过 `--output-format json` 获取精确 token 数据

## Lesson 详细格式

Gap 类型（强制字段）：
- 🔧 配置错误 → 立刻修
- 🏗️ 系统能力缺失 → 填触发动作，EMP_0012 triage
- 📄 文档更新 → 更新对应文件
- 🔗 集成缺失 → 填触发动作，EMP_0012 triage
- 📚 纯知识 → 留存即可

🏗️ 和 🔗 必须填触发动作（任务描述 + Owner + 验收条件）
