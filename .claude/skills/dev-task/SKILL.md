---
name: dev-task
description: "派活给 Dev Agent：解析任务、选 agent、用 CC Agent tool 启动"
---

# /dev-task — 派活给 Dev Agent

用户会在 /dev-task 后面跟一段任务描述。

## 1. 解析任务
- 从用户输入中提取任务描述
- 判断涉及的领域和代码仓库
- 判断任务类型（bug 修复、新功能、重构）

## 2. 选择 Agent

| 领域 | Agent 定义 | 适用场景 |
|------|-----------|---------|
| mason-hub 基础设施 | `.claude/agents/platform-dev.md` | scripts/、kernel/、hooks、部署 |
| 素仁轩/电商业务 | `.claude/agents/biz-dev.md` | 店铺 API、看板、MediaCrawler 配置 |
| 数据管道 | `.claude/agents/data-engineer.md` | data/、健康检查、SDK、同步 |
| SocialMesh/内容 | `.claude/agents/content-dev.md` | socialmesh/、视频管道、内容工具 |

## 3. 启动 Agent

使用 CC Agent tool，类型为 general-purpose，在 prompt 中注入 agent 定义：

```
Agent tool 调用:
  subagent_type: general-purpose
  prompt: |
    You are the {agent-name} agent for mason-hub.
    Read your agent definition at .claude/agents/{agent-name}.md first, then follow its rules.

    Your task: {用户的任务描述}

    After completing the task:
    1. Verify your changes work (run tests/checks as defined in your agent rules)
    2. Git commit with a clear message
    3. Report what you did, what you changed, and verification results
```

如果任务可能修改多个文件且需要隔离，加 `isolation: "worktree"`。

## 4. 记录和汇报
- 在 tasks/NOW.md 对应优先级下追加任务（如果还没记录）
- Agent 完成后：标记 [x]，汇报改动摘要
- Agent 失败后：保留 [ ]，记录失败原因，问 Mason 下一步

## 注意
- 任务描述太模糊 → 先问清楚再启动
- 不确定选哪个 agent → 问 Mason
- 涉及多个领域 → 拆成多个子任务，每个派给对应 agent