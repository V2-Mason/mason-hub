# Agent 通信协议 · Message Schema

> 所有跨 EMP 通信必须使用此格式。
> 禁止自由文本传递任务或决策，task_id 必须存在。

---

## 标准消息格式

```yaml
sender: EMP_XXXX
receiver: EMP_XXXX        # escalate 类型自动路由到 EMP_0000，可省略
type: <见下表>
task_id: TASK-YYYYMMDD-XXX
payload: |
  [具体内容]
requires_response: true / false
deadline: ISO8601 / null
timestamp: ISO8601
```

---

## 消息类型

| type | 触发场景 | requires_response 默认值 |
|------|---------|------------------------|
| task_complete | 任务完成，通知下游消费者 | false |
| task_failed | 任务失败，等待裁决 | true |
| review_request | 请求另一 EMP 审核产出 | true |
| review_response | 返回审核结果（含 approved / rejected + 原因） | false |
| escalate | 超出能力边界，向上汇报 | true |
| ping | 确认对方存活/可用 | true |
| state_update | 通知下游自己的 state.md 已更新 | false |

---

## 使用规则

1. 所有跨 EMP 通信使用此格式，不允许自由文本传递任务
2. task_id 必须存在且可在 audit.jsonl 中追溯
3. escalate 类型自动路由到 EMP_0000，receiver 可省略
4. requires_response: true 的消息，发送方在 state.md 的
   "等待/阻塞"字段记录：等待 [receiver] 回复 [task_id]
5. 收到 review_request 的 EMP，必须在 payload 里明确写
   approved 或 rejected，不允许模糊表态

---

## 示例

### task_complete

```yaml
sender: EMP_0002
receiver: EMP_0000
type: task_complete
task_id: TASK-20260314-001
payload: |
  run-agent.sh 适配 v2 文件结构完成。
  agent-loader.sh 已提取，验证通过。
  变更：scripts/agent-loader.sh（新增）· scripts/run-agent.sh（修改）
requires_response: false
deadline: null
timestamp: 2026-03-14T10:00:00Z
```

### review_request

```yaml
sender: EMP_0001
receiver: EMP_0012
type: review_request
task_id: TASK-20260314-002
payload: |
  请审核素仁轩 Q2 内容策略草案。
  文件位置：data/reports/srx-q2-strategy.md
  重点确认：定价策略部分是否与产品架构方向一致
requires_response: true
deadline: 2026-03-15T18:00:00Z
timestamp: 2026-03-14T10:05:00Z
```

### escalate

```yaml
sender: EMP_0004
receiver: null       # 自动路由到 EMP_0000
type: escalate
task_id: TASK-20260314-003
payload: |
  GCP 实例磁盘使用率 94%，超出处理能力边界。
  已尝试：清理 logs/archive/（释放 2GB），问题未解决。
  需要：扩容决策或数据迁移授权
requires_response: true
deadline: 2026-03-14T12:00:00Z
timestamp: 2026-03-14T10:10:00Z
```

---

## 与现有文件的关系

| 文件 | 关系 |
|------|------|
| agents/EMP_*/soul.md | 下游通知章节描述"发什么"，本文件定义"怎么发" |
| agents/EMP_*/state.md | requires_response:true 的消息在此记录等待状态 |
| logs/audit.jsonl | 所有消息的 task_id 必须可在此追溯 |
| agents/states/manager.json | 未来扩展：消息路由表可在此注册 |
