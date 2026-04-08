# P3 Tier 2/3 Top 10 Hook 采集日志

Batch Recon 2026-04 Line A: 8 个 Tier 2/3 账号各取 Top 10 高播放视频做 hook 分析。

执行顺序：数据量从小到大，串行（rate limit + 单 GPU）。

跳过：tier2-suozhang-linchao (所长林超，停更 1.5 年)

---

## tier3-yuanxiaozhi (袁小智)

- 采样: 4 / 10 (账号本身只有 4 个 ≥60s 视频，全部采集)
- 下载: 4 成功 / 0 失败
- 转录: 4 成功 / 0 失败 (RTF 0.037, Vulkan)
- full_text.txt: 588 行
- error: 无

## tier2-yihui-indiedev (一辉 indiedev)

- 采样: 10 / 10
- 下载: 10 成功 / 0 失败
- 转录: 10 成功 / 0 失败 (Vulkan)
- full_text.txt: 802 行
- error: 无

## tier2-weisheng-ai (未生 AI)

- 采样: 10 / 10 (复用前一 subagent 留下的 selected.tsv)
- 下载: 10 成功 / 0 失败
- 转录: 10 成功 / 0 失败 (Aggregate RTF 0.330, Vulkan)
- full_text.txt: 1647 行
- error: 无

## tier2-mark-tech (马克的技术工作坊)

- 采样: 10 / 10 (复用 selected.tsv)
- 下载: 10 成功 / 0 失败
- 转录: 10 成功 / 0 失败 (Aggregate RTF 0.029, Vulkan)
- full_text.txt: 6420 行
- error: 无

## tier3-dasheng (花果山大圣)

- 采样: 10 / 10 (复用 selected.tsv)
- 下载: 10 成功 / 0 失败
- 转录: 10 成功 / 0 失败 (Aggregate RTF 0.029, Vulkan)
- full_text.txt: 6421 行
- error: 无

## tier2-xiaoa-finance (小 A 学财经)

- 采样: 10 / 10 (复用 selected.tsv)
- 下载: 10 成功 / 0 失败
- 转录: 10 成功 / 0 失败 (Aggregate RTF 0.042, Vulkan)
- full_text.txt: 1309 行
- error: 无

## tier2-he-tongxue (何同学)

- 采样: 10 / 10 (复用 selected.tsv)
- 下载: 8 成功 + 2 手动重下载 (BV1Nt4y1D7pW_p1/_p2 多分页, download_audio.py 不识别 `_pN` 后缀, 直接 yt-dlp `?p=N` 绕过)
- 转录: 10 成功 / 0 失败 (Aggregate RTF 0.034, Vulkan)
- full_text.txt: 2874 行
- error: download_audio.py 多分页 BV ID 处理 bug (Gap, 见 lessons)

## tier2-wuyifei (温义飞)

- 采样: 10 / 10 (复用 selected.tsv)
- 下载: 10 成功 / 0 失败
- 转录: 10 成功 / 0 失败 (Aggregate RTF 0.042, Vulkan)
- full_text.txt: 2097 行
- error: 无

