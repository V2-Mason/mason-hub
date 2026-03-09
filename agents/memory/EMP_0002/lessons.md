## TrendRadar + RSSHub 趋势监控系统 (2026-03-08)

### 部署概况
- TrendRadar: ~/mason-hub/tools/trendradar/，Python 脚本模式，cron */30 采集
- RSSHub: Docker 容器 diygod/rsshub，端口 1200，--restart always
- 配置备份: tools/trendradar-config/（config.yaml + frequency_words.txt）
- 数据: output/news/ 和 output/rss/ 下 SQLite 按日期分文件
- 不推 Slack，/standup 晨会读 SQLite 汇报

### 数据源
- 11 个中文热榜（百度/微博/抖音/知乎/B站/头条/华尔街见闻/澎湃/财联社/凤凰/贴吧）
- 10 个 RSS 源：3 个走 RSSHub（36氪/虎嗅/HN），7 个原生（ProductHunt/TechCrunch/阮一峰/少数派/a16z/Sequoia/YC）
- 关键词 14 组，配置在 frequency_words.txt

### 维护职责（EMP_0002 负责）
- RSSHub Docker 容器健康检查
- TrendRadar cron 正常运行
- 配置变更后同步 tools/trendradar-config/ 备份
- RSSHub 路由失效时排查替换

### 教训
- TrendRadar 是 clone 的外部仓库（46MB），不提交到 mason-hub git，只备份配置
- RSSHub 公共实例不稳定且有隐私问题，自建更可靠（~150MB RAM）
- Indie Hackers 无 RSS，网站是 SPA
- Sequoia feed 返回 301 但 follow redirect 后正常

## Radar Tracker 关注率 + 每日去重 (2026-03-09)

### 关注率（relevance rate）实现
- 关注率 = 1 - (dismissed / total_hits)，total_hits 从 TrendRadar 每日 SQLite 数据统计
- `_count_weekly_hits(weeks)` 函数遍历 7 天数据，用 `_load_matcher()` 匹配关键词组，算每组总命中数
- `/api/weekly-report` 现在返回 `hits_by_group` + `relevance_by_group`，不再只看绝对 dismiss 数
- 淘汰建议改为：连续两周关注率低于 `RETIRE_THRESHOLD`（默认 50%）
- 注意：RSS 源（华尔街见闻/McKinsey/CB Insights）的命中数取决于 TrendRadar 关键词是否匹配到它们的标题，如果关键词没覆盖到则 hits=0 但 dismiss>0，关注率直接为 0%

### 每日去重实现
- 新增 `seen_items` 表（news_title UNIQUE, source, first_seen_date）
- 逻辑：首次展示时 INSERT OR IGNORE 记录标题，次日起自动隐藏（first_seen_date < today）
- 同一天内刷新不会隐藏（只过滤往日已读）
- 使用和 dismiss 相同的模糊匹配（`_is_dismissed` 函数复用），处理标题微调
- 热榜主页和趋势分析页（/insights）都集成了去重
- 顶部 badge 分别显示"X 个标记无用 + Y 个往日已读"

### 教训
- 用 closure + mutable list `dedup_hidden = [0]` 在 regex callback 中累计计数，比全局变量干净
- batch insert（`executemany` + `INSERT OR IGNORE`）比逐条插入高效，35 条标题一次写入
