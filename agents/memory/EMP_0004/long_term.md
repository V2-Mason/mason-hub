# EMP_0004 SRE — 长期记忆

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
- 当前数据库 148 条笔记（韩国护肤 35 + 竞品 60 + Task 1 新增 57 — 但 Task 1 其实应该更多，部分被风控截断）

## 监控与告警教训
