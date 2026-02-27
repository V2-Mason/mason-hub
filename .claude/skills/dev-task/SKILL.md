# /dev-task — 派活给 Dev Agent

用户会在 /dev-task 后面跟一段任务描述。你需要：

## 1. 解析任务
- 从用户输入中提取任务描述
- 判断涉及的代码仓库（surenxuan 还是 mason-hub）
- 判断任务类型（bug 修复、新功能、重构）

## 2. 创建任务记录
在 tasks/backlog.md 中追加任务（如果还没记录的话）：
```markdown
### TASK-{编号}: {标题}
- **状态:** in-progress
- **优先级:** {P0/P1/P2}
- **类型:** {bug/feature/refactor}
- **描述:** {用户的原始描述}
- **创建时间:** {当前时间}
```

## 3. 启动 Dev Agent
通过 run-agent.sh 启动 EMP_0005 (电商 Dev) 或 EMP_0002 (Platform Dev)：

```bash
cd ~/mason-hub
bash scripts/run-agent.sh EMP_0005 "任务描述"
```

选择哪个 Dev：
- 涉及 surenxuan 代码 → EMP_0005（电商 Dev）
- 涉及 mason-hub 代码 → EMP_0002（Platform Dev）

## 4. 监控和汇报
- run-agent.sh 会自动处理验证循环（最多 3 轮）
- 成功时：更新 backlog.md 状态为 done，汇报改动摘要
- 失败时：run-agent.sh 会自动触发 Escalation 链路
  - Dev 3 轮失败 → PM 评估 → 重新分配（最多 2 次）→ Platform Dev → Mason

## 注意
- 如果 run-agent.sh 不存在或无法执行，告诉用户需要先确认 agent 系统就绪
- 如果任务描述太模糊，先问清楚再启动
- 不要跳过 backlog.md 的记录步骤——这是任务追踪的唯一信息源
