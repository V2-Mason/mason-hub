# Escalation 架构总览（系统级）

agent 体系采用四层 debug escalation 架构：

```
Layer 0: Dev — 自动修复（每次最多 3 轮）
  │ 代码修改 → dev-verify-loop（语法→模块测试→回归）
  │ 3 轮失败 → git checkout 恢复 + audit.jsonl + Slack 通知
  │ → 自动触发 PM
  │
  ▼ repair_failed（自动链式触发）
Layer 1: PM — 评估分类（对同一任务最多重分配 Dev 2 次）
  │ 运行 check-escalation.sh → 检查 can_retry
  │ A/B 类：ACTION → 自动触发 Dev
  │ C/D 类：ACTION → 自动触发 Platform Dev
  │ E 类：ACTION → Slack 通知 Mason
  │
  ▼ 架构/测试问题 或 PM 重试耗尽（自动链式触发）
Layer 2: Platform Dev (EMP_0002) — 跨域修复（最多 3 轮）
  │ 修复 skills/测试框架/agent 配置
  │ 无法修复 → Slack 通知 Mason（链结束）
  │
  ▼ 无法解决
Layer 3: Mason — 人工决策
  需求调整、架构重设计、或搁置任务

横向: SRE (EMP_0004) — 全局监控
  持续监控 audit.jsonl + chain depth + token 消耗
```

## 链式触发规则
- Dev 失败 → 自动触发 PM（无需人工干预）
- PM 决策 → 通过 ACTION 输出自动触发下一步
- Platform Dev 失败 → Slack 通知 Mason（链结束）
- 全局 chain depth 上限：10

## 完整消耗上限
- Dev: 3 轮 × 3 次 = 9 轮
- PM: 3 次评估
- Platform Dev: 3 轮
- 总计: ~15 次 claude -p，~216k tokens
- 超过此上限必定交给 Mason

## 原则
- **不跳层**：Dev 不直接找 Mason
- **带上下文**：每次附 audit.jsonl 记录
- **有时限**：每层一个工作周期，超时自动升级
- **可追溯**：所有 escalation 记录在 audit.jsonl + logs/tasks/
- **有上限**：每层明确重试次数，防止无限循环
