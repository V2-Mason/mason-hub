# Meta Manager 操作手册

> 本文件是 EMP_0000（Meta Manager）的详细操作流程。
> 按需读取，不要在 session 启动时全量加载。

## 每日规划流程

Gateway 每天第一次重巡时发射 `daily-plan-request` 事件。收到此事件时：

1. 读取 `SYSTEM_MAP.md`（能力线状态）
2. 读取 `tasks/backlog.md`（任务池）
3. 读取昨天的审计摘要：`python3 scripts/audit-query.py summary --date <昨天>`
4. 输出 **`data/daily_plan.yaml`**，格式：

```yaml
date: "YYYY-MM-DD"
planner: EMP_0000
priorities:
  - task_id: <kebab-case-id>
    agent: agents/EMP_XXXX/config.md
    description: "任务描述"
    priority: P0|P1|P2
    reason: "为什么今天要做这个"
    mode: serial|parallel_ok
```

Dispatcher 会读此文件并按优先级派发。如果你不生成此文件，Dispatcher fallback 到 autonomous_tasks.yaml 静态扫描。

## Lesson Gap 检查（晨会时执行）

扫描最近 lesson 文件中的 🏗️ / 🔗 标记 → ping EMP_0012 做 triage → 确认条目写入 backlog。

## 团队索引

查看 `docs/system/agents.yaml`（SSOT）。按需查询能力索引：
```bash
python3 scripts/roster/build-capability-index.py --query <能力关键词>
```
