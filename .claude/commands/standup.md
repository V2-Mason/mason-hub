执行晨会流程：

1. 读取 agents/EMP_0000/config.md 获取 Meta Manager 角色定义
2. 读取 tasks/backlog.md 了解当前状态
3. 检查 git log --since="yesterday" 获取最近变更
4. 检查 logs/audit.jsonl 最近 24h 的 agent 活动
5. 运行 skills/monitoring/agent-status-report.sh 获取系统状态
6. 趋势热榜 — 运行以下命令获取分层趋势报告：
   ```bash
   cd ~/mason-hub && .venv/bin/python3 tools/trendradar-config/trend_report.py
   ```
   直接将输出嵌入晨会报告。如果脚本报错或无输出，显示"趋势热榜：数据不可用"
7. Email Patrol — 检查是否有新的巡查报告或直接运行巡查：
   - 先检查 data/patrol-logs/ 是否有今天的报告（YYYY-MM-DD-patrol.md）
   - 如果有：读取并展示 dashboard 摘要（待处理项数、批量操作数）
   - 如果没有：运行 /email-patrol 执行今日巡查
   - 展示格式按 skills/email-patrol.md 中定义的 dashboard 格式
8. 汇总为晨会报告，包含：
   - 昨日完成的工作
   - 系统健康状态
   - 今日待办（从 backlog 提取）
   - Email Patrol 摘要（第 7 步的结果）
   - 趋势热榜（第 6 步的结果）
   - 风险和阻塞项
9. 发送摘要到 Slack #system-alerts
