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
