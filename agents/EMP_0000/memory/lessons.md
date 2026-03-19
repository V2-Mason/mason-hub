# EMP_0000 Meta Manager 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---



## 2026-02-28: Team Agents 开团标准
≥2 个不重叠领域且每边 ≥3 文件才开 team，否则一人做更省 token；team lead 核心价值是验收接缝，不只是派活。

## 2026-02-28: Team Agents API 合约
并行派活前须用 Pydantic model / TypeScript type 定义接口 schema，自然语言不够。M1 踩坑：backend 返 flat dict vs 前端期望 `{value, label}`；M2 踩坑：传 `list[dict]` vs API 期望 `list[str]`。

## 2026-02-28: 晨会数据交叉验证
任务状态须同时查 `audit.jsonl` + `agent.log` + `backlog` 三者一致才能确认，`audit.jsonl` 可能只记录中间轮次失败状态。

## 2026-02-28: 派活前查现有 cron
派活前先执行 `crontab -l` 排查现有定时任务，避免新建 skill 与已有 cron 功能重复（本次与 CST 10:00 客户跟进 cron 重叠）。

## 2026-03-01: 平台 ≠ 品牌
EMP_0008 只管 SocialMesh 平台方法论，派活不附品牌上下文；品牌定位归 Mason 或 EMP_0001；长会话切换话题时主动检查目标 agent 角色边界。

## 2026-02-28: 重启生产服务验证三件套
重启后立即执行：`curl health`（期望 200）→ `curl 首页`（期望 <2s）→ SSH 连通确认；不能直接让 Mason 访问验证。

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

## 2026-03-02: 内容制作管线架构决策

端到端管线跑通：Gemini 拆解 → 品牌本地化 → Nano Banana 2 分镜 → VEO 3.1 视频 → ffmpeg 组装 → Drive 上传 → Sheet 同步。关键架构决策：
1. **Sheet 作为统一看板**：Mason 在 Sheet 下拉菜单改状态，系统自动移 Drive 文件到对应文件夹。无需额外项目管理工具。
2. **双向同步**：Drive→Sheet 发现新内容，Sheet→Drive 响应状态变更。Sheet 本身就是 state store，不需要额外状态文件。
3. **模型命名坑**：Google AI 模型的 display name ≠ API model ID（Nano Banana 2 = `gemini-3.1-flash-image-preview`，不是 `nano-banana-2`）。调用前必须 `client.models.list()` 确认。
