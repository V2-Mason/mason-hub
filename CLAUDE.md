# Mason Hub — 工作规范

> 系统当前运行状态、能力线、推荐行动：见 SYSTEM_MAP.md
> 本文件只包含开发规范和项目结构说明

> 通用开发规范见 ~/CLAUDE.md

## mason-hub 专属规则

### 授权边界

- 授权范围内 → 直接做完，commit 记录
- 授权范围外 → 收集所有待决策项，一次性问

### 开发铁律（mason-hub 补充）

4. 收工必须写 Lesson — session 结束前更新 agents/EMP_XXXX/memory/，Gap 类型必填
5. 发现问题走 /solve — 非 trivial 问题必须走 /solve 流程，不能跳步直接执行

### Role 调用规则

- "用 XX 视角分析" → Lens：读 config.md，在当前对话切换视角
- /dev-task、"派活给 XX" → Instance：启动新 session
- Workflow step → Dialogue：按 workflow 定义执行

### 执行检查点

- 每完成 3 步暂停汇报（完成了什么、验证结果、下一步、发现的问题）
- Mason 确认后继续

### Backlog

当前待办: tasks/NOW.md（每次 session 必读，控制在 150 行以内）
完整历史: tasks/backlog.md（按需读取，需要全局视图时才读）
收工流程：把当前 session 的完成项标 [x] 到 backlog.md，
         然后重新生成 NOW.md 只保留 [ ] 待办项

### 按需参考（不要预加载）

| 文件 | 何时读 |
|------|--------|
| MASON_AUTHORITY.md | 判断是否在授权范围内时 |
| SYSTEM_MAP.md | /standup 或需要了解能力线状态时 |
| docs/system/org-chart.md | 需要知道 agent 职责/团队加载规则时 |
| docs/system/dev-rules.md | Agent 配置架构、Code Review、反合理化清单 |
| MASONHUB.md | Gateway 相关工作时 |
| data/autonomous_tasks.yaml | Dispatcher/任务调度相关时 |
| shared/protocols/ | Escalation、Dev 执行等跨 agent 协议时 |
| docs/playbooks/ | PM 操作手册时 |

### 快捷命令

/standup /commit /deploy /health /dev-task /scout /solve

### 组织架构

16 个 Agent，详见 docs/system/org-chart.md。Agent 名册 SSOT: docs/system/agents.yaml
