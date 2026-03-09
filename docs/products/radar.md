# Radar — 产品定义

> 产出者：EMP_0012 (Product Architect)
> 创建日期：2026-03-08
> 更新日期：2026-03-09（补充模块接口定义、反馈回路详设、迭代路径细化）

## 一句话描述

Mason 的个人趋势情报系统：三条数据管道汇聚热榜、RSS、深度分析，星型拓扑以 Mason 为唯一决策中心，通过点击反馈逐步优化信噪比。

## 归属

- 所属项目：mason-hub 子模块（`~/mason-hub/tools/trendradar/` + Scout 脚本）
- 临时负责人：EMP_0002 (Platform Dev) -- 部署和维护
- 目标负责人：EMP_0002 长期持有，EMP_0006 (Scout) 是使用者不是维护者
- 迁移条件：无需迁移，已在目标位置

## 架构

```
                    ┌─────────────────┐
                    │     Mason       │
                    │  （唯一用户）     │
                    └────────┬────────┘
                             │
                    阅读 HTML 报告
                    标记"无用"话题 ──→ 反馈回路
                             │              │
                ┌────────────┼────────────┐  │
                │            │            │  │
        ┌───────▼──┐  ┌─────▼────┐  ┌────▼──▼──┐
        │TrendRadar│  │  Scout   │  │  RSSHub  │
        │ 广度采集  │  │ 深度分析  │  │ RSS转换  │
        └──────────┘  └──────────┘  └──────────┘
             │                           │
             └───────── RSS 依赖 ─────────┘
                 (36kr/虎嗅/HN 通过
                  RSSHub 转换后输入
                  TrendRadar)
```

**星型拓扑说明**：三条管道独立运行，不互相调用。Mason 是唯一的信息汇聚点和决策点。反馈回路是从纯星型走向有反馈的星型的第一步——Mason 的"无用"标记写入 SQLite，影响后续关键词权重。

## 边界

- **MVP（当前状态）**：TrendRadar cron */30 采集 → HTML 报告 → /standup 晨会汇报，Scout 按需手动触发
- **V1**：HTML 报告加"无用"按钮 → SQLite 记录 → 每周统计关注率 → 低关注话题建议淘汰 → Mason 确认
- **不做**：
  - 不做自动淘汰（必须 Mason 确认）
  - 不做 AI 推荐新关键词（Mason 手动添加）
  - 不做实时调权（批量周频率即可）
  - 不做多用户支持
  - 高盛/Mary Meeker 报告不自动化（手动查阅）

## 模块

### 管道 1：TrendRadar（广度采集）

- **职责**：定时抓取热榜 + RSS，关键词匹配，生成 HTML 报告
- **数据源**：11 热榜平台（百度/微博/抖音/知乎/B站/头条/华尔街见闻/澎湃/财联社/凤凰/贴吧）+ 17 RSS 源
- **运行方式**：cron */30，外部调度，内置调度已关闭
- **存储**：本地 SQLite（`trendradar.db`）+ HTML 报告（`output/`）
- **代码位置**：`~/mason-hub/tools/trendradar/`

### 管道 2：Scout（深度分析）

- **职责**：针对特定话题做深度搜索和分析，产出结构化情报
- **触发方式**：Mason 手动或 /scout 命令
- **执行者**：EMP_0006 (Scout Agent)
- **产出**：情报简报，发送到 Slack 或直接汇报

### 管道 3：RSSHub（RSS 转换服务）

- **职责**：将无原生 RSS 的网站转换为 RSS feed，供 TrendRadar 消费
- **当前路由**：36氪（`/36kr/information/web_news`）、虎嗅（`/huxiu/article`）、Hacker News（`/hackernews/best`）
- **运行方式**：Docker `localhost:1200`，常驻服务
- **代码位置**：Docker 镜像，无需自维护

## 模块间接口定义

### RSSHub → TrendRadar

```
协议: HTTP GET (RSS 2.0 / Atom XML)
端点: localhost:1200/<route>
当前路由:
  - /36kr/information/web_news
  - /huxiu/article
  - /hackernews/best
数据格式: 标准 RSS XML（title, link, pubDate, description）
调用方: TrendRadar cron 任务，每 30 分钟拉取
故障处理: RSSHub 不可用时 TrendRadar 跳过这 3 个源，其余 14 个原生 RSS + 11 热榜正常运行
```

### TrendRadar → Radar Tracker

```
协议: 文件系统（共享磁盘路径）
路径: tools/trendradar/output/html/latest/current.html
数据格式: HTML（含 .news-item / .rss-item class 标记的条目块）
写入方: TrendRadar cron
读取方: Radar Tracker (Flask) 加载 → 注入按钮 → 返回给 Mason
历史报告: tools/trendradar/output/html/YYYY-MM-DD/<timestamp>.html
```

### TrendRadar → Radar Tracker（数据库）

```
协议: 文件系统（只读 SQLite）
路径: tools/trendradar/output/news/YYYY-MM-DD.db + output/rss/YYYY-MM-DD.db
用途: weekly_report.py 读取每日新闻/RSS 命中数，计算关注率分母
Tracker 自身不写入 TrendRadar 的 DB
```

### Mason → Radar Tracker（反馈输入）

```
协议: HTTP POST (AJAX)
端点:
  - POST /api/dismiss   {title, keyword_group, source}  → 标记"无用"
  - POST /api/mark-read  {title, source}                → 标记"已读"
存储: tools/radar-tracker/tracker.db (SQLite)
表结构:
  - dismissals(id, news_title, keyword_group, source, dismissed_at)
  - read_items(id, news_title, source, read_at)
  - seen_items(id, news_title, source, first_seen_date)  ← 去重用
```

### Radar Tracker → Mason（报告输出）

```
协议: HTTP GET
端点:
  - GET /                        → 最新报告（注入按钮后的 HTML）
  - GET /history/<date>/<time>   → 历史报告
  - GET /api/stats               → 聚合统计 JSON
  - GET /api/weekly-report?weeks=N → 关注率周报 + 淘汰建议
  - GET /insights                → 7 天趋势分析
运行: Flask :8081, systemd 常驻
```

### Scout → Mason（情报输出）

```
协议: Slack 消息 + 终端 stdout
触发: 手动 /scout 或 run-agent.sh
数据源: 当前 9 个脚本全部基于 GitHub API search
去重: scripts/scout-dedup.py → intel/seen.jsonl
产出格式: Markdown（🆕 新 repo / 📈 更新 repo，含 stars/语言/描述）
```

### 模块间无直接通信

Scout ↔ TrendRadar 之间**没有数据流**。它们是独立管道，Mason 是唯一汇聚点。这是星型拓扑的核心约束——避免管道间耦合。

## 系统级接口（外部输入/输出汇总）

- **外部输入**：热榜平台页面（11个）、RSS feed URL（17个）、GitHub API
- **Mason 输入**：关键词配置（`frequency_words.txt`）、反馈点击（dismiss/read）
- **Mason 输出**：HTML 报告（Tracker :8081）、晨会摘要（/standup）、Scout 情报（Slack）
- **基础设施依赖**：GCP 服务器、RSSHub Docker、systemd、cron

## 关键词体系

15 组关键词，分四层：

| 层级 | 定位 | 关键词组 |
|------|------|---------|
| A 现有业务 | 直接相关 | 韩妆/护肤、跨境电商、小红书 |
| B 技术能力 | 可执行 | AI视频、Vibe Coding、AI Agent |
| C 赛道扫描 | 机会发现 | 出海、AI工具/SaaS、内容电商、抖音/TikTok、个人IP、新消费 |
| C+ 硬科技 | 基础设施 | 基础设施/硬科技（内存/HBM/算力/储能） |
| D 通用信号 | 弱信号捕捉 | 独立开发、趋势观察 |

每组含正向匹配词 + 排除词（`!` 前缀），减少噪音。

## 反馈回路设计（星型拓扑反馈详设）

### 核心原则

Mason 是星型拓扑的中心节点。所有反馈数据从 Mason 行为中被动采集，系统只产出建议，**Mason 确认后才执行任何权重变更**。

### 数据采集层

Mason 在 Radar Tracker 上的每次交互产生以下行为数据：

| 行为 | 采集方式 | 存储位置 | 含义 |
|------|---------|---------|------|
| 点击 × (dismiss) | POST /api/dismiss | tracker.db → dismissals | "这条对我没用" |
| 点击 ✓ (mark-read) | POST /api/mark-read | tracker.db → read_items | "我看了" |
| 未交互（既不 × 也不 ✓） | 隐式（seen_items 中有记录但无 dismiss/read） | 推断 | 跳过 = 弱无用信号 |

### 关注率计算

```
每周日 weekly_report.py 执行:

对每个关键词组 K:
  total_hits(K) = 本周 TrendRadar 匹配到 K 的新闻/RSS 条数
                  (来源: output/news/*.db + output/rss/*.db，按 frequency_words.txt 匹配)
  dismissed(K)  = 本周 tracker.db 中 keyword_group=K 的 dismiss 记录数
  attention_rate(K) = 1 - (dismissed(K) / total_hits(K))

淘汰条件: attention_rate(K) < 50% 连续 2 周
```

### 反馈→行动 数据流

```
┌──────────────────────────────────────────────────────┐
│                    采集阶段（自动）                     │
│                                                      │
│  Mason 阅读报告 ──→ 点击 × ──→ tracker.db.dismissals │
│                 ──→ 点击 ✓ ──→ tracker.db.read_items  │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│                    统计阶段（周频）                     │
│                                                      │
│  weekly_report.py:                                   │
│    读 TrendRadar DB → 每组命中总数                     │
│    读 tracker.db    → 每组 dismiss 数                  │
│    计算 attention_rate per 关键词组                    │
│    对比前一周 → 标记连续 2 周 < 50% 的组               │
│    产出: 淘汰建议列表 + 每组趋势                       │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│                    展示阶段（/standup 或 GET /api）    │
│                                                      │
│  "建议淘汰: 新消费 (本周 38%, 上周 42%)"               │
│  "建议降级: 独立开发 D→观察 (本周 48%, 上周 51%)"       │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│                    决策阶段（Mason 人工）               │
│                                                      │
│  Mason 选择: 淘汰 / 降级 / 保留 / 调整排除词           │
│  执行: EMP_0002 修改 frequency_words.txt              │
│  不做: 系统自动执行任何权重变更                         │
└──────────────────────────────────────────────────────┘
```

### 未来可选扩展（当前不做，记录备查）

- **阅读时长推断**：通过 mark-read 时间戳 - seen 时间戳估算停留，信号太弱，暂不采集
- **关键词组内细分**：当前粒度是关键词组级别，不追踪单个关键词的关注率
- **AI 推荐新关键词**：基于高关注率话题的语义扩展，Mason 明确说不做
- **跨管道关联**：Scout 发现的 topic 自动加入 TrendRadar 关键词，破坏星型拓扑独立性，不做

## 迭代路径

### Phase 0：实验部署 ✅（2026-03-08 已达成）

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| TrendRadar cron */30 运行 | ✅ | 11 热榜 + 17 RSS，每 30 分钟生成 HTML |
| RSSHub Docker 常驻 | ✅ | localhost:1200，3 个转换路由 |
| /standup 晨会集成 | ✅ | 热门话题摘要出现在晨会报告 |
| 关键词 15 组配置 | ✅ | A/B/C/C+/D 四层体系 |

### Phase 1：反馈回路 V1（当前阶段）

| 里程碑 | 状态 | 负责人 | 说明 |
|--------|------|--------|------|
| Radar Tracker Flask 服务 | ✅ | EMP_0002 | :8081 systemd 常驻，HTML 注入 ×/✓ 按钮 |
| dismiss/read API | ✅ | EMP_0002 | POST 端点 + tracker.db 存储 |
| 去重逻辑（跨日 + 相似标题） | ✅ | EMP_0002 | seen_items 表 + 子串匹配 ≥8 字符 |
| weekly_report.py | ✅ | EMP_0002 | 关注率统计 + 淘汰建议，代码完成 |
| weekly_report cron 注册 | ⬜ | EMP_0002 | 需加入每周日定时执行 |
| /standup 展示淘汰建议 | ⬜ | EMP_0002 | 晨会报告中引用 weekly_report 输出 |
| Mason 首次走完淘汰流程 | ⬜ | Mason | 第一个关键词组被淘汰或降级 = V1 闭环 |

**Phase 1 完成标准**：Mason 基于关注率数据做出至少 1 次关键词调整决策（淘汰/降级/调整排除词）。

### Phase 2：信噪比优化（Phase 1 闭环后启动）

| 里程碑 | 说明 |
|--------|------|
| 累积 4 周关注率数据 | 足够判断淘汰建议的准确性 |
| 排除词精调 | 根据 dismiss 数据中的高频噪音话题，反推需要添加的排除词 |
| Scout 数据源多元化 | 当前 9 个脚本全部是 GitHub API，需扩展到 Google/X/XHS 等 |
| AI 分析激活 | 接入 DeepSeek API，对 TrendRadar 命中条目做摘要和趋势判断 |

**Phase 2 完成标准**：连续 4 周 Mason 使用 Radar 报告且不需要手动过滤大量噪音。

### 长期（不排期，条件触发）

| 方向 | 触发条件 | 说明 |
|------|---------|------|
| 关键词组自动建议 | Mason 主动要求 | 当前明确不做，等 Mason 改主意 |
| 多维度反馈 | dismiss 数据不够用时 | 加"有用"正向标记、优先级标记 |
| 看板 UI | Mason 对 HTML 报告不满意时 | 当前 Flask 注入方案够用 |

### 交接

无需交接。EMP_0002 长期维护代码和部署，EMP_0006 长期作为 Scout 管道的使用者。

## Mason 批准

- 日期：2026-03-08
- 决定：做
- 备注：会议决议。统一命名为 Radar，星型拓扑 + 反馈回路方案 1（无用按钮 → 建议淘汰 → Mason 确认）
