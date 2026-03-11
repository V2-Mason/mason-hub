# Mason Hub — 工作规范

## 授权边界

**必须在 session 启动时读取 `MASON_AUTHORITY.md` + `SYSTEM_MAP.md`**
- 授权范围内 → 直接做完，commit 记录
- 授权范围外 → 收集所有待决策项，一次性问
- 3 步以上任务 → 先输出执行计划确认单，Mason 说"执行"后再动手

## 基础设施

| 环境 | 地址 | 用途 |
|------|------|------|
| GCP | 34.63.188.198 | 指挥中心，mason-hub + surenxuan 开发 |
| 阿里云 | 106.14.44.68 | 生产环境，surenxuan FastAPI |
| 部署 | `skills/deploy/deploy-to-aliyun.sh --git` | SSH deploy key，venv 必须 |

## 快捷命令

`/standup` 晨会 | `/commit` 智能提交 | `/deploy` 部署 | `/health` 健康检查 | `/dev-task` 派活 | `/scout` 情报

## 开发铁律

1. **完成前必须验证** — 改完代码必须跑验证，禁止"应该没问题"。commit 前至少 `python3 -c "import ast; ast.parse(...)"`
2. **修 bug 先定位根因** — 不允许"先试试"，每次只改一个变量。连续 3 次失败 → 停下来质疑架构
3. **记忆追加不删除** — 新内容加新条目，过时标注 `→ 已更新 (日期)`，Mason 授权才删
4. **收工必须写 Lesson** — session 结束前更新 `agents/EMP_XXXX/memory/`，格式参照 `shared/templates/lesson_format.md`，Gap 类型必填

## 执行检查点

- 每完成 3 步暂停汇报（完成了什么、验证结果、下一步、发现的问题）
- Mason 确认后继续

## Backlog

路径: `tasks/backlog.md`（唯一 source of truth）
- 会话开始先读，结束前必须更新（完成标 [x]，新问题加入）

## 组织架构

16 个 Agent，详见 `docs/system/org-chart.md`（按需读取）。
Agent 名册 SSOT: `docs/system/agents.yaml`

当作为 Agent Team teammate 启动时 → 读 `docs/system/org-chart.md` 找对应配置文件。

## 关键参考（按需读取，不要预加载）

| 文件 | 何时读 |
|------|--------|
| `docs/system/org-chart.md` | 需要知道 agent 职责/cron 时间表/团队加载规则时 |
| `SYSTEM_MAP.md` | /standup 或需要了解能力线状态时 |
| `MASON_AUTHORITY.md` | 判断是否在授权范围内时 |
| `MASONHUB.md` | Gateway 相关工作时 |
| `data/autonomous_tasks.yaml` | Dispatcher/任务调度相关时 |
| `shared/qa/` | QA Gate 流程时 |
| `docs/system/dev-rules.md` | 反合理化清单、Code Review、Lesson 格式、Token 记录 |
