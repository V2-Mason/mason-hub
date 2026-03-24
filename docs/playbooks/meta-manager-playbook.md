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

## Agent 自主度评估流程（每月执行）

每月 heartbeat 或 Mason 要求时触发。评估所有活跃 Agent 的自主运行能力。

### 步骤

1. **采集数据**（每个 Agent）：
   - `agents/EMP_XXXX/state.md` — 近 30 天任务完成记录
   - `agents/EMP_XXXX/memory/memory.md` — 经验积累和错误记录
   - `audit.jsonl` — 该 Agent 的 task_complete / task_failed 事件

2. **逐维打分**（5 维度，各 1-5 分）：
   - 任务完成率：自主完成 vs 需人工介入的比例
   - 决策质量：escalate 是否恰当（不该 escalate 的是否自主处理了）
   - 异常恢复：遇错后的处理能力（停下 / 重试 / 自愈）
   - 输出稳定性：输出是否持续符合质量标准和格式契约
   - 协作效率：消息响应、上下游通知是否及时准确

3. **生成报告**：
   ```
   data/reports/autonomy-assessment-YYYY-MM.md
   ```
   格式：每个 Agent 一个小节，含分数 + 证据 + 趋势 + 建议

4. **行动分流**：
   - 总分 ≤12 → escalate Mason，附具体提升建议
   - 总分 13-19 → 正常，记录存档
   - 总分 ≥20 → 高自治，可考虑扩展权限

5. **更新 SYSTEM_MAP** — 将评估结论同步到对应能力线

### 注意事项
- 新 Agent（上线 <30 天）标"观察期"，不强制评分
- 基于客观记录打分，不主观推测
- 方法论调整需 Mason 确认

## 团队索引

查看 `docs/system/agents.yaml`（SSOT）。按需查询能力索引：
```bash
python3 scripts/roster/build-capability-index.py --query <能力关键词>
```
