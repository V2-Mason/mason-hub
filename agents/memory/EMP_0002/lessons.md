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
