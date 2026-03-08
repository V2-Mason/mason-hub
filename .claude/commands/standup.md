执行晨会流程：

1. 读取 agents/EMP_0000.md 获取 Meta Manager 角色定义
2. 读取 tasks/backlog.md 了解当前状态
3. 检查 git log --since="yesterday" 获取最近变更
4. 检查 logs/audit.jsonl 最近 24h 的 agent 活动
5. 运行 skills/agent-status-report.sh 获取系统状态
6. 读取 TrendRadar 趋势热榜数据：
   - 打开当天的 SQLite 数据库：~/mason-hub/tools/trendradar/output/news/YYYY-MM-DD.db（热榜）和 ~/mason-hub/tools/trendradar/output/rss/YYYY-MM-DD.db（RSS）
   - 用 Mason 的关键词组（见 ~/mason-hub/tools/trendradar/config/frequency_words.txt）对所有标题做正则匹配
   - 按关键词分组统计命中条数和 top 标题
   - 格式示例：
     ```
     趋势热榜（今日命中 12 条）：
       AI工具出海(3): "xxx", "yyy", "zzz"
       独立开发者(2): "xxx", "yyy"
       内容电商(1): "xxx"
     ```
   - 如果当天 .db 文件不存在或无命中，显示"趋势热榜：今日无命中"
7. 汇总为晨会报告，包含：
   - 昨日完成的工作
   - 系统健康状态
   - 今日待办（从 backlog 提取）
   - 趋势热榜（第 6 步的结果，放在 Scout 情报摘要之后）
   - 风险和阻塞项
8. 发送摘要到 Slack #system-alerts
