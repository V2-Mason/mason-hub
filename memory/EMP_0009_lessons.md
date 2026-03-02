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
