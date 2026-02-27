# 素仁轩 Backlog — Agent 工作任务清单

> **Meta Manager 每日晨会必读此文件**
> 最后更新: 2026-02-27
> 更新人: Meta Manager (via Claude Code)

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

### GCP (34.68.172.191) — 指挥中心
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
- [ ] shared/ 目录创建 — 角色文件引用了这个路径但不存在

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
- [ ] 建立追踪表：记录 Agent 推荐得分 → Mason 采购决策 → 实际销量/毛利/周转
- [ ] 每月回溯报告：Agent 推荐且采购的品表现如何、未推荐但自选的品表现如何
- [ ] 用销售数据反馈优化 Agent 评估模型的权重

P1 — Agent 上线:
- [ ] Agent #0（数据COO）: 每日库存巡检 + 每周报告
- [ ] Agent #2（营销引擎）: 每日客户跟进建议 + 话术生成
- [ ] 风险提示行动指引：风险卡片 → 行动报告 → 跳转操作页（轻量版先做跳转，完整版靠 Agent #0）

P1 — 通知 + 稳定性:
- [ ] 通知系统: Server酱或企业微信 webhook → Mason 手机
- [ ] 记忆系统 v2: 三个 Agent 独立记忆 + 共享知识层
- [ ] 连续运行 7 天无崩溃

P2 — UX 持续优化:
- [ ] 根据 system_feedback 表持续迭代
- [ ] agent.log 结构化
- [ ] swap 配置评估

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
