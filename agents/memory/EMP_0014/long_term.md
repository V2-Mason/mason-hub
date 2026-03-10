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
