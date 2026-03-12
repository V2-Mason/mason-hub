# Agent 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: Python 中文字符串（强化）

生成 Python 代码时**禁止出现任何中文标点**（引号 `""''`、括号 `（）`、逗号 `，`、冒号 `：`）。写完代码后第一件事检查非 ASCII 字符。踩坑记录：中文全角引号导致 SyntaxError: unexpected EOF，浪费了 1 轮修复机会。

## 2026-03-02: 第三方 API 字段值校验 + LLM JSON 健壮解析

两个通用模式，不只适用于视频管道：
1. **API 字段值校验**：字段名不等于字段内容。greenvideo.cc 的 `baseUrl` 字段装的是视频标题文字而非 URL。任何外部 API 返回的值都要校验格式（如 URL 检查 `startswith('http')`）。
2. **LLM JSON 解析**：LLM 输出的 JSON 常有 trailing comma、markdown 包裹、前后多余文字。标准链：去 markdown fences → 提取 `{}` → regex 去 trailing commas → json.loads。参考 `skills/video/video-download/gemini_analyze.py::_parse_gemini_json()`。

## 2026-03-02: Google Sheets API 双向同步模式

Drive ↔ Sheet 同步看板（`content_board.py`）的技术要点：
1. **Sheet 做 state store**：用 Sheet 行的 `内容ID` 列做去重，不需要额外状态文件。`values().append()` 追加新行，`values().get()` 读现有数据。
2. **下拉验证**：`setDataValidation` + `ONE_OF_LIST` + `showCustomUi: True` 设置下拉菜单。
3. **Drive 文件夹原子移动**：`files().update(addParents=new, removeParents=old)` 不改 fileId/webViewLink，Sheet 链接保持有效。
4. **幂等设计**：sync 可重复跑，已存在的行不会重复插入，已在正确文件夹的不会重复移动。
