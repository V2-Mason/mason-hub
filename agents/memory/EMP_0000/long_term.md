# EMP_0000 Meta Manager — 长期记忆

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
  - Manager Agent 不直接跟小红书/微信 Connector 交互，只跟 EMP_1000 对话
  - 平台数量增加不影响 Manager Agent 复杂度
- **跨境通信协议**（标准化 JSON）：
  - 总部→中国：业务目标、营销策略、定价指导（无 PII）
  - 中国→总部：销售统计、库存快照、品类趋势（脱敏聚合）
  - 中国→总部：审批请求（脱敏决策上下文）
  - 总部→中国：审批结果（批准/拒绝 + 理由）
- **演进路线**：Phase 1 阿里云做哑执行网关 → Phase 2 加规则引擎 → Phase 3 部署 EMP_1000
- **可扩展**：未来 japan-hub、korea-hub 用同样模式复制
- 注册路径：素仁轩中国主体 → 商家后台系统（自研）→ 未来转 SaaS 时另注册跨境企业 ERP
- 合规红线：数据不跨平台合并、用户退订删数据、XHS 界面不引导去其他平台

### 数据合规原则：数据不动，人来看 (2026-02-28, Mason 确认)
- 采集的公开数据（笔记/互动数据）全部存阿里云，Mason 通过浏览器访问阿里云看板查看
- 等同于 Mason 访问任何中国网站，数据没有跨境传输
- GCP 只收 Slack 一句话通知 + 阿里云看板链接，不存原始数据
- 把原始数据库 scp 到 GCP = 数据出境 = 有合规风险，禁止
- 聚合统计结论（无个体可识别信息）可以推送到 GCP

### XHS 发帖：半自动模式 (2026-02-28, Mason 确认)
- 官方无笔记发布 API，Playwright 自动发帖有封号风险
- SocialMesh 负责内容生产（AI 生成 + 排程管理），实际发布 Mason 手动操作（复制粘贴到 APP）
- 新增 READY 状态：排程到时 → 标记 READY → Mason 复制内容 → 手动发 → 点"已手动发布"
- 其他有官方 API 的平台（Reddit/LinkedIn/Twitter）维持自动发布

### 阿里云基础设施资源架构定位 (2026-02-28, Mason 确认)
- MediaCrawler 和 china-hub 看板属于**基础设施层资源**，不归任何业务 Agent 所有
- 类比：跟 SQLite 数据库、SSH 隧道、Slack Webhook 同一层级 — 谁都可以消费，但谁都不拥有
- EMP_0004 (SRE) 负责部署维护，业务 Agent 按需取用数据
- MediaCrawler 是**数据管道**（定时采集→存库→被动查询），不是 MCP 式的实时工具
- china-hub 看板是 MediaCrawler 数据的消费接口
- 消费方：EMP_0005（选品+看板）、EMP_0010（内容参考）、EMP_0003（竞品决策）、EMP_0001（进货决策）、EMP_0008（排程策略）

### MediaCrawler 集成决策 (2026-02-28)
- 开源项目（44.5k stars），Python + Playwright，支持 XHS 等 7 个平台
- 部署在阿里云 /opt/mediacrawler/，通过代理 IP 采集（保护店铺 API 的 IP）
- 月预算 ¥200：代理 ¥150 + DeepSeek 分析 ¥30 + 预留 ¥20
- 日产能：~6,400 条摘要 + ~120 篇完整内容（K-Beauty 品类分析足够）

## 晨会模式总结

## 技术参考资料

### Gemini API 完整文档 (2026-03-03, Mason 要求记忆)
- **单文件版**: Google Drive — https://drive.google.com/file/d/1Ls_-ataj3d9TNqcsptkkWRTZZqHuwnpN/view?usp=drivesdk
- **分文件版**: Google Drive — https://drive.google.com/file/d/1nr5jfoCsY1onoFNlcjGtD4ChsAal2C9r/view?usp=drivesdk (tar.gz)
- **本地路径**: /tmp/gemini-api-docs/ (74 个 md 文件，按官网目录分 11 个子目录)
- **合并文件**: /tmp/gemini-api-docs-all.md (1.6 MB，全部合并)
- **来源**: https://ai.google.dev/gemini-api/docs (2026-03-03 下载)
- **用途**: 内容管线大量使用 Gemini API（VEO 视频生成、Nano Banana 图片生成、Flash 文本处理），遇到 API 问题时先查本地文档
- **核心章节速查**:
  - 视频生成 (VEO): `01-models/04-video.md`
  - 图片生成 (Nano Banana/Imagen): `01-models/03-image-generation.md`, `01-models/06-imagen.md`
  - 配额与限制: `07-resources/03-rate-limits.md`
  - 定价: `00-get-started/05-pricing.md`
  - Context Caching: `05-guides/05-caching.md`
  - 文件上传 API: `05-guides/04-files.md`
  - Batch API: `05-guides/02-batch-api.md`
  - 结构化输出: `02-capabilities/08-structured-output.md`

### 内容管线：一素材多剪能力上线 (2026-03-04)
- Pipeline step 8 (multicut) 支持渠道×目标组合，一套 VEO 素材产出多版本成片分发不同渠道
- 5 渠道（抖音/小红书/视频号/微信私域/产品聚焦）× 7 营销目标（认知/种草/教育/信任/促销/复购/互动）
- **设计决策**：参数表是给 Gemini 的风格指南，不是 ffmpeg 硬编码 — Gemini 看完实际素材后动态判断具体剪辑方案
- **成本影响**：多剪只加 1 次 Gemini Flash 调用（~$0.01），不增加 VEO 消耗（复用素材）
- **数据闭环规划**：Layer 1 剪辑指纹已上线 → Layer 2 按渠道/品类统计（待 10-15 个视频积累后） → Layer 3 发布数据回流
- **架构文档**：`~/socialmesh/docs/plans/2026-03-04-multicut-architecture.md`
- **Pipeline CLI**：`--cuts "抖音×认知型,小红书×种草型"`，不带则走 simple concat（向后兼容）

## 参考文档索引

### Gemini API 完整文档 (2026-03-06, Mason 指定)
- **路径**: `intel/processed/Gemini-API-Docs-Complete.md`（45667 行，1.7MB）
- **Google Drive**: `Gemini-API-Docs-Complete.md`（ID: 1Ls_-ataj3d9TNqcsptkkWRTZZqHuwnpN）
- **用途**: 所有关于 Gemini API 的问题（定价/配额/模型能力/rate limits/policy），优先查这份文档，不要去网上搜
- **覆盖内容**: Gemini 全系列模型、Imagen、VEO、文本/图片/视频生成、API 调用方式、免费层/付费层区别
- **规则**: Mason 明确要求 — Gemini API 相关问题必须先查此文档

## Agent 协作 Pattern
