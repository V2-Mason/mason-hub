# EMP_0005 电商 Dev — 长期记忆

## 小红书对接架构 (2026-02-28, Mason 确认)

### 模块 A：店铺运营 API（我负责全部）
- 签名+鉴权模块代码放 /opt/surenxuan/，不做跨项目依赖
- 签名算法：参数字母排序拼接 + method + appSecret → MD5
- OAuth 自研模式：添加店铺 ID → 授权链接 → code → accessToken（10 分钟有效）→ refreshToken 续期
- 商品/库存双向同步 + 订单/售后自动处理

### 模块 B：MediaCrawler 采集（我负责任务配置）
- **架构定位**：MediaCrawler 是基础设施层数据管道（EMP_0004 部署维护），我只负责业务配置
- 4 类采集任务：内容灵感（1,280 摘要+160 详情/月）、选品情报（1,120+12）、竞品监控（120+100）、趋势发现（480+20）
- 我负责：K-Beauty 关键词配置、采集频率、数据入库逻辑
- 数据存阿里云 SQLite，不出境
- 消费方还有：EMP_0010（内容参考）、EMP_0003（竞品决策）、EMP_0001（进货决策）

### 模块 C：china-hub 分析看板（我负责后端+前端）
- FastAPI 看板部署在阿里云 :8080
- 功能：品类热度趋势、爆款排行、竞品分析、关键词监控
- Mason 从美国浏览器直接访问（数据不出境）
- 定期推送 Slack 一句话摘要 + 看板链接
- DeepSeek API 在阿里云本地调用做分析

### 月预算（按需反向计算，非填满预算）
- 代理 IP: ~¥20（~87 个 IP/月，按需采集 3,000 摘要+292 详情）
- DeepSeek 分析: ~¥3
- 代理最低消费预留: ~¥7
- 总计 ~¥30/月

## 部署环境

### 工作目录
- 电商代码：/opt/surenxuan/（我的专属）
- 看板代码：/opt/china-hub/（新增，也归我）
- 采集引擎：/opt/mediacrawler/（EMP_0004 部署，我配置）

### 内容→转化追踪系统（待建）(2026-03-01, Mason 确认)
- 需要建：帖子 ID ↔ 商品 ID ↔ 订单时间窗 的关联追踪
- 帖子发布后 3 天窗口期内，相关商品订单增量
- 数据源：MediaCrawler（帖子数据）+ 官方 API（订单数据）
- 消费方：EMP_0008 用来判断内容→转化效果
- 等官方 API 接通后实现

## 踩坑记录

### MediaCrawler 首次采集成功 (2026-03-01)
- "韩国护肤" 关键词成功采集 20 条笔记，数据存 `/opt/mediacrawler/database/sqlite_tables.db`
- 表名 `xhs_note`，字段包含：note_id, title, desc, liked_count, collected_count, comment_count, nickname, tag_list, source_keyword, note_url
- Cookie 登录方式可用，无需扫码
- 代理隧道 + cookie 组合正常工作
- 注意：CRAWLER_MAX_NOTES_COUNT 设 5 但实际抓了一页 20 条（搜索结果按页返回，非精确控制）
- Cookie 会过期（几天到几周），过期后需 Mason 重新从浏览器提取
