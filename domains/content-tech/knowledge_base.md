# Content-Tech Domain Knowledge Base
# 适用范围：所有内容技术类 project（社媒管理、GEO 优化、内容营销）
# 最后更新：2026-02-27

## GEO（Generative Engine Optimization）

### 核心概念
- GEO 是针对 AI 搜索引擎（ChatGPT、Perplexity、Google AI Overview）的优化
- 目标：让你的内容被 AI 引用（citation），而不仅仅是被搜索引擎索引
- 与 SEO 的关系：GEO 是 SEO 的进化，SEO 优化排名，GEO 优化引用概率

### GEO 评分维度
- **引用友好度**：内容是否有明确的 claim + evidence 结构
- **实体覆盖**：是否提及关键实体（品牌、产品、概念）
- **结构化程度**：是否有清晰的标题层级、列表、表格
- **独特价值**：是否提供独家数据、原创观点、一手经验
- **时效性**：内容是否标注日期、是否定期更新

### GEO 优化技巧
- 使用"根据[来源]，..."的引用格式，增加可信度
- 提供具体数据和统计数字，AI 倾向引用有数据支撑的内容
- 内容开头 200 字包含核心观点，AI 摘要优先读取开头
- 使用 FAQ 格式回答常见问题，匹配 AI 搜索的问答模式

## 平台 API 规则与限制

### Reddit
- **API 类型**：官方 REST API（免费，需注册 app）
- **认证**：OAuth 2.0（script 类型即可）
- **速率限制**：60 请求/分钟（authenticated）
- **发帖限制**：每账号每 10 分钟 1 帖（新账号更严格）
- **关键规则**：
  - 禁止纯推广内容（需符合 subreddit 规则）
  - self-promotion 比例不超过 10%
  - Karma 不够的新号会被 shadowban
- **最佳实践**：先养号（评论互动），再发帖；内容要有价值，不是广告

### 小红书 (XHS)
- **API 类型**：无公开 API，需 Playwright 浏览器自动化
- **发布方式**：模拟真人操作（登录→创建笔记→上传图片→发布）
- **反爬策略**：指纹检测、行为分析、验证码
- **关键规则**：
  - 图文笔记：封面图决定点击率，正文 500-1000 字最佳
  - 标题不超过 20 字，带 emoji 提升点击
  - Hashtag 选择：1-2 个大流量 + 3-5 个精准长尾
  - 发布时间：早 7-9、午 12-14、晚 18-21 效果最佳
- **风险**：账号被限流、内容被折叠、账号被封

### LinkedIn
- **API 类型**：官方 REST API（需创建 LinkedIn App）
- **认证**：OAuth 2.0（需申请 Marketing API 或 Community Management API）
- **速率限制**：100 请求/天（基础），更高需申请
- **发帖限制**：文字贴免费 API 可发，图片/视频需 Marketing API
- **关键规则**：
  - 长文（article）和短帖（share）走不同 API
  - 个人贴 vs 公司页贴权限不同
  - 内容偏专业/行业洞察，纯营销效果差

### X/Twitter（Phase 2）
- **API 类型**：REST API v2
- **费用**：Free tier 极度受限（1500 帖/月读取，仅发帖）
  - Basic: $200/月（10k 帖/月读取）
  - Pro: $5000/月
- **速率限制**：Free tier 50 请求/24 小时
- **关键规则**：
  - 280 字符限制（Premium 用户 25000）
  - 媒体上传走单独 API
  - 自动化发帖需要标注为 automated

### TikTok（Phase 2）
- **API 类型**：Content Publishing API（需审批）
- **审批流程**：需要公司实体申请，个人开发者困难
- **限制**：仅支持视频内容，图文需走 Photo Mode API
- **替代方案**：Playwright 自动化（类似 XHS 方案）

## 内容适配最佳实践

### 一条内容 → 多平台版本
- **核心原则**：同一主题，不同表达方式，适配平台调性
- **不是简单改格式**：每个平台的用户期望不同，需要重写而非复制

### 平台调性差异
| 平台 | 调性 | 内容长度 | 媒体偏好 | 互动方式 |
|------|------|----------|----------|----------|
| Reddit | 深度讨论、真实经验分享 | 长文（500-2000 字） | 可选配图 | 评论回复 |
| 小红书 | 种草、攻略、生活方式 | 中等（500-1000 字） | 必须配图 | 收藏 > 点赞 > 评论 |
| LinkedIn | 专业洞察、行业分析 | 中等（300-1500 字） | 可选 | 转发 > 评论 |
| X/Twitter | 快速观点、热点跟进 | 短（280 字） | 可选 | 转发 > 点赞 |
| TikTok | 娱乐、教学、展示 | 视频为主 | 必须视频 | 点赞 > 评论 |

### 适配流程
1. 撰写核心内容（平台无关的主题和观点）
2. LLM 根据平台调性生成不同版本
3. 人工审核和调整（特别是 XHS 的 emoji 和 hashtag）
4. GEO 评分检查（确保每个版本都 GEO 友好）
5. 排程发布（考虑各平台最佳发布时间）

## 社媒算法要点

### 通用规则
- 发布后 1 小时的互动数据决定推荐量级
- 完读率/完播率比点赞更重要
- 定期发布比偶尔爆款更有利于账号权重
- 评论区互动能显著提升内容分发

### 内容营销指标
- **曝光量**：内容被展示的次数
- **点击率 (CTR)**：标题/封面的吸引力
- **互动率**：（点赞+评论+转发+收藏）/ 曝光量
- **AI 引用率**：内容被 AI 搜索引擎引用的次数（GEO 核心指标）

## 踩过的坑
（随项目积累持续更新）

## 成功模式
（随项目积累持续更新）

## 开发规范（适用于 Content-Tech Dev EMP_0009）

### 代码风格
- Python: Black (line-length=100, py311), snake_case, type hints on public functions
- JavaScript/React: Prettier (printWidth=100, singleQuote), const by default, PascalCase for components
- SQL: 关键字大写（SELECT, WHERE, JOIN）

### Git 工作流
- Commit format: type(scope): description (feat/fix/refactor/style/docs/perf/chore/test)
- Branch format: type/short-description
- 每个完成的任务必须提交，保持 atomic commits
- 禁止 force-push、禁止提交 .env 和数据库文件
