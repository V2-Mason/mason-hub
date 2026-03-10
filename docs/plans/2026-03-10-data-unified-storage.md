# 数据统一存储方案对比

> 日期: 2026-03-10 | 状态: Draft — 待 Mason 评审
> 关联: `data/data_catalog.yaml` — 15 datasets (7 raw / 5 analysis / 3 consumption)

---

## 现状

3 个数据孤岛，15 个数据集，全量 < 50 MB：

| 位置 | 数据 | 存储 |
|------|------|------|
| Aliyun 106.14.44.68 | XHS 采集 (167 notes), 分析 JSON, kbeauty.db | SQLite + JSON |
| GCP mason-hub | TrendRadar, Radar Tracker | SQLite (daily .db) |
| GCP trendradar | 热榜快照, RSS 命中 | SQLite (daily .db) |

**约束**: GCP e2-micro (1 vCPU, 1GB RAM) / SSH 单向 GCP→Aliyun / Aliyun 无 rsync / 月预算 <=200

---

## 方案 A: 文件同步 (File Sync)

### 架构

```
Aliyun                              GCP
┌───────────────────┐  SSH+scp    ┌───────────────────────┐
│ sqlite_tables.db  │ ─────────→ │ data/mirror/           │
│ analysis/*.json   │  (cron)    │   sqlite_tables.db     │
│ kbeauty.db        │            │   analysis/*.json      │
└───────────────────┘            │   kbeauty.db           │
                                 │ trendradar/*.db (本地)  │
                                 │ radar-tracker/ (本地)   │
                                 └───────────────────────┘
                                    All queries run locally
```

### 迁移路径

1. 写 `scripts/data-sync.sh` (~50 行): `sqlite3 .backup` → `scp` 到 GCP mirror/
2. Aliyun crontab 每日采集后触发同步
3. GCP 侧脚本改为读 `data/mirror/` 路径
4. **工时: ~2-3h**

### 复杂度与维护

- 开发: 一个 shell 脚本 + 改几个路径引用
- 维护: cron 日志 + SRE 监控 `.last_sync` 时间戳

### 故障模式

| 故障 | 影响 | 恢复 |
|------|------|------|
| SSH 连接失败 | mirror 过期，GCP 用旧快照 | 自动重试 / SRE 告警 |
| 传输中断 | 文件不完整 | sqlite3 .backup 先做快照再传，原子性保证 |
| Aliyun DB 写入中 | 同步跳过本次 | 检查锁文件，下次重试 |

### 成本

| 项目 | 成本 |
|------|------|
| 额外基础设施 | ¥0 |
| 磁盘 | < 100 MB |
| 开发工时 | 2-3h |

---

## 方案 B: PostgreSQL 中心化

### 架构

```
Aliyun                              GCP
┌───────────────────┐  INSERT     ┌─────────────────────┐
│ MediaCrawler 采集  │ ─────────→ │ PostgreSQL :5432     │
│ (psycopg2 写入)   │ SSH tunnel  │  raw.xhs_notes      │
└───────────────────┘             │  raw.xhs_comments   │
                                  │  trendradar.*       │
                                  │  radar.*            │
                                  └─────────────────────┘
                                    Single source of truth
```

### 迁移路径

1. GCP 安装 PostgreSQL，低内存配置 (shared_buffers=32MB)
2. Schema 按 data_catalog 分层: `raw.*` / `analysis.*` / `report.*`
3. 历史数据一次性导入 (sqlite3 → CSV → COPY)
4. 改写所有采集脚本 (SQLite → PG)，改写所有分析脚本
5. Aliyun 采集通过 SSH tunnel 写入 GCP PG
6. **工时: ~15-20h**

### 复杂度与维护

- 开发: 全链路改造 (采集 + 分析 + 查询)
- 维护: PG backup cron, vacuum, 内存监控, OOM 风险 (e2-micro 仅 1GB)

### 故障模式

| 故障 | 影响 | 恢复 |
|------|------|------|
| GCP PG 挂掉 | 全部数据不可用 | pg_dump 恢复 |
| SSH tunnel 断开 | Aliyun 无法写入，数据丢失 | 本地缓存 + 重连 |
| e2-micro OOM | PG + 现有服务争内存，可能全崩 | 升配到 e2-small (+¥45/月) |

### 成本

| 项目 | 成本 |
|------|------|
| 现有实例 | ¥0 (但 OOM 风险高) |
| 升配 e2-small | ~¥45/月 |
| 开发工时 | 15-20h |

---

## 方案 C: 轻量 API 网关

### 架构

```
Aliyun                              GCP
┌───────────────────┐              ┌───────────────────┐
│ FastAPI :8082     │  HTTP via    │ data_client.py    │
│  /api/xhs/notes   │ ←────────── │  get_xhs_notes()  │
│  /api/xhs/analysis │ SSH tunnel  │  get_products()   │
│  /api/srx/products │             │                   │
│ (reads local DB)  │             │ trendradar/*.db   │
└───────────────────┘             │ radar-tracker/    │
                                  │ (reads local)     │
                                  └───────────────────┘
                                  Data stays where it lives
```

### 迁移路径

1. Aliyun: FastAPI 服务 (~80 行)，暴露 XHS + 产品数据
2. SSH tunnel 增加 8082 端口转发
3. GCP: `data_client.py` 统一封装 (本地 + 远程)
4. 改 optimization-cycle.sh / product_match.py 用 client
5. **工时: ~8-10h**

### 复杂度与维护

- 开发: 两端代码 (API 服务 + client SDK)
- 维护: API 服务 systemd + 隧道端口 + 两套读取方式 (API vs 本地文件)

### 故障模式

| 故障 | 影响 | 恢复 |
|------|------|------|
| SSH tunnel 断开 | 所有 Aliyun 数据不可查 (无离线缓存) | autossh 自动重连 |
| Aliyun API 挂 | XHS 数据不可用，GCP 本地数据正常 | systemd 自动重启 |
| 跨源 JOIN 需求 | API 层无法直接做 | client 端内存合并 (数据量小可接受) |

### 成本

| 项目 | 成本 |
|------|------|
| 额外基础设施 | ¥0 |
| Aliyun 内存 | ~30 MB (FastAPI 常驻) |
| 开发工时 | 8-10h |

---

## 对比总表

| 维度 | A: 文件同步 | B: PostgreSQL | C: API 网关 |
|------|------------|---------------|-------------|
| 开发工时 | 2-3h | 15-20h | 8-10h |
| 数据延迟 | 小时级 | 实时 | 实时 |
| 离线可用 | 有快照 | N/A | 不可用 |
| 统一程度 | 低 (仍是文件) | 高 (真正 SSOT) | 中 (两套接口) |
| GCP 资源消耗 | 零 | 高 (~120MB PG) | 低 |
| 隧道依赖 | 仅同步时 | 写入时 | 每次查询 |
| 扩展性 | 差 | 好 | 中 |
| 月增量成本 | ¥0 | ¥0-45 | ¥0 |

---

## 推荐

**当前阶段** (数据量 < 50MB, 月预算 <=200, e2-micro):

- **方案 A (文件同步) 或 方案 C (API 网关) 最务实** — A 用 2-3h 解决 80% 问题 (去掉 SSH 实时依赖)；C 提供更干净的接口抽象但开发成本高 3 倍且隧道依赖更重。
- **方案 B 是未来增长方案** — 当数据量 > 500MB、出现跨表 JOIN 需求、或需要分钟级实时查询时再考虑。当前规模用 PG 属于过度工程。

**建议演进路径**: A → C → B (按需升级，不过早投入)

- Phase 1 (现在): 方案 A — scp 同步，立即消除 SSH 实时依赖
- Phase 2 (需要实时查询时): 方案 C — API 网关，数据留原地
- Phase 3 (数据量/复杂度爆发时): 方案 B — PG 中心化，真正 SSOT
