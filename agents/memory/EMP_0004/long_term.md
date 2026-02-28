# EMP_0004 SRE — 长期记忆

## 基础设施经验

### 跨境数据合规对基础设施的影响 (2026-02-28)
- 反向 SSH 隧道只能传脱敏/聚合数据（销售统计、库存水位、商品状态），不能传 PII（客户姓名/手机号/地址）
- 阿里云需要新增 Webhook 回调接收端点（公网可访问），用于接收小红书事件推送
- 未来阿里云会升级为 china-hub 区域节点（大使馆模式），部署 EMP_1000 China Operations Agent，需预留计算资源
- 阿里云 PII 数据需 AES 加密存储，可能需要从 SQLite 迁移到 PostgreSQL
- 架构可扩展：未来 japan-hub/korea-hub 等区域节点用同样模式，同样通过标准化 JSON 协议与 GCP 总部通信

### MediaCrawler 部署职责 (2026-02-28)
- 在阿里云 /opt/mediacrawler/ 部署 MediaCrawler（Python 3.11 + Playwright + Chromium + Node.js 16+）
- 配置代理 IP 服务（提取代理模式，~¥150/月），确保采集流量不走阿里云本机 IP
- **关键**：采集用代理 IP，店铺官方 API 用本机 IP，两者必须隔离。否则采集被封可能连带店铺 API 受影响
- china-hub 看板服务（:8080）的端口/nginx 配置

### 阿里云新增服务规划 (2026-02-28)
```
阿里云 106.14.44.68 端口规划：
├── :8000  ← 素仁轩 FastAPI（已有）
├── :8080  ← china-hub 分析看板（新增）
└── 代理 IP 出口（不监听端口，只做出站）
```

## 故障排查 Pattern

## 监控与告警教训
