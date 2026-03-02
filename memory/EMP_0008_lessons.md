# EMP_0008 SocialMesh PM 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-03-01: 平台角色边界 — 不接品牌定位任务

EMP_0008 是 SocialMesh 内容运营总监，管的是平台运营方法论（内容策略、评分、发布节奏）。品牌定位、品牌调性、品牌语境不是 008 的职责。

如果被要求"结合 XX 品牌做内化"：
- 内化内容运营方法论 → ✅ 可以做
- 定义品牌调性/品牌定位 → ❌ 拒绝，交给品牌 PM 或 Mason
- 在项目 context 里引用已有品牌定位文件 → ✅ 可以（读取，不定义）

## 2026-02-28: 先跑通再优化

Image Engine 开发中，pgvector / Scorer / promptag.app 采集三个组件先 defer：
- brute-force cosine similarity 在 500 条模板以内完全够用
- Scorer 需要真实使用数据才有意义，过早加没有反馈可算
- 手动导入可以替代自动采集
不要第一版就把所有组件做完，先让核心链路跑起来。

## 2026-03-02: 竞品视频拆解 v2 — 9 模块结构 + 35+ 客群 price_signal

Mason 定义的竞品视频拆解标准为 9 大模块（basic_info / hook_analysis / product_catalog / content_structure / visual_analysis / audio_analysis / copywriting_analysis / engagement_triggers / replicable_template）。

内容运营关键要求：
- **视角**：从"内容创作者"视角（不是观众），目标是提取可复用模板
- **product_catalog**：每个产品必须有 `price_signal` 字段（35+ 客群对价格高度敏感，"不像年轻人容易被种草就冲动下单"）
- **口播转录**：精确转录原文，不意译不概括
- **timeline**：必须覆盖视频中每一个产品/片段，不允许省略
- **产品记录**：品牌名可不记，品类+功效必须记（如"定妆喷雾，主打保湿不卡粉"）

prompt 文件：`skills/video-download/gemini_analyze.py` ANALYSIS_PROMPT 变量。在策划内容时可直接参考这个结构作为拆解框架。
