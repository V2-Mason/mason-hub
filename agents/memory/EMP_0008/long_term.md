# EMP_0008 Long-Term Memory

## 项目里程碑
- 2026-02-27: 项目从 0 到 MVP 全栈搭建完成（FastAPI + React + PostgreSQL + Celery + Playwright）
- 2026-02-27: XHS Playwright QR 登录流程调通，Mason 成功扫码连接
- 2026-02-27: 内容适配引擎上线（OpenAI gpt-4o-mini 主力 + Anthropic Haiku 备用）
- 2026-02-27: 第一轮 QA + bug 修复完成（7 个 bug 修复）

## 踩过的坑
- XHS QR 截图：必须用 element-specific screenshot（.qrcode-container），全页截图太小看不清
- check-login 不能 reload 页面，否则 QR 码会刷新，用户扫了等于白扫
- 适配接口返回格式必须是 array（不是 dict），否则前端 Array.isArray() 判断会丢弃结果
- OAuth 字段名 authorize_url vs authorization_url 不一致会导致按钮静默失效
- Playwright persistent context 的 session 持久化在 headless 模式下可能不可靠

## 有效模式
- bug 修复用 team agent（1 个 QA + 1 个功能开发），并行效率最高
- 每次改动后先 python3 -c "from backend.main import app" 验证导入，再重启服务
- 前端用 npx vite build --mode development 验证编译，比等 dev server 自动刷新更可靠

## Mason 偏好
- 喜欢一体化流程，不要碎片化操作（写内容 → 适配 → 发布应该是一个连贯体验）
- 不喜欢"Coming Soon"标签，要么能用要么别显示
- 加载慢的操作必须有明确的等待提示

## XHS 发帖流程变更 (2026-02-28, Mason 确认)
- XHS 从全自动改为**半自动**：SocialMesh 准备内容 → READY 状态 → Mason 手动复制粘贴到 APP → 点"已手动发布"
- 新增 READY 状态（紫色标签），排程到时自动触发，不再调 Playwright
- 其他有官方 API 的平台（Reddit/LinkedIn/Twitter）维持自动发布
- 3 个 XHS 号的排程管理：每个号每天 2-3 条，内容风格差异化（品牌风/种草风/人设风）
- MediaCrawler 采集的趋势数据可以作为排程策略参考（如某品类本周热度高 → 优先排相关内容）

## 内容分析职责 (2026-03-01, Mason 确认)

### 我是分析层 owner
- 负责定分析规则、判断什么内容值得复刻、制定内容策略
- 采集数据来源：MediaCrawler → /opt/mediacrawler/database/sqlite_tables.db（xhs_note 表）
- 分析维度：内容形式(video/image)、标题套路、标签策略、互动比(赞/藏/评)、主题分类

### 爆帖拆解方法
- 藏赞比高 = 实用型内容（教程、攻略），评赞比高 = 争议型内容
- 不看绝对赞数判断质量，看**内容→转化**（帖子发出后相关商品订单是否增长）
- 素人爆帖比大号爆帖更值得学（说明内容本身有力量）

### 假流量过滤信号
- 评赞比异常低（1 万赞 20 条评论 → 大概率刷量）
- 评论质量低（全是"好好看""收藏了"水评）
- 藏赞比异常（刷量帖点赞高但收藏低）
- 粉互动不匹配（50 万粉帖子常年几百赞 → 粉丝买的）

### 内容→转化闭环（与 EMP_0001 配合）
- EMP_0001 提供官方 API 订单数据（帖子发布后 3 天窗口期内相关商品订单变化）
- 我负责将转化数据与内容 pattern 关联，产出结论：哪类内容真正带单
- **核心原则**：不靠赞数判断成败，靠自己的实际订单
- 评论中的购买意图（"怎么买""求链接"）比点赞数更有参考价值

### 输出给 EMP_0010 Creator
- 每周产出"本周内容策略简报"：爆帖规律 + 推荐内容方向 + 3 个号的差异化建议

### 采集数据可用范围 (2026-03-02)
- **搜索结果已含**：标题(display_title)、互动数据(liked_count/collected_count/comment_count/shared_count)、作者(nickname)、发布日期(corner_tag_info)、内容类型(video/normal)
- **笔记详情额外有**：正文(desc)、标签(tag_list)、视频URL — 但 feed API 容易触发风控
- **结论**：搜索结果足够做内容分析（爆帖排行、互动比、关键词趋势），不依赖笔记详情
- **影响**：分析脚本(xhs-analyze.sh)如果只用搜索结果数据，需调整字段名映射
- 采集不能一次跑完所有任务，必须按 cron 分散（每天一个任务），否则触发账号风控

### 自动化管道已上线 (2026-03-01)
- 采集→分析→策略简报完整管道已部署（GCP cron 触发）
- 每周六自动生成 weekly_analysis.json + briefings/YYYY-MM-DD.json
- 策略简报自动推 Slack #socialmesh，含 3 号内容建议
- 当前用规则引擎（藏赞比→教程类，评赞比→话题类），DeepSeek 增强待后续
- 策略简报路径：阿里云 /opt/mediacrawler/analysis/briefings/
- Schema 定义：~/mason-hub/shared/xhs-briefing-schema.json

### 首次爆款分析实战 (2026-03-02, 167 条数据)
- 分析脚本: `skills/xhs-analyze-viral.py`，在阿里云跑，报告存 `docs/analysis/`
- **视频互动分是图文的 2.7 倍**（67,670 vs 24,654）— 内容策略应以视频为主
- **藏赞比 >100% 的帖子**（收藏>点赞）= 干货清单类，长尾流量大（oliveyoung必买清单、伴手礼合集）
- **高转赞比帖子**共同特征：实用攻略 + 明确场景（"去韩国变美省20000块"）
- **"oliveyoung" + "必买/清单/攻略"** 是韩国护肤赛道的流量密码
- **标题含数字**互动分高 32%（69,534 vs 52,710）
- **品牌测评类**（SOME BY MI、COSRX）互动远低于场景类（韩国护肤、韩国好物）— 用户不爱看品牌硬推
- 假流量检测阈值：评赞比<0.2%且赞>1000 或 藏赞比<5%且赞>1000
- **待改进**：正文内容分析、标签组合分析、时间维度分析还没做

### 多账号 + 拟人化采集架构 (2026-03-02, Mason 确认)

**账号隔离**:
- A 号（内容博主）→ Task 1 内容灵感 + Task 4 趋势发现
- B 号（选品生意）→ Task 2 选品情报 + Task 3 竞品监控
- 主号（素仁轩运营号）→ 绝不碰自动化，只用手机 APP 手动
- 每个号有独立浏览器指纹（UA、分辨率）

**拟人化策略**:
- Cron 触发后随机延迟 0-45 分钟
- 关键词每次随机选子集（不全搜），隔 2-3 天才重搜同一个词
- 搜索间 30-90 秒随机延迟，详情间模拟阅读 10-30 秒
- 启动先逛首页暖场（随机滚动）
- 采集时间窗口对齐国内用户活跃时段（晚 20-22 CST = Mason 早 7-9 ET）

**配置文件**:
- 账号配置：阿里云 /opt/mediacrawler/accounts.json（cookie + 指纹）
- 模板：~/mason-hub/shared/accounts.template.json
- Cookie 不再存 base_config.py，改存 accounts.json

**数据量控制**:
- 每个号每天 200-300 次请求（正常用户刷 1-2 小时的量）
- 每次只搜 2-3 个关键词 × 1-2 页 = 40-120 条搜索结果
- 详情深挖只取 Top 10
- 一天跑 1 个 session（~30 分钟）
