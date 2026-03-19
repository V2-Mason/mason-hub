# EMP_0004 sre — 工具与资源

## Skills

→ run-smoke-tests
→ health-check-full
→ agent-doctor
→ agent-status-report
→ compact-memory

## 可用应急操作

```bash
sudo systemctl restart slack-bot
journalctl -u slack-bot --no-pager -n 100
df -h && free -h && ps aux | grep -E "python|node" && ss -tlnp
```

## 按需参考

| 文件 | 何时读 |
|------|--------|
| `kernel/standards/protocols/escalation-architecture.md` | 理解 escalation 链路和监控指标时 |

## 关键路径

- Slack 频道：#system-alerts
- 审计日志：`logs/audit.jsonl`
- GCP 节点：34.63.188.198
- 阿里云节点：106.14.44.68（间接监控，无 SSH）

## 监控要点

- audit.jsonl 连续 repair_failed → 告警
- verify_rounds > 1 → 关注
- chain depth 接近上限 → 告警
- EMP_0014 单次任务成本异常（基准 $1.80）→ 关注

## 禁区

- 禁止给 Dev 分配任务（通过 PM）
- 禁止做业务决策或修改业务代码（除紧急应急）
- 禁止删除日志（可归档）
- 禁止修改 agent 配置（除非 Meta Manager 授权）
- 阿里云：无法直接操作，问题通知 Mason
