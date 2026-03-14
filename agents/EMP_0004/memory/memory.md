# EMP_0004 sre — 记忆库

> 写入规则：每条带日期 + Gap分类标签。主题下追加，不另开文件。
> 浓缩触发：条目超过 150 条时，运行 compact-memory.sh 压缩归档。

---


## 基础设施经验

### 跨境数据合规对基础设施的影响 (2026-02-28)
- 反向 SSH 隧道只能传脱敏/聚合数据（销售统计、库存水位、商品状态），不能传 PII（客户姓名/手机号/地址）
- 阿里云需要新增 Webhook 回调接收端点（公网可访问），用于接收小红书事件推送
- 未来阿里云会升级为 china-hub 区域节点（大使馆模式），部署 EMP_1000 China Operations Agent，需预留计算资源
- 阿里云 PII 数据需 AES 加密存储，可能需要从 SQLite 迁移到 PostgreSQL
- 架构可扩展：未来 japan-hub/korea-hub 等区域节点用同样模式，同样通过标准化 JSON 协议与 GCP 总部通信

### MediaCrawler 部署职责 (2026-02-28)
- **架构定位**：基础设施层数据管道（跟 SQLite、SSH 隧道同级），不归任何业务 Agent 所有，我负责部署维护
- 在阿里云 /opt/mediacrawler/ 部署 MediaCrawler（Python 3.11 + Playwright + Chromium + Node.js 16+）
- 代理 IP 已配置（快代理隧道代理 TPS，~¥20/月），采集流量走代理出口，不走阿里云本机 IP
- **关键**：采集用代理 IP，店铺官方 API 用本机 IP，两者必须隔离。否则采集被封可能连带店铺 API 受影响
- **已验证**：代理出口 IP 182.34.xx.xx，阿里云真实 IP 106.14.44.68 已隐藏
- china-hub 看板服务（:8080）的端口/nginx 配置
- 数据流：MediaCrawler 定时采集 → SQLite 存库 → 各业务 Agent 被动查询（不是实时工具调用）

### 阿里云新增服务规划 (2026-02-28)
```
阿里云 106.14.44.68 端口规划：
├── :8000  ← 素仁轩 FastAPI（已有）
├── :8080  ← china-hub 分析看板（新增）
└── 代理 IP 出口（不监听端口，只做出站）
```

## 故障排查 Pattern

### MediaCrawler .env 不生效 (2026-03-01)
- MediaCrawler 依赖 python-dotenv 但代码中从未调用 `load_dotenv()`
- .env 文件存在但 `os.getenv()` 读不到值，环境变量为空
- 修复：在 `config/db_config.py` 头部加 `from dotenv import load_dotenv; load_dotenv()`
- 教训：部署第三方项目时，不要假设 .env 会被自动加载，先验证

### 快代理隧道代理 vs 提取代理 (2026-03-01)
- MediaCrawler 内置的 kuaidaili provider 是 DPS（提取代理）模式：调 API 获取 IP 列表
- Mason 买的是 TPS（隧道代理）模式：固定 host:port + 用户名密码，服务端自动轮换 IP
- 两者 API 完全不同，不能混用
- 修复：新建 `proxy/providers/kuaidl_tunnel_proxy.py` 适配器，注册为 `kuaidaili_tunnel` provider
- 教训：买代理前确认产品类型（DPS/TPS），或买了之后确认代码支持哪种

### MediaCrawler 源码已 Patch (2026-03-02)
- 阿里云 `/opt/mediacrawler/` 有 3 处代码修改（未提交 git，直接改的线上文件）：
  - `media_platform/xhs/login.py`：login_by_cookies 加载全部 cookie（原来只加载 web_session）
  - `media_platform/xhs/core.py`：get_note_detail_async_task 失败时跳过而非崩溃
  - `media_platform/xhs/client.py`：request 方法处理缺少 `success` 字段的响应
- **注意**：这些是直接改的线上文件，如果 MediaCrawler 升级会被覆盖

### XHS Feed API 风控阈值 (2026-03-02)
- `/api/sns/web/v1/feed`（笔记详情）：连续调用 ~50-60 次后触发 461 `账号异常`（code 300011）
- 搜索 API 和 selfinfo 不受影响
- 风控解除时间：数小时到一天
- **监控要点**：如果 cron 采集报 0 新笔记但无 SSH 错误，大概率是 feed API 被风控
- 当前数据库 167 条笔记

### 多账号采集架构 (2026-03-02)
- Cookie 不再存 base_config.py，改存 /opt/mediacrawler/accounts.json
- 模板：~/mason-hub/shared/accounts.template.json（SCP 初始化）
- 采集脚本 _two_tier_crawl.py 每次从 GCP SCP 到阿里云再执行
- Cookie 过期检测改为按账号检测（xhs-cookie-check.sh --account A）
- **监控要点**：Slack 通知会指明哪个账号过期，不再是笼统的"cookie 过期"

### 阿里云隧道 keepalive IP 错误 (2026-03-11)
- **问题**：阿里云侧 `/opt/surenxuan/scripts/tunnel-keepalive.sh` 硬编码了旧 GCP IP `34.68.172.191`（正确是 `34.63.188.198`），导致每 5 分钟误判"隧道断了"并 restart reverse-tunnel，600+ 次无故重启
- **症状**：GCP 侧 keepalive 日志显示每 ~50 分钟断连一次，但实际上 SSH 直连和反向隧道都通
- **修复**：`sed -i 's/34.68.172.191/34.63.188.198/g'` 一行命令
- **教训**：部署保活脚本时，IP 不要硬编码，应该用 SSH config 别名或环境变量
- **gap 类型**：🔧 配置错误 → 已修复

### repair-dispatch.sh 日志双写 (2026-03-12)
- **问题**：`log()` 用 `tee -a $LOG_FILE` 同时写 stdout 和文件，cron/dispatcher 用 `>> repair.log` 重定向 stdout，导致每行写入两次
- **修复**：`tee -a` 改为 `>> $LOG_FILE` 直接追加 + `>&2` 输出到 stderr。同步修复 3 处 `submit-repair.py` 调用的 `| tee -a`
- **教训**：shell 脚本如果会被 cron 用 stdout 重定向调用，log 函数不能用 tee（stdout+file），应该直接写文件+stderr
- **gap 类型**：🔧 配置错误 → 已修复

### X/Twitter API 配置 (2026-03-11)
- Mason 提供 Consumer Key + Consumer Secret + Bearer Token，已配到 ~/mason-hub/.env
- 变量名：X_CONSUMER_KEY / X_CONSUMER_SECRET / X_BEARER_TOKEN
- 用途：Scout v2 搜索 Twitter/X 数据源
- Reddit/LinkedIn API — Mason 确认暂不接入
- **gap 类型**：📚 纯知识 → 留存

## 监控与告警教训

### Scout Cron 首次执行验证 (2026-03-11)
- 每日快扫 cron（23:00 UTC）首次触发成功，EMP_0006 完整执行 3 个 skill（anthropic/trending/github）
- 产物路径：每日快扫 → `intel/raw/`，周度深度巡逻 → `intel/digests/`。最初任务描述说"确认 digests/ 有新文件"，实际每日快扫不产 digest
- 三档 Scout cron 调度：每日 23:00 UTC（快扫）/ 一三五 23:30 UTC（中频）/ 周一 00:00 UTC（深度）
- triggers.log 作为 cron 执行审计日志运转正常，包含完整 agent 输出
- **gap 类型**：📚 纯知识 → 留存（scout 三档产物路径差异）

### 日报巡检 audit.jsonl 路径 (2026-03-12)
- audit.jsonl 实际路径是 `logs/audit.jsonl`，不在 `data/audit.jsonl`
- 24h 内 18 次任务全部 completed，无 repair_failed
- EMP_0014 单次任务成本 $1.80（42 turns, 1.6M input tokens），需持续监控是否常态
- slack-bot `/resume` 命令未注册 handler，多次 404 — P2，功能缺失非故障
- **gap 类型**：📚 纯知识 → 留存
