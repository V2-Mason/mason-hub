# EMP_0008 PM-SocialMesh — 工具与资源

## Skills
→ run-backend-tests
→ check-escalation
→ xhs-crawl
→ xhs-analyze
→ xhs-publish-log
→ semantic-snapshot

## 关键数据路径
- 任务列表：`accounts/socialmesh/project/task_list.json`
- XHS 分析报告：`data/reports/`
- 策略简报：阿里云 `/opt/mediacrawler/analysis/briefings/`
- 简报 Schema：`shared/xhs-briefing-schema.json`
- 内容日历：`accounts/surenxuan/context/2026-content-calendar.md`
- 排期 Google Sheet ID: `1icNxvwx8LHZaXvcl7EV010x7id4ZxAwYwg3EgZDXsDs`

## 内容情报分析框架
- 框架 A：竞品内容扫描（5 维度）
- 框架 C：选题方向生成（四步法）
- 框架 D：痛点词挖掘（三层）
- 详见 memory/memory.md

## 视频管线
- 剪辑规则库：`shared/editing_intelligence/styles/`（9 个文件）
- 品牌覆盖：`accounts/surenxuan/context/editing_overrides.md`
- 多剪参数表：`socialmesh/docs/plans/2026-03-04-multicut-architecture.md`

## 按需参考
| 文件 | 何时读 |
|------|--------|
| `docs/playbooks/pm-socialmesh-playbook.md` | 操作流程细节（运营/分析/任务拆解/QA Gate） |
| `kernel/standards/protocols/escalation.md` | Dev 失败需评估/上报时 |
| `kernel/standards/protocols/startup.md` | 标准启动/中断恢复流程 |
| `kernel/standards/protocols/tools.md` | 使用 Semantic Snapshot 等通用工具时 |
| `docs/system/org-chart.md` | 了解组织架构和其他 agent 职责时 |

## 禁区
- 禁止修改 knowledge_base.md / meta/ 目录
- 禁止同时给 Dev 分配超过 2 个并行任务
- 禁止在回复里暴露内部文件名、agent 编号、系统架构细节
