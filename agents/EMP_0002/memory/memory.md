# EMP_0002 Platform Dev — 记忆库

> 写入规则：每条带日期 + Gap分类标签。主题下追加，不另开文件。
> 浓缩触发：条目超过 150 条时，运行 compact-memory.sh 压缩归档。

---

## 平台架构

### agent-loader.sh 创建与 run-agent.sh v2 适配 (2026-03-14)
<!-- written: 2026-03-14 · last_ref: 2026-03-14 · ref_count: 1 -->
- 从 run-agent.sh 提取文件加载逻辑为独立模块 `scripts/agent-loader.sh`
- 两个核心函数：`load_agent_context`（组装 5 文件上下文）、`update_agent_state`（覆写 state.md）
- Layer 参数：`0`=identity+state（T1），`01`=全部五文件（T3+，默认）
- run-agent.sh 改为：检测 identity.md 存在 → `USE_V2_LOADER=true` → 调用 agent-loader
- fallback 保留：无 identity.md 时回退读 config.md，无感降级
- launcher_args 提取从 frontmatter YAML 改为 identity.md body 的 `**launcher**:` 行
- 验证结果：bash -n 通过，load_agent_context 输出 5 个分隔符 + 正确内容
- 下游调用（901/908/1212/1219 行）仍硬编码 config.md 路径，待后续迁移

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
- 小红书 API 签名机制：参数字母排序拼接 + 路径 + appSecret → MD5。**签名模块放 /opt/surenxuan/（EMP_0005 负责），不做跨项目依赖**
- **跨境通信协议**：GCP↔阿里云之间用标准化 JSON 消息，通过反向 SSH 隧道传输
- **未来 employee 结构**：EMP_1000 中国区总管 / EMP_1001 数据管家 / EMP_1002 CRM / EMP_1003 物流

### china-hub 第一个真实用例：分析看板 (2026-02-28)
- 大使馆模式 Phase 1 的落地：MediaCrawler 采集 → 阿里云 SQLite 存储 → FastAPI 看板 → Mason 浏览器直接访问
- 数据合规原则「数据不动，人来看」：原始数据不出境，Mason 通过浏览器访问阿里云看板
- GCP 只收 Slack 通知（一句话趋势摘要 + 阿里云看板链接）
- 目录结构：/opt/mediacrawler/（采集）+ /opt/china-hub/（看板+分析）

### Backlog 主动消化系统 (2026-03-11, Mason 确认)
- 新建 `scripts/backlog-scanner.py`：解析 backlog.md 中所有 `[ ]` 任务，5 层过滤
- 过滤层：① 红线（品牌/账号/密钥）② Section 阻塞（Phase 前置条件）③ 外部依赖关键词 ④ agent 标注 ⑤ 能力线状态
- 改造 `find-actionable-task.py`：合并静态注册表（autonomous_tasks.yaml）+ 动态扫描结果
- 静态任务优先于动态任务（同优先级时），防止重复执行
- 全角括号 `（EMP_XXXX）` 需要正则同时匹配半角和全角
- 每日计数器 `data/.backlog_dispatch_today`：JSON 文件记录日期+计数，次日自动归零
- Mason 决策：直接执行不需先通知，每天上限按 8 小时工作量（6 个任务）
- 并行升级 (2026-03-11)：dispatcher.sh 从串行改为按 lane 并行。`--batch` 模式按 lane 去重，每 lane 取优先级最高的 1 个
- lane-lock.sh 补齐映射：EMP_0014→platform, EMP_0015→ecommerce

### Gateway 成本优化三层方案 (2026-03-11)
- **问题**：首日实际成本 $11.71（预估 $0.5-0.8），29 次 API 调用，轻巡每次都升级为重巡
- **根因**：① prompt caching 未开启 ② 全用 Sonnet（$3/M）③ 轻巡因 XHS 已知缺失每次都触发重巡
- **方案**：① `cache_control: ephemeral` 注入 ② 常规用 Haiku ③ 轻巡读 gateway-known-states.yaml 抑制
- Gap 类型：🔧 配置错误 → 已修复

### Skill 自动蒸馏器 (2026-03-11)
- `scripts/distill-skills.py` — 从 gateway-memory.jsonl 提取可复用 skill
- 两阶段：纯规则分析（重复 finding ≥3 / 升级链 / 监控疲劳）→ Haiku 蒸馏（$0.01/次）
- cron 每周日 11:30 CST，compact-memory.sh 之后
- Gap 类型：🏗️ 系统能力缺失 → 已修复

### Gateway 决策广播机制 (2026-03-11)
- **问题**：Gateway 和 Mason 的 Claude Code session 是两个独立循环，Mason 做的决策不会自动传播到 Gateway
- **方案**：`data/gateway-known-states.yaml` 结构化注册表 + `/commit` skill 步骤 5 强制检查 + Gateway heartbeat 自动加载
- **设计原则**：零 token 成本（纯文件 I/O）、expires 字段自动失效
- Gap 类型：🏗️ 系统能力缺失 → 已修复

### OS-Model 架构 + Gene 系统 + 理论框架融入 (2026-03-11)
- **Gene 系统**：`shared/genes/` 目录，3 个行为原语（skeptical_verification / practical_epistemology / ashby_variety），通过 run-agent.sh Phase 2.7 按角色自动注入
- **Self-Evolution Flywheel 度量**：Gateway 新增 `track_skill` 工具 + `data/learned-skills-stats.json`
- **知行转化率**：/standup 每日输出 backlog 可自动执行 / 总未完成
- Gap 类型：🏗️ 系统能力缺失 → 已修复

### Agent 四层声明补齐（第二批 8 个）(2026-03-12)
- 为 EMP_0000/0001/0003/0004/0006/0008/0012/0013 补齐四层声明
- 模板来源：`docs/system/AGENT_DESIGN_TEMPLATE.md`
- **发现 2 个 config 超 5KB**：EMP_0000 (5.3KB)、EMP_0008 (7.1KB)。需后续拆 playbook
- Gap 分类：📄 文档更新 → 已更新 8 个 config.md

### agent.log 结构化改造 (2026-03-12)
- **问题**：agent.log 混杂纯文本 + JSON，2007 行中 546 行非 JSON
- **改造**：log_structured() 增强 + 日志轮转 >1MB 自动归档 + 查询工具 log-query.sh + Schema 文档
- **注意**：`START_EPOCH` 用 `${START_EPOCH:-$(date +%s)}` fallback
- Gap 分类：🏗️ 系统能力缺失 → 已修复

---

## 部署与运维

### 第三方项目 .env 加载不能想当然 (2026-03-01)
- MediaCrawler 声明 python-dotenv 依赖但从未 import/调用
- 部署任何第三方项目时，必须验证 .env 是否真的被加载（看 import 语句）

### 代理服务产品类型区分 (2026-03-01)
- DPS（提取代理）：调 API 获取临时 IP 列表，每个 IP 有过期时间
- TPS（隧道代理）：固定 host:port + auth，服务端自动轮换出口 IP
- 同一服务商（如快代理）两种产品的 API 和接入方式完全不同
- MediaCrawler 内置只支持 DPS，需写适配器支持 TPS

### MediaCrawler 源码 Bug 修复 (2026-03-02, 已在阿里云 patch)
1. **`login_by_cookies` 只加载 `web_session`**（login.py）— 修复：去掉 filter，加载全部 cookie
2. **`get_note_detail_async_task` 单条失败导致整批崩溃**（core.py）— 修复：改为 warning + return None
3. **`request` 方法 `data["success"]` KeyError**（client.py）— 修复：加 key 存在检查

### XHS 内部 API 风控规则 (2026-03-02)
- XHS 没有公开 API，MediaCrawler 用的全是逆向的网页内部接口
- **搜索 API**：风控较松，正常可用
- **笔记详情 API**：风控严格，~50-60 次调用后触发 461
- **方案**：两层采集 — 搜索 API 广撒网，Feed API 只深挖 Top 10

### 多账号采集架构 (2026-03-02, Mason 确认)
- 不再用 MediaCrawler 的 main.py，改用自建 _two_tier_crawl.py
- Cookie 从 accounts.json 读，每个账号独立浏览器指纹
- 关键词轮换：每次随机选子集（shuf | head）
- 拟人化延迟：首页暖场 + 搜索间 30-90s + 详情间 10-30s + cron 随机偏移 0-45min
- 文件路径：GCP skills/xhs/ + 阿里云 /opt/mediacrawler/

### SearXNG Docker 部署 (2026-03-11)
- 端口 8889（8888 被 nginx 占用），`--restart always`
- 默认 `formats: [html]` 需手动编辑添加 json/csv/rss
- Gap 分类：🔧 配置错误 → 已修

### TrendRadar + RSSHub 趋势监控系统 (2026-03-08)
- TrendRadar: ~/mason-hub/tools/trendradar/，cron */30 采集
- RSSHub: Docker diygod/rsshub，端口 1200
- 11 个中文热榜 + 10 个 RSS 源，14 组关键词
- TrendRadar 是 clone 的外部仓库（46MB），不提交 git，只备份配置
- RSSHub 公共实例不稳定，自建更可靠（~150MB RAM）

### Radar Tracker 关注率 + 每日去重 (2026-03-09)
- 关注率 = 1 - (dismissed / total_hits)
- HTML 报告注入 dismiss + read 按钮，Flask API :8081 systemd 托管
- 淘汰阈值 30%（Mason 指定），需至少 2 周数据积累
- 每日去重：`seen_items` 表，首次展示记录，次日起自动隐藏

---

## 调度系统

### 自治闭环 v2 — 效率修复 + 闭环补全 (2026-03-11)
- **问题**：Gateway 首日自治运行效率低 — 3.4M tokens/$3-11 消耗，信噪比 15%
- **根因**：① save_memory 重复写 ② Dispatcher 不检查完成状态（同任务每小时重复派发 12 次）③ heartbeat 轻巡误触发
- **效率修复**：save_memory 去重 + 轻巡只比较 health 状态 + 记忆注入从 5 条减到 3 条
- **闭环补全 4 组件**：MASONHUB.md 检查清单 + run-agent.sh emit 事件 + find-actionable-task.py 跳过已完成 + backlog-scanner 增强
- **关键教训**：backlog 里没标 `(EMP_XXXX)` 的任务不会被 scanner 发现
- Gap 类型：🏗️ 系统能力缺失 → 已修复

### 自治系统诊断 + 目录重组 (2026-03-11)
- `claude -p` 从 cron 调用时用 `/usr/bin/claude`（旧版），不是 `~/.local/bin/claude` → 所有 agent 静默失败
- `find-actionable-task.py --batch` 按 lane 去重导致 5/6 任务被挡
- audit.jsonl 只在成功时写入 → 失败任务无限重派
- CLAUDE.md + MEMORY.md 每条消息带 ~6755 tokens 固定税，80% 无关上下文
- 修复：PATH 修正 + (lane,agent) 去重 + 失败记账 + 实时触发 + Prompt 精简 79%
- Gap 类型：🔧 配置错误 + 🏗️ 系统能力缺失

### Token 成本优化三件套 + Agent OS v1.1 落地 (2026-03-13)
- T1 任务直接 bash 执行不启动 Agent session，失败时才升级为 T3
- run-agent.sh 新增 `--max-budget-usd $0.50` 默认上限
- warm.md 记忆层：compact-memory.sh 生成滚动摘要，注入优先级 warm.md → 语义搜索 → 全量 lessons
- 关键发现：health-fix 任务跑了 10 次花 $4.36，本质是 T1 脚本不需要 LLM

### Dispatcher 失败降级策略 (2026-03-12)
- `find-actionable-task.py` 新增 `get_yesterday_failed_max()`，≥2 次 failed 的任务排最后
- 持续失败写 `data/failed_tasks_for_review.jsonl`，Mason + Meta Manager 手动裁决
- Gap 类型：🏗️ 调度策略缺失

### Dispatcher Mason 让路机制 (2026-03-12)
- Mason 在用 Claude Code 时 dispatcher 会撞车
- 修复：检测交互式 claude 进程（排除 `claude -p`），有就跳过本轮
- 配合 `/tmp/mason-pause` 手动开关形成两层让路
- Gap 类型：设计缺口

### Scout v2 Cron 注册 (2026-03-11)
- 旧 Scout 每次启动完整 Claude session 来跑 shell 脚本 — 成本高
- 新 Scout v2 直接 `python -m intel.engines.pipeline`，无需 Claude session
- 从 ~10 次/周 减少到 周二+周五 = 2 次/周
- Gap 分类：📄 文档更新

### Git Worktree 工作流 (2026-03-11)
- `scripts/worktree.sh`：统一管理 create/list/merge/cleanup
- 分支命名：`agent/<EMP_ID>/<task_id>`，worktree 目录：`.worktrees/`
- `run-agent.sh` 集成：`USE_WORKTREE=1` 环境变量触发
- Gap 分类：🏗️ 系统能力缺失 → 已修复

---

## 踩坑记录

### run-agent.sh `set -euo pipefail` 静默崩溃 (2026-03-11)
- `grep -oP` 无匹配返回 exit 1 → `pipefail` 传播 → `set -e` 杀脚本
- 修复：所有可能无匹配的 grep 加 `|| true`；EXIT trap 增加异常退出日志
- **教训**：`set -euo pipefail` 脚本中，任何 `grep` 在变量赋值中都必须 `|| true`
- Gap 分类：🔧 编码错误 → 已修

### Gateway 轻巡变化检测导致成本失控 (2026-03-11)
- 轻巡 `current = health_output[:200]` 包含时间戳 → 每次都"变化" → 每小时升级为 Sonnet 重巡
- 修复：只比较 `emoji + 数据集名` 的 sorted fingerprint
- **教训**：变化检测的比较对象必须是「稳态指纹」，不含时间/计数等动态值
- Gap 分类：🔧 设计缺陷 → 已修

### XHS 分析函数单元测试 (2026-03-11)
- 55 个测试用例发现 2 个源码 bug：`parse_count('万')` ValueError + 浮点精度丢失
- parse_count 函数在 5+ 个文件中重复定义，应抽成共享模块
- Gap 分类：🔧 配置错误 + 📚 纯知识

### backlog-scanner section_context 泄漏 (2026-03-12)
- `infer_line()` 用 `current_section` 而非 `section_context`，子标题切换时丢失父级关键词
- 修复：引入 `parent_section` 变量
- Gap 类型：设计缺口

### inbox 通信机制实现 (2026-03-14)
<!-- written: 2026-03-14 · last_ref: 2026-03-14 · ref_count: 1 -->
- agent-loader.sh 新增 `send_message()` + `check_inbox()`，集中式 `data/messages/inbox_<id>.jsonl`
- check_inbox 用 inline python3 处理 JSONL（bash 原生处理 JSON 不可靠）
- archive 按月归档到 `archive/inbox_<id>_YYYY-MM.jsonl`，inbox 文件处理后清空
- `load_agent_context` 末尾自动 `check_inbox`，启动即收信
- `update_agent_state` 第5参数 receiver 触发自动 `send_message`，完成即发信
- 15 个 soul.md 追加"收件处理规则"：EMP_0000/0001/0002 定制，其余通用
- TASK-20260314-002 端到端验证：send → inbox → load_context → auto check → archive，零人工传递
- Gap 类型：🏗️ 系统能力缺失 → 已修复

### task_assign 协议扩展 + 首个业务场景验证 (2026-03-14)
<!-- written: 2026-03-14 · last_ref: 2026-03-14 · ref_count: 1 -->
- message_schema.md 新增 `task_assign` 类型，payload 强制四字段（title/description/context_files/deadline）
- EMP_0001 soul.md 新增"任务派发规则"4步流程 + task_assign_confirm 收件规则
- EMP_0010 soul.md 新增 task_assign 收件规则（含超出范围拒绝路径）
- 首个真实场景：EMP_0001→EMP_0010 素仁轩短视频脚本，4 条消息链路全自动
- Gap 类型：🏗️ 系统能力缺失 → 已修复

### 注入优化三级架构 + SessionStart Hook (2026-03-14)
- CLAUDE.md 从 89→52 行，run-agent.sh 新增 `lightweight` 任务类型
- SessionStart hook：新 interactive session 自动注入系统快照（~300 tokens）
- **关键经验**：interactive session 和 agent session 是两个独立 memory 通道
- CLAUDE.md 里"必须启动时读取"会导致 Claude 主动 read_file → 上下文累积
- Gap 类型：设计缺口

### 铁律执行 + 质量框架 + 四支柱诚实评估 (2026-03-14)
- pre-commit hook 是唯一可靠的铁律执行方式——规则写在文档里 Claude 会合理化绕过
- "文件存在"≠"能力存在"。写了脚本但未在真实流程中验证不应算 90%
- 四支柱评估揭示 mason-hub 是"自动化调度系统"不是"Agent 系统"
- run-agent.sh 从 50 行长到 1300 行是 God Script 反模式
- Gap 类型：认知偏差
