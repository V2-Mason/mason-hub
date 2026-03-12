## TrendRadar + RSSHub 趋势监控系统 (2026-03-08)

### 部署概况
- TrendRadar: ~/mason-hub/tools/trendradar/，Python 脚本模式，cron */30 采集
- RSSHub: Docker 容器 diygod/rsshub，端口 1200，--restart always
- 配置备份: tools/trendradar-config/（config.yaml + frequency_words.txt）
- 数据: output/news/ 和 output/rss/ 下 SQLite 按日期分文件
- 不推 Slack，/standup 晨会读 SQLite 汇报

### 数据源
- 11 个中文热榜（百度/微博/抖音/知乎/B站/头条/华尔街见闻/澎湃/财联社/凤凰/贴吧）
- 10 个 RSS 源：3 个走 RSSHub（36氪/虎嗅/HN），7 个原生（ProductHunt/TechCrunch/阮一峰/少数派/a16z/Sequoia/YC）
- 关键词 14 组，配置在 frequency_words.txt

### 维护职责（EMP_0002 负责）
- RSSHub Docker 容器健康检查
- TrendRadar cron 正常运行
- 配置变更后同步 tools/trendradar-config/ 备份
- RSSHub 路由失效时排查替换

### 教训
- TrendRadar 是 clone 的外部仓库（46MB），不提交到 mason-hub git，只备份配置
- RSSHub 公共实例不稳定且有隐私问题，自建更可靠（~150MB RAM）
- Indie Hackers 无 RSS，网站是 SPA
- Sequoia feed 返回 301 但 follow redirect 后正常

## Radar Tracker 关注率 + 每日去重 (2026-03-09)

### 关注率（relevance rate）实现
- 关注率 = 1 - (dismissed / total_hits)，total_hits 从 TrendRadar 每日 SQLite 数据统计
- `_count_weekly_hits(weeks)` 函数遍历 7 天数据，用 `_load_matcher()` 匹配关键词组，算每组总命中数
- `/api/weekly-report` 现在返回 `hits_by_group` + `relevance_by_group`，不再只看绝对 dismiss 数
- 淘汰建议改为：连续两周关注率低于 `RETIRE_THRESHOLD`（默认 50%）
- 注意：RSS 源（华尔街见闻/McKinsey/CB Insights）的命中数取决于 TrendRadar 关键词是否匹配到它们的标题，如果关键词没覆盖到则 hits=0 但 dismiss>0，关注率直接为 0%

## Radar 点击追踪 Sprint (2026-03-09, Team Sprint)

### 完成内容
- HTML 报告注入 dismiss + read 按钮（inject_dismiss_buttons），统一视图直接渲染，104 个按钮验证通过
- Flask API :8081 systemd 托管，支持 GET/POST dismiss + mark-read + stats + weekly-report
- CORS `Access-Control-Allow-Origin: *` 支持 file:// 和跨端口访问
- 淘汰阈值从 50% 调整为 30%（Mason 指定）

### 教训
- 按 task spec 做 GET 支持很重要 — HTML 按钮用 GET 比 POST 简单（不需要 fetch+JSON），用户体验更好
- systemd 托管 Flask 单文件服务是最轻量的部署方式，比 Docker 省资源
- 淘汰建议需要至少 2 周数据积累才有意义，第一周结果全为空是预期行为

### 每日去重实现
- 新增 `seen_items` 表（news_title UNIQUE, source, first_seen_date）
- 逻辑：首次展示时 INSERT OR IGNORE 记录标题，次日起自动隐藏（first_seen_date < today）
- 同一天内刷新不会隐藏（只过滤往日已读）
- 使用和 dismiss 相同的模糊匹配（`_is_dismissed` 函数复用），处理标题微调
- 热榜主页和趋势分析页（/insights）都集成了去重
- 顶部 badge 分别显示"X 个标记无用 + Y 个往日已读"

### 教训
- 用 closure + mutable list `dedup_hidden = [0]` 在 regex callback 中累计计数，比全局变量干净
- batch insert（`executemany` + `INSERT OR IGNORE`）比逐条插入高效，35 条标题一次写入

## 2026-03-11: 自治系统诊断 + 目录重组

### 发现的坑
- `claude -p` 从 cron 调用时用 `/usr/bin/claude`（旧版 npm），不是 `~/.local/bin/claude`（当前版本） → 所有 dispatcher 派发的 agent 静默失败
- `find-actionable-task.py --batch` 按 lane 去重导致 5/6 任务被挡（EMP_0002+EMP_0004 都在 platform lane）
- audit.jsonl 只在成功时写入 → 失败任务无限重派（SearXNG 被派了 3 次）
- Gateway heartbeat 是真正的 token 大户（3.4M tokens），不是 dispatcher agents
- CLAUDE.md + MEMORY.md 每条消息带 ~6755 tokens 固定税，其中 80% 是无关上下文

### 修复方案
- PATH: `run-agent.sh` 开头 `export PATH="$HOME/.local/bin:$PATH"`
- Lane: 改为 (lane, agent) 去重，同 lane 不同 agent 可并行
- 失败记账: `claude -p` 空输出时写 audit status=failed，≥2 次/天停重试
- 实时触发: agent-task-complete → event_router → dispatch（秒级，不等 cron）
- Token: 语义搜索 vs lessons 互斥 + task_type 条件注入（省 19-41%）
- Prompt 精简: CLAUDE.md 246→57 行，MEMORY.md 127→65 行（省 79%）
- 目录重组: skills/ 68 文件 → 10 子目录，agents/ 每 agent 独立目录

### Gap 类型: 🔧 配置错误（PATH）+ 🏗️ 系统能力缺失（Task 结构化/实时触发）

## Dispatcher 失败降级策略 (2026-03-12)

### 背景
Mason 决策：反复失败的任务不应无限重试占用额度，第二天应优先做别的。

### 实现
- `find-actionable-task.py` 新增 `get_yesterday_failed_max()`，查昨天 audit 中 ≥2 次 failed 的任务
- 排序三元组变为 `(yesterday_failed, priority, source)`，失败任务排最后
- 持续失败写 `data/failed_tasks_for_review.jsonl`，Mason + Meta Manager 手动裁决
- `--list` 输出中标注 `⬇️昨日失败降级`

### Gap 类型: 🏗️ 调度策略缺失（失败任务无降级机制，反复浪费 agent 额度）
