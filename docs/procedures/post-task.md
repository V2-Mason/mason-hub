# 收工流程（所有 agent 必须遵守）

> 此文件是 single source of truth。交互式 /commit skill 和自动 claude -p 都遵循此流程。

任务完成后，**必须**按顺序执行以下步骤。缺一不可，不执行视为任务未完成。

## 1. 写 Lesson

写入 `agents/{你的agent_id}/memory/long_term.md`，使用以下格式：

```
## YYYY-MM-DD: <模块名>
- 做了什么
- 发现了什么 / 踩了什么坑
- Gap 分类（必选一个）：
  - 🔧 配置错误 → 已修
  - 🏗️ 系统能力缺失 → 触发动作: <描述>
  - 📄 文档更新 → 已更新 <文件>
  - 🔗 集成缺失 → 触发动作: <描述>
  - 📚 纯知识 → 留存
```

如果你不知道自己的 agent_id，用任务中指定的 agent 或默认 EMP_0002。

## 2. 更新 Backlog

编辑 `tasks/backlog.md`：
- 完成的任务 → 标记 `[x]` 并注明日期
- 新发现的问题 → 添加到对应优先级
- 过时的任务描述 → 标注更新

## 3. Git Commit

```bash
git add agents/*/memory/ tasks/backlog.md <你修改的文件>
# 不要 add: logs/, .env, *.db, data/gateway-memory.jsonl
git commit -m "<一句话总结变更>"
```

## 注意事项

- 即使任务失败也要写 lesson（记录失败原因和尝试过的方案）
- lesson 控制在 5-15 行
- commit message 用中文
- 不要 push（自动任务不推代码）
