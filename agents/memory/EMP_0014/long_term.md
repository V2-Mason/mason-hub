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
- health check 的 TrendRadar 阈值需要调整（30min 频率但检测窗口过窄）
- catalog 中 aliyun: 路径的数据集，方案 A 后应考虑同时注册 gcp:mirror 路径
