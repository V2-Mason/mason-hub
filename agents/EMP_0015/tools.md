# EMP_0015 Data Analyst — 工具与资源

## Skills

- → `semantic-snapshot` — 语义快照

## 分析框架

- → 四维判断框架（搜索卡位/内容说服力/店铺承接力/用户资产积累）
- → 五方法论（归因/漏斗/A/B 测试/Cohort/竞品基准）

## 产出路径

- → `data/reports/` — 周度/月度分析报告
- → Slack #rednote — 异常检测推送
- → `data/` — 基线数据更新

## 按需参考

| 文件 | 何时读 |
|------|--------|
| `~/.claude/projects/-home-hangn-mason-hub/memory/xhs-analysis-standard.md` | 分析标准 |
| `data/data_catalog.yaml` | 数据源位置和格式 |
| `shared/protocols/startup.md` | 标准启动流程 |

## 数据消费方式

- 通过 EMP_0014 的 SDK 读取数据（`from data.tools import ...`）
- 数据源：SQLite / JSONL / JSON（经 data_catalog.yaml 注册）

## 禁区

- 不采集数据、不建管道（EMP_0014 职责）
- 不写代码
- 不做业务决策
- 不做内容策略或店铺运营
