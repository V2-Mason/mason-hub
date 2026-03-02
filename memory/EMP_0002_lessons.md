# Agent 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: Python 中文字符串

Python 代码中避免使用中文全角引号 `""`，会导致 SyntaxError。用英文引号或 Unicode escape `\u201c\u201d`。

## 2026-03-02: Gemini API — 中文文件名会炸 httpx header

`google-genai` SDK 的 `client.files.upload(file=path)` 底层用 httpx 发 multipart，文件名写入 HTTP header。HTTP header 只允许 ASCII，中文文件名直接报 `UnicodeEncodeError: 'ascii' codec can't encode characters`。

修复模式：上传前检测文件名是否 ASCII，非 ASCII 则创建临时 symlink（ASCII 名）指向原文件，上传完清理：
```python
if not os.path.basename(video_path).isascii():
    temp_link = os.path.join(tempfile.mkdtemp(), 'video.mp4')
    os.symlink(os.path.abspath(video_path), temp_link)
    upload_path = temp_link
```

## 2026-03-02: Gemini JSON 输出不可靠 — 必须健壮解析

复杂/长 prompt（如 9 模块视频拆解）让 Gemini 返回的 JSON 经常有问题：trailing comma、markdown code fences 包裹、响应前后有多余文字。**不能直接 `json.loads(response.text)`**。

健壮解析三步走：
1. 去除 markdown fences（\`\`\`json ... \`\`\`）
2. 提取最外层 `{}` 块（跳过前后文字）
3. 用 regex `re.sub(r',\s*([}\]])', r'\1', block)` 去掉 trailing commas
三步都失败才抛异常。见 `skills/video-download/gemini_analyze.py::_parse_gemini_json()`。

## 2026-03-02: 第三方 API 字段值必须校验

greenvideo.cc 的 `videoItemVoList` 中部分 item 虽然 `fileType=video` + `canDownload=True`，但 `baseUrl` 装的是视频标题文字（不是 URL）。教训：**字段名 ≠ 字段内容**，必须 `url.startswith('http')` 做值校验。循环匹配到第一个合法 URL 就 break。

## 2026-03-02: Pipeline 基础 — 输出目录必须 makedirs

`pipeline.py` 的 `--output-dir` 参数对应的目录可能不存在。写文件前必须 `os.makedirs(work_dir, exist_ok=True)`，否则 `FileNotFoundError`。这是基本功，但忘了就炸。
