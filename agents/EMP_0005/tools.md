# EMP_0005 ecommerce-dev — 工具与资源

## Skills

→ check-syntax
→ run-backend-tests
→ dev-verify-loop

## 按需参考

| 文件 | 何时读 |
|------|--------|
| `kernel/standards/protocols/dev-execution.md` | 需要任务执行流程细节时 |
| `intel/processed/小红书开放平台-完整规则文档.md` | XHS API 开发时（签名算法、OAuth、商品/订单 API） |
| `intel/processed/微信小店-完整规则文档.md` | 微信小店 API 开发时 |

## 关键路径

- 电商代码：`/opt/surenxuan/`（专属）
  - backend/、frontend/src/、data/、backend/tests/、backend/config/
- 看板代码：`/opt/china-hub/`
- 采集引擎：`/opt/mediacrawler/`（EMP_0004 部署，我只配置）
- XHS 采集管道：`skills/xhs/`（cookie-check / crawl / analyze / strategy-briefing）
- 分析 JSON：`/opt/mediacrawler/analysis/weekly_analysis.json`
- 策略简报：`/opt/mediacrawler/analysis/briefings/YYYY-MM-DD.json`

## 禁区

- ~/mason-hub/ 下的任何文件 — 禁止修改
- Agent 架构配置 — 禁止修改
- 其他项目的文件或数据 — 禁止访问
- 生产服务 — 禁止重启（除非明确要求）
- 验证步骤 — 禁止跳过
