# EMP_0006 Scout — 长期记忆

## 情报简报格式规范 (2026-02-28, Mason 反馈)

### 必须有具体日期
- 每条情报标注发现日期或发布日期，禁止只写"本周""最近"
- 好：`(2026-02-26)` 坏：`(本周新建)`

### 链接必须紧贴信息
- 每条标题直接是可点击链接，Mason 能第一时间打开
- 好：`🔴 [Agent SDK v0.1.44](https://github.com/...) (2026-02-26) — 新增文件检查点回退`
- 坏：先写分析段落，链接在文末或单独一节

### 去重：区分新发现和已知更新
- 维护 `intel/seen.jsonl`（repo name + 首次报告日期 + 上次 star 数）
- 新项目标 🆕，已知项目仅在 star 变化显著时标 📈 +N，无变化不报
- digest 分两部分：**新发现** 和 **已知项目动态**
- （去重机制待 EMP_0002 实现后生效）

## 数据源真实性 (2026-02-28)

### 脚本名称必须匹配实际数据源
- `scout-xhs-trends.sh` 实际搜的是 GitHub，搜不到小红书内容 — 这会给 Mason 造成情报来源的错觉
- 如果脚本做不到名称暗示的能力，应在输出开头注明实际数据源
- 未来方向：不同渠道用不同 API/模型（GitHub→Claude，Google→Gemini，X→Grok，小红书→DeepSeek）

## 2026-03-11: config.md Engine 架构更新
- 在 config.md 的"搜集规范"前新增 "Scout v2 Engine 架构" 章节
- 涵盖：6 引擎职责表、入口命令、多模型策略、搜索源、与旧脚本关系、数据流目录
- 更新了 weekly-deep-patrol cron 任务描述，从手动脚本改为 pipeline 调用
- 更新了数据存储目录，加入 engines/scout.db/validated/reports/
- Gap 分类：📄 文档更新 → 已更新 agents/EMP_0006/config.md

## 2026-03-11: 每日快扫
- 三脚本并行执行（anthropic/trending/github），总耗时约 2 分钟
- 发现 superset ⭐2046→6626 爆发增长，多 agent IDE 赛道验证
- claude-mem ⭐34k 说明社区对 agent 记忆需求极高
- ask-search (SearxNG) 可能是 Scout v2 搜索引擎层候选方案
- plugins-plus-skills 1367 个 skills 合集值得深入挖掘
- Gap 分类：📚 纯知识 → 留存

## 巡逻经验

### 当前所有脚本只用 GitHub REST API（无认证）
- 9 个脚本无一例外
- GitHub API 无认证限流 60 次/小时，高频巡逻会触发限流

### 第三方数据平台现状 (2026-02-28)
- 蝉妈妈/新红/千瓜均无正式开放 API，只有网页端查询 + CSV 导出
- 蝉妈妈主攻抖音直播电商，小红书数据不是强项
- 新红（新榜旗下）性价比最高、小红书专属，但也没有 API
- 爆品情报暂时只能靠 Scout 轻量监测 + 小红书广告后台数据

### XHS 采集与 Scout 的边界 (2026-02-28, Mason 确认)
- XHS 公开笔记采集由 MediaCrawler（阿里云基础设施）独立完成，**不是 Scout 的执行任务**
- Scout 在 GCP 上跑 GitHub/技术/电商情报，MediaCrawler 在阿里云上跑 XHS 内容采集 — 两套独立系统
- 但 china-hub 看板上的品类趋势数据，Scout 可以引用纳入情报简报（作为数据源之一）
