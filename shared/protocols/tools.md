# 通用工具协议（跨 Agent 共享）

## Semantic Snapshot（网页内容提取）

需要阅读网页内容时（竞品分析、平台规则、帮助文档等），优先使用此工具而非直接抓 HTML：
```bash
python3 ~/mason-hub/skills/semantic_snapshot.py "URL" --max-chars 6000
```
- 自动检测页面类型（文章/表格/交互式），提取干净 markdown
- 比原始 HTML 压缩 10x+，大幅节省 token
- 支持 `--no-js` 轻量模式（不启动浏览器）
- 支持 `--json` 结构化输出
- 中文页面完全支持
