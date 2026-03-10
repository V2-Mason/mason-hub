# 素仁轩 Backlog — Agent 工作任务清单

> **Meta Manager 每日晨会必读此文件**
> 最后更新: 2026-03-10
> 更新人: Session Operator（Scout v2 Engine 架构实现 + 数据管道修复 + 素仁轩 API JWT 认证）

---

## 当前阶段: Phase 3 — 定时任务 + 主动 Agent + 选品闭环

Phase 1（系统骨架）✅ Phase 2（云部署 + AI Agent）✅ 2026-02-27 完成验证。
Phase 3 目标：Agent #0 和 #2 上线，选品建立销量反馈闭环，通知推送到 Mason 手机。

---

## 基础设施现状

### 阿里云 (106.14.44.68) — 生产环境
- surenxuan FastAPI (:8000) — **systemd 管理，Restart=always**
- 数据库: /opt/surenxuan/data/kbeauty.db
- MediaCrawler: /opt/mediacrawler/（Python 3.11 venv + Playwright Chromium + SQLite）— 2026-02-28 部署
- Swap: 1GB /swapfile（fstab 持久化）— 2026-02-28 添加
- 反向SSH隧道: reverse-tunnel.service → GCP:2222
- 隧道保活: tunnel-keepalive.sh (cron */5, 2026-02-26 部署)
- 日志: /var/log/surenxuan.log

### GCP (34.63.188.198) — 指挥中心
- slack-bot (systemd)
- reports (:8080)
- 反向SSH隧道入口 (:2222)
- 隧道保活: tunnel-keepalive.sh (cron */5, 2026-02-26 部署)
- Cron 守护脚本: /opt/surenxuan/scripts/
- Agent 角色文件: ~/mason-hub/agents/EMP_0000~0013.md
- Token 追踪: api_logger.py + claude-logged.sh (2026-02-26 部署)

### Slack (Mason HQ)
- #system-alerts — 守护脚本告警频道
- Webhook: https://hooks.slack.com/services/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

---

## 今日待办（按优先级）

### P0 — 必须今天完成

- [x] GCP Crontab 注册（三个守护脚本） — 2026-02-26 完成，SRE 验证
  ```
  0 */6 * * * /opt/surenxuan/scripts/health-check.sh
  0 0 * * * /opt/surenxuan/scripts/system-monitor.sh
  0 1 * * * /opt/surenxuan/scripts/daily-report.sh
  ```
- [x] 阿里云隧道保活 cron — 2026-02-26 完成，GCP+阿里云双向守护已部署
  - GCP 侧: /opt/surenxuan/scripts/tunnel-keepalive.sh (cron */5)
  - 阿里云侧: /opt/surenxuan/scripts/tunnel-keepalive.sh (cron */5)

### P1 — 今天尽量完成

- [x] 补上 api_usage.jsonl — 2026-02-26 完成，Platform Dev 实现
  - api_logger.py (Python + CLI 双接口)
  - claude-logged.sh (交互式 session 包装)
  - run-agent.sh 已接入，精确 token 追踪（非 unknown）
- [x] shared/ 目录创建 — 2026-02-28 完成，shared/common.sh 共享函数库 + README

### P2 — 排入本周

- [ ] agent.log 结构化 — 当前日志只有纯文本对话输出，不利于审计
- [x] swap 配置评估 — 2026-02-28 完成，阿里云已添加 1GB swap（/swapfile, fstab 持久化）；GCP 暂不需要
- [x] FIX: /standup cron 检测逻辑修复 — 2026-02-27 完成，改为 grep -cE 'mason-hub|surenxuan'，现在正确显示 10 条

---

## Phase 路线图摘要

### Phase 1: 系统骨架 + 手动操作 — 基本完成

**已完成**:
- [x] 两轮 QA 检查 + P0/P1 bug 修复（JWT、SQL注入等）
- [x] 自动化测试 45 个 test cases
- [x] 阿里云服务器购买并部署
- [x] Web 工作台 17 页面 + 130+ API 端点
- [x] 选品→采购→入库→销售→客户 全链路基本跑通

**未完成（带入 Phase 2）**:
- [x] 销售折扣/实付金额功能 — 2026-02-27 完成，summary 增加 total_discount + CSV 导入补 original_price
- [x] 保质期数据贯穿全链路（选品→采购→库存→临期预警）— 2026-02-27 完成，前端增加填写警告 + 补录脚本
- [x] 客户-销售关联（客户详情页显示消费历史）— 2026-02-27 完成，增加折扣和渠道展示
- [x] 退换货基本流程 — 2026-02-27 完成，SalesPage 新增退换货 tab + ReturnsPanel

### Phase 2: 云部署 + AI Agent — 当前阶段

**目标**: 系统稳定运行在云端，Agent #1（选品助手）上线。Mason 在美国可远程管理。

**已完成**:
- [x] 阿里云生产部署 + systemd
- [x] GCP 指挥中心（slack-bot + reports + 反向隧道）
- [x] Cron 守护系统（健康检查/系统监控/日报）
- [x] Agent 角色文件 6 个就位
- [x] Git 版本控制 + 自动化变更追踪
- [x] 阿里云隧道保活（GCP+阿里云双向守护）— 2026-02-26
- [x] api_usage.jsonl token 精确追踪 — 2026-02-26

**待完成**:
- [x] 日报增强（选品指标）— 2026-02-27 完成，generate_report.py 增加选品管线状态
- [x] Agent #1 选品助手接入 LLM API（DeepSeek 为主）— 2026-02-27 完成，llm_client.py 多 provider 支持
- [x] Agent 记忆系统 v1（每个 Agent 独立 memory 空间）— 2026-02-27 完成，agents/memory/ 目录 + 6 个角色 Step 1.5
- [x] API 成本监控 — 2026-02-27 完成，GET /api/intelligence/api-costs 端点

**2026-02-27 运维部署（已完成）**:
- [x] 感知层 cron 实际部署 — 2026-02-27，3 条 cron 已添加到 GCP
- [x] fix_expiry_dates.py 在阿里云执行 — 2026-02-27，dry-run 显示无需补录
- [x] Slack webhook 安全修复 — 2026-02-27，4 脚本改环境变量
- [x] 阿里云+GCP 设置 SLACK_WEBHOOK_URL 环境变量 — 2026-02-27
- [x] DeepSeek API key 配置到系统 — 2026-02-27，provider 已切换
- [x] 代码同步到阿里云生产 + 前端 build + 服务重启 — 2026-02-27

**2026-02-27 代码收尾（已完成）**:
- [x] 录单 UI 增加客户选择提示 — 2026-02-27
- [x] 阿里云数据快照增加 selection 字段 — 2026-02-27，collector.py 已增加
- [x] data_coo.receive_order() 与 purchases.py receive_order() 重复逻辑合并 — 2026-02-27
- [x] 所有代码同步阿里云 + 前端 build + 服务重启 — 2026-02-27

**完成标志**:
- [x] Mason 在美国通过浏览器正常使用系统 — 2026-02-27 验证通过
- [x] Agent #1 完成完整选品流程（上传→过滤→评估→报告）— 2026-02-27 验证通过（准确率改为 Phase 3 持续 KPI，以实际销量衡量而非人工判断）
- [x] API 月度成本 < ¥50 — 2026-02-27 验证通过（月估 ¥2.85，累计 ¥0.57）

**2026-02-27 UX 反馈 Sprint（已完成）**:
- [x] 系统反馈功能上线（浮动按钮 + API + DB）— 2026-02-27
- [x] 退货标记图标修复（RotateCcw → 文字按钮）— 2026-02-27
- [x] 仪表盘"个产品"数字缺失修复 — 2026-02-27
- [x] Dashboard + Intelligence 页面加 loading 骨架屏 — 2026-02-27
- [x] 反馈按钮优化（继续反馈/完成 + 首次气泡提示）— 2026-02-27
- [x] 搜索栏移至顶部 header — 2026-02-27
- [x] PM 角色新增 UX 巡检 + 反馈处理职责 — 2026-02-27
- [x] nginx 504 timeout 修复 + php 扫描拦截 — 2026-02-27
- [x] SQLite NULLS LAST 兼容性修复 — 2026-02-27
- [x] standup cron 检测逻辑修复 — 2026-02-27

**Phase 2 已完成。** 正式进入 Phase 3。

---

### Phase 3: 定时任务 + 主动 Agent + 选品闭环

**目标**: Agent #0（数据COO）和 #2（营销引擎）上线，系统能主动推送通知。选品 Agent 建立销量反馈闭环。

**关键任务**:

P0 — 选品准确率追踪闭环:
- [x] 建立追踪表 — 2026-02-28 完成，selection_tracking.py + DB schema + BatchDetailPage 集成
- [x] 每月回溯报告 — 2026-02-28 完成，selection_monthly_report.py（190 行）+ AI trust ratio 设置
- [ ] 用销售数据反馈优化 Agent 评估模型的权重 — 等销售数据积累

P1 — Agent 上线:
- [x] Agent #0（数据COO）— 2026-02-28 完成，skills/data-coo-daily.sh + cron 08:30 CST，调现有 API 汇总发 Slack
- [x] Agent #2（营销引擎）— 2026-02-28 完成，skills/marketing-daily.sh 数据采集层，现有 cron（CST 10:00）已覆盖话术生成
- [x] 风险提示行动指引 — 2026-02-28 完成，5 种风险类型动态 action_suggestions + 前端可展开跳转

P1 — 通知 + 稳定性:
- [ ] 通知系统: 推送通道待定（Server酱已排除，企业微信/飞书待 Mason 选择）。脚本框架 notify-mason.sh 已就绪，配 key 即可用
- [ ] 记忆系统 v2: 当前 v1 够用（独立记忆 + run-agent.sh 知识注入），v2 共享知识自动沉淀等 Agent 跑一段时间再设计
- [ ] 连续运行 7 天无崩溃 — 观察中

P1 — 开发流程强化 (2026-03-02 superpowers 参考):
- [x] CLAUDE.md 开发铁律 — 2026-03-02 完成，3 条铁律 + 执行检查点 + 反合理化清单 + code review + 设计文档
- [x] Code reviewer agent — 2026-03-02 完成，agents/code-reviewer.md，两阶段审查（spec + quality）
- [x] 设计文档目录 — 2026-03-02 完成，docs/plans/，首份文档：多账号采集架构
- [x] QA Gate 验收系统 — 2026-03-09 完成，shared/qa/（gate1_checks.py 自动验证 + gate2_checklist.md 人工清单 + risk_categories.md 风险分类 + 3 个平台 YAML 参数）
- [x] /commit 智能提交 skill — 2026-03-09 完成，.claude/skills/commit/SKILL.md，5 步流程（盘点→backlog→记忆→commit→汇报）
- [x] EMP_0012 Product Architect 轻量化重写 — 2026-03-09 完成，去掉 Lab 管理/审计扫描，保留两个 Checklist（功能边界 6 问 + Agent 创建 5 问）
- [x] EMP_0008 新增发布前质量门控 — 2026-03-09 完成，Gate 1 自动 → Gate 2 EMP_0008 执行 → Gate 3 Mason 签批
- [x] Lesson Triage 机制 — 2026-03-09 完成，lesson 强制 gap 分类 + EMP_0012 triage + EMP_0000 晨会检查（shared/templates/lesson_format.md）
- [x] 自优化闭环协议 — 2026-03-09 完成，shared/qa/optimization_loop.md，3 轮上限 + 多维目标防漂移
- [x] Gate 2 bias 修正 + Agent 名册 SSOT — 2026-03-10 完成，docs/system/agents.yaml 单一来源 + Gate 2 注入结构化上下文（agent 清单/数据限制/执行容量）+ Step 3 因果推理要求
- [x] 数据中台框架 + EMP_0014 Data Engineer — 2026-03-10 完成，混合式架构（中台+嵌入式分析），data/data_catalog.yaml 盘点 15 个数据集，agents/EMP_0014.md 配置
- [ ] 关键函数单元测试 — parse_count() / interaction_score() / 假流量过滤逻辑，防回归 bug
- [ ] git worktree 工作流 — 重要改动在分支上做，不直接改 main（项目规模变大后启用）

P1 — Agent 基础设施修复 (2026-02-28 讨论产出):
- [x] run-agent.sh 嵌套检测 — 2026-03-05 确认已实现（scripts/run-agent.sh:55-62），检测 CLAUDECODE=1 报错退出（EMP_0002）
- [x] Skills 去重 — 2026-03-05 检查完毕，user 级 skills 目录为空，无重复项（EMP_0002）
- [ ] Scout cron 首次执行验证 — 今晚 23:00 CST 首次触发，明天确认 triggers.log 有输出（EMP_0004）

P1 — Scout 情报系统重构 (2026-02-28 讨论产出):
- [x] Scout 去重机制 — 2026-03-05 确认已实现（scripts/scout-dedup.py + intel/seen.jsonl），9 个 scout 脚本全部已集成 dedup 调用（EMP_0002）
- [x] Scout 简报格式改进 — 2026-03-05 完成，6 个 scout 脚本修改（模糊时间→具体日期，补 markdown 链接），9 个脚本 bash -n 验证通过（EMP_0002）
- [x] Scout 多数据源 — 2026-03-10 完成，Scout v2 search.py 实现 GitHub API + SearXNG(Google/Twitter/DuckDuckGo) + DuckDuckGo fallback 三源统一接口（旧 9 脚本保留但被 Engine 架构取代）
- [ ] 每个 cron agent 配对 /skill — run-agent.sh 无法在 Claude Code 内调用，Mason 手动触发必须有 /skill 替代方案（EMP_0002）

P2 — UX 持续优化:
- [ ] 根据 system_feedback 表持续迭代
- [x] agent.log 结构化 — 2026-02-28 完成，run-agent.sh 新增 log_structured() JSONL 格式
- [x] swap 配置评估 — 2026-02-28（同上）
- [x] 产品去重/合并功能 — 2026-02-28 完成，find-similar API（SequenceMatcher 0.6）+ merge API（9 张关联表）+ 前端 InventoryPage 查找相似 Tab + BatchDetailPage 自动检测警告 badge

**2026-02-28 组织架构调整（已完成）**:
- [x] 新增 EMP_0010 Content Creator 角色 — 2026-02-28，多平台内容生产+社区互动，有状态有记忆
- [x] EMP_0008 PM 升级为内容运营总监 — 2026-02-28，新增内容策略/发布排程/效果复盘/Creator调度职责
- [x] EMP_0007 Domain Manager 新增品牌调性审核职责 — 2026-02-28
- [x] EMP_0006 斥候扩展情报范围 — 2026-02-28，新增内容趋势/电商情报/技术选型侦察(find-skill)
- [x] 新增 3 个 Scout skill — 2026-02-28，scout-find-skill.sh + scout-xhs-trends.sh + scout-ecom-compete.sh
- [x] CLAUDE.md 组织架构更新 — 2026-02-28
- [x] Creator 记忆空间初始化 — 2026-02-28，agents/memory/EMP_0010/

**2026-02-28 PM 巡检 + Bug 修复（已完成）**:
- [x] adapted_title 列 Alembic 迁移 — 2026-02-28，Celery 定时任务崩溃已修复
- [x] XHS disconnect 安全修复 — 2026-02-28，关闭浏览器+清除 cookies+清理引用
- [x] XHS session 竞态条件修复 — 2026-02-28，stale context 重建 + 重复 poll 容错 + 错误日志
- [x] Feedback API 权限修复 — 2026-02-28，按 user_id 过滤
- [x] GEO analyze-raw 端点加认证 — 2026-02-28
- [x] datetime.utcnow() 弃用替换 — 2026-02-28，2 处
- [x] cleanup_stale_pending 注册到 Celery beat — 2026-02-28
- [x] .env.example 同步 + config.py 旧 IP 修复 — 2026-02-28
- [x] 全量代码提交（之前 2302 行裸跑无版本控制） — 2026-02-28，按功能分 8 个 commit

**SocialMesh 内容管线 — 音频架构优化（2026-03-04 加入）**:

> 三轨音频架构已实装（voiceover_writer + tts_generate + assemble 三轨混音），
> 但 CosyVoice TTS 自然度不够（AI 感重、节奏僵硬），需优化。

P1 — TTS 自然度优化:
- [ ] 调参优化：全文一次性生成（不逐段）、限制语速 0.9-1.2（当前 Qwen 给到 1.7-1.9 太快）、换 cosyvoice-v3-plus 模型、试不同音色
- [ ] 如调参不够：换 TTS 引擎（Fish Audio / 豆包 TTS / Azure Neural TTS），tts_generate.py 已做引擎抽象可替换
- [ ] 终极方案：真人录 10s 参考音频 → CosyVoice voice clone 复刻音色；或直接找配音

**SocialMesh 统一 Sprint — 基础功能 + 模块化重构（2026-03-03 合并重排）**:

> 原 Sprint 1 + Sprint 2 合并，去掉与模块化重构冲突的 UI 项，新增 Phase A 代码迁移。
> 产品定义文档：docs/products/socialmesh-v2.md（2026-03-03 Mason 批准）

P0 — 基础功能（模块2 内容管理）:
- [ ] 内容编辑器增加图片上传 — 需前端上传组件 + 后端存储 API + adapter 传递 image_paths（EMP_0009）
- [ ] 内容列表/草稿管理 — 后端 API 已有但前端未接，增加内容列表页或编辑器左侧列表（EMP_0009）
- [ ] 界面中文化 — 先硬编码中文（EMP_0009）
- [ ] Content.status 发布后更新 — publish_post 成功后更新状态为 published（EMP_0009）
- [ ] 内容列表显示发布状态 badge — 已发布/已排程/失败（EMP_0009）

P1 — 模块化代码迁移（Phase A）:
- [ ] 模块1 代码迁移：mason-hub/skills/video-download/ → socialmesh/backend/content/video_pipeline/（EMP_0009）
- [ ] 模块3 代码迁移：mason-hub/skills/ 下 xhs-*.sh + 分析脚本 → socialmesh/scripts/ 或 socialmesh/backend/analytics/（EMP_0009）
- [ ] 依赖项处理：Google OAuth credentials 共享方案、环境变量统一（EMP_0009 + EMP_0004）
- [ ] Agent 角色定义更新：EMP_0008 + EMP_0009 + EMP_0010 加入视频/分析职责（EMP_0012 产出定义，Mason 批准）

P1 — 体验补全:
- [ ] 增加"立即发布"按钮 — 后端已支持，前端补上（EMP_0009）
- [ ] 错误提示可关闭 + 自动消失时间延长（EMP_0009）
- [ ] XHS 标题长度实时校验 — 限制 20 字（EMP_0009）

已完成:
- [x] 发布结果截图展示 — 2026-02-28
- [x] AI 适配内容可编辑 — 2026-02-28
- [x] 发布失败后跳转编辑 — 2026-02-28

砍掉（与模块化重构冲突，等重构后重新设计）→ 已更新 (2026-03-03):
- ~~移动端导航优化~~ — 重构后导航结构大改，现在做会白做
- ~~Dashboard 内容列表可点击~~ — Phase B 会重做 Dashboard
- ~~精简导航栏~~ — 重构后新增模块入口，导航需重新设计
- ~~新用户引导 onboarding~~ — 等重构稳定后再做
- ~~i18n 框架~~ — 等重构稳定后再接
- ~~内容编辑器富文本~~ — 锦上添花，推迟

**小红书对接 (2026-02-28 讨论产出，API 文档审读 + 合规架构确认)**:

> **架构原则**：数据不动，人来看。
> 所有采集数据存阿里云，Mason 通过浏览器访问阿里云看板查看（等同访问任何中国网站）。
> GCP 只收 Slack 一句话通知 + 阿里云看板链接，不存原始数据。
> 官方 API（ARK）只覆盖电商（商品/订单/库存/售后），无笔记/内容 API。
> XHS 自动发帖已改为半自动模式（SocialMesh 准备内容，Mason 手动发布到 APP）。

P0 — 准入 (Mason 手动):
- [ ] 向清谭索取品牌授权书（DAERA + CDL，需包含：授权方/被授权方/品牌/期限，明确可在 xiaohongshu.com 销售，有效期>30天）— 2026-03-09 确认需要
- [ ] 注册小红书企业专业号（蓝V）+ 个体店（个体工商户执照，美容护肤类目，保证金 ¥1,000，支持 0 元开店）— 2026-03-09 确认方案
- [ ] 用素仁轩中国营业执照注册 open.xiaohongshu.com 开发者账号，选「商家后台系统」类目（零成本、权限全）
- [ ] 拿到 appKey / appSecret

P1 — 模块 A：店铺运营 API 对接（官方 API，全部 EMP_0005）:
- [ ] 签名+鉴权模块 — 签名算法（参数排序+MD5）+ OAuth token 获取/自动刷新，代码放 /opt/surenxuan/
- [ ] 商品+库存双向同步 — 拉取 XHS 商品列表对应素仁轩产品 ID，库存增减双向同步
- [ ] 订单+售后自动处理 — 定时拉取新订单，收件人信息解密（调批量解密 API），发货回传快递单号，售后单同步+Slack 通知

P1 — 模块 B：MediaCrawler 采集系统（阿里云本地）:
- [x] 部署 MediaCrawler 到阿里云 /opt/mediacrawler/（Python 3.11 + Playwright + Chromium + Node.js 16+）— 2026-02-28 完成，venv + SQLite 初始化 + 1GB swap 添加，等 Mason 提供 XHS cookie 即可采集
- [x] 配置代理 IP — 2026-03-01 完成，快代理隧道代理（TPS）已配置，出口 IP 验证通过（182.34.xx.xx），阿里云真实 IP 已隐藏
- [x] 采集任务配置 — 2026-03-01 完成，4 类任务（内容灵感/选品情报/竞品监控/趋势发现）
  - xhs-cookie-check.sh: Cookie 有效性检测（多账号），过期按账号 Slack 通知
  - xhs-crawl.sh --task 1~4 --account A|B: 两层采集调度器
- [x] 两层采集架构 — 2026-03-02 完成，搜索 API 广撒网 + Feed API 仅 Top N 深挖，避免风控
- [x] 多账号隔离 + 拟人化 — 2026-03-02 完成:
  - accounts.json 多账号配置（A 号内容博主 + B 号选品生意，主号不碰自动化）
  - 独立浏览器指纹（UA/分辨率）、随机延迟（30-90s 搜索间 / 10-30s 阅读）
  - 关键词每次随机选子集、cron 随机偏移 0-45 分钟
  - Cookie 过期按账号通知
  - 待 Mason: 注册 2 个小号 → 养号 3-5 天 → 提供 cookie
- [x] 分析管道 — 2026-03-02 完成，已在阿里云验证通过（167 条数据）:
  - xhs-analyze-viral.py: 数字归一化（"1.2万"→12000）+ 假流量过滤（评赞比<0.2%/藏赞比<5%）+ 互动评分（赞+藏×3+评×5+转×8）+ 爆帖排行 Top 20 + 关键词统计 + JSON 输出
  - xhs-analyze.sh: SCP 分析脚本到阿里云执行 + Slack 摘要（不再用 SSH heredoc 嵌 Python）
  - _xhs_strategy_briefing.py: 规则策略引擎（干货型/话题型/社交货币型分类）+ 内容建议
  - xhs-strategy-briefing.sh: SCP 策略脚本到阿里云执行 + 读取最新分析 JSON
  - _xhs_slack_summary.py: 独立 Slack 摘要生成器
  - 分析存档: docs/analysis/ + 阿里云 /opt/mediacrawler/analysis/
  - EMP_0008 新增数据分析职责（Mason: "策略必须基于数据"）
  - 周六自动跑（分析 + 简报），cron 待注册
  - **注意**: 主号搜索被 XHS 软封（API 返回 200+success 但 items 为空），等小号就绪后才能采集新数据

P1 — 模块 C：china-hub 分析看板（阿里云本地 :8080）:
- [ ] 看板后端 — FastAPI 查询采集数据库，提供品类热度/爆款排行/竞品分析/关键词监控 API（EMP_0005）
- [ ] 看板前端 — Mason 从美国浏览器直接访问阿里云看板（数据不出境，等同访问中国网站）（EMP_0005）
- [x] Slack 通知集成 — 2026-03-01 完成，采集/分析/简报每步都推送 Slack 摘要到 #socialmesh
- [ ] DeepSeek 分析集成 — 在阿里云本地调 DeepSeek API 分析采集内容（EMP_0005）

P2 — 模块 A 增强:
- [ ] Webhook 实时推送 — 阿里云公网端点接收 XHS 事件推送，替代定时轮询（EMP_0004 配置端口/nginx + EMP_0005 写业务逻辑）

> **月度成本预算 ~¥30**：代理 IP ~¥20（待切换 DPS 按 session 绑定 IP）+ DeepSeek ~¥3
> 每个号每天 200-300 次请求，2-3 个关键词 × 1-2 页 + Top 10 详情
>
> **采集时间窗口**（对齐国内用户活跃时段 + Mason 东部时间方便）:
> - 晚高峰 20:00-22:00 CST（= Mason 07:00-09:00 ET）→ A 号
> - 午休 12:00-13:30 CST（= Mason 23:00-00:30 ET）→ B 号
> - Cron 设窗口起点 + 脚本内随机延迟 0-45 分钟，每天实际时间不同
> - 任务不绑死星期几，每周每号跑 2-3 次，关键词自动轮换
>
> **XHS 账号矩阵（3 台手机 + 3 张 SIM 卡）**:
> - 号 1 素仁轩品牌号：产品介绍/教程/开箱 → 直接导购
> - 号 2 韩国好物种草号：护肤+零食+家居 → 种草引流 + 试探新品类
> - 号 3 韩国生活人设号：代购日常/信任建设 → 私域引流
> 采集数据 3 个号共享，内容生成时分风格输出。扩号到 15 个的前提是验证品类+雇人或 API 开放

**待 Mason 手动处理**:
- [x] SECRET_KEY 替换为强密钥 — 2026-02-28 完成，JWT_SECRET 已配到阿里云 systemd service，服务已重启验证
- [ ] 小红书开发者账号注册（需中国手机号 + 素仁轩营业执照 + 法人信息）
- [x] XHS 采集 cookie 配置 — 2026-03-01 完成，cookie 已填入 MediaCrawler config
- [x] 快代理账号购买 + 隧道代理配置 — 2026-03-01 完成
- [x] MediaCrawler 首次采集测试 — 2026-03-01 完成，"韩国护肤" 关键词成功采集 20 条笔记入库
- [ ] XHS 爬虫小号注册（2 个）— 用不同手机号，养号 3-5 天后提供 cookie
- [ ] XHS 采集 cron 注册 — 等小号 cookie 就绪后注册（晚高峰 A 号 + 午休 B 号 + 每天 cookie 检测）
- [ ] Reddit OAuth API Key 配置 — 需在 reddit.com/prefs/apps 注册
- [ ] LinkedIn OAuth API Key 配置 — 需在 LinkedIn Developer Portal 注册
- [ ] Twitter/X Client Secret 配置 — 需在 developer.x.com 注册

**Radar — Mason 个人情报系统（原 TrendRadar + RSSHub，2026-03-08 正式命名）**:

> 统一产品名：**Radar**。归属 mason-hub 子模块，Platform Dev 维护。
> 三个数据管道：TrendRadar（热榜+RSS 广度采集）、Scout（深度分析）、RSSHub（RSS 转换）。
> 架构：星型拓扑，Mason 为决策中心，所有情报汇聚到他。
> Mason 战略方向：bottom-up（已知业务）+ top-down（新赛道探索）。

已完成:
- [x] RSSHub Docker 自托管 — 2026-03-08，localhost:1200，--restart always
- [x] TrendRadar 部署 — 2026-03-08，~/mason-hub/tools/trendradar/，cron */30
- [x] 11 中文热榜 + 10 RSS 源配置 — 2026-03-08（36氪/虎嗅/少数派/a16z/Sequoia/YC/HN/ProductHunt/TechCrunch/阮一峰）
- [x] 14 组关键词配置（A/B/C/D 四层）— 2026-03-08
- [x] /standup 晨会新增趋势热榜板块 — 2026-03-08
- [x] 配置备份到 tools/trendradar-config/ — 2026-03-08
- [x] RSS 源扩展 10→17 个 — 2026-03-08，新增：The Verge / Ars Technica / MIT Tech Review / McKinsey / CB Insights / Tom's Hardware / Utility Dive（BCG/Bain 无公开 RSS 已跳过）
- [x] 新增关键词组 [基础设施/硬科技] — 2026-03-08，C+ 层，8 匹配词（内存/存储/光纤/电力/储能/HBM/数据中心/算力）+ 14 排除词
- [x] 关键词组总数 14→15 — 2026-03-08

待办:
- [ ] 启用 AI 分析功能 — 需配 DeepSeek API key 到 config.yaml（EMP_0002）
- [ ] 关键词淘汰回顾 — 每两周检查命中质量，替换低效关键词（Mason）→ 已更新见下方点击追踪 (2026-03-08)
- [x] Scout 脚本接入 TrendRadar SQLite — 2026-03-10 完成，Scout v2 spider.py 直读 TrendRadar news/rss SQLite（2163+1494 条），提取本周搜索话题
- [x] Scout 脚本接入 Radar 关注率 API — 2026-03-10 完成，Scout v2 spider.py 读 tracker.db（read_items + dismissals），高关注话题优先搜索

**EMP_0013 店铺运营 Agent（2026-03-09 三方评审定稿）**:

> Agent 状态：设计完成，待开店后激活。
> 三方评审参与者：Product Architect (EMP_0012) + 电商 Domain Manager (EMP_0003) + 素仁轩 PM (EMP_0001)
> Slack 频道：#srx-ops（已创建）
> 设计文档：agents/EMP_0013.md

Phase 1 — 开店日激活（5 个核心职能，匹配小红书 5 维店铺分）:
- [ ] 物流体验：发货时效监控 + 物流异常预警（EMP_0013）
- [ ] 服务咨询：3 分钟响应 SLA 监控 + 买家消息提醒（EMP_0013）
- [ ] 商品体验：差评/负面评价预警 + 商品质量问题追踪（EMP_0013）
- [ ] 售后退款：退货退款流程监控 + 超时预警（EMP_0013）
- [ ] 交易纠纷：纠纷单预警 + 升级阈值 8%（EMP_0013）

Phase 2 — 月均订单 > 100 后启用:
- [ ] 供应链协调：补货建议 + 供应商沟通协议（EMP_0013）
- [ ] 促销活动执行：活动日历 + 库存预留（EMP_0013，限价权限需 PM 审批）
- [ ] 竞品动态追踪：价格/评价/上新监控（EMP_0013）

PM/0013 分工:
- PM (EMP_0001) 管 system_feedback 表 + UX 巡检 + 战略决策
- 0013 管 XHS 买家消息 + 店铺分 + 日常运营执行
- 库存巡检已从 PM 移交 0013（2026-03-09）

P1 — Radar 产品定义（2026-03-08 会议决议）:
- [x] 产品定义文档 — 2026-03-09 完成，docs/products/radar.md（模块间接口 + 反馈回路 + 迭代路径）
- [x] 星型拓扑反馈回路设计 — 2026-03-09 完成，纳入 radar.md（dismiss/read/隐式跳过三种行为数据）

P1 — 话题淘汰点击追踪（2026-03-08 Mason 批准方案 1）:
- [x] HTML 报告加"无用"按钮 — 2026-03-09 完成，inject_dismiss_buttons() + 统一视图直接渲染（EMP_0002）
- [x] 轻量 API 服务 — 2026-03-09 完成，Flask :8081 systemd 托管，GET/POST dismiss + CORS（EMP_0002）
- [x] 每周关注率统计 — 2026-03-09 完成，/api/weekly-report + weekly_report.py CLI（EMP_0002）
- [x] 淘汰建议生成 — 2026-03-09 完成，阈值 30%，需 2 周数据积累（EMP_0002）

**ComfyUI 自建节点 — GPU 实例部署（2026-03-08 加入）**:

> 自建 ComfyUI 节点，直接调官方 API，不经过第三方代理。
> GPU 实例: instance-20260307-184545, Zone: us-central1-a
> Docker: yanwk/comfyui-boot:cu128-slim, 持久化卷 ~/comfyui-storage:/root

P1 — 可灵 Kling Direct 节点（代码已写好，待部署）:
- [x] ComfyUI 节点代码 — 2026-03-08 完成，skills/comfyui-kling-direct/（KlingTextToVideo + KlingImageToVideo）
  - 支持模型: kling-v3-omni / kling-v2-5-turbo / kling-v2-6 / kling-v2-1 / kling-v1-6
  - JWT 认证纯 stdlib，无额外依赖
  - 异步任务轮询，支持 text2video + image2video + tail_image（结束帧控制）
- [ ] 待 Mason: 去 klingai.com/dev 申请 API access_key + secret_key
- [ ] 部署节点到 GPU 实例 Docker 容器 — 等 Mason 启动实例后 SSH 部署
- [ ] 安装 opencv-python-headless 到容器（视频帧提取依赖）
- [ ] 端到端验证: text-to-video + image-to-video 各跑一次

P2 — Seedance 2.0 节点（等官方 API 开放）:
- [ ] 火山引擎 Seedance 2.0 API 开放后，自建 ComfyUI 节点（同 Gemini/Kling 模式）
- [ ] 支持传入参考音频 → 数字人口型同步（Seedance 1.5 Pro 不支持此功能）

P2 — Qwen Image Edit 模型下载（待部署）:
- [ ] 下载 5 个模型文件到 GPU 实例 Docker（总计 ~31GB）:
  - VAE: qwen_image_vae.safetensors (254MB)
  - CLIP: qwen_2.5_vl_7b_fp8_scaled.safetensors (9.38GB)
  - UNET: qwen_image_edit_2509_fp8_e4m3fn.safetensors (20.4GB)
  - LoRA 1: Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors (850MB)
  - LoRA 2: Qwen-Edit-2509-Multiple-angles.safetensors (236MB)

已完成:
- [x] Gemini Direct Pro 节点 — 2026-03-07，skills/comfyui-gemini-direct/，已部署并验证
- [x] fix-comfyui-gemini.sh — NakanoSanku 插件第三方代理修复脚本

**数据中台建设 — EMP_0014 Data Engineer（2026-03-10 Mason 确认混合式架构）**:

> 架构模式：混合式（中台提供工程+工具+标准，业务线嵌入分析师用中台数据）
> 中台职责：管道/存储/加工/目录/SDK，不做业务分析
> 设计文档：agents/EMP_0014.md，数据目录：data/data_catalog.yaml

Phase 1 — 数据治理基础:
- [x] 数据全盘盘点 — 2026-03-10 完成，15 个数据集登记到 data_catalog.yaml
- [x] EMP_0014 角色设计 — 2026-03-10 完成，混合式架构下的分工边界定义
- [x] 数据健康检查脚本 — 2026-03-10 完成，data/pipelines/data_health_check.sh（解析 catalog，检查所有 active 数据集新鲜度/可达性，支持 --slack）
- [x] 统一存储方案设计 — 2026-03-10 完成，docs/plans/2026-03-10-data-unified-storage.md，Mason 选定方案 A（文件同步），方案 C（API 网关）作为 >50MB 触发升级
- [x] 方案 A 实施 — 2026-03-10 完成，data/pipelines/data-sync.sh（sqlite3 .backup + scp + 7 天窗口），optimization-cycle.sh 改读本地 mirror，健康检查 cron 09:15 + 文档刷新提醒 cron 每月 1 日已注册
- [ ] 方案 C 升级（触发条件：数据总量 >50MB）— 阿里云 FastAPI + GCP data_client.py SDK，参考设计文档（EMP_0014，~8-10h）

Phase 2 — 主干管道统一:
- [ ] XHS 主干管道改造 — 采集→分析→briefing→optimization-cycle 用标准接口串联，不再 SSH 读文件（EMP_0014）
- [ ] 管道编排机制 — 上游完成写标记，下游检查后再跑，防止"趋势数据静止"类问题（EMP_0014）
- [x] Scout 产出标准化 — 2026-03-10 完成，data/schemas/scout_intel.yaml（11 字段 schema）+ data/pipelines/scout-normalize.py（digest md → JSONL），23 条情报已提取，data_catalog.yaml 注册 clean_scout_intel

**Scout v2 Engine 架构（2026-03-10 实现，参考 BettaFish）**:

> 设计文档: docs/plans/2026-03-10-scout-v2-design.md
> 代码: intel/engines/（11 个 Python 模块）
> 管道: spider → query → media → insight → forum → report
> 入口: python -m intel.engines.pipeline [--resume] [--force spider,query]

已完成:
- [x] SpiderEngine — TrendRadar + RSS + Radar 关注率 → LLM 提取搜索话题
- [x] QueryEngine — ReflectionNode + 多源搜索（GitHub/SearXNG/DuckDuckGo）
- [x] MediaEngine — Gemini 图片分析（仅图片，不做视频）
- [x] InsightEngine — 内部数据关联（XHS/销售/历史情报）+ DeepSeek 情感分析
- [x] ForumEngine — 话题聚类 + LLM 交叉验证 + 置信度评估
- [x] ReportEngine — IR 中间层 + 动态模板（alert/weekly_full/weekly_light）+ markdown/json/slack 三渲染
- [x] 状态管理 — checkpoint/resume 断点续跑
- [x] 统一 LLM 客户端 — DeepSeek(默认)/Gemini(多模态)/Qwen(交叉验证) 三模型
- [x] SQLite 数据库 — scout.db（topics/intel_items/topic_intel_relation/pipeline_runs）
- [x] 统一搜索接口 — search.py（GitHub API + SearXNG + DuckDuckGo fallback）
- [x] pipeline.py 编排器 — 6 引擎串行 + checkpoint + Slack 通知

待办:
- [ ] SearXNG Docker 部署 — 当前 SearXNG 未运行，搜索 fallback 到 DuckDuckGo（EMP_0002/EMP_0004）
- [ ] Gemini API key 配置 — MediaEngine 需要 GEMINI_API_KEY 才能启用（Mason 后补）
- [ ] 首次端到端测试 — 配好 DASHSCOPE_API_KEY 后 `python -m intel.engines.pipeline` 全流程跑通
- [ ] Scout v2 cron 注册 — 替换旧 scout-*.sh cron 为新管道（EMP_0004）
- [ ] EMP_0006.md 更新 — 加入 Engine 架构职责描述

Phase 3 — 数据 SDK + 扩展:
- [ ] 数据读取 SDK — Python 模块，业务 agent 一行代码获取干净数据（EMP_0014）
- [ ] 加工层标准化 — raw→clean→analysis→report 四层命名 + 指标唯一口径（EMP_0014）
- [ ] 素仁轩历史销售快照 — 定期快照 API 到时序表，支持趋势分析（EMP_0014）

### Phase 4: 事件驱动 + 自主决策（生意稳定后）

**目标**: Agent 不仅按时间运行，还能响应事件自主决策。Mason 从操作者变成审批者。

**场景**:
- 库存降到阈值 → Agent #0 自动生成采购建议 → Mason 审批
- 新客户首次购买 → Agent #2 生成欢迎话术 → Mason 复制发送
- 产品临近保质期 → Agent #0 告警 + Agent #2 生成促销文案
- 客户超过 N 天未购买 → Agent #2 生成唤醒话术

---

## 架构原则（所有 Agent 必须遵守）

1. **记忆物理隔离** — 每个 Agent 独立记忆空间，不互相污染
2. **模型与任务匹配** — 数据查询用 DeepSeek/Haiku，文案用 Sonnet/Opus
3. **Web 系统即 Gateway** — 不另建路由层，现有 Web 工作台就是入口
4. **能力 Skill 化** — 每个能力是独立可插拔模块
5. **记忆驱动成长** — Agent 靠记忆积累变聪明，不靠模型升级
6. **QA 分层迭代** — 第一轮修基础，第二轮修业务逻辑，第三轮压力测试

## 关键约束

- **微信自动化: 绝对禁止** — Phase 4 之前不碰微信自动化，封号风险致命
- **NMPA 合规** — 所有产品必须有备案号、中文标签、授权链
- **成本控制** — 月度 API 成本目标 < ¥50（Phase 2）

---

## 工作流规则

1. **Meta Manager 每日晨会读此文件**，了解当前状态和优先级
2. **任务完成后更新此文件**，标记 [x] 并记录日期
3. **新任务由 Mason 或 Meta Manager 添加**，标注优先级
4. **战略决策（架构变更、新 Phase 进入）由 Mason 通过 Claude.ai 讨论后更新**
5. **执行层（具体部署、编码）由 Agent Team 在 Claude Code 中完成**
