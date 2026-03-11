# 感知层触发器 — Cron 接入方案
# 更新于 2026-02-27

## 原理

每个触发器 = 一条 cron 表达式 + 一次 run-agent.sh 调用。
run-agent.sh 已支持 `<agent配置文件> <任务内容>` 格式。
触发器通过给 Agent 发送特定的"巡检指令"实现，Agent 读完角色定义后按指令执行。

## GCP Cron 表达式（部署到 GCP 34.63.188.198）

```crontab
# === 感知层触发器 ===

# 1. PM 每日库存巡检 (20:00 ET = 00:00 UTC)
0 0 * * * /home/hangn/mason-hub/scripts/run-agent.sh agents/EMP_0001.md "库存巡检任务：1) 读取最新库存数据 2) 检查临期SKU（30天内）3) 检查低库存SKU（remaining_quantity < 5）4) 检查滞销SKU（30天无销售）5) 有异常则通过 slack_notify.sh 发送 alert 到 #srx-alerts 6) 无异常则记录巡检正常" "C0AGXNH7F6J" >> /home/hangn/mason-hub/logs/triggers.log 2>&1

# 2. SRE 每日基础设施报告 (21:00 ET = 01:00 UTC)
0 1 * * * /home/hangn/mason-hub/scripts/run-agent.sh agents/EMP_0004.md "每日基础设施报告：1) 检查 slack-bot 服务状态 2) 检查磁盘和内存 3) 统计过去24小时 agent 调用次数和成功率（从 audit.jsonl）4) 汇总发送到 #system-alerts" "C0AHCMUC057" >> /home/hangn/mason-hub/logs/triggers.log 2>&1

# 3. PM 每周记忆压缩 (周一 22:00 ET = 02:00 UTC)
0 2 * * 1 /home/hangn/mason-hub/scripts/run-agent.sh agents/EMP_0001.md "每周记忆压缩任务：1) 读取 task_list.json 中本周 completed_tasks 2) 读取 agents/memory/EMP_0001/long_term.md 3) 从完成任务中提取可复用经验 4) 更新 long_term.md 5) 汇报压缩结果" "C0AGWBWU0BF" >> /home/hangn/mason-hub/logs/triggers.log 2>&1
```

## 部署步骤

1. SSH 到 GCP：`ssh 34.63.188.198`
2. 编辑 crontab：`crontab -e`
3. 添加上述三条 cron 表达式
4. 确认：`crontab -l | grep triggers`
5. 创建日志文件：`touch /home/hangn/mason-hub/logs/triggers.log`

## 注意事项

- run-agent.sh 使用 `claude -p`（非交互模式），每次调用消耗 token
- 预估成本：PM 巡检 ~$0.05/次，SRE 报告 ~$0.03/次，记忆压缩 ~$0.05/次
- 月度预估：(30 × $0.05) + (30 × $0.03) + (4 × $0.05) = ~$2.60/月
- 远低于 ¥50/月 的成本目标

## 事件触发器（Phase 3 实现）

以下触发器需要后端 event_bus 配合，当前阶段只做规范定义：
- LOW_STOCK：需要在 inventory_movements INSERT 后触发
- EXPIRY_WARNING：可以由每日巡检覆盖
- SALES_ANOMALY：需要在 sales INSERT 后触发统计对比
- SERVICE_DOWN：需要 health-check.sh 在失败时调用 run-agent.sh

这些在 Phase 3 实现时，通过修改 data_coo_agent.py 的 event handler 或新增 webhook 端点实现。
