# Agent OS v2 — 全子系统 90% 实施路线图

> 日期：2026-03-14
> 决策人：Mason
> 执行：EMP_0002 (Platform Dev) 为主
> 目标：6 个子系统全部从当前水平提升到 90%

## 当前状态 → 目标

```
Infrastructure    90% → 90%  (已达)
Roster            63% → 90%  (+27%, 2 个能力点)
Accounts          50% → 90%  (+40%, 3 个能力点)
Protocols         50% → 90%  (+40%, 3 个能力点)
Memory            75% → 90%  (+15%, 2 个能力点)
Task Engine       29% → 90%  (+61%, 5 个能力点)
Control Plane     14% → 90%  (+76%, 6 个能力点)
```

总计：21 个能力点待建。

## 依赖图

```
Phase 1 (无依赖，可并行)
├── Roster ③④
├── Accounts ③⑥⑦
└── Protocols ④⑤⑥

Phase 2 (依赖 Phase 1 的 Accounts)
└── Task Engine ①②③⑤⑥⑦

Phase 3 (依赖 Phase 2 的 Task Engine)
├── Memory ⑤⑦
└── Control Plane ①②③④⑤
```

## Phase 1：独立子系统补全（Roster + Accounts + Protocols）

### 1A. Roster → 90%（当前 63%，+2 能力点）

**③ 能力索引生成**
- 从 `docs/system/agents.yaml` 提取每个 agent 的 skills/domain/capabilities
- 生成 `data/roster/capability_index.json`：反向映射 `{"python": ["EMP_0002","EMP_0005","EMP_0009"], "xhs": ["EMP_0008","EMP_0010"], ...}`
- 脚本：`scripts/roster/build-capability-index.py`

**④ Dispatcher 按能力动态匹配**
- dispatcher.sh 的任务分配逻辑：读 capability_index.json，按任务 description 关键词匹配可用 agent
- 匹配失败时 fallback 到 autonomous_tasks.yaml 里的硬编码 agent

交付物：`scripts/roster/build-capability-index.py` + `data/roster/capability_index.json` + dispatcher.sh 改造
验证：新任务无 agent 指定时，Dispatcher 能自动匹配

### 1B. Accounts → 90%（当前 50%，+3 能力点）

**③ brief 注入 budget 截断**
- run-agent.sh 的 `inject_if_exists` 已有 budget 控制（MAX_INJECT_CHARS=16000）
- 但 brief.md 7KB 可能挤占其他内容 → 新增 `inject_if_exists_truncated` 函数，截取前 N 行
- 参数：`ACCOUNT_BRIEF_MAX_CHARS=3000`（~750 tokens）

**⑥ 多 account 隔离验证**
- 创建 `accounts/_test/` 作为第二个 account
- 验证：TASK_ACCOUNT=_test 时只加载 _test 的 context，不泄露 surenxuan 数据
- 验证脚本：`tests/test_account_isolation.sh`

**⑦ data/ 私有数据隔离**
- 创建 `accounts/surenxuan/data/`（symlink 到 `domains/ecommerce/projects/srx/`）
- run-agent.sh 加检查：agent 写文件时路径必须在 `accounts/$TASK_ACCOUNT/` 内（或通用区域）
- 实现：post-task hook 检查 git diff 的路径

交付物：inject 截断 + test account + 隔离验证脚本 + data/ symlink
验证：`bash tests/test_account_isolation.sh` 全通过

### 1C. Protocols → 90%（当前 50%，+3 能力点）

**④ 声明式 YAML 格式**
- 将 `shared/protocols/*.md` 转为 `shared/protocols/*.yaml`
- 保留 markdown 的描述性内容作为 `description` 字段
- Schema：
```yaml
id: escalation-protocol
version: "1.0"
type: global  # global / domain / agent
description: "升级规则"
rules:
  - trigger: "连续 3 次失败"
    action: "escalate_to_manager"
    params: {max_retries: 3}
```

**⑤ 协议版本管理**
- 每个 protocol YAML 有 `version` 字段
- 变更时版本号递增 + 在文件内 `changelog:` 追加记录
- config.md 引用协议时带版本：`protocol: escalation@1.0`

**⑥ 协议冲突检测**
- 脚本：`scripts/protocol-check.py`
- 检查：同一 trigger 是否有多个 protocol 定义了不同 action
- 检查：config.md 引用的 protocol 版本是否存在
- 集成到 `/commit` 的 Step 5b（config-health-check.sh 已有类似能力）

交付物：YAML 格式 protocols + 版本号 + protocol-check.py
验证：`python3 scripts/protocol-check.py` 零冲突

## Phase 2：Task Engine → 90%（当前 29%，+5 能力点）

依赖：Accounts（Task 需要 account 字段）

**① Task 标准数据对象 schema**
- `data/schemas/task.yaml`：定义所有字段
- 每个任务执行时生成 `data/tasks/{task_id}.yaml`（替代散落的 audit.jsonl + summary.json）
- run-agent.sh 在任务开始时创建 task YAML，结束时更新 status + result

**② 任务状态机**
- 状态流转：`created → assigned → in_progress → verifying → done | failed | escalated`
- dispatcher.sh 负责 `created → assigned`
- run-agent.sh 负责 `assigned → in_progress → verifying → done/failed`
- escalation 逻辑负责 `failed → escalated`
- 每次状态变更写入 task YAML + 发射事件

**③ depends_on 实际执行**
- dispatcher.sh 扫描任务时，检查 depends_on 列表里的 task 是否全部 status=done
- 未完成的依赖 → 跳过该任务（已有字段定义，补实现）

**⑤ 经验自动提取**
- run-agent.sh post-task 阶段：调用 `skills/learning/extract-lessons.py`
- 输入：task YAML（含 input + acceptance_criteria + result）
- 输出：1-3 条 Memory Entry JSON
- 自动路由到正确的 Pipe（根据 agent_scope + account_scope）

**⑥ acceptance_criteria 注入**
- autonomous_tasks.yaml 每个任务加 `acceptance_criteria` 字段
- run-agent.sh 注入到 prompt："验收标准：{criteria}"
- 任务完成时 verify_command 对照 criteria 检查

**⑦ lessons_extracted 写入 Memory**
- extract-lessons.py 的输出直接 append 到对应 Pipe 文件
- Pipe 判定规则：有 TASK_ACCOUNT → Pipe 3（agent×account），无 → Pipe 1（agent 职能）
- 无法判定时写 `data/memory_pending.jsonl`（推给 Control Plane）

交付物：task.yaml schema + run-agent.sh 状态机 + depends_on 执行 + extract-lessons.py + acceptance_criteria 注入
验证：端到端跑一个任务，检查 task YAML 完整性 + lesson 自动写入正确 Pipe

## Phase 3：Memory + Control Plane → 90%

依赖：Task Engine（经验提取 + Escalation 产出）

### 3A. Memory → 90%（当前 75%，+2 能力点）

**⑤ 写入归属自动判定器**
- `scripts/memory-router.py`：接收 Memory Entry JSON，根据 scope 字段路由
- 集成到 extract-lessons.py 的输出端
- 路由规则：agent_scope + account_scope → Pipe 3，agent only → Pipe 1，account only → Pipe 2，都无 → Pipe 4
- 无法判定 → `data/memory_pending.jsonl`

**⑦ 四管分别压缩**
- compact-memory.sh 改造：对 Pipe 1-4 分别运行压缩，不同阈值
  - Pipe 1（agent 职能）：>300 行压缩
  - Pipe 2（account 公共）：>200 行压缩
  - Pipe 3（account×agent）：>100 行压缩
  - Pipe 4（全局）：>500 行压缩

交付物：memory-router.py + compact-memory.sh 四管分别压缩
验证：模拟写入 4 种类型的 lesson，确认路由到正确文件

### 3B. Control Plane → 90%（当前 14%，+6 能力点）

**① Escalation 队列聚合**
- `scripts/control/escalation-queue.py`
- 扫描源：audit.jsonl（status=failed/escalated）+ memory_pending.jsonl + gateway-known-states 过期项
- 输出：`data/control/escalation_queue.json`（按 level×urgency 排序）

**② Task dashboard**
- `scripts/control/task-dashboard.py`
- 扫描 `data/tasks/*.yaml`，按 account 分组，按 status 统计
- 输出：`data/control/dashboard.json` + 可选 Slack 推送

**③ Memory pending 分类**
- 读取 `data/memory_pending.jsonl`
- 展示给 Mason：每条 pending entry + 建议的 Pipe 归属
- Mason 决定后写回对应 Pipe 文件

**④ attention prioritization**
- 算法：urgency(时间衰减) × impact(影响范围) × actionability(是否可操作)
- 在 escalation-queue.py 里实现排序
- /standup 时自动呈现 Top 3 需要 Mason 处理的事项

**⑤ 批量审批接口**
- `/approve` skill：Mason 说 `/approve` 后显示 pending 队列，Mason 逐条或批量 approve/reject
- 结果写回 Task 或 Memory

交付物：escalation-queue.py + task-dashboard.py + memory-pending 处理 + attention 排序 + /approve skill
验证：模拟 3 个 escalation + 2 个 memory pending，确认排序正确 + 审批写回

## 实施顺序（按 session 拆分）

| Session | 内容 | 预计能力点 | 依赖 |
|---------|------|-----------|------|
| **S1** | Phase 1A (Roster) + Phase 1B (Accounts) | 5 | 无 |
| **S2** | Phase 1C (Protocols) | 3 | 无 |
| **S3** | Phase 2 前半（Task schema + 状态机 + depends_on） | 3 | S1 |
| **S4** | Phase 2 后半（经验提取 + criteria + lessons写Memory） | 3 | S3 |
| **S5** | Phase 3A (Memory) + Phase 3B 前半（Escalation + Dashboard） | 4 | S4 |
| **S6** | Phase 3B 后半（pending + attention + /approve） | 3 | S5 |

6 个 session，21 个能力点。

## 风险

| 风险 | 缓解 |
|------|------|
| Protocols YAML 转换影响所有引用 | 保留 .md 文件作 symlink，渐进迁移 |
| Task Engine 改造动 run-agent.sh 核心 | 分支开发，单元测试覆盖 |
| Control Plane 过度工程 | 先 CLI 脚本，不建 Web UI |
| 6 session 跨多天，中间状态不一致 | 每 session 结束可独立运行，不依赖下一步 |
