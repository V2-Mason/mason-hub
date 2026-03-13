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

`/standup` 晨会 | `/commit` 智能提交 | `/deploy` 部署 | `/health` 健康检查 | `/dev-task` 派活 | `/scout` 情报 | `/solve` 问题解决

## Role 调用规则（防止 token 浪费）

Role 有三种使用模式，**必须先判断模式再行动**：

| 模式 | 触发词 | 做法 | 成本 |
|------|--------|------|------|
| **Lens（视角）** | "用 XX 视角分析"、"让 XX 评估"、"XX 来看看" | 读 config.md，在当前对话中切换思维模式，直接输出 | ≈0（只读一个文件） |
| **Instance（实例）** | `/dev-task`、"派活给 XX"、dispatcher 自动派发 | 启动新 session，注入 config + memory + 品牌上下文 | 完整 session 开销 |
| **Dialogue（对话）** | workflow 中的 agent-to-agent step | 当前 session 内加载多个 role config，按协议交替 | 共享 session |

**判断口诀**：只需要"换个角度想" → Lens。需要"独立去做一件事" → Instance。

## 开发铁律

1. **完成前必须验证** — 改完代码必须跑验证，禁止"应该没问题"。commit 前至少 `python3 -c "import ast; ast.parse(...)"`
2. **修 bug 先定位根因** — 不允许"先试试"，每次只改一个变量。连续 3 次失败 → 停下来质疑架构
3. **记忆追加不删除** — 新内容加新条目，过时标注 `→ 已更新 (日期)`，Mason 授权才删
4. **收工必须写 Lesson** — session 结束前更新 `agents/EMP_XXXX/memory/`，格式参照 `shared/templates/lesson_format.md`，Gap 类型必填
5. **发现问题走 /solve** — 非 trivial 问题必须走 `/solve` 流程（定级→方案→验收），不能跳步直接执行。简单问题至少要有定级+验收标准

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

## Agent 配置架构（三层分离）

修改 agent 行为时必须遵守：

| 层级 | 路径 | 内容 | 规则 |
|------|------|------|------|
| **config** | `agents/EMP_*/config.md` | 身份、判断框架、决策权限、禁止事项 | **≤ 5KB**（含 frontmatter），只放"你是谁"+"你怎么判断" |
| **protocol** | `shared/protocols/*.md` | 跨 agent 共享的标准流程 | 改一处，所有引用者生效。Owner: EMP_0002 |
| **playbook** | `docs/playbooks/*.md` | 单个 agent 的详细操作手册 | 按需 read_file，不注入 system prompt |

**铁律**：
- 新增 agent 行为时，先问"这是身份定义还是操作流程？" → 身份→config，流程→playbook
- 跨 agent 重复的内容 → 抽到 protocol，config 里一行引用
- Config 超过 5KB → 必须拆分，把操作细节移到 playbook
- 修改 protocol 后 → 检查所有引用该 protocol 的 config 是否需要同步
- **Owner**: EMP_0002 (Platform Dev) 负责 shared/protocols/ 维护，各 PM 负责自己的 playbook
- **自动检查**: `scripts/config-health-check.sh`（/commit 自动触发）— 检查膨胀、引用断裂、过时

## 关键参考（按需读取，不要预加载）

| 文件 | 何时读 |
|------|--------|
| `docs/system/org-chart.md` | 需要知道 agent 职责/cron 时间表/团队加载规则时 |
| `SYSTEM_MAP.md` | /standup 或需要了解能力线状态时 |
| `MASON_AUTHORITY.md` | 判断是否在授权范围内时 |
| `MASONHUB.md` | Gateway 相关工作时 |
| `data/autonomous_tasks.yaml` | Dispatcher/任务调度相关时 |
| `shared/qa/` | QA Gate 流程时 |
| `shared/protocols/` | Escalation、Dev 执行、启动流程等跨 agent 协议时 |
| `docs/playbooks/` | PM 操作手册（任务拆解、QA Gate、数据分析细节）时 |
| `docs/system/dev-rules.md` | 反合理化清单、Code Review、Lesson 格式、Token 记录 |
