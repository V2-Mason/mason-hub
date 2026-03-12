# 启动流程协议（跨 Agent 共享）

本文件定义有状态 Agent 的标准启动流程。
run-agent.sh 已自动处理记忆注入和上下文加载，本文件供 agent 在 session 内按需参考。

> **注意**：run-agent.sh 已自动注入 lessons 和 knowledge_base。
> 以下步骤是 agent 在 session 开始后的补充行为，不要重复加载已注入的内容。

## Step 1：加载项目上下文

读取你的 domain 下的项目文件（具体路径见你的 config.md）：
1. `knowledge_base.md` — 业务判断框架（如已被 run-agent.sh 注入则跳过）
2. `context.json` — 项目当前状态
3. `task_list.json` — 待办/进行中/已完成任务
4. `decisions.md` — 历史决策记录

## Step 2：评估当前任务状态

读完后内部评估（不需要输出）：
- 当前有几个 pending 任务？优先级如何？
- 有没有 in_progress 的任务？是不是中断恢复场景？
- 最近的 decisions.md 里有没有影响当前任务的新决策？

## Step 3：中断恢复检查

如果发现 task_list.json 中有状态为 in_progress 的任务：
1. 这是上次中断的未完成任务
2. 检查该任务对应的文件是否有部分修改（通过 git status 或文件时间戳）
3. 评估：是从头重做还是接续完成
4. 如果子任务是原子性的（应该是），重新分配给 Dev 即可

## 记忆写入时机

- **长期记忆**：每完成 5 个任务或每周一次做记忆压缩时，从 audit.jsonl 和 completed_tasks 中提取经验写入 `long_term.md`
- **短期记忆**：session 异常退出时可选写入 `short_term.json`，正常完成不写
