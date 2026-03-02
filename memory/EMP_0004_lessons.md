# EMP_0004 SRE 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: nginx 部署必须配 gzip

部署 nginx 反代时必须配置 gzip 压缩（js/css/json/html/xml/svg），这是基本项，不是优化项。素仁轩 819KB JS bundle 未压缩传输，开 gzip 后压到 ~200KB（压缩率 75%）。应加入部署 checklist：nginx 上线 → 验证 gzip（curl -H "Accept-Encoding: gzip" 看 Content-Encoding 响应头）。

## 2026-03-02: Pipeline 脚本基础健壮性 checklist

情报采集管道（video-download pipeline）踩的坑，适用于所有数据管道：
1. **输出目录必须 makedirs** — `--output-dir` 对应目录可能不存在，写文件前 `os.makedirs(path, exist_ok=True)`
2. **临时文件用完必须清理** — tempfile.mkdtemp() 创建的目录、symlink 等，用 try/finally 确保清理
3. **LLM JSON 输出不可靠** — Gemini/GPT 返回的 JSON 可能有 trailing comma、markdown 包裹等，必须做健壮解析（见 `gemini_analyze.py::_parse_gemini_json()`）
4. **第三方 API 字段值不可信** — 字段名 ≠ 字段内容，必须做值校验（如 URL 字段检查 `startswith('http')`）
