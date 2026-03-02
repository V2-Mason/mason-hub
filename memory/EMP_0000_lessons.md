# EMP_0000 Meta Manager 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---


## 2026-02-28: Team Agents 开团标准

- ≥2 个不重叠领域（前端+后端）且每边 ≥3 文件 → 开 team
- 否则直接做更省 token（例：Scorer 改 3 文件，一个人做就好）
- Team lead 核心价值是验收接缝，不只是派活

## 2026-02-28: Team Agents API 合约必须明确

并行派活给前端+后端 worker 时，必须把接口 schema 写成明确的字段定义（Pydantic model / TypeScript type）传给两边。自然语言描述不够，SocialMesh M1 和 M2 都因此踩坑：
1. M1: backend 返回 flat dict，前端期望 `{value, label}` 嵌套结构
2. M2: import 脚本传 `list[dict]`，API 期望 `list[str]`

## 2026-02-28: 晨会汇报需交叉比对数据源

audit.jsonl 可能只记录中间轮次的失败状态，不一定反映最终结果。晨会汇报任务状态时，必须同时查 audit.jsonl + agent.log + backlog，三者交叉验证。本次差点把已修复的 sales summary 任务误报为失败。

## 2026-02-28: 拆任务前先查现有 cron/skill 是否已覆盖

派活前必须先 `crontab -l` 核对现有定时任务，避免功能重叠。本次 Agent #2 营销引擎 skill 创建后发现现有 crontab 已有"每日客户跟进"cron（CST 10:00），功能重复。应在任务拆解阶段就排查，而不是让 worker 执行时自行判断。

## 2026-03-01: 平台 ≠ 品牌 — 派活时必须区分

SocialMesh 是内容运营**平台**，素仁轩是它服务的**品牌**。EMP_0008 管平台运营方法论，不管品牌定位。

错误复现：长会话中持续处理素仁轩关键词（采集/分析/简报），到派活 EMP_0008 时默认把 SocialMesh = 素仁轩，让 008 "结合素仁轩品牌" 做内化。Mason 当场纠正。

规则：
- 派活给 EMP_0008 时，不附带品牌上下文，只给平台方法论任务
- 品牌定位由 Mason 定义，或交给对应品牌的 PM（EMP_0001）
- 长会话中切换话题时，主动重新检查目标 agent 的角色边界

## 2026-02-28: 重启生产服务后必须立即验证连通性

修改生产环境配置并重启服务后，必须立即执行验证三件套：1) `curl health` 确认后端 200；2) `curl 首页` 确认前端加载时间正常（<2s）；3) 确认 SSH 连通。不能改完就告诉 Mason 去访问——本次重启后阿里云出现短暂网络波动（TCP 连接 36s），Mason 直接撞上了慢加载。

## 2026-03-02: Gemini 视频拆解 v2 prompt 设计决策

Mason 要求竞品视频拆解必须从"内容创作者视角"（不是观众视角），输出 9 大模块：basic_info / hook_analysis / product_catalog / content_structure / visual_analysis / audio_analysis / copywriting_analysis / engagement_triggers / replicable_template。

关键设计要求：
- 35+ 年龄客群对价格高度敏感，product_catalog 每个条目必须有 `price_signal` 字段
- 产品品牌名可以不记录，但必须记录品类+功效（"定妆喷雾，主打保湿不卡粉"）
- timeline 必须覆盖视频中每一个产品/片段，不允许省略
- 口播内容要精确转录原文，不要意译
- prompt 开头加"你必须按要求严格执行"强制 LLM 遵守规则

教训：v1 prompt 只有 10 个基础字段，Mason 认为"表面量化毫无价值"——缺少产品目录、音频分析、封面设计拆解、拍摄手法、具体说服技巧实例。prompt 设计必须从"下游消费者（Mason 团队）能拿来直接复用"出发。

## 2026-03-02: 第三方 API 响应不可信 — 必须校验字段值

greenvideo.cc 的 videoItemVoList API 响应中，某些 item 的 `baseUrl` 字段装的是视频标题文字而非 URL（fileType=video, canDownload=True 但 baseUrl="💓 cleanmakeup｜完美底妆的诞生"）。教训：**任何第三方 API 的字段值都必须做类型/格式校验**，不能假设字段名 = 字段内容。修复方法：`url.startswith('http')` + break on first valid match。
