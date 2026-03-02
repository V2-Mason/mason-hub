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
