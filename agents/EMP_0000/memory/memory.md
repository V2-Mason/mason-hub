# EMP_0000 Meta Manager — 记忆库

> 写入规则：每条带日期 + Gap分类标签。主题下追加，不另开文件。
> 浓缩触发：条目超过 150 条时，运行 compact-memory.sh 压缩归档。

---

## 跨域调度经验

### Cron 部署后必须验证首次执行 (2026-02-28)
- Scout 三档 cron 注册后从未实际触发过，但没有人发现
- 规则：新 cron 部署后，必须安排手动触发一次 + 检查 logs 有输出，确认端到端通路
- 不能只看 `crontab -l` 有条目就认为"已部署"

### 每个自动化 agent 必须有手动触发通路 (2026-02-28)
- `run-agent.sh` 无法在 Claude Code session 内执行（`claude -p` 不支持嵌套）
- 因此每个 cron agent 都应有对应的 `/skill` 作为 Mason 手动触发的替代方案
- 两条路径：cron 自动 + `/skill` 手动，缺一不可

### 跨境架构：大使馆模式 (2026-02-28, Mason 确认)
- **核心思路**：不搬 SocialMesh 到中国，也不拆平台模块。在阿里云部署"中国办事处"(china-hub)，作为 GCP 总部在中国的全权代理
- GCP mason-hub = 总部（战略决策 + 全球平台），阿里云 china-hub = 中国办事处（中国平台执行 + 数据合规）
- 敏感数据绝不出境，只传脱敏聚合数据
- **EMP_1000 China Operations Agent**（未来）= 中国区总管，Manager Agent 的唯一中国对话窗口
- **跨境通信协议**（标准化 JSON）：总部→中国 业务目标/策略；中国→总部 脱敏统计/审批请求
- **演进路线**：Phase 1 哑执行网关 → Phase 2 规则引擎 → Phase 3 部署 EMP_1000
- **可扩展**：未来 japan-hub、korea-hub 用同样模式复制

### 数据合规原则：数据不动，人来看 (2026-02-28, Mason 确认)
- 采集的公开数据全部存阿里云，Mason 通过浏览器访问看板查看
- GCP 只收 Slack 一句话通知 + 阿里云看板链接，不存原始数据
- 把原始数据库 scp 到 GCP = 数据出境 = 有合规风险，禁止
- 聚合统计结论（无个体可识别信息）可以推送到 GCP

### XHS 发帖：半自动模式 (2026-02-28, Mason 确认)
- 官方无笔记发布 API，Playwright 自动发帖有封号风险
- SocialMesh 负责内容生产，实际发布 Mason 手动操作（复制粘贴到 APP）
- 新增 READY 状态：排程到时 → 标记 READY → Mason 复制 → 手动发 → 点"已手动发布"
- 其他有官方 API 的平台维持自动发布

### 阿里云基础设施资源架构定位 (2026-02-28, Mason 确认)
- MediaCrawler 和 china-hub 看板属于**基础设施层资源**，不归任何业务 Agent 所有
- EMP_0004 (SRE) 负责部署维护，业务 Agent 按需取用数据
- MediaCrawler 是**数据管道**（定时采集→存库→被动查询），不是 MCP 式的实时工具

### MediaCrawler 集成决策 (2026-02-28)
- 开源项目（44.5k stars），Python + Playwright，部署在阿里云
- 月预算 ¥200：代理 ¥150 + DeepSeek 分析 ¥30 + 预留 ¥20
- 日产能：~6,400 条摘要 + ~120 篇完整内容

---

## Agent 协作 Pattern

### 多 Agent 并行开发成功案例 (2026-03-07)
- **场景**: 视频管线 11 项改动，~10 个文件，871 行新增代码
- **方法**: 分 2 Sprint，每 Sprint 2 个并行 Agent，按文件区域分工
- **结果**: 全部一次通过语法验证，无冲突
- **教训**: 接口字段名必须事先约定（命名歧义会导致对接失败）

### 记忆系统 v2 评估 (2026-03-12, 二次审查)
- v1 运行 13 天：16 个 agent，long_term.md 总计 1862 行
- Top 4: EMP_0008 (336行)、EMP_0014 (300行)、EMP_0003 (209行)、EMP_0002 (183行)
- **已暴露痛点**：① 记忆膨胀无控制 ② 知识重复 ③ 跨 agent 不流通 ④ gap 跟进断裂
- **决策：暂不启动 v2**，标记 3 个 v1.5 改进：Lesson 压缩 / Gap Triage 自动化 / 跨 Agent 经验广播
- v2 触发条件：任一 agent >500行 / 3次以上重复踩坑 / Mason 主动要求
- Gap 分类：📚 纯知识

### L3a/L3b 拆分框架 (2026-03-12)
- L3a 决策型（需要 Mason 判断力，可通过经验积累降级）vs L3b 执行型（一次性门槛队列）
- 降级条件按任务类型区分：可观测结果用成功率自动降级；主观判断用置信度+抽检
- 61 个 L3 任务中 10 个是 L3b 一次性动作，其中 5 个 <5 分钟可完成
- Gap 类型：设计缺口

---

## 技术参考资料

### Gemini API 完整文档 (2026-03-06, Mason 指定)
- **路径**: `intel/processed/Gemini-API-Docs-Complete.md`（45667 行，1.7MB）
- **Google Drive**: ID 1Ls_-ataj3d9TNqcsptkkWRTZZqHuwnpN
- **规则**: Mason 明确要求 — Gemini API 相关问题必须先查此文档
- **核心速查**: 视频生成 `01-models/04-video.md` / 图片生成 `01-models/03-image-generation.md` / 配额 `07-resources/03-rate-limits.md` / 定价 `00-get-started/05-pricing.md`

### 内容管线：一素材多剪 (2026-03-04)
- Pipeline step 8 (multicut) 支持渠道×目标组合，一套 VEO 素材产出多版本
- 5 渠道 × 7 营销目标，参数表给 Gemini 动态判断剪辑方案
- 多剪只加 1 次 Gemini Flash 调用（~$0.01），不增加 VEO 消耗
- 架构文档：`~/socialmesh/docs/plans/2026-03-04-multicut-architecture.md`

---

## 赛道分析

### TrendRadar + RSSHub 上线 (2026-03-08)
- 11 个中文热榜 + 10 个 RSS 源，cron */30 采集
- 部署维护: EMP_0002，数据消费: EMP_0006，赛道判断: Mason 亲自做
- 关键词四层框架：A（现有业务）B（技术能力圈）C（赛道扫描）D（同类人社区）
- C层重点方向：AI工具出海、AI内容电商、抖音/TikTok

### Radar Tracker 关注率 (2026-03-09)
- 关注率 = hits vs dismissed 比率，淘汰阈值 < 50% 连续两周
- 每日去重：Mason 看过的新闻次日自动隐藏

---

## 平台架构

### agent-loader.sh 上线 + run-agent.sh v2 适配 (2026-03-14)
<!-- written: 2026-03-14 · last_ref: 2026-03-14 · ref_count: 1 -->
- EMP_0002 完成 TASK-20260314-001：从 run-agent.sh 提取文件加载逻辑为独立模块
- `scripts/agent-loader.sh`（168 行）：`load_agent_context`（Layer 0/01 分层加载）+ `update_agent_state`（覆写 state.md）
- run-agent.sh 适配：检测 identity.md → v2 loader，否则 fallback 到 config.md
- 这是 v2 文件架构的运行时支撑层——之前只有文件结构，现在 Dispatcher 也能按层加载
- 首次完整走通 message_schema.md 双向通信：EMP_0002 → task_complete → EMP_0000 接收处理
