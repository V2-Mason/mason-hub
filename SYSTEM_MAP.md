# System Map — 受力分析

> 最后更新: 2026-03-14 23:45 ET (EMP_0000 架构变更更新)
> 更新权: Agent 自动更新可推断字段，耦合关系变更需 Mason 确认
> 所有 Agent session 启动时读取此文件 + MASON_AUTHORITY.md

---

## 全局状态

**Agent OS v2 基础设施落地** — 16 EMP 完成 v2 四文件迁移 + 通信协议栈建立（8 种消息类型 + inbox 机制 + 权限矩阵 + 异常处理）+ 首次真实业务场景 multi-agent 端到端跑通（EMP_0001→0010→0001→0000，零人工介入）。四支柱差距仍在（Planning 10%/Reflection 15%）。Dispatcher 处于 /pause 状态。

当前合力方向: **通信层验证 + claude -p 替换 + Dispatcher 恢复**（基础设施就绪，进入集成验证阶段）

---

## 能力线受力分析

### 1. Agent 自治线
```
状态:    active
里程碑:  Agent OS v2 六子系统 21/21 + 16 EMP v2 四文件迁移完成 + agent-loader.sh 提取 + 通信协议栈（message_schema 8类型 + inbox + permissions + requires_review + task_failed 决策树 + system-status.sh）+ 首次 multi-agent e2e 跑通（零人工）
阻力:    内部工程: claude -p 需替换为 Claude API 调用层（嵌套限制）；workflow 文件兼容性待验证
         设计缺口: 四支柱（Planning/Reflection/Tool Use/Collab）全面不足，run-agent.sh 1300行 God Script 待拆
耦合:    ↓ 效率影响 → 数据线、内容线、商业线
上次更新: 2026-03-14
```
**解读**: 3/14 完成 Agent OS v2 基础设施三大块——(1) 16 EMP 从单文件 config.md 迁移到 v2 四文件格式（identity/state/soul/tools + memory），agent-loader.sh 从 run-agent.sh 提取适配新结构；(2) 通信协议栈全栈建立，从消息格式到权限控制到异常处理到可观测性；(3) 首次真实业务场景 multi-agent 跑通（素仁轩短视频脚本：EMP_0001 派活→EMP_0010 执行→EMP_0001 验收→EMP_0000 归档，4 条消息完整归档，零人工介入）。下一步：claude -p 替换 + workflow 兼容性验证 + Dispatcher 恢复。

### 2. 数据线
```
状态:    active
里程碑:  data_health_check 17/17 全绿 + 数据中台四层标准化完成 + SDK v0.1.0 + Scout v2 e2e 跑通
阻力:    内部工程: XHS 主干管道待统一（当前各段独立运行，未串联标准接口）
耦合:    ↓ 效率影响 → 内容线（策略输入逐步恢复可信度）
         ↓ 效率影响 → 商业线（无销售数据 = 无法归因，外部依赖不变）
上次更新: 2026-03-12
```
**解读**: 管道全绿。EMP_0014 连续 8 轮健康检查 17/17 全绿（从 16/17 升级完成）。Scout v2 首次 e2e 测试跑通（73 条 intel）。数据中台基础建设基本完成（四层标准化 + SDK + 清洗管道 + 销售快照），下一步是主干管道串联。

### 3. 内容生产线
```
状态:    waiting
里程碑:  SocialMesh 基础功能完成 + 首条内容发布
阻力:    外部依赖: CosyVoice TTS 自然度不够（需调参或换引擎）
         设计缺口: SocialMesh 模块化重构方案待执行（Phase A 代码迁移）
耦合:    ← 被阻塞: 数据线（没有可信的 XHS 趋势数据，内容策略缺乏依据）
         无下游依赖
上次更新: 2026-03-10
```
**解读**: 脚本层基本完成，但两个维度都在等——等数据线提供可信输入，等 TTS 问题解决。当前推这条线 ROI 不高。

### 4. 商业运营线
```
状态:    waiting
里程碑:  XHS 店铺开业 + 首单
阻力:    外部依赖: 品牌授权书（等清谭/DAERA/CDL）
         外部依赖: XHS 企业号注册（需营业执照+法人信息）
         外部依赖: 开发者账号审批（平台周期）
耦合:    ← 被阻塞: 数据线（无销售数据 = 无法做运营决策）
         无下游依赖
上次更新: 2026-03-10
```
**解读**: 几乎全是外部依赖，推了也没用。Agent 侧能做的只有代码准备（签名模块、API 对接框架），等外部条件就绪后立即接入。

### 5. 审计与可观测性线
```
状态:    active
里程碑:  audit schema + error-analysis.py + critic.py + system-status.sh（EMP 状态/消息队列/任务统计实时快照）+ permissions.md 权限矩阵 + check_permission() 运行时校验
阻力:    设计缺口: 评估维度是规则引擎不是 LLM，深度不够
耦合:    ← 依赖: 自治线稳定（agent 要先能自主跑，才有东西可审计）
         ↓ 解锁: 系统自我诊断、历史追溯、自动优化建议
上次更新: 2026-03-14
```
**解读**: 审计数据持续积累，30 条记录。新增记录包含精确 token/cost 追踪（input_tokens/output_tokens/cost_usd/model 字段）。三层审计中执行层完成，决策层和因果层待设计。

---

## 通信协议层（3/14 新增）

```
架构:
  shared/protocols/message_schema.md    ← 8 种消息类型定义
  shared/protocols/permissions.md       ← 权限矩阵（谁能发什么给谁）
  scripts/agent-loader.sh               ← send_message / check_inbox / check_permission
  scripts/system-status.sh              ← 实时可观测快照

消息生命周期:
  send_message() → data/messages/inbox_<id>.jsonl → check_inbox() 自动读取
                                                   → archive/inbox_<id>_YYYY-MM.jsonl

治理四层:
  1. 权限控制    check_permission() — task_assign 仅 Manager/PM，review_response 仅 EMP_0000/0012
  2. 验证机制    requires_review 字段 — 对外内容必须 review_request → approved 才能 complete
  3. 异常处理    task_failed 决策树 — 重试/人工裁决/拆分/基础设施升级
  4. 可观测性    system-status.sh — EMP 状态 + 消息队列 + 任务统计

验证状态:
  ✅ 首次 e2e 跑通: EMP_0001→EMP_0010→EMP_0001→EMP_0000（素仁轩短视频脚本，4 条消息完整归档）
```

---

## 耦合关系图

```
  Agent 自治线 (active)
       │
       ├─ 效率影响（非阻塞）──▶ 数据线、内容线、商业线
       │
       └─ 前置依赖 ──▶ 审计线（自治稳定后才有东西审计）

  数据线 (active) ◀── 采集已恢复
       │
       ├─ 效率影响 ──▶ 内容生产线 (waiting)
       │
       └─ 效率影响 ──▶ 商业运营线 (waiting)

  审计线 (active) ◀── schema 落地 + 30 条记录
       │
       └─ 解锁 ──▶ 系统自我诊断 + 历史追溯 + 自动优化建议
```

**读法**: 箭头方向 = 依赖方向。数据线是当前瓶颈（fan-out 阻塞两条下游线）。审计线是下一阶段的关键能力。

---

## 当前推荐行动

**只推荐当前能推动的事，不列"推了也没用"的。**

| 优先级 | 行动 | 理由 | Owner |
|--------|------|------|-------|
| 1 | claude -p → Claude API 调用层 | claude -p 嵌套限制是 agent 自主执行的硬阻塞，通信层已就绪但执行层受限 | EMP_0002 |
| 2 | workflow 文件兼容性验证 | v2 迁移后 workflow 四个 grep 命令待跑，确认无断裂 | EMP_0002 |
| 3 | Dispatcher /pause 解除 | 3/13 起暂停，v2 基础设施+通信层已就绪，应恢复自动派发 | Mason 决定 |
| 4 | Planning 能力建设 | 让 agent 收到目标自己拆解（decompose.py 接 LLM），四支柱突破点 | EMP_0002 |
| 5 | run-agent.sh 模块化拆分 | 1300 行 God Script → 子系统模块，降低维护成本和 bug 风险 | EMP_0002 |
| 6 | 阿里云连通性排查 | 当前 SSH 不通，影响数据同步 | EMP_0004 |

**不推荐现在做的**:
- 商业运营线任何事 → 全是外部依赖
- CosyVoice 调参 → 内容线优先级低于自治线
- 方案 C 升级（API 网关）→ 数据总量未触发 50MB 阈值

---

## 硬性等待项

> 这些事推了也没用，记录在这里避免浪费精力。只在状态变化时更新。

| 等待项 | 等谁 | 预计时间 | 到了之后触发什么 |
|--------|------|----------|------------------|
| XHS 小号注册+养号 | Mason 手动 | 3-5 天养号期 | 多账号轮换降低风控风险（采集已恢复，非阻塞） |
| 品牌授权书 | 清谭/DAERA/CDL | 未知 | 提交 XHS 店铺申请 |
| XHS 企业号审核 | 平台 | 依赖授权书先到 | 激活 EMP_0013 店铺运营 |
| XHS 开发者账号 | 平台 | 依赖企业号先到 | 对接 ARK API（签名/鉴权/商品同步） |
| CosyVoice 调参结果 | 内部测试 | 低优先级 | 解除内容线 TTS blocker |
| Kling API key | Mason 申请 | Mason 决定时间 | 部署 ComfyUI Kling 节点 |

---

## 更新协议

### 谁更新什么

| 字段 | 更新者 | 触发条件 |
|------|--------|----------|
| 能力线状态（active/blocked/waiting/stable） | Agent 自动 | health check / cron 结果变化时 |
| 里程碑 | Agent 自动 | 里程碑完成或重新定义时 |
| 阻力来源 | Agent 自动标记，Mason 确认分类 | 发现新 blocker 时 |
| 耦合关系 | Agent 标记 ⚠️待确认，Mason 确认 | 触发事件发生时（见下） |
| 推荐行动 | Agent 生成 | 每次 morning briefing 时刷新 |
| 硬性等待项 | 发现时 Agent 添加，到期时 Mason 触发 | 状态变化时 |

### 耦合关系自动触发条件

当以下事件发生时，Agent 在对应能力线的耦合字段追加 `⚠️待确认`，在 `/standup` 的"需要 Mason 确认"区块呈现：

| 触发事件 | 为什么耦合可能变了 |
|----------|-------------------|
| 新 Agent 创建 | 新的依赖节点出现 |
| blocker 状态 blocked → active/stable | 依赖可能解除，下游线可能解锁 |
| MASON_AUTHORITY.md 架构级修改 | Layer 变更可能重新定义线间关系 |
| 新业务需求（Mason 提出） | 可能引入新的跨线依赖 |

Mason 确认后，Agent 移除 `⚠️待确认` 标记并更新耦合描述。未确认前，旧耦合关系仍然有效。

### Ashby 多样性审视（每次能力线状态变为 active 时检查）

> Ashby 必要多样性定律：控制系统的多样性 ≥ 环境的多样性。
> 翻译：Gateway 检查清单必须覆盖该能力线所有可能的故障模式。

当一条能力线从 waiting/blocked → active 时，检查：
1. MASONHUB.md 检查清单是否有该能力线的故障检测项？
2. Dispatcher 的 autonomous_tasks.yaml 是否注册了该线的任务？
3. backlog 里该线的 `[ ]` 任务是否标注了 `(EMP_XXXX)`？

如果缺失 → 在推荐行动中加一条"补齐 XX 线的监控/任务注册"。
新业务线激活（如开店后商业线 active）时，此检查为 **P0**。

### 更新频率

- **自动字段**: 每次 `/standup` 时检查并增量更新（不重建）
- **耦合关系**: 触发事件发生时 Agent 标记，Mason 确认后生效
- **Mason 覆盖**: 任何字段 Mason 都可以直接改，Agent 不得回滚

### 状态判定规则

```
active  = 有明确下一步 + 无阻断 + 当前在推进
blocked = 有明确下一步 + 被具体的事阻断
waiting = 无阻断，但在等外部条件（时间/依赖/审批）
stable  = 已达当前里程碑，等解锁下一层
```

### 阻力分类规则

```
内部工程    = 自己能解决，排优先级 → 值得现在投入精力
外部依赖    = 推了没用，等或绕     → 记录到"硬性等待项"
资源限制    = 有上限，优化不突破   → 评估是否需要扩资源
设计缺口    = 还没想清楚           → 先设计再执行，不要边做边想
```

**核心过滤规则**: 只有"内部工程"类阻力值得立即投入。其他三类要么等、要么绕、要么先设计。

---

## 联邦节点状态

> Mason 联邦体系：mason-hub 作为中枢调度，各项目保持独立运行能力。
> 协议版本: v0.1（声明式，无实际通信）
> 规范文档: shared/adapter-spec.md

| 节点 | 项目路径 | 类型 | 端点 | 能力数 | 状态 | 备注 |
|------|----------|------|------|--------|------|------|
| surenxuan | ~/surenxuan | API | localhost:8000 | 9 | active | 有 P0 bug 待修 |
| tiktok-viral | ~/tiktok-viral-analysis | Script | script-based | 7 | active | Pipeline 80% |
| socialmesh | ~/socialmesh | API | localhost:8001 | 5 | active | 基础功能完成 |

### 联邦能力全景

```
数据采集        tiktok-viral: scrape_tiktok, scrape_amazon
分析            tiktok-viral: viral_score, review_nlp, competitor_price
库存管理        surenxuan: inventory.query, inventory.update
商品管理        surenxuan: product.list, product.detail
订单管理        surenxuan: order.create, order.list
定价            surenxuan: pricing.get
内容生成        surenxuan: content.generate
视频生成        tiktok-viral: video.generate, video.reverse_engineer
内容发布        socialmesh: content.publish, content.schedule, content.draft
数据分析        socialmesh: analytics.engagement, analytics.reach
报表            surenxuan: report.sales
```

### 未来节点（planned）

| 节点 | 用途 | 触发条件 |
|------|------|----------|
| shopify connector | Shopify API 对接 | 素仁轩出海启动时 |
| amazon connector | Amazon API 对接 | merchant agent Layer 1B |
| tiktok-shop connector | TikTok Shop API 对接 | 素仁轩出海启动时 |
| EMP_0017 merchant agent | 跨平台商家代理 | 联邦架构 v0.2 就绪后 |

### 联邦架构版本路线

```
v0.1（当前）  声明式 — adapter.yaml 只读，无实际通信
v0.2          单向 — mason-hub 可通过 hooks 向节点发指令
v0.3          双向 — 节点可主动向 mason-hub 上报事件
v1.0          完整 A2A — 支持跨平台 agent 间协作
```
