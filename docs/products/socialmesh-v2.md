# SocialMesh v2 — 产品定义

> 产出者：EMP_0012 (Product Architect)
> 创建日期：2026-03-03

## 一句话描述

多品牌内容运营中台：从竞品情报到内容生产到发布管理到效果复盘，全链路闭环。

## 产品愿景

SocialMesh 不再是"多账号发布工具"，而是覆盖内容生命周期的运营中台。
品牌不绑死——通过 Account Manager (EMP_0011) 的 brief 注入品牌上下文，平台本身是品牌无关的。

## 归属

- 所属项目：SocialMesh（现有项目升级，非新建）
- 项目负责人：EMP_0008（内容运营总监）
- 技术负责人：EMP_0009（Content-Tech Dev）
- 内容执行：EMP_0010（Content Creator）

## 模块架构

```
SocialMesh（内容运营中台）
│
├── 模块1：内容生产
│   ├── 图文生产（image_engine，已在 socialmesh）
│   └── 视频生产（video pipeline，从 mason-hub/skills/video/video-download/ 迁入）
│
├── 模块2：内容管理
│   ├── 多账号管理
│   ├── 内容编辑器 + 草稿
│   ├── 排期 + 发布
│   └── 素材库
│
└── 模块3：数据与分析
    ├── 竞品情报（调用阿里云 MediaCrawler 采集 + 分析脚本）
    └── 自有复盘（发布后数据回收 + ROI 分析）
```

### 模块间数据流

```
模块3 竞品情报 → 选题方向 / 趋势洞察
        ↓
模块1 内容生产 → 成品（图片/视频/文案）
        ↓
模块2 内容管理 → 发布到各平台 → 发布记录（post_id + 时间）
        ↓
模块3 自有复盘 → 效果数据（24h/72h/7d）→ 反馈回模块1调优
```

---

## 模块1：内容生产

### 边界
- MVP：video pipeline 迁入 socialmesh，能通过 CLI 跑通完整流程（拆解→本地化→脚本→分镜→视频→组装）
- V1：Web UI 中可触发视频生产流程，展示制作进度，分镜审核在 UI 上完成（不依赖 Slack/Google Drive）
- 不做：视频剪辑（用 ffmpeg 自动组装，不做交互式剪辑）；不做实时渲染预览

### 现有代码迁移清单
从 `mason-hub/skills/video/video-download/` 迁入：
- content_pipeline.py（总调度，8 步）
- download.py（视频下载）
- gemini_analyze.py（Gemini 拆解）
- localize.py（品牌本地化）
- product_match.py（产品匹配推荐）
- shooting_script.py（拍摄脚本生成）
- storyboard.py（Nano Banana 分镜图）
- videogen.py（VEO 视频生成）
- assemble.py（ffmpeg 组装）
- content_board.py（排期表注册）
- generate_storyboard_doc.js（分镜文档生成）
- pencil_storyboard.py（Pencil 画布预览）
- slack_review.py（Slack 审核流程）
- gdrive_upload.py（Google Drive 上传）
- pipeline.py（旧版管线，向后兼容）

### 依赖项
- Google OAuth credentials（`mason-hub/.credentials/google-token.json`）→ 迁移或共享
- Gemini API key → 环境变量注入
- ffmpeg → 系统依赖
- Node.js（generate_storyboard_doc.js）→ 系统依赖

### Agent 职责
- EMP_0008：决定做什么内容（选题、分镜审核、品牌风格把关）
- EMP_0009：维护 pipeline 代码、bug 修复、新功能开发
- EMP_0010：视频脚本文案（旁白、字幕、镜头描述）

---

## 模块2：内容管理

### 边界
- MVP：当前 SocialMesh 已有功能（编辑器、排期、XHS 半自动发布）
- V1：Sprint 1 完成后的状态（图片上传、草稿管理、中文化、立即发布、Content.status 闭环）
- 不做：全自动 XHS 发布（保持半自动，防封号）

### 统一 Sprint 功能项（与 Phase A 并行）
- 内容编辑器图片上传
- 内容列表 / 草稿管理
- 界面中文化
- Content.status 发布后更新 + 状态 badge
- "立即发布"按钮
- 错误提示优化 + XHS 标题校验

### Agent 职责
- EMP_0008：排期决策、发布审批
- EMP_0009：前后端开发
- EMP_0010：内容撰写、社区互动

---

## 模块3：数据与分析

### 边界
- MVP：现有采集 + 分析脚本的能力归属迁移（代码进 socialmesh repo，数据留阿里云）
- V1：新增自有复盘视角——SocialMesh 发布记录与 XHS 帖子数据关联，展示自有内容的互动趋势
- 不做：实时数据流（保持批量采集模式）；不做跨平台归因（先只做 XHS）

### 数据架构原则
- **数据不出境**：采集数据、分析结果全部存阿里云
- **MediaCrawler 保持独立部署**：SocialMesh 不包含 MediaCrawler 本体，通过脚本调用 + 消费结果
- **展示入口**：竞品情报继续走阿里云看板（http://106.14.44.68/xhs/）；自有复盘新增 SocialMesh Dashboard 面板

### 代码迁移清单
从 `mason-hub/skills/` 迁入：
- xhs-crawl.sh（采集调度器）
- xhs-analyze.sh（分析调度器）
- xhs-analyze-viral.py（爆帖分析）
- _xhs_strategy_briefing.py（策略简报）
- _xhs_slack_summary.py（Slack 摘要）
- xhs-cookie-check.sh（Cookie 检测）

保持不动（阿里云独立运行）：
- /opt/mediacrawler/（MediaCrawler 本体 + SQLite）
- /opt/mediacrawler/analysis/（分析结果 JSON）
- _two_tier_crawl.py（两层采集核心逻辑，阿里云本地）

### 自有复盘新增内容
- 数据关联：SocialMesh 发布记录（post_id, published_at, account_id）↔ MediaCrawler 采集的互动数据
- 采集节奏：发布后 24h / 72h / 7d 自动回收该帖子互动数据
- 展示：SocialMesh Dashboard 新增 analytics 面板（按帖子/按账号/按时间段）
- ROI 粗算：互动数据 × 归因窗口（72h 内订单）— 等官方 API 接通后才能做精确归因

### Agent 职责
- EMP_0008：数据分析职责全权负责，决定采什么、分析什么、策略产出
- EMP_0009：采集脚本维护、分析面板开发
- EMP_0010：消费分析结论，调整内容策略

---

## 不做清单（负向边界）

- 不做通用 SaaS（不服务外部客户，只服务 Mason 的品牌矩阵）
- 不做微信自动化（Phase 4 之前绝对禁止）
- 不做实时数据管道（批量采集够用）
- 不做交互式视频剪辑（ffmpeg 自动组装）
- 不做跨境数据传输（数据留阿里云，通过浏览器看板访问）
- 不把 MediaCrawler 本体纳入 SocialMesh 代码库

---

## 迭代路径

### 统一 Sprint（基础功能 + Phase A 并行，2026-03-03 启动）

### Phase A：代码归属迁移（与基础功能并行）
- [ ] 模块1 代码迁移：video pipeline → socialmesh/backend/content/video_pipeline/
- [ ] 模块3 代码迁移：分析脚本 → socialmesh/backend/analytics/ 或 socialmesh/scripts/
- [ ] 依赖项处理：credentials 共享方案、环境变量统一
- [ ] Agent 角色定义更新：EMP_0008 + EMP_0009 + EMP_0010

### Phase B：模块间集成
- [ ] 模块3→模块1 数据流：竞品分析结果自动填入内容生产的选题输入
- [ ] 模块2→模块3 数据流：发布记录自动触发自有复盘数据采集
- [ ] Dashboard 统一：SocialMesh UI 展示三个模块的状态

### Phase C：自有复盘闭环
- [ ] 发布后自动回收互动数据（24h/72h/7d）
- [ ] 效果数据反馈到内容生产（哪种内容效果好→调整生产策略）
- [ ] Analytics 面板上线

---

## Mason 批准

- 日期：2026-03-03
- 决定：做
- 备注：原 Sprint 1/2 合并为统一 Sprint，与 Phase A 代码迁移并行推进
