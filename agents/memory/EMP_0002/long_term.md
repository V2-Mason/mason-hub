# EMP_0002 Platform Dev — 长期记忆

## 平台架构经验

### Skills 去重 (2026-02-28)
- `~/.claude/skills/` (user 级) 和 `~/mason-hub/.claude/skills/` (project 级) 存在同名 skill，导致系统提示里重复显示
- 应统一保留一套，推荐 project 级（跟 git 走）

### `run-agent.sh` 嵌套限制 (2026-02-28)
- `claude -p` 不支持在 Claude Code session 内嵌套调用，会静默挂死无报错
- 应在 `run-agent.sh` 入口加检测：`if [ "${CLAUDECODE:-}" = "1" ]; then echo "ERROR: 不能从 Claude Code session 内调用"; exit 1; fi`
- 每个 cron agent 都应有对应的 `/skill` 作为手动触发替代方案

### Scout 系统重构待办 (2026-02-28)
- 当前 9 个 scout 脚本全部只用 GitHub REST API，包括名为 `xhs-trends` 的脚本也搜的是 GitHub
- 需要引入真正的多数据源：Google/Web → Gemini，X/Twitter → xAI Grok，小红书 → DeepSeek
- 需要实现去重机制：维护 `intel/seen.jsonl`（repo name + 首次报告日期 + 上次 star 数），新项目标 🆕，已知项目仅在 star 变化显著时报告 📈，无变化不报
- 情报简报格式改进：每条标题直接是可点击链接 + 具体日期，不要链接和信息分离

### 阿里云 china-hub 架构：大使馆模式 (2026-02-28)
- **定位**：不是某平台的专属模块，而是 GCP 总部在中国的"全权代理"区域节点
- 管理所有中国平台（小红书、微信、未来抖音/拼多多等），向 GCP 汇报脱敏聚合数据
- **关键设计原则**：每个 Connector（小红书/微信/...）和每个能力（脱敏/加密/订单处理）都是独立可调用的服务模块
  - 现在由 GCP 远程调用
  - 未来 EMP_1000 China Operations Agent 上线后，在本地直接调用同样的服务，零改动
- **数据网关**：接收平台原始数据 → PII 加密存储 → 脱敏聚合 → 推送到 GCP
- 两种数据流：实时流（Webhook 事件脱敏摘要）+ 批量同步（每日聚合统计）
- 执行引擎：接收 GCP agent 指令（只含 ID 引用），本地查询敏感数据后调 API 执行
- PII 加密存储：手机号/姓名/地址 AES 加密，与脱敏业务数据分开存储
- 多租户架构预留：appKey/appSecret/token 不硬编码，按商家 ID 动态选用
- 小红书 API 签名机制：参数字母排序拼接 + 路径 + appSecret → MD5。**签名模块放 /opt/surenxuan/（EMP_0005 负责），不做跨项目依赖**。自用单项目，未来需要共享时迁移成本极低（几十行代码提取）
- **跨境通信协议**：GCP↔阿里云之间用标准化 JSON 消息，通过反向 SSH 隧道传输。未来加 japan-hub 等区域节点用同样协议
- **未来 employee 结构**：EMP_1000 中国区总管 / EMP_1001 数据管家 / EMP_1002 CRM / EMP_1003 物流

### china-hub 第一个真实用例：分析看板 (2026-02-28)
- 大使馆模式 Phase 1 的落地：MediaCrawler 采集 → 阿里云 SQLite 存储 → FastAPI 看板 → Mason 浏览器直接访问
- 数据合规原则「数据不动，人来看」：原始数据不出境，Mason 通过浏览器访问阿里云看板（等同访问中国网站）
- GCP 只收 Slack 通知（一句话趋势摘要 + 阿里云看板链接）
- 目录结构：/opt/mediacrawler/（采集）+ /opt/china-hub/（看板+分析）

## 部署与运维 Pattern

### 第三方项目 .env 加载不能想当然 (2026-03-01)
- MediaCrawler 声明 python-dotenv 依赖但从未 import/调用
- 部署任何第三方项目时，必须验证 .env 是否真的被加载（看 import 语句，不是看 .env 文件存不存在）

### 代理服务产品类型区分 (2026-03-01)
- DPS（提取代理）：调 API 获取临时 IP 列表，每个 IP 有过期时间
- TPS（隧道代理）：固定 host:port + auth，服务端自动轮换出口 IP
- 同一服务商（如快代理）两种产品的 API 和接入方式完全不同
- MediaCrawler 内置只支持 DPS，需写适配器支持 TPS

## 踩坑记录
