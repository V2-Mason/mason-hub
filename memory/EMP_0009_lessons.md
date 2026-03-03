# EMP_0009 Content-Tech Dev 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: Python 中文字符串

`adapter_engine.py` 里用了中文全角引号 `""` 导致 SyntaxError。Python prompt 字符串里避免中文引号，用英文引号或 Unicode escape `\u201c\u201d`。

## 2026-03-02: google-genai SDK — 中文文件名导致 httpx header 编码失败

`client.files.upload(file=path)` 的 HTTP multipart header 只接受 ASCII。中文文件名报 `UnicodeEncodeError`。修复：上传前用 ASCII 名临时 symlink，上传后清理。模式见 `skills/video-download/gemini_analyze.py` 的 ASCII-safe upload 段。

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
