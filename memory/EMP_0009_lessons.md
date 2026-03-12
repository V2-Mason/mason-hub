# EMP_0009 Content-Tech Dev 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---


## 2026-02-28: Python 中文字符串

`adapter_engine.py` 中文全角引号 `""` 导致 SyntaxError，Python 字符串改用英文引号或 `“”`。

## 2026-03-02: google-genai SDK — 中文文件名导致 httpx header 编码失败

`client.files.upload(file=path)` 的 HTTP multipart header 只接受 ASCII。中文文件名报 `UnicodeEncodeError`。修复：上传前用 ASCII 名临时 symlink，上传后清理。模式见 `skills/video/video-download/gemini_analyze.py` 的 ASCII-safe upload 段。

## 2026-03-02: LLM JSON 输出健壮解析模式

LLM（Gemini/GPT 等）生成的 JSON 常有问题：markdown fences 包裹、trailing commas、前后多余文字。不能直接 `json.loads()`。

标准处理链：去 markdown fences → 提取最外层 `{}` → regex 去 trailing commas → json.loads。见 `gemini_analyze.py::_parse_gemini_json()` 实现。

## 2026-03-02: Google AI 模型 ID 查询

Google 模型 display name ≠ API model ID。用 `client.models.list()` 查确切 ID：
- Nano Banana 2 → `gemini-3.1-flash-image-preview`（图片生成，`response_modalities=['IMAGE']`）
- VEO 3.1 → `veo-3.1-generate-preview`（视频生成，异步 operation）
- 用 display name 调 API 会 404

## 2026-03-02: Sheets API 实用模式

- **下拉菜单**：`setDataValidation` + `ONE_OF_LIST` + `showCustomUi: True`
- **追加行**：`values().append()` + `insertDataOption='INSERT_ROWS'`
- **清空数据保留表头**：`values().clear(range='Sheet!A2:Z200')`
- **Drive 文件移动不改链接**：`files().update(addParents=, removeParents=)`，fileId 和 webViewLink 保持不变

## 2026-03-03: VEO 视频生成 — 配额管理与 prompt 工程

### 配额限制
- VEO 所有模型（3.1/3.1-fast/3.0/3.0-fast/2.0）共享同一个每日配额，不是按模型分开的
- 免费/付费 tier 每天大约能跑 ~10 个视频生成调用，超出全部 429 RESOURCE_EXHAUSTED
- 配额每天重置（UTC 时间）
- **必须实现 skip_existing**：已有 clip 跳过不生成，避免浪费配额。检查 `os.path.exists(video_path) and os.path.getsize(video_path) > 1024`

### 模型选择策略
- `veo-3.1-generate-preview`（$0.40/s）配额容易打满 → 优先用 `veo-3.1-fast-generate-preview`（$0.15/s）
- 质量差别不大，成本省 60%
- 一次跑不完就分天跑，skip_existing 自动续接

### Prompt 工程 — 必须严格还原分镜脚本
- **之前的错误**：只传了 frame_description + camera_movement + lighting，丢失了 voiceover/props/acting_direction/text_overlay/audio_note/wardrobe 等字段
- **正确做法**：用结构化标签格式，把脚本里每个字段都传给 VEO：
  ```
  【格式】竖版9:16短视频片段。
  【场景】{location}
  【服装】{wardrobe}
  【灯光】{lighting_setup}
  【景别】{shot_type}
  【镜头运动】{camera_movement}
  【时长】{duration}秒
  【画面描述】{frame_description}
  【表演指导】{acting_direction}
  【道具】{props}
  【画面文字】{text_overlay}
  【口播台词】{voiceover}
  【声音设计】{audio_note}
  ```
- 全局字段（location/wardrobe/lighting_setup）每个 shot 都要重复传，VEO 不记上下文
- prompt 从 ~80 字增加到 ~330-400 字后，视频质量显著提升

### Google Docs docx 渲染
- Google Docs 导入 docx 时，图片按像素大小渲染，忽略 DXA 列宽约束
- 280px 图片 = 2.92 英寸（96 DPI），必须确保表格列宽 ≥ 图片宽度
- 解决方案：4 列表格 + columnSpan 合并，合并后半宽 4680 DXA（3.25 英寸）> 2.92 英寸

## 2026-03-03: 内容排期表自动注册

- `content_board.py` 新增 `register_review_content()` — 管线生成审核文档后直接写 Sheet，不依赖 Drive 文件夹扫描
- 素材明细 Sheet 新增"生成日期"列（L 列），记录每条素材的生成时间
- 幂等设计：先查 project_id 是否已存在，存在则更新，不重复插入

## 2026-03-04: VEO Prompt 第二次重写 — 结构化标签 → 自然叙事

### 第一次重写（结构化标签）的问题
第一版用中文标签格式（【格式】【场景】...），15 个 shot 中 4 个失败（shot 1/9/12/13）。Mason 反馈 9 个具体问题：
1. 中英混杂、结构凌乱 → 应该是流畅自然语言
2. 对话格式机械（"The person says"） → VEO 大概率不支持中文口播
3. camera_movement 全写"固定" → 缺乏运动引导
4. negative prompt 和 prompt 内容矛盾（prompt 里有定格/虚化，negative 里禁止）
5. "挥手打招呼"是瞬间动作，撑不满 4 秒
6. "干净明亮的背景"太抽象
7. "虚化处理"是后期术语，不是拍摄指令
8. "双手展示产品"对 6 秒来说太静态
9. props 暴露了 Python list 语法 `['COSRX...']`

### 第二次重写（自然叙事）成功
改为 VEO 官方推荐的 flowing narrative 格式：Subject+Action → Style/Setting → Camera+Motion → Ambiance/Lighting
- 一个连续段落，无标签/标记
- camera "固定" → 默认 "slow gentle drift"
- voiceover/text_overlay/audio_note **不传给 VEO**（VEO 无法处理）
- props 用视觉描述（"a white bottle with blue cap"），不用品牌名
- 每个 prompt 以 "Vertical 9:16 video. Photorealistic, natural texture, cinematic quality." 锚定风格
- 结果：15/15 全部成功

### 教训
- VEO prompt 不是"信息越多越好"，而是"视觉描述越具体越好"
- 后期概念（虚化/分屏/定格/贴纸/特效）必须在拍摄脚本阶段就拦住（已在 shooting_script.py 加 VEO 约束 A-E）
- 瞬间动作不能做 VEO prompt（至少要 4 秒的持续动作）

## 2026-03-04: 多版本剪辑 — 渠道×目标 架构升级

### 架构变更
- **旧系统**：4 个简单 preset（xhs_tutorial, douyin_fast, product_focus, highlight_15s），每个硬编码平台+风格+时长
- **新系统**：5 渠道（抖音/小红书/视频号/微信私域/产品聚焦）× 7 营销目标（认知/种草/教育/信任/促销/复购/互动）的矩阵组合
- **核心原则**：参数表是给 Gemini 的风格指南，不是 ffmpeg 硬编码命令。同样是"抖音认知型"，化妆刷教程和成分科普的具体剪辑方案完全不同，必须让 Gemini 看完实际素材后动态判断

### 代码变更速查
- `config.py`：`MULTICUT_VARIANTS_DEFAULT` → `MULTICUT_DEFAULTS`，格式 `['小红书×种草型', '抖音×认知型']`
- `multicut.py`：`VARIANT_PRESETS` → `CHANNEL_GUIDES` + `GOAL_GUIDES`；`generate_edls(variants=)` → `generate_edls(cuts=)`
- `content_pipeline.py`：CLI `--variants` → `--cuts`，接受 `"抖音×认知型,小红书×种草型"` 格式
- `gemini_analyze.py`：拆解 prompt 新增 `marketing_goal` 字段（primary_goal/secondary_goal/funnel_stage/intended_user_action）

### 新 EDL schema
Gemini 输出的 EDL JSON 新增字段（assemble.py 暂未对接，等实际 Gemini 输出后再做）：
- `visual_effects`: slow_zoom_in / slow_zoom_out / speed_ramp / reverse / blur_bg
- `end_card`: 结尾卡片（时长+文案+视觉风格）
- `cover_suggestion`: 封面建议（源素材+时间戳+封面文字）
- `editing_rationale`: 剪辑思路说明

### 无效组合自动跳过
- 微信私域×认知型（私域用户已认识你）
- 微信私域×互动型（微信群互动用文字更有效）

### 参考文档
完整架构文档：`~/socialmesh/docs/plans/2026-03-04-multicut-architecture.md`

## 2026-03-09: Celery prefork + asyncio.run() 产生 zombie 进程

### 问题
SocialMesh Celery worker（prefork 模式）中 `publishing.py` 用 `asyncio.run()` 调用 adapter 的 async 方法，每次执行都 fork 子进程但父进程不回收，产生 zombie。Playwright 浏览器实例也随之泄漏（每 6h 多 2 个 node 进程，每个 ~54MB）。从 Mar06 开始积累 14 个 zombie + 10 个 Playwright 泄漏，共浪费 ~884MB。

### 根因
- `asyncio.run()` 在 Celery prefork worker 中会创建新事件循环并 fork 子进程
- 父进程（Celery worker PID 1123）没有正确 `waitpid()` 回收
- adapter 内部启动的 Playwright 浏览器实例用完没关闭

### 修复
1. `scheduler.py` 加 `worker_max_tasks_per_child=50`（worker 跑 50 个任务后自动回收，治标）
2. `publishing.py` 新增 `_run_async()` 替代 `asyncio.run()`（复用事件循环而非每次新建，治本）
3. 当前 SocialMesh 无实际发帖需求，Celery 已停止

### 教训
- **Celery prefork + asyncio.run() = zombie 工厂**，必须用 `loop.run_until_complete()` 复用事件循环
- **空转服务也要关**：没有帖子要发的 Celery 每分钟空跑 `check_scheduled_posts`，依然产生 zombie
- **未使用的服务不应常驻**：SocialMesh 暂未上线，Celery + Vite dev server 不该一直跑
