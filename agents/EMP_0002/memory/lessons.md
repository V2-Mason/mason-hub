# Agent 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---


## 2026-02-28: Python 中文字符串

避免中文全角引号 `""`（致 SyntaxError），改用英文引号或 `“”`。

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
三步都失败才抛异常。见 `skills/video/video-download/gemini_analyze.py::_parse_gemini_json()`。

## 2026-03-02: 第三方 API 字段值必须校验

greenvideo.cc 的 `videoItemVoList` 中部分 item 虽然 `fileType=video` + `canDownload=True`，但 `baseUrl` 装的是视频标题文字（不是 URL）。教训：**字段名 ≠ 字段内容**，必须 `url.startswith('http')` 做值校验。循环匹配到第一个合法 URL 就 break。

## 2026-03-02: Pipeline 基础 — 输出目录必须 makedirs

`pipeline.py` 的 `--output-dir` 参数对应的目录可能不存在。写文件前必须 `os.makedirs(work_dir, exist_ok=True)`，否则 `FileNotFoundError`。这是基本功，但忘了就炸。

## 2026-03-02: Google AI 模型 ID ≠ Display Name

Google Gemini 生态的模型 display name 和 API model ID 不同。必须用 `client.models.list()` 查确切 ID：
- Nano Banana 2（图片生成）→ `gemini-3.1-flash-image-preview`
- VEO 3.1（视频生成）→ `veo-3.1-generate-preview`
- 直接用 display name 调用会 404

## 2026-03-02: VEO 3.1 视频生成 API 模式

VEO 是异步 API：`client.models.generate_videos()` 返回 operation → 轮询 `client.operations.get(operation)` → `operation.done` 后取结果。关键点：
- `duration_seconds` 只接受字符串 `'4'`/`'6'`/`'8'`
- image-to-video 用 `types.Image(image_bytes=bytes, mime_type='image/png')`
- 每段视频约 60-75 秒生成，轮询间隔 15 秒够用
- 下载用 `client.files.download(file=video)` + `video.save(path)`

## 2026-03-02: Google Sheets API 下拉菜单

用 `setDataValidation` + `ONE_OF_LIST` 设置下拉菜单。`showCustomUi: True` 显示下拉箭头。范围用 `sheetId`（非 sheet name）+ row/column index。Sheet tab 的 sheetId 在创建时由 `properties.sheetId` 指定。

## 2026-03-02: Drive 文件夹移动

`files().update(fileId=id, addParents=new, removeParents=old)` 原子移动。文件 ID 和 webViewLink 不变，Sheet 里的链接仍有效。

## 2026-03-09: Radar 系统合并 — 趋势分析 + Scout 情报集成到 :8081

### 变更
- Radar Tracker (:8081) 新增 `/insights` 路由（合并自 trend_report.py 的 HTML 功能）
- 新增 `/intel` 路由（渲染 `intel/digests/*.md` Scout 情报简报）
- cron 已移除 `trend_report.py html` 生成（旧 :8080/trends/latest.html 不再更新）
- `trend_report.py` 文本模式保留给 `/standup` 晨会用
- LAYERS 和 LAYER_DISPLAY 补充了 `基础设施/硬科技` (C+ 层)
- `/intel` 文件排序改为按修改时间倒序（修复 W09-digest 字典序排在日期前面的 bug）

### Radar :8081 当前路由一览
- `/` — 统一视图（分层命中 + 未分类热榜 + Scout 摘要）
- `/hotlist` — 原始热榜 + dismiss 按钮
- `/insights` — 趋势分析（分层 + 7天热度）
- `/intel` — Scout 情报简报（Markdown 渲染）
- `/api/dismiss` / `/api/mark-read` / `/api/stats` / `/api/weekly-report` — API

## 2026-03-12: claude -p 认证机制 + Gateway 成本优化

- `claude -p` 有 `ANTHROPIC_API_KEY` 环境变量时走 API 计费，没有时 fall back 到 OAuth（Max 订阅）
- `.env` 里配了 API key + `run-agent.sh` 调 `claude -p` = 每个 agent 任务都走 API 计费，3/11 花了 $17
- 修复：`call_claude()` 里 `unset ANTHROPIC_API_KEY`，让 Dispatcher 任务走 Max 订阅
- Gateway LLM 心跳 ROI 极低：11 次重巡全部结论"系统正常"，花 $12+ 确认没问题。用纯 bash `health-check-lite.sh` 替代，mason-gateway.py 保留作按需诊断工具
- `anthropic.Anthropic()` Python SDK 只能走 API key，不能走 Max — slack-ask.py 仍需 API key
