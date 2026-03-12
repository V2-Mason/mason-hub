# EMP_0008 SocialMesh PM 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---


## 2026-03-01: EMP_0008 角色边界

EMP_0008 仅负责内容运营方法论（内容策略/评分/发布节奏），品牌定位/调性定义拒绝并转交品牌PM或Mason；可读取已有品牌文件，不可定义。

## 2026-02-28: Image Engine 开发原则

pgvector/Scorer/promptag.app 采集三组件 defer：<500 条模板用 brute-force cosine similarity，Scorer 需真实数据才有意义，采集用手动导入替代；先跑通核心链路再优化。

## 2026-03-02: 竞品视频拆解 v2 — 9 模块结构 + 35+ 客群 price_signal

Mason 定义的竞品视频拆解标准为 9 大模块（basic_info / hook_analysis / product_catalog / content_structure / visual_analysis / audio_analysis / copywriting_analysis / engagement_triggers / replicable_template）。

内容运营关键要求：
- **视角**：从"内容创作者"视角（不是观众），目标是提取可复用模板
- **product_catalog**：每个产品必须有 `price_signal` 字段（35+ 客群对价格高度敏感，"不像年轻人容易被种草就冲动下单"）
- **口播转录**：精确转录原文，不意译不概括
- **timeline**：必须覆盖视频中每一个产品/片段，不允许省略
- **产品记录**：品牌名可不记，品类+功效必须记（如"定妆喷雾，主打保湿不卡粉"）

prompt 文件：`skills/video/video-download/gemini_analyze.py` ANALYSIS_PROMPT 变量。在策划内容时可直接参考这个结构作为拆解框架。

## 2026-03-02: 内容制作管线全链路

端到端管线已就位（`skills/video/video-download/content_pipeline.py`）：
1. Gemini 拆解参照视频 → 9 模块 JSON（timeline = 脚本）
2. 品牌本地化（`localize.py`）→ 同格式 JSON，只改调性/话术
3. Nano Banana 2 分镜（`storyboard.py`）→ 每个 segment 一张 9:16 图
4. VEO 3.1 视频（`videogen.py`）→ 每个分镜一段视频
5. ffmpeg 组装（`assemble.py`）→ 成片

**内容看板**（`content_board.py`）：Drive ↔ Sheet 双向同步。Mason 在 Sheet 下拉菜单改状态 → 文件自动移到对应文件夹。状态流：🔄审核中 → ✅已确认 → 📋排期 → 🚀已发布。

Sheet: `2026-03_内容排期表`（02-排期看板/）。素材明细 tab K 列是状态下拉菜单。

## 2026-03-04: 一素材多剪 — 渠道×目标矩阵系统

内容管线升级为"剪辑情报系统"，一套 VEO 素材产出多版本成片。

关键运营知识：
- **渠道时长甜点**：抖音 15-25s，小红书 45-60s，视频号 30-45s，微信私域 15-25s — 超甜点的视频数据会差
- **冲突时渠道优先**：节奏/时长/字幕以渠道为准，镜头选择/内容结构以目标为准，文案以品牌 voice.md 为准
- **无效组合**：微信私域×认知型（私域用户已认识你）、微信私域×互动型（文字更有效）— 系统自动跳过
- **特殊组合处理**：抖音×教育型压缩到 20-30s 只讲一个知识点；抖音×信任型快切幕后片段配大号文字标注
- **成本**：多剪只加 1 次 Gemini Flash（~$0.01），不增加 VEO 消耗
- **拆解 prompt 现在输出** `editing_style`（14 维剪辑指纹）+ `marketing_goal`（营销目标标签），积累后供策略分析
- **管线代码已迁移**：从 `skills/video/video-download/` 迁到 `~/socialmesh/backend/content/video_pipeline/`
- **Pipeline CLI**：`--cuts "抖音×认知型,小红书×种草型"` 启用多剪
- **架构文档**：`~/socialmesh/docs/plans/2026-03-04-multicut-architecture.md`
