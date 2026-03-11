# Agent Communication Protocol v2.0
# 更新于 2026-02-27：增加 alert, data_request, handoff, task_review 消息类型 + 感知层触发规范 + 自省层复盘模板

## task_assign
触发者：Manager或PM
目标：Dev agent
必填字段：
  - task_id: 唯一标识（格式：{project}_{date}_{序号}，例如srx_20260225_001）
  - assignee: 目标agent名称
  - description: 任务描述（清晰到Dev agent不需要猜测）
  - context_files: 需要读取的文件路径列表
  - expected_output: 期望的输出格式和内容
  - allowed_paths: 允许读写的路径列表
  - retry_policy: {max_retries: 3, notify_on_failure: "pm"}

## task_complete
触发者：Dev agent（主动上报，不等被问）
目标：PM
必填字段：
  - task_id: 对应的task_id
  - output_summary: 做了什么（100字以内）
  - files_modified: 修改了哪些文件
  - insights: 这个任务产生了什么新发现（没有则填null）
  - needs_escalation: true/false
  - escalation_reason: 如果needs_escalation为true，说明原因

## task_failed
触发者：Dev agent
目标：PM
必填字段：
  - task_id: 对应的task_id
  - failure_reason: 失败原因
  - retry_count: 已重试次数
  - last_state: 失败前的最后状态

## escalate
触发者：PM
目标：Manager
必填字段：
  - issue_description: 问题描述
  - options: 可选方案列表（至少两个）
  - pm_recommendation: PM的推荐方案和理由
  - urgency: low/medium/high

## memory_update_request
触发者：任何agent
目标：上级agent
必填字段：
  - content: 建议写入的内容
  - target_layer: project/domain/meta
  - reason: 为什么这个值得被记住

## shutdown_request
触发者：Manager或PM
目标：任何agent
必填字段：
  - reason: 关闭原因
  - allow_refusal: true/false（是否允许agent拒绝）

## shutdown_response
触发者：被关闭的agent
目标：发出shutdown_request的agent
必填字段：
  - approve: true/false
  - reason: 如果拒绝，说明原因
  - estimated_completion: 如果拒绝，预计完成时间

---

# 以下为 v2.0 新增消息类型

## alert
触发者：SRE、PM、或感知层触发器
目标：PM 或 Mason（取决于严重程度）
场景：系统监测到异常状态需要关注时
必填字段：
  - alert_id: 唯一标识（格式：alert_{date}_{序号}）
  - severity: P0/P1/P2
  - source: 触发来源（cron_job/event_trigger/manual）
  - category: 类型（inventory_low/expiry_warning/sales_anomaly/service_down/cost_spike）
  - description: 问题描述
  - affected_scope: 影响范围（哪些产品/服务/客户）
  - suggested_action: 建议的处理方式（可选）
  - auto_resolved: true/false（是否已自动处理）
路由规则：
  - P0 → 同时通知 PM + Mason（Slack #srx-alerts）
  - P1 → 通知 PM，PM 决定是否 escalate
  - P2 → 记录到日报，下次巡检处理

## data_request
触发者：任何 agent
目标：有数据访问权限的 agent（通常是 Dev 或 SRE）
场景：Agent 需要查询数据但自己没有直接访问权限时
必填字段：
  - request_id: 唯一标识
  - requester: 请求方 agent
  - query_description: 需要什么数据（自然语言描述）
  - data_source: 数据来源（database/api/log/cache）
  - format: 期望的返回格式（json/text/csv）
  - urgency: low/medium/high
响应：data_response
  - request_id: 对应的 request_id
  - data: 查询结果
  - notes: 数据备注（如：数据截至时间、采样方式等）

## handoff
触发者：任何 agent
目标：接手方 agent
场景：任务需要跨角色协作时（如 PM 拆解完交给 Dev，Dev 做完交给 PM 验收）
必填字段：
  - handoff_id: 唯一标识
  - task_id: 关联的任务 ID
  - from_agent: 交出方
  - to_agent: 接手方
  - handoff_type: 类型（assign/review/escalate/return）
  - context_summary: 当前状态摘要（接手方需要知道的最少信息）
  - artifacts: 产物列表（文件路径、commit hash 等）
  - expected_action: 期望接手方做什么

## task_review
触发者：PM（任务完成后的自省/复盘）
目标：自己（写入 long_term.md）
场景：任务链完成后，PM 对整个过程做复盘
必填字段：
  - task_id: 复盘的任务 ID
  - outcome: success/partial/failed
  - duration_estimate: 预估耗时 vs 实际耗时
  - what_went_well: 哪些做得好
  - what_went_wrong: 哪些做得不好
  - root_cause_if_failed: 如果失败，根因是什么
  - lesson_learned: 值得记住的教训（写入 long_term.md）
  - process_improvement: 流程改进建议（如果有）

---

# 感知层触发规范

## 定时触发（Cron-based Triggers）

以下触发器通过 cron 调度，Agent 在 session 启动时检查是否需要执行：

| 触发器 | 频率 | 负责 Agent | 动作 |
|--------|------|-----------|------|
| 库存巡检 | 每日 20:00 ET | PM (EMP_0001) | 扫描临期（30天内）、低库存（<5）、滞销（30天无销售）SKU，生成 alert |
| 日报生成 | 每日 21:00 ET | SRE (EMP_0004) | 基础设施日报 → #system-alerts |
| 健康检查 | 每 30 分钟 | SRE (EMP_0004) | 服务存活 + 日志异常检查 |
| 记忆压缩 | 每周一 | PM (EMP_0001) | 从 completed_tasks 提取经验 → long_term.md |
| 阶段提炼 | Phase 结束时 | Domain Manager (EMP_0003) | 提炼 domain 级经验 → knowledge_base.md |

## 事件触发（Event-based Triggers）

以下触发器由业务事件驱动，需要后端 event_bus 配合：

| 事件 | 触发条件 | 动作 |
|------|---------|------|
| LOW_STOCK | inventory_movement 后 remaining_quantity < 阈值 | 生成 alert(category=inventory_low) → PM |
| EXPIRY_WARNING | 每日巡检发现 batch expiry_date 在 30 天内 | 生成 alert(category=expiry_warning) → PM |
| SALES_ANOMALY | 日销量偏离 7 日均值 >50% | 生成 alert(category=sales_anomaly) → PM |
| SERVICE_DOWN | 健康检查失败 | 生成 alert(category=service_down, severity=P0) → SRE + Mason |

## 触发器响应规则

Agent 收到 alert 后的标准处理流程：
1. 评估严重程度（P0/P1/P2）
2. P0：立即响应，通知 Mason
3. P1：创建任务，分配给 Dev 或自行处理
4. P2：记录到日报，下次维护窗口处理
5. 所有 alert 处理结果写入 audit.jsonl

---

# 自省层规范

## 复盘时机
- 每个任务链完成后，PM 必须做一次 task_review
- 每周一记忆压缩时，PM 回顾本周所有 task_review，提炼到 long_term.md
- Phase 结束时，Domain Manager 做全局复盘

## 复盘写入位置
- 单次任务复盘 → PM 的 agents/memory/EMP_0001/long_term.md
- 周度总结 → 对应项目的 decisions.md（如果产生了新的判断模式）
- Phase 总结 → domain 的 knowledge_base.md（由 Domain Manager 执行）

## 复盘质量标准
- 不是"做了什么"的复述（那是 task_complete）
- 而是"下次遇到类似情况，应该怎么做更好"
- 每条教训必须有具体的情境和具体的改进建议，不要写空泛的"要更加注意"
