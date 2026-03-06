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
- 需要建：帖子 ID ↔ 商品 ID ↔ 订单时间窗 的自动关联追踪
- 帖子发布后 72h 窗口期内，相关商品订单增量自动归因
- 数据源：MediaCrawler（帖子数据）+ 官方 API（订单数据）
- 消费方：EMP_0008 用来判断内容→转化效果
- **不做手动标记**，跟官方 API 签名鉴权一起建（同一条依赖链）
- 前置：Mason 注册开发者账号 → 接通 API → 拉订单 → 关联

## XHS 采集分析管道 (2026-03-01)

### 管道组件
- `skills/xhs-cookie-check.sh`: Cookie 有效性检测（SSH→阿里云→XHS API），过期自动 Slack 通知
- `skills/xhs-crawl.sh --task 1~4`: 采集调度器，先 cookie 检查再跑 MediaCrawler
- `skills/xhs-analyze.sh`: 数字归一化 + 假流量过滤 + 互动评分 + 爆帖 Top20 + 关键词统计 → JSON
- `skills/xhs-strategy-briefing.sh`: 规则策略推荐（3 号各自内容建议）→ JSON + Slack 摘要

### Cron 调度 (GCP, UTC 时间)
- 周一+周四 22:00 UTC: Task 1 内容灵感
- 周二 22:00 UTC: Task 2 选品情报
- 周三 22:00 UTC: Task 3 竞品监控（关键词待 Mason 提供）
- 每天 22:00 UTC: Task 4 趋势发现（脚本内判断 CST 1号/15号才执行）
- 周六 00:00 UTC: 分析
- 周六 02:00 UTC: 策略简报

### 数据文件路径（阿里云）
- 分析 JSON: /opt/mediacrawler/analysis/weekly_analysis.json
- 策略简报: /opt/mediacrawler/analysis/briefings/YYYY-MM-DD.json
- Schema: ~/mason-hub/shared/xhs-briefing-schema.json

### 待办
- Task 3 竞品关键词待 Mason 提供
- DeepSeek 分析增强待后续加入

## 平台规则完整文档 (2026-03-04)

### 文档位置
- **小红书开放平台**: `intel/processed/小红书开放平台-完整规则文档.md`（1.5MB, 19833 行, 18 章）
  - 来源 1: apifox 114 个 API 端点详情（参数/返回值/示例）
  - 来源 2: 官网 169 页（开发指南/SDK/消息推送/规则中心/平台公告）
  - 覆盖：签名算法、授权流程、商品/订单/售后/物流 API、数据加解密、电子面单
- **微信小店**: `intel/processed/微信小店-完整规则文档.md`（895KB, 27686 行, 18 章）
  - 来源: developers.weixin.qq.com 208 页开发者文档
  - 覆盖：商品管理、订单管理、售后管理、物流管理、资金管理、品牌资质、营销、优选联盟、数据分析、客服、主页管理
- **Google Drive**: `素仁轩-内容中台/01-平台规则/` 下两份文件

### 开发时参考要点
- XHS 签名算法在文档「一、开发指南 > 签名算法」章节，参数排序+MD5
- XHS OAuth 授权流程有自研版和服务商版两种，素仁轩用自研版
- 微信小店的接口凭据获取在「三、接口凭据与通用管理」章节
- 微信小店有免审更新商品的接口（部分字段修改不需要重新审核）
- 两个平台的电子面单对接方式不同，各自有独立章节

## 踩坑记录

### MediaCrawler 首次采集成功 (2026-03-01)
- "韩国护肤" 关键词成功采集 20 条笔记，数据存 `/opt/mediacrawler/database/sqlite_tables.db`
- 表名 `xhs_note`，字段包含：note_id, title, desc, liked_count, collected_count, comment_count, nickname, tag_list, source_keyword, note_url
- Cookie 登录方式可用，无需扫码
- 代理隧道 + cookie 组合正常工作
- 注意：CRAWLER_MAX_NOTES_COUNT 设 5 但实际抓了一页 20 条（搜索结果按页返回，非精确控制）
- Cookie 会过期（几天到几周），过期后需 Mason 重新从浏览器提取
