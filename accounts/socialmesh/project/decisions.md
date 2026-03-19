# SocialMesh — 决策记录
# 格式：[日期] 情境 → 决策 → 理由 → 放弃的选项

[2026-02-27]
情境：社媒管理工具技术栈选择
决策：FastAPI + PostgreSQL + React + Celery + Redis + Playwright
理由：与素仁轩一致（Mason 熟悉），PostgreSQL 多租户就绪，Celery 支持定时发帖，Playwright 适合无 API 平台
放弃的选项：Django（过重）、MongoDB（不适合关系数据）、Puppeteer（Python 生态 Playwright 更好）

[2026-02-27]
情境：平台接入优先级
决策：Phase 1 先做 Reddit → XHS → LinkedIn，Phase 2 做 X/Twitter → TikTok
理由：Reddit 有免费 API 最简单，XHS 是 Mason 核心渠道但需 Playwright，LinkedIn 基础 API 可用。X 免费版限制太多（$200/月），TikTok 审批复杂
放弃的选项：全平台同时开发（资源不够）、先做 X（成本太高）

[2026-02-27]
情境：适配器架构模式
决策：每个平台一个 adapter 文件，实现统一接口（authenticate/publish/get_metrics）
理由：新增平台 = 新增一个文件，不改核心代码。借鉴 OpenClaw 的 skill 架构
放弃的选项：单一大文件（不可维护）、插件系统（过早抽象）

[2026-02-27]
情境：LLM 选择
决策：OpenAI gpt-4o-mini 作为主力，Anthropic Haiku 作为备用，最终降级为规则引擎
理由：Mason 已有 OpenAI API key，gpt-4o-mini 性价比高，多级降级保证可用性
放弃的选项：纯 Anthropic（Mason 给的是 OpenAI key）、单一 LLM 无降级（可靠性不够）

[2026-02-27]
情境：XHS 认证方式
决策：Playwright persistent context + QR 码扫描登录
理由：XHS 无公开 API，Playwright 可持久化 session（cookies + IndexedDB），QR 扫码是唯一可靠登录方式
放弃的选项：模拟密码登录（会触发安全验证）、第三方非官方 API（不稳定且有法律风险）

[2026-02-27]
情境：内容适配 API 返回格式
决策：统一返回 array [{platform, adapted_body, character_count, has_account}]
理由：前端用 Array.isArray() 判断，dict 格式会被丢弃。array 格式也更适合遍历渲染
放弃的选项：dict 格式 {platform: {...}}（前端无法识别）

[2026-02-27] PM经验
情境：Mason 报告发帖流程太碎（保存 → 适配 → 排程分三步）
做法：新增 /adapt-raw 端点允许不保存直接适配，ContentEditor 重写为一体化流程
效果：待 Mason 验证
