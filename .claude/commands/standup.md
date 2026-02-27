执行晨会流程：

1. 读取 agents/EMP_0000.md 获取 Meta Manager 角色定义
2. 读取 tasks/backlog.md 了解当前状态
3. 检查 git log --since="yesterday" 获取最近变更
4. 检查 logs/audit.jsonl 最近 24h 的 agent 活动
5. 运行 skills/agent-status-report.sh 获取系统状态
6. 汇总为晨会报告，包含：
   - 昨日完成的工作
   - 系统健康状态
   - 今日待办（从 backlog 提取）
   - 风险和阻塞项
7. 发送摘要到 Slack #system-alerts
