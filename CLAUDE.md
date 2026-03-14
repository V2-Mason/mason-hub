# Mason Hub — 工作规范

## 授权边界

- 授权范围内 → 直接做完，commit 记录
- 授权范围外 → 收集所有待决策项，一次性问
- 3 步以上任务 → 先输出执行计划确认单，Mason 说"执行"后再动手

## 开发铁律

1. **完成前必须验证** — 改完代码必须跑验证，禁止"应该没问题"。commit 前至少 `python3 -c "import ast; ast.parse(...)"`
2. **修 bug 先定位根因** — 不允许"先试试"，每次只改一个变量。连续 3 次失败 → 停下来质疑架构
3. **记忆追加不删除** — 新内容加新条目，过时标注 `→ 已更新 (日期)`，Mason 授权才删
4. **收工必须写 Lesson** — session 结束前更新 `agents/EMP_XXXX/memory/`，Gap 类型必填
5. **发现问题走 /solve** — 非 trivial 问题必须走 `/solve` 流程，不能跳步直接执行

## Role 调用规则

- "用 XX 视角分析" → **Lens**：读 config.md，在当前对话切换视角
- `/dev-task`、"派活给 XX" → **Instance**：启动新 session
- Workflow step → **Dialogue**：按 workflow 定义执行

## 执行检查点

- 每完成 3 步暂停汇报（完成了什么、验证结果、下一步、发现的问题）
- Mason 确认后继续

## Backlog

路径: `tasks/backlog.md`（唯一 source of truth）
- 会话开始先读，结束前必须更新（完成标 [x]，新问题加入）

## 按需参考（不要预加载）

| 文件 | 何时读 |
|------|--------|
| `MASON_AUTHORITY.md` | 判断是否在授权范围内时 |
| `SYSTEM_MAP.md` | /standup 或需要了解能力线状态时 |
| `docs/system/org-chart.md` | 需要知道 agent 职责/团队加载规则时 |
| `docs/system/dev-rules.md` | Agent 配置架构（三层分离）、Code Review、反合理化清单 |
| `MASONHUB.md` | Gateway 相关工作时 |
| `data/autonomous_tasks.yaml` | Dispatcher/任务调度相关时 |
| `shared/protocols/` | Escalation、Dev 执行等跨 agent 协议时 |
| `docs/playbooks/` | PM 操作手册时 |

## 快捷命令

`/standup` `/commit` `/deploy` `/health` `/dev-task` `/scout` `/solve`

## 组织架构

16 个 Agent，详见 `docs/system/org-chart.md`（按需读取）。Agent 名册 SSOT: `docs/system/agents.yaml`
