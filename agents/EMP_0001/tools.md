# EMP_0001 pm-srx — 工具与资源

## Skills

→ run-acceptance-tests
→ run-backend-tests
→ check-escalation
→ semantic-snapshot

## 主动汇报

```bash
$SLACK_NOTIFY "$SLACK_CHANNEL" "消息内容"
```

汇报时机：开始复杂任务、每完成一个子任务、全部完成、需要决策时。

## 按需参考

| 文件 | 何时读 |
|------|--------|
| `docs/playbooks/pm-srx-playbook.md` | 需要操作流程细节时（任务拆解、反馈处理、巡检、复盘） |
| `kernel/standards/protocols/escalation.md` | 遇到 Dev 失败需要评估/上报时 |
| `kernel/standards/protocols/startup.md` | 参考标准启动/中断恢复流程时 |
| `kernel/standards/protocols/tools.md` | 使用通用工具时 |
| `docs/system/org-chart.md` | 了解组织架构时 |

## 关键路径

- 任务列表：`accounts/surenxuan/project/task_list.json`
- Escalation 目标：EMP_0003（电商 Domain Manager）
- Dev：EMP_0005（电商 Dev）
- Slack 频道：#srx-business

## 禁区

- 禁止修改 `knowledge_base.md` 或 `meta/` 目录
- 禁止暴露内部文件名、agent 编号、系统架构细节给 Mason
