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

### MediaCrawler 源码 Bug 修复 (2026-03-02, 已在阿里云 patch)

1. **`login_by_cookies` 只加载 `web_session`**（login.py）
   - 原代码 `if key != "web_session": continue` 导致浏览器上下文只有 web_session
   - API 签名需要 `a1` 等 cookie，缺失导致签名无效
   - 修复：去掉 `if key != "web_session": continue`，加载全部 cookie

2. **`get_note_detail_async_task` 单条失败导致整批崩溃**（core.py）
   - 原代码对获取失败的笔记 `raise Exception`，`asyncio.gather` 传播异常导致整页 20 条全丢
   - 修复：改为 `logger.warning` + `return None`，跳过失败笔记，保留成功的

3. **`request` 方法 `data["success"]` KeyError**（client.py）
   - XHS API 异常时可能返回不含 `success` 字段的 JSON，触发 KeyError → 被 `@retry` 重试 3 次 → RetryError
   - 修复：加 `if "success" not in data:` 检查，抛 `DataFetchError` 替代 KeyError

### XHS 内部 API 风控规则 (2026-03-02)
- XHS 没有公开 API，MediaCrawler 用的全是逆向的网页内部接口
- **搜索 API**（`/api/sns/web/v1/search/notes`）：风控较松，正常可用
- **笔记详情 API**（`/api/sns/web/v1/feed`）：风控严格，~50-60 次调用后触发 461 `账号异常，请稍后重试`（code 300011）
- 被风控后搜索和 selfinfo 仍正常，只有 feed API 被封
- **方案**：两层采集 — 搜索 API 广撒网（安全），Feed API 只深挖 Top 10（控量）

### 多账号采集架构 (2026-03-02, Mason 确认)
- **不再用 MediaCrawler 的 main.py**，改用自建 _two_tier_crawl.py 直接调 Playwright + signing
- Cookie 从 accounts.json 读（不再依赖 base_config.py）
- 每个账号独立浏览器指纹（UA/viewport/locale/timezone）
- xhs-crawl.sh 支持 --account 参数，按 task 自动选默认账号
- 关键词轮换：每次从完整池随机选子集（shuf | head），不全搜
- 拟人化延迟：首页暖场 + 搜索间 30-90s + 详情间 10-30s + cron 随机偏移 0-45min
- 文件路径：
  - GCP: skills/xhs/_two_tier_crawl.py + skills/xhs/xhs-crawl.sh
  - 阿里云: /opt/mediacrawler/two_tier_crawl.py（每次 SCP 覆盖）+ accounts.json

### Backlog 主动消化系统 (2026-03-11, Mason 确认)
- 新建 `scripts/backlog-scanner.py`：解析 backlog.md 中所有 `[ ]` 任务，5 层过滤
- 过滤层：① 红线（品牌/账号/密钥）② Section 阻塞（Phase 前置条件）③ 外部依赖关键词 ④ agent 标注 ⑤ 能力线状态
- 改造 `find-actionable-task.py`：合并静态注册表（autonomous_tasks.yaml）+ 动态扫描结果
- 静态任务优先于动态任务（同优先级时），防止重复执行
- 全角括号 `（EMP_XXXX）` 需要正则同时匹配半角和全角
- 每日计数器 `data/.backlog_dispatch_today`：JSON 文件记录日期+计数，次日自动归零
- Mason 决策：直接执行不需先通知，每天上限按 8 小时工作量（6 个任务）
- 并行升级 (2026-03-11)：dispatcher.sh 从串行改为按 lane 并行。`--batch` 模式按 lane 去重，每 lane 取优先级最高的 1 个。dispatcher 检查 lane-lock 空闲状态后同时派发。repair 任务仍独占（不和常规并行）
- lane-lock.sh 补齐映射：EMP_0014→platform, EMP_0015→ecommerce

### Gateway 成本优化三层方案 (2026-03-11)
- **问题**：首日实际成本 $11.71（预估 $0.5-0.8），29 次 API 调用，轻巡每次都升级为重巡
- **根因**：① prompt caching 未开启（cache_write/read 全 0）② 全用 Sonnet（$3/M）③ 轻巡因 XHS 已知缺失的 ❌ 每次都触发重巡
- **方案**：① `cache_control: ephemeral` 注入 system prompt → cache read $0.30/M ② 常规用 Haiku（$0.80/M），4h 强制/L3 事件用 Sonnet ③ 轻巡读 gateway-known-states.yaml 抑制已知基线内的失败
- **参考**：OpenClaw 55min heartbeat + 60min cache TTL 保持缓存热；SkillRL 蒸馏 10-20x token 压缩
- **gap 类型**：🔧 配置错误 → 已修复

### Skill 自动蒸馏器 (2026-03-11)
- `scripts/distill-skills.py` — 从 gateway-memory.jsonl 提取可复用 skill
- 两阶段：纯规则分析（重复 finding ≥3 / 升级链 / 监控疲劳）→ Haiku 蒸馏（$0.01/次）
- cron 每周日 11:30 CST，compact-memory.sh 之后
- 灵感来源：SkillRL 论文（分层 SkillBank + 递归演化 + 失败蒸馏）
- **gap 类型**：🏗️ 系统能力缺失 → 已修复

### Gateway 决策广播机制 (2026-03-11)
- **问题**：Gateway（mason-gateway.py）和 Mason 的 Claude Code session 是两个独立循环，Mason 做的决策（如"XHS 小号先不配"）不会自动传播到 Gateway，导致 Gateway 反复对已知状态误报告警
- **方案**：`data/gateway-known-states.yaml` 结构化注册表 + `/commit` skill 步骤 5 强制检查 + Gateway heartbeat 自动加载（`load_known_states()`）
- **设计原则**：零 token 成本（纯文件 I/O）、expires 字段自动失效、/commit 流程强制而非靠记忆
- **参考**：OpenClaw Gateway 架构 — 所有通道汇聚单一 Gateway 天然无信息孤岛；mason-hub 有双入口（session + daemon），需要显式同步机制
- **gap 类型**：🏗️ 系统能力缺失 → 已修复

### 自治闭环 v2 — 效率修复 + 闭环补全 (2026-03-11)
- **问题诊断**：Gateway 首日自治运行效率低 — 3.4M tokens/$3-11 消耗，信噪比 15%。三个根因：① save_memory 重复写（同 finding+status 反复写入）② Dispatcher 不检查任务完成状态（同任务每小时重复派发 12 次）③ heartbeat 轻巡误触发（内存波动导致不必要的重巡 API 调用）
- **效率修复**：save_memory 加去重（最近 10 条 finding+status 匹配跳过）、轻巡变化检测只比较 health 状态不比较内存/磁盘波动、记忆注入从 5 条减到 3 条、dispatcher log() tee→直写
- **闭环补全 4 组件**：① MASONHUB.md 检查清单 8→10 项（dispatcher 行为模式+agent 产出验证+完成确认）② run-agent.sh 完成/失败时 emit agent-task-complete 事件 ③ find-actionable-task.py 检查 audit.jsonl 跳过今日已完成任务 + report 运行检查 ④ backlog-scanner.py 增强外部依赖检测
- **Repair 端到端验证**：首次成功跑通全链路（submit → repair_queue.json → repair-dispatch.sh → claude -p → 修复代码 → bash -n 验证 → resolve）。发现 CLAUDECODE 嵌套问题：repair-dispatch.sh 需要 `unset CLAUDECODE` 才能在 Gateway 子进程中启动 claude -p
- **关键教训**：backlog 里没标 `(EMP_XXXX)` 的任务不会被 scanner 发现 → 所有可自动执行的任务必须标注 owner
- **gap 类型**：🏗️ 系统能力缺失 → 已修复

### OS-Model 架构 + Gene 系统 + 理论框架融入 (2026-03-11)
- **灵感来源**：王军杰 × 小军杰 "Model 派 vs Harness 派" 讨论
- **Gene 系统**：`shared/genes/` 目录，3 个行为原语（skeptical_verification / practical_epistemology / ashby_variety），通过 run-agent.sh Phase 2.7 按角色自动注入
- **Self-Evolution Flywheel 度量**：Gateway 新增 `track_skill` 工具 + `data/learned-skills-stats.json` 追踪 Skill applied_count
- **知行转化率**：/standup 每日输出 backlog 可自动执行 / 总未完成
- **Ashby 审视**：SYSTEM_MAP.md 更新协议新增多样性覆盖率检查（能力线 active 时触发）
- **skeptical_verification prompt**：MASONHUB.md 工作节奏步骤 3b，Gateway 诊断后强制自我质疑
- **gap 类型**：🏗️ 系统能力缺失 → 已修复

### SearXNG Docker 部署 (2026-03-11)
- 部署 SearXNG 到 GCP，`--restart always`，端口 8889（8888 被 nginx/SocialMesh 占用）
- SearXNG 默认 `formats: [html]` 只允许 HTML 输出，JSON API 返回 403。需手动编辑 `/opt/searxng/settings.yml` 添加 json/csv/rss
- 配置文件路径：`/opt/searxng/settings.yml`（容器 volume 挂载）
- Scout v2 的 search.py 可以把 SearXNG URL 从 fallback 改为 primary
- Gap 分类：🔧 配置错误 → 已修（端口冲突 + JSON 格式未启用）

### XHS 分析函数单元测试 (2026-03-11)
- 为 parse_count / interaction_score / 假流量检测 / median 写了 55 个测试用例
- 发现 2 个源码 bug：
  1. `parse_count('万')` 会 ValueError — `'万'.replace('万','')` 变空字符串，`float('')` 失败。万/亿分支在 try/except 之外，没有防护
  2. `parse_count('2.3亿')` 浮点精度丢失 → 229999999 而非 230000000。应改用 `round()` 包裹
- parse_count 函数在 5+ 个文件中重复定义（viral / compare / crawl / collect_comments / publish_log），应抽成共享模块
- Gap 分类：🔧 配置错误 → 已记录（bug 不在本次修复范围）+ 📚 纯知识 → 留存

### run-agent.sh `set -euo pipefail` 静默崩溃 (2026-03-11)
- `grep -oP` 无匹配时返回 exit 1，`pipefail` 传播，`set -e` 杀脚本 → 在 Task ID 提取（line 134）静默退出
- Dispatcher 派发的任务描述是 "自主任务: ..." 格式，不含 `task_id:` 或 `srx_` 前缀 → grep 必定无匹配
- 症状：lane lock acquire/release 之间无任何输出，`logs/tasks/` 无新文件，API 无消耗
- 修复：所有可能无匹配的 grep 加 `|| true`；EXIT trap 增加异常退出日志（记录 exit code + agent name）
- **教训**：`set -euo pipefail` 脚本中，任何 `grep` 在变量赋值中都必须 `|| true`，否则"没找到"就等于"崩溃"
- Gap 分类：🔧 编码错误 → 已修

### Gateway 轻巡变化检测导致成本失控 (2026-03-11)
- 轻巡 `current = health_output[:200]` 包含时间戳 + 相对时间（"更新于 16h 前"）
- 每次轻巡 current 都不同 → `changed=True` → 每小时都升级为 Sonnet 重巡
- 重巡 18 轮 agentic loop，conversation history 累积 → 195K input tokens/次
- 实际成本 $10+/天 vs 设计预期 $1/天
- 修复：只比较 `emoji + 数据集名` 的 sorted fingerprint，忽略时间/描述
- 同时修复 `has_error` 抑制逻辑：`returncode != 0` 也应被 known-states 覆盖
- **教训**：变化检测的比较对象必须是「稳态指纹」（只含状态，不含时间/计数等动态值），否则每次都是"变化"
- Gap 分类：🔧 设计缺陷 → 已修

### Scout v2 Cron 注册 (2026-03-11)
- 旧 Scout 三档调度（每日快扫/中频/深扫）全部通过 `run-agent.sh agents/EMP_0006/config.md` 调用，每次启动完整 Claude session 来跑 shell 脚本 — 成本高
- 新 Scout v2 pipeline 直接 `python -m intel.engines.pipeline`，6 引擎串行 + checkpoint，无需 Claude session
- 旧条目注释保留（不删除），新条目加 `cd /home/hangn/mason-hub &&` 前缀确保 cwd 安全
- 从 每天+周一三五+周一 共 ~10 次/周 减少到 周二+周五 = 2 次/周，与 Mason 建议一致
- Gap 分类：📄 文档更新 → 已更新 backlog

### Git Worktree 工作流 (2026-03-11)
- 新建 `scripts/worktree.sh`：统一管理 create/list/merge/cleanup/cleanup-all
- 分支命名：`agent/<EMP_ID>/<task_id>`，worktree 目录：`.worktrees/`（已 gitignore）
- `run-agent.sh` 集成：`USE_WORKTREE=1` 环境变量触发，默认关闭不影响现有流程
- 任务完成后自动检测 worktree 有无新 commit，无改动自动清理，有改动提示 merge 命令
- `git worktree list --porcelain` 的 awk 解析比较 tricky，branch 行格式是 `branch refs/heads/xxx`
- Gap 分类：🏗️ 系统能力缺失 → 已修复

## 踩坑记录
