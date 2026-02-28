# 素仁轩 Backlog — Agent 工作任务清单

> **Meta Manager 每日晨会必读此文件**
> 最后更新: 2026-02-28
> 更新人: EMP_0008 PM 巡检 + Bug 修复

---

## 当前阶段: Phase 3 — 定时任务 + 主动 Agent + 选品闭环

Phase 1（系统骨架）✅ Phase 2（云部署 + AI Agent）✅ 2026-02-27 完成验证。
Phase 3 目标：Agent #0 和 #2 上线，选品建立销量反馈闭环，通知推送到 Mason 手机。

---

## 基础设施现状

### 阿里云 (106.14.44.68) — 生产环境
- surenxuan FastAPI (:8000) — **systemd 管理，Restart=always**
- 数据库: /opt/surenxuan/data/kbeauty.db
- 反向SSH隧道: reverse-tunnel.service → GCP:2222
- 隧道保活: tunnel-keepalive.sh (cron */5, 2026-02-26 部署)
- 日志: /var/log/surenxuan.log

### GCP (34.63.188.198) — 指挥中心
- slack-bot (systemd)
- reports (:8080)
- 反向SSH隧道入口 (:2222)
- 隧道保活: tunnel-keepalive.sh (cron */5, 2026-02-26 部署)
- Cron 守护脚本: /opt/surenxuan/scripts/
- Agent 角色文件: ~/mason-hub/agents/EMP_0000~0005.md
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
- [ ] swap 配置评估 — GCP 内存 47%，暂时不急，但没有 swap 缓冲
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

P2 — UX 持续优化:
- [ ] 根据 system_feedback 表持续迭代
- [x] agent.log 结构化 — 2026-02-28 完成，run-agent.sh 新增 log_structured() JSONL 格式
- [ ] swap 配置评估
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

**SocialMesh Sprint 1 — 核心流程打通（2026-02-28 排入）**:

P0 — 阻断核心流程:
- [ ] 内容编辑器增加图片上传 — 小红书不允许纯文本发帖，目前自动生成占位纯色图。需前端上传组件 + 后端存储 API + adapter 传递 image_paths（EMP_0009 Dev）
- [ ] 内容列表/草稿管理 — Save Draft 后找不回来，后端 API 已有但前端未接。增加内容列表页或编辑器左侧列表（EMP_0009 Dev）
- [ ] 界面中文化 — 所有 label/placeholder/button 全英文，素仁轩用户无法使用。先硬编码中文（EMP_0009 Dev）

P1 — 提升体验:
- [ ] 增加"立即发布"按钮 — 后端 `/schedule/{id}/publish-now` 已支持，前端编辑器只有 Schedule 没有 Publish Now（EMP_0009 Dev）
- [ ] 移动端导航优化 — 7 个 tab 横向排列手机端溢出，需改为汉堡菜单或底部 tab bar（EMP_0009 Dev）
- [ ] Dashboard 内容列表可点击 — 近期内容 `<li>` 无 onClick，点击应跳转编辑器加载对应内容（EMP_0009 Dev）
- [ ] 精简导航栏 — GEO 独立页已内嵌在编辑器中（重复），Feedback 有浮动按钮入口，可隐藏/合并到 5 个核心 tab（EMP_0009 Dev）
- [x] 发布结果截图展示 — 2026-02-28，Schedule 页面已发布帖子增加"查看截图"按钮，modal 展示 base64 截图 + 创作中心链接
- [ ] 错误提示可关闭 + 自动消失时间延长 — 错误类消息 4 秒消失太快，应保持直到用户关闭（EMP_0009 Dev）

P2 — 锦上添花:
- [ ] 新用户引导 onboarding — 0 账号/0 内容时显示步骤引导（EMP_0009 Dev）
- [ ] i18n 框架接入 — react-i18next，为多语言做准备（EMP_0009 Dev）
- [ ] 内容编辑器富文本 — textarea 升级为 TipTap 等（EMP_0009 Dev）
- [x] AI 适配内容可编辑 — 2026-02-28，`<pre>` 改为 `<textarea>`，用户可直接修改文案，排程时自动保存编辑版本到 DB
- [ ] XHS 标题长度实时校验 — 限制 20 字，编辑器无字数提示（EMP_0009 Dev）
- [x] 发布失败后跳转编辑 — 2026-02-28，Failed 帖子增加"编辑内容"按钮，跳转 `/content?id=xxx`

**SocialMesh Sprint 2 — 发布状态闭环（从 team agents 残留任务提取）**:

P1 — 发布状态:
- [ ] Content.status 发布后更新 — publish_post 成功后检查是否所有 PlatformPost 已发布，更新 Content.status 为 published；collect_metrics 只更新 metrics 键，不覆盖 screenshot/post_id（EMP_0009 Dev）
- [ ] 内容列表显示发布状态 — ContentEditor 内容列表每条显示各平台发布状态 badge（已发布/已排程/失败），后端 content list API 需附带 platform_posts 摘要（EMP_0009 Dev）

**待 Mason 手动处理**:
- [x] SECRET_KEY 替换为强密钥 — 2026-02-28 完成，JWT_SECRET 已配到阿里云 systemd service，服务已重启验证
- [ ] Reddit OAuth API Key 配置 — 需在 reddit.com/prefs/apps 注册
- [ ] LinkedIn OAuth API Key 配置 — 需在 LinkedIn Developer Portal 注册
- [ ] Twitter/X Client Secret 配置 — 需在 developer.x.com 注册

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
