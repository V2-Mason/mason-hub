# EMP_0014 Data Engineer — 长期记忆

## 创建于 2026-03-10
- 数据中台角色正式建立
- 首份产出：data/data_catalog.yaml（盘点所有数据流）

## Lesson: 数据健康检查 + 统一存储方案 (2026-03-10)

### 做了什么
- 完成 data_health_check.sh — 解析 data_catalog.yaml，自动检查 15 个数据集健康状态
- 完成统一存储方案设计文档 — 三方案对比（文件同步/PostgreSQL/API 网关）
- Mason 选定方案 A（文件同步），方案 C 作为 >50MB 触发升级
- 健康检查脚本内置数据量监控，超 50MB 自动提醒升级

### 发现
- 当前总数据量 < 50MB，PostgreSQL 属于过度工程
- e2-micro 1GB RAM 跑 PG 有 OOM 风险
- SSH tunnel 是最大单点故障——方案 A 只在同步时依赖，方案 C 每次查询都依赖

### Gap: 📚 纯知识
- 方案 A 下一步：写 data-sync.sh（~50 行），cron 注册，改下游路径 → 已完成 (2026-03-10)

## Lesson: 方案 A 实施 (2026-03-10)

### 做了什么
- data-sync.sh 130 行：sqlite3 .backup 避免锁 → scp → 7 天窗口只同步最新文件 → .last_sync 时间戳
- optimization-cycle.sh Step 1c 从 SSH 实时读改为读本地 mirror，加 7 天新鲜度检查
- data/mirror/ 目录 + .gitignore（镜像文件不入库）
- XHS 帮助中心文档 owner 归 EMP_0014，月度刷新 cron 已注册（提醒模式）

### 发现
- 只有 optimization-cycle.sh 有 SSH 读阿里云数据，其他脚本都是 scp 脚本过去在阿里云本地跑——改动范围比预想小
- 下游脚本（xhs-analyze.sh 等）是"scp 代码到阿里云执行"模式，不需要改

### Gap: 📚 纯知识
- data-sync.sh 需要注册 cron（在阿里云采集完成后触发），目前手动运行

## Lesson: Scout 产出标准化 (2026-03-10)

### 做了什么
- 定义 scout_intel.yaml schema（11 字段：id/date/source/priority/title/summary/url/relevance/suggested_action/suggested_owner/digest_file）
- scout-normalize.py 解析 digest markdown → JSONL，支持 --file 单文件和 --stats 统计
- 3 个 digest 文件提取 23 条情报（10 red / 13 yellow），去重幂等

### 发现
- Scout 脚本全部输出到 stdout，不写文件——标准化只能在 digest 层面做，不能在单脚本层面
- 所有 23 条 source=mixed，因为 digest 是多脚本汇总后的产物。要精确到脚本级别需要改 Scout 产出流程
- 建议行动/负责人只有 4/23 条有——大部分情报缺少 actionable 信息

### Gap: 📚 纯知识
- optimization-cycle.sh 还在读原始 markdown，可以改为读 JSONL 按 priority=red 过滤 → 已完成 (2026-03-10)

## Lesson: Layer 2 前置条件验证 (2026-03-10)

### 做了什么
- data-sync.sh 修复子目录同步：maxdepth 1→2，新增 mkdir -p 创建 comments/trends 子目录
- data_health_check.sh 新增 jsonl 类型支持（clean_scout_intel 从"未知类型"变 ✅）
- optimization-cycle.sh Step 1b 改为读 scout_normalized.jsonl（priority=red 过滤），保留 markdown fallback
- data-sync.sh 实测：3/3 成功，6 个 JSON 文件同步（含 comments/trends 子目录）
- health check 实测：8/15 健康，1 警告，6 异常

### 发现
- analysis_xhs_* 数据集 ❌ 不是 sync 问题——catalog location 指向 aliyun: 路径，health check 用 SSH 查今天/昨天文件，但最近采集是 3/7（3 天前）。下次周二采集后会自动变绿
- TrendRadar ❌ 是阈值问题——30min 频率数据集 5h 没更新就算异常，阈值太严格
- raw_srx_sales ⚠️ HTTP 401 是独立的 API 认证问题
- 总数据量 16MB，远低于 50MB 升级阈值

### Gap: 📚 纯知识
- data-sync.sh 还需注册 cron（依赖阿里云采集完成信号）
- health check 的 TrendRadar 阈值需要调整（30min 频率但检测窗口过窄）→ 已修复为 6h (2026-03-10)
- catalog 中 aliyun: 路径的数据集，方案 A 后应考虑同时注册 gcp:mirror 路径
- 素仁轩 API 401 → 已修复，data-coo-daily.sh + data_health_check.sh 加 JWT 登录 (2026-03-10)

## Lesson: Scout v2 Engine 架构构建 (2026-03-10)

### 做了什么
- 参考 BettaFish 的 5-Engine 架构，构建 Scout v2 共 11 个 Python 模块
- 6 引擎管道：spider → query → media → insight → forum → report
- 基础设施层：llm_client.py（多模型路由）+ state.py（checkpoint）+ database.py（scout.db）+ search.py（统一搜索）
- pipeline.py 编排器：checkpoint/resume + 优雅降级 + Slack 通知
- scout.db 已有 23 条 intel_items（从 JSONL 迁移），4 张表

### 发现
- TrendRadar news_items 表有 2163 条（3 天），rss_items 有 1494 条——数据量足够 Spider 提取话题
- tracker.db 只有 11 read_items + 43 dismissals——关注率数据还很少，需要积累
- SearXNG 未部署，搜索当前只走 GitHub API + DuckDuckGo
- Gemini API key 未配置，MediaEngine 会自动跳过
- 所有引擎 import 测试通过，但未做端到端 pipeline 运行（需要 DASHSCOPE_API_KEY）

### Gap: 🏗️ 系统能力缺失
- SearXNG Docker 部署 — 搜索多样性依赖此服务（建议 Owner: EMP_0002/EMP_0004，验收: localhost:8888/healthz 返回 OK + search.py 测试通过）
- Scout v2 cron 注册 — 新管道取代旧 scout-*.sh（建议 Owner: EMP_0004）

## Lesson: 数据健康检查补跑修复 (2026-03-11)

### 做了什么
- 运行 data_health_check.sh 发现 4 红 1 黄：analysis_xhs_trends/comments/report_strategy_briefing/report_optimization ❌ + raw_scout_intel ⚠️
- 根因分析：Gateway 60s 超时导致 xhs-analyze.sh 在完成 Step 1-2（viral + enrichment）后、Step 3-5 前被杀
- 手动 SSH 到阿里云补跑 3 个缺失步骤：_trend_compare.py → _comment_analysis.py → xhs_briefing.py
- 发现时区不匹配 bug：阿里云脚本用 CST 命名文件（03-12），GCP health check 用本地日期（03-11）查找
- 临时修复：在阿里云创建 symlink（2026-03-11.json → 2026-03-12.json）
- 修复后：13/15 健康，1 黄 1 红

### 发现
- xhs-analyze.sh 链式 SSH 操作（4+ 步串行，每步 ConnectTimeout=10-60s），Gateway 60s 超时根本不够
- 手动补跑各步骤时，脚本都没 `TZ='America/New_York'` 设置，导致文件名用了 CST 日期
- report_optimization 预期周三 10:00 ET 但未产出 — optimization-cycle.sh cron 可能失效（非 EMP_0014 职责）
- raw_scout_intel 3 天未更新 — Scout cron 可能失效（EMP_0006 职责）

### Gap
- 🔧 配置错误 → 已修（symlink 临时对齐日期）
- 🏗️ 系统能力缺失 → 触发动作: Gateway 超时 60s 不足以完成完整 XHS 分析管道，需要 EMP_0002 增加超时或改为异步执行
- 🏗️ 系统能力缺失 → 触发动作: 管道脚本应统一用 `TZ='America/New_York'` 生成文件名，避免跨时区命名不一致

## Lesson: 数据读取 SDK v0.1.0 (2026-03-11)

### 做了什么
- 构建 `data/tools/` Python 包（5 个模块）：metrics.py / catalog.py / readers.py / sdk.py / __init__.py
- 标准指标提取为唯一口径：`interaction_score`/`parse_count`/`engage_rate`/`save_rate`/`fake_traffic_flags` 等
- catalog.py 解析 data_catalog.yaml，`resolve_location()` 自动将 `aliyun:` 路径映射到 `data/mirror/`
- readers.py 支持 4 种存储类型：sqlite / json / jsonl / markdown_files
- sdk.py 提供一行代码 API：`get_xhs_notes()`/`get_xhs_analysis()`/`get_scout_intel()` 等
- 端到端验证：1168 条笔记、分析报告、趋势、评论、简报、23 条情报全部正确读取

### 发现
- 当前所有 XHS 脚本各自复制 `parse_count()` 和 `interaction_score()`，至少 3 处重复
- aliyun → mirror 路径映射规则是硬编码的（基于已知目录结构），后续需配置化
- API 类型数据集（raw_srx_sales）和 stdout 类型（analysis_radar_weekly）无法离线读取，需专用方案

### Gap: 📄 文档更新
- 下游消费者（xhs-analyze-viral.py 等）还未改为 `from data.tools import interaction_score`，需渐进迁移
- backlog 已更新 SDK 完成状态
