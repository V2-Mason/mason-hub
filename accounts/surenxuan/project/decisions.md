# 素仁轩 — 决策记录
# 格式：[日期] 情境 → 决策 → 理由 → 放弃的选项

[2026-02-25] 
情境：需要建立agent系统架构
决策：采用文件系统作为记忆载体，而非数据库
理由：agent天然理解文件系统，Markdown对agent可读性最好，避免过早引入数据库复杂度
放弃的选项：向量数据库（过早）、SQL数据库（结构化过强，不适合知识内容）

[2026-02-25]
情境：Manager是否应该每个project独立一个
决策：Manager每个domain一个，跨project共享
理由：Manager是COO角色，需要全局视角，多Manager会导致信息孤岛
放弃的选项：每个project独立Manager（会导致资源调度无法跨project）

[2026-02-27]
情境：Agent 需要跨 session 记忆能力，否则每次启动都从零开始
决策：实施 Agent 记忆层 v1 — agents/memory/{EMP_ID}/ 目录，short_term.json + long_term.md
理由：文件系统载体（沿用 2025-02-25 决策）、每个 Agent 独立记忆空间（物理隔离）、Dev 只有短期记忆（无状态设计不变）、记忆读写嵌入启动流程 Step 1.5
放弃的选项：数据库存储（过早复杂）、共享记忆池（Agent 间会互相污染）、完全无记忆（无法积累经验）

[2026-02-27]
情境：P0-1 gross_profit 计算被认为有 bug（没减 discount_amount）
决策：实际排查后确认 actual_sale_price 已经是折后价，公式本身正确。真正修复是：(a) 增加 total_discount 汇总字段 (b) CSV 导入补充 original_price 和 discount_amount
理由：Dev 实际阅读代码后发现 PM 初始诊断有偏差——如果按 PM 的方案减 discount_amount 会双重扣减
教训：利润计算类问题必须先读完整代码链路再下结论，不能只看单行 SQL

---
# 以下决策迁移自旧架构 ~/.mason-hub/logs/decisions.md

[迁移自旧架构 2026-02-25]
情境：中国网络环境下 Google OAuth 不可靠
决策：用 email+password (bcrypt) 替换 Google OAuth
理由：Google OAuth 在中国网络环境不稳定，影响用户登录体验
放弃的选项：继续使用 Google OAuth（不稳定）、微信登录（需要企业资质）
影响：修改了后端和前端认证流程，新增 init_admin.py

[2026-03-19]
情境：surenxuan 和 mason-hub 的架构关系需要定义
决策：采用 Option C (OS模式) + 选择 3 (deployment清单)
理由：mason-hub = 产品原型（多租户），surenxuan = 第一个客户（dogfood）。EMP 全留 mason-hub，通过 deployment yaml 索引每个项目的 agent 配备。accounts/ 统一客户数据。三层记忆：EMP(技术) + accounts(业务) + kernel(跨客户)
放弃的选项：A(中央大脑，agent跨两个repo读文件) / B(项目自治，手动跨项目协作)

[2026-03-19]
情境：品牌知识分散在 shared/brands/ 和 accounts/ 两处
决策：合并到 accounts/（按客户分），shared/ 只保留真正跨客户共享的资源
理由：多租户产品模型下，品牌资产属于客户，不是"共享"的
放弃的选项：C(保持两处，用规则区分——增加认知负担)

[2026-03-19]
情境：EMP 记忆按项目分还是通用共享
决策：通用共享 + 三层写入规则（EMP/accounts/kernel）
理由：Mason 的项目是一个生态（都围绕电商），经验应该跨项目复用。按项目分会导致 16 EMP × N 项目的记忆爆炸
放弃的选项：按项目分目录（适合互不相关的外包项目，不适合 Mason 的场景）
