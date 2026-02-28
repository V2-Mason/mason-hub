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

### 阿里云数据网关设计 (2026-02-28)
- 阿里云需要新增"数据网关"服务：接收小红书 API 原始数据 → 脱敏处理 → 推送聚合结果到 GCP
- 两种数据流：实时流（Webhook 事件脱敏摘要）+ 批量同步（每日聚合统计）
- 执行引擎：接收 GCP agent 指令（只含 ID 引用），本地查询敏感数据后调 API 执行
- PII 加密存储：手机号/姓名/地址 AES 加密，与脱敏业务数据分开存储
- 多租户架构预留：appKey/appSecret/token 不硬编码，按商家 ID 动态选用
- Connector 模式：每个平台（小红书/微信/未来平台）是独立 connector，统一输出到 PostgreSQL
- 小红书 API 签名机制：参数字母排序拼接 + 路径 + appSecret → MD5，需封装为通用中间件
- 模块化设计：每个能力（数据脱敏/API调用/订单处理）是独立 skill，方便未来中国侧 agent 直接调用

## 部署与运维 Pattern

## 踩坑记录
