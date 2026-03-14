# EMP_0006 Scout — 工具与资源

## Skills
→ scout-github
→ scout-trending
→ scout-anthropic
→ scout-search-topic
→ scout-ui-inspiration
→ scout-products
→ scout-find-skill
→ scout-xhs-trends
→ scout-ecom-compete
→ semantic-snapshot

## Scout v2 Engine
- 代码：`intel/engines/`
- 入口：`python -m intel.engines.pipeline [--resume] [--force spider,query] [--days 3]`
- 数据库：`intel/scout.db`
- 管道：spider → query → media → insight → forum → report
- 多模型：DeepSeek（默认分析）、Gemini（图片）、Qwen（中文验证备用）
- 旧版脚本 `skills/scout/scout-*.sh` 继续作为 SpiderEngine 采集器

## 数据存储
- `intel/raw/` → `intel/processed/` → `intel/validated/` → `intel/reports/`
- `intel/digests/` — 周度简报
- `intel/skill-scouts/` — find-skill 结果
- `intel/watchlist.md` — 巡逻前必读
- `intel/seen.jsonl` — 去重记录

## 按需参考
| 文件 | 何时读 |
|------|--------|
| `shared/protocols/tools.md` | 使用 Semantic Snapshot 时 |
| `docs/plans/2026-03-10-scout-v2-design.md` | Engine 详细设计 |

## 情报分发路由

| 情报类型 | 分发频道 |
|----------|----------|
| 内容趋势 | #socialmesh |
| 电商竞品 | #srx-intel |
| 通用情报 | #scout |
| find-skill | 请求方频道 |

## 禁区
- 禁止修改代码/agent 配置/meta/ 目录
- 禁止触发其他 agent 或做业务决策
- 禁止在没有读取 watchlist.md 的情况下巡逻
