# Radar -- 产品定义

> 产出者：EMP_0012 (Product Architect)
> 创建日期：2026-03-08

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

## 接口

- **输入**：
  - 热榜平台公开 API / 页面（TrendRadar 爬虫）
  - RSS feed URL（原生 + RSSHub 转换）
  - Mason 手动输入的关键词（`config/frequency_words.txt`）
  - Mason 的"无用"标记点击（V1 新增）
- **输出**：
  - HTML 报告（本地文件，/standup 晨会引用）
  - SQLite 数据库（历史查询）
  - Scout 情报简报（Slack / 终端）
- **依赖**：
  - RSSHub Docker 服务（TrendRadar 的 3 个 feed 依赖它）
  - GCP 服务器（cron + 存储）
  - DeepSeek API（AI 分析功能，当前关闭）

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

## 反馈回路设计

话题淘汰机制（Mason 批准方案 1）的数据流：

```
1. HTML 报告每条话题旁加"无用"按钮
2. 点击 → 写入 SQLite feedback 表（话题 ID + 时间戳 + "useless"）
3. 每周日统计：每个关键词组的关注率 = 1 - (无用标记数 / 总展示数)
4. 连续两周关注率低于阈值 → 生成淘汰建议列表
5. /standup 晨会展示淘汰建议 → Mason 确认
6. Mason 确认后 → 从 frequency_words.txt 移除或降级
```

**关键约束**：步骤 5→6 必须有 Mason 人工确认，系统只建议不执行。

## 迭代路径

- [x] 实验阶段：TrendRadar + RSSHub 部署完成，cron 运行稳定，HTML 报告可用（2026-03-08 已达成）
- [ ] V1 反馈回路：HTML 加"无用"按钮 + SQLite feedback 表 + 周统计脚本 + 淘汰建议展示
- [ ] 稳定信号：连续 4 周 Mason 使用晨会报告且反馈回路正常运转
- [ ] 交接：无需交接，EMP_0002 长期维护，EMP_0006 长期使用

## Mason 批准

- 日期：2026-03-08
- 决定：做
- 备注：会议决议。统一命名为 Radar，星型拓扑 + 反馈回路方案 1（无用按钮 → 建议淘汰 → Mason 确认）
