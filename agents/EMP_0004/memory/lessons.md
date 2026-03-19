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

## 2026-03-02: GCP 系统依赖 checklist

内容制作管线需要 ffmpeg（拼接视频片段）。GCP 实例默认未安装。上线新管道前检查系统依赖：`sudo apt install ffmpeg`。应加入部署 checklist：管线上线 → 验证 ffmpeg/imagemagick 等多媒体工具是否就位。

## 2026-03-09: agent-status-report.sh 监控盲区 — 进程级检查缺失

### 问题
SocialMesh Celery 产生 14 个 zombie 进程 + 10 个 Playwright 泄漏进程（530MB），空转 Celery 占 354MB，Vite dev server 占 87MB。总计 ~970MB 纯浪费，占 3.8GB 机器的 25%。**现有 SRE 日报完全没发现**，因为只看了 `free -h` 总量和 `df -h` 磁盘，没有进程级检查。

### 根因
- `agent-status-report.sh` 缺少：zombie 检测、Top N 内存进程、同名进程过多告警、内存使用率阈值告警
- 没有"预期进程白名单"概念，Vite dev server 常驻生产无人问

### 修复
已给 `agent-status-report.sh` 新增 Section 6b:
1. **Zombie 检测** — `ps -eo stat | grep Z`，有就 🔴 告警
2. **Top 5 内存进程** — 按 RSS 排序列出
3. **内存使用率阈值** — 60% ⚠️ / 80% 🔴
4. **同名进程过多** — 同名 ≥5 个实例告警（抓到 Playwright 泄漏）
5. Slack 摘要带 zombie + 内存告警标记

### 教训
- **监控必须到进程粒度**，"总内存还剩 1.3GB" 看不出谁在泄漏
- **增长趋势比瞬时值更重要**：Playwright 每 6h 多 2 个进程，只看一次快照看不出来
- **空转服务也吃资源**：未使用的 Celery/Vite 应该关掉而非让它跑着
