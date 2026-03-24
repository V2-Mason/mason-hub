# MediaCrawler 采集系统 (2026-03-01)

## 部署现状
- 位置：阿里云 /opt/mediacrawler/
- 看板：http://106.14.44.68/xhs/
- 数据库：sqlite_tables.db（167 条笔记）
- 采集脚本：自建 _two_tier_crawl.py（不再用 MediaCrawler main.py）
- 源码已 patch 3 处（login.py/core.py/client.py），未提交 git

## XHS Cookie 机制
- **并行采集会触发风控** — 同时跑 3 个任务导致 APP 被踢出登录
- **登录必须走代理** — 否则 cookie 绑阿里云 IP，采集走代理 IP，不一致导致失效
- **真正的登录态标志**：galaxy_creator_session_id / access-token-creator / x-user-id-creator
- **两步验证**：扫码登录后还有 Security Verification QR

## XHS 内部 API 风控
- 搜索 API 风控较松
- Feed API ~50-60次后触发 461 `账号异常`
- 搜索结果已含标题+互动数据，应优先直存

## 踩坑教训
- .env 不自动加载，需手动 load_dotenv()
- 内置 kuaidaili 是 DPS，Mason 买的是 TPS，需自建 tunnel proxy
- **采集绝对不能并行** — 串行跑，每个任务间隔至少几分钟
- SSH heredoc 嵌 Python 代码 → regex 反斜杠被 bash 吃掉，必须用独立 .py 文件
