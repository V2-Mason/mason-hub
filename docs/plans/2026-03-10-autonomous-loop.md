# 自治闭环设计 — Push→Pull 转型

> 日期: 2026-03-10
> 决策者: Mason
> 状态: 设计中

## 问题

MASON_AUTHORITY 定义了"能做什么"，SYSTEM_MAP 定义了"状态是什么"，backlog 定义了"要做什么"。
但没有任何东西定义"什么时候自己去做"。

系统是 Push 模式（Mason 推任务），需要变成 Pull 模式（Agent 拉任务）。

## 设计目标

```
事情发生 → agent 自动处理 → 异常和决策项自动浮现到 Mason 面前
```

Mason 只看两样东西：
1. 摘要（发生了什么，都处理好了）
2. 决策项（这几个事需要你拍板）

---

## 第一层：过滤规则（信息分级）

> 核心问题：什么信息应该被静默处理、聚合上报、还是立刻升级？

### Level 0: 静默处理（Agent 自己做完，不上报）

Agent 做完后只写结构化日志，不推送任何通知。

适用条件（全部满足）：
- 任务在 MASON_AUTHORITY "直接做" 层级
- SYSTEM_MAP 中该任务所在能力线状态是 active 或 stable
- 执行成功，无异常
- 不涉及硬性红线

示例：
- 日常 health check 全绿
- 记忆文件更新
- 日志轮转
- 已有脚本的定时执行（且成功）

### Level 1: 聚合上报（Manager 汇总，下次 briefing 呈现）

Agent 做完后写汇报到 /data/reports/，Manager 聚合后在 morning briefing 呈现。

适用条件（任一）：
- 任务在 MASON_AUTHORITY "做完通知" 层级
- 任务改变了系统状态（新文件、配置变更、依赖更新）
- 任务是从 backlog 认领的（非定时任务）
- 执行成功但有 warning

示例：
- Agent 自主修复了一个 P2 bug
- 数据同步完成，新增 N 条记录
- health check 发现非关键异常并自动修复
- 单元测试新增 N 个 case

### Level 2: 主动通知（Slack 推送，不需要 Mason 回复）

需要 Mason 知道，但不需要决策。通过 Slack 实时推送。

适用条件（任一）：
- 任务失败且自动重试也失败（连续 2 次）
- SYSTEM_MAP 能力线状态发生变化（blocked→active 或 active→blocked）
- 硬性等待项有状态变化（外部条件到达）
- 完成了 P0/P1 级别的 backlog 任务

示例：
- srx_sales JWT 验证通过，数据线 blocked→active
- cron 任务连续 2 次失败
- 小号 cookie 过期检测到

### Level 3: 需要决策（集中呈现，等 Mason 回复）

收集到 /standup 的"需要 Mason 确认"区块，或 Slack 单独推送。

适用条件（任一）：
- 涉及 MASON_AUTHORITY 硬性红线
- 架构级决策（多个可选方案）
- 任务连续 3 次失败，怀疑是架构问题
- 耦合关系 ⚠️待确认 标记
- 涉及费用、外部服务、生产部署

示例：
- 需要 API key
- 方案选择（A vs B）
- 生产部署确认
- 新 Agent 创建

### 过滤规则判定流程

```
任务完成
  │
  ├─ 涉及硬性红线？ ─── 是 ──→ Level 3（需要决策）
  │
  ├─ 执行失败？
  │   ├─ 首次失败 ──→ 自动重试，Level 0
  │   ├─ 连续 2 次 ──→ Level 2（主动通知）
  │   └─ 连续 3 次 ──→ Level 3（怀疑架构问题）
  │
  ├─ 改变了系统状态？ ─── 是 ──→ Level 1（聚合上报）
  │
  ├─ P0/P1 backlog 任务？ ── 是 ──→ Level 2（主动通知）
  │
  └─ 其他 ──→ Level 0（静默处理）
```

---

## 第二层：自主触发协议

### 任务可执行条件（四道安全门）

一个 backlog 任务可以被 Agent 自主认领，当且仅当：

```
Gate 1: 权限 — 任务在 MASON_AUTHORITY 当前 Layer 的"直接做"或"做完通知"层级
Gate 2: 状态 — SYSTEM_MAP 中该任务所在能力线状态是 active（不是 blocked/waiting）
Gate 3: 依赖 — 任务的上游依赖健康（data_health_check 对应数据集无 ❌）
Gate 4: 时间 — 当前不在静默时段（CST 22:00-08:00 不启动新任务）
```

四道门全过 → 可以自主执行
任何一道没过 → 跳过，等下次检查

### Dispatcher 机制

```
┌─────────────────────────────────────────────┐
│  dispatcher.sh (cron 每小时)                 │
│                                              │
│  1. 读取 SYSTEM_MAP → 各能力线状态           │
│  2. 读取 backlog → 未完成任务列表             │
│  3. 对每个任务过四道安全门                     │
│  4. 通过的任务 → 按优先级排序                  │
│  5. 取优先级最高的 1 个任务                    │
│  6. 通过 run-agent.sh 启动对应 Agent          │
│  7. 写入 /data/events/ 事件标记               │
│                                              │
│  约束:                                       │
│  - 每次只启动 1 个任务（避免资源争抢）          │
│  - Lane Queue 自动防止同域并发                 │
│  - 如果已有 agent 在跑 → 跳过本轮              │
└─────────────────────────────────────────────┘
```

为什么每次只启动 1 个：
- GCP 3.8G 内存，Claude CLI session 吃 ~500MB
- Lane Queue 已经防并发，但内存是硬限制
- 每小时检查一次，一天最多执行 14 个任务（08:00-22:00），够用

### 事件触发（补充 cron 轮询）

对于需要实时响应的场景，用事件标记补充 cron 的延迟：

```
事件产生端:
  任何脚本完成后 → 写 JSON 到 /data/events/
  格式: { "event": "类型", "source": "脚本", "timestamp": "...", "data": {...} }

事件消费端（两种）:
  A. inotifywait 实时监听（安装后启用）
  B. dispatcher.sh 每小时扫描（兜底）

事件路由:
  data-sync-complete    → 检查数据线是否可解锁
  health-check-failed   → 标记对应能力线 blocked
  agent-task-complete   → 写汇报 + 检查下游任务
  blocker-resolved      → 更新 SYSTEM_MAP + 检查 waiting 任务
```

---

## 第三层：汇报链

### 结构化汇报格式

每个 Agent 完成任务后写入 `/data/reports/YYYY-MM-DD/`:

```json
{
  "agent_id": "EMP_0005",
  "task_id": "backlog_item_identifier",
  "timestamp": "2026-03-10T14:30:00+08:00",
  "status": "success|failed|partial",
  "level": 0,
  "summary": "一句话描述做了什么",
  "changes": ["file1.py", "file2.sh"],
  "blockers_found": [],
  "blockers_resolved": ["srx_sales_401"],
  "next_steps": [],
  "metrics": {}
}
```

### 聚合流程

```
执行层 Agent (EMP_0005/0009/0010/0014)
  │ 写 /data/reports/ JSON
  │
Manager 层 (EMP_0001/0002/0008)
  │ 各自收集下属汇报
  │ 过滤 Level 0（静默）
  │ 聚合 Level 1（合并同类项）
  │ 透传 Level 2-3（不过滤）
  │
Meta Manager (EMP_0000)
  │ 收集所有 Manager 汇报
  │ 生成 Mason briefing:
  │   - "已处理" 区块（Level 0-1 的摘要统计）
  │   - "需要知道" 区块（Level 2 的具体事项）
  │   - "需要决策" 区块（Level 3 的决策项 + 推荐方案）
  │
Mason
  只看 briefing，回复决策项
```

### 实际约束

当前 `run-agent.sh` 的限制：
- Agent 是 `claude -p` 一次性 session，不是常驻进程
- Manager "收集下属汇报" 实际上是 dispatcher 下次启动 Manager 时让它读 reports 目录
- 所以汇报链不是实时的，而是批量的（每小时 dispatcher 一轮）

这意味着：
- Level 0-1 的汇报天然是批量的（morning briefing 呈现）
- Level 2 需要脚本直接发 Slack（不等 Manager 聚合）
- Level 3 需要脚本直接发 Slack + 标记到 SYSTEM_MAP

---

## 建设顺序

### Phase 1: 过滤规则 + Dispatcher 骨架（2-3h）
- [x] 过滤规则定义（本文档）
- [ ] dispatcher.sh 骨架（扫描 backlog + 四道安全门 + 启动 agent）
- [ ] /data/events/ 目录 + 事件 JSON schema
- [ ] /data/reports/ 目录 + 汇报 JSON schema

### Phase 2: 第一条链路跑通（2-3h）
- [ ] 选一个具体任务（如 "SearXNG Docker 部署"）作为 pilot
- [ ] dispatcher 识别到这个任务 → 启动 EMP_0002 → 执行 → 写汇报
- [ ] 汇报出现在下次 /standup 的受力分析区块
- [ ] 验证四道安全门是否正确拦截了不该执行的任务

### Phase 3: 事件触发 + Slack 通知（2-3h）
- [ ] 安装 inotify-tools
- [ ] event-watcher.sh + systemd 服务
- [ ] Level 2 事件直接发 Slack
- [ ] data-sync → 下游任务 这条链路跑通

### Phase 4: 汇报链完整接入（3-4h）
- [ ] Manager 聚合脚本
- [ ] EMP_0000 briefing 生成
- [ ] /standup 读取 reports 目录展示 "已处理" 摘要
- [ ] 过滤规则调优（观察 1 周后调整阈值）
