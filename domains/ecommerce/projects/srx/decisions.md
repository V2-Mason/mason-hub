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

---
# 以下决策迁移自旧架构 ~/.mason-hub/logs/decisions.md

[迁移自旧架构 2026-02-25]
情境：中国网络环境下 Google OAuth 不可靠
决策：用 email+password (bcrypt) 替换 Google OAuth
理由：Google OAuth 在中国网络环境不稳定，影响用户登录体验
放弃的选项：继续使用 Google OAuth（不稳定）、微信登录（需要企业资质）
影响：修改了后端和前端认证流程，新增 init_admin.py
