## TrendRadar 作为上游数据源 (2026-03-08)

### 可用数据
- TrendRadar 每 30 分钟采集 11 个中文热榜 + 10 个 RSS 源，存入本地 SQLite
- 热榜数据: ~/mason-hub/tools/trendradar/output/news/YYYY-MM-DD.db
- RSS 数据: ~/mason-hub/tools/trendradar/output/rss/YYYY-MM-DD.db
- 已配 14 组关键词过滤（韩国护肤/跨境电商/AI工具出海/独立开发者等）

### 如何使用
- Scout 脚本可以直接查询 SQLite 获取趋势数据，不需要自己爬
- 热榜表: news_items（title, url, platform_id, rank）
- RSS 表: rss_items（title, url, feed_id, published_at, summary）
- 部署和维护归 EMP_0002，Scout 只是消费者

### 注意
- 这不替代 Scout 的专项情报搜集（GitHub trending、特定领域深挖），而是提供一个持续的趋势信号底座

## Radar Tracker 新增能力 (2026-03-09)

### 关注率统计
- `/api/weekly-report` 现在返回每组关键词的关注率（1 - dismissed/total_hits）
- 可用于判断哪些关键词组对 Mason 有价值（关注率高）vs 哪些是噪音（关注率低）
- Scout 情报简报可以参考关注率数据，优先深挖高关注率方向

### 每日去重
- Radar Tracker 自动记录 Mason 看过的标题，次日起隐藏已读
- Mason 每天看到的都是新内容，不会重复浏览
- Scout 生成情报时也应注意去重：检查 intel/seen.jsonl + Radar 的 seen_items 表，避免重复推荐
