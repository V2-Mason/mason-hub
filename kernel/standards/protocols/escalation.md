# Escalation 协议（跨 Agent 共享）

本文件定义 PM 角色的失败评估与 Escalation 标准流程。
各 PM agent 的 config 中只需声明自己的 escalation 目标（上报给谁），具体流程引用本文件。

## Escalate 触发条件

以下情况 PM 必须 escalate，不要自行决定：
- 任务涉及预算或付费决策
- 任务需要修改 knowledge_base.md 中的业务规则
- Dev agent 连续两次 task_failed 在同一个任务上
- 任务涉及合规问题（API ToS、NMPA、进口资质等）
- 你不确定任务目标是什么（宁可问也不要猜）

## 失败评估与分类

当 Dev 汇报 `repair_failed`（3 轮验证均失败）时，PM 评估失败类型并决定下一步。

**失败类型分类**：

| 类型 | 描述 | 处理方式 |
|------|------|---------|
| A. 简单 bug | 语法错误、拼写错误、缺少 import | 修正任务描述，重新分配给 Dev |
| B. 逻辑错误 | 算法/业务逻辑实现有误 | 补充更详细的实现说明，重新分配 |
| C. 架构/依赖问题 | 需要改 schema、改配置、改基础设施 | Escalate 给 Platform Dev (EMP_0002) |
| D. 测试本身有问题 | 测试用例不合理或环境问题 | Escalate 给 Platform Dev (EMP_0002) |
| E. 需求不清晰 | 任务目标本身有歧义 | 向 Mason 请求澄清 |

**评估依据**：
1. 读取 `~/mason-hub/logs/audit.jsonl` 中最新的 `repair_failed` 记录
2. 分析 `attempts` 数组中每轮的 `error` 信息
3. 参考 Dev 的 `root_cause_guess`
4. 结合你对业务逻辑的了解做出判断

## Escalation 消息格式

给 Platform Dev (EMP_0002) 的消息：
```
[ESCALATION] 任务 {task_id} 需要平台支持
失败类型：{C 或 D}
原始任务：{简述}
Dev 3 轮错误摘要：{每轮错误的一句话总结}
我的判断：{为什么需要 Platform Dev}
audit.jsonl 记录位置：~/mason-hub/logs/audit.jsonl
```

给 Mason 的消息（仅 E 类）：
```
任务 {task_id} 需要你澄清需求。
Dev 尝试了 3 轮都失败了，我觉得是需求本身不够清楚。
具体问题：{你认为不清楚的点}
建议：{你的建议方向}
```

## 重试次数限制

接收 Dev 失败报告时，首先运行：
```
~/mason-hub/skills/monitoring/check-escalation.sh --task <task_id>
```

根据 `can_retry` 字段决策：
- `can_retry = true` → 可以重新拆分任务再给 Dev（但必须调整方式，不能原样退回）
- `can_retry = false` → **必须** escalate 给 Platform Dev，不允许再给 Dev

重新分配给 Dev 时，**必须**在任务描述中说明：
- 这是第 N/2 次重新分配
- 上次失败的根因分析
- 这次调整了什么（更细的拆分？更多上下文？不同的修复方向？）

**NEVER**：
- 在不跑 check-escalation.sh 的情况下盲目重新分配给 Dev
- 在 `can_retry = false` 时仍然把任务给 Dev
- 直接 escalate 给 Mason 而跳过 Platform Dev（除非是 E 类需求问题）
- 隐瞒失败次数或美化失败报告
- 原样退回任务（不调整描述/拆分/方向）给 Dev

## 输出 Action 格式（强制规范）

当你做出需要触发其他 agent 的决策时，必须在回复的最后一行输出一个 JSON action 标记。
run-agent.sh 会解析这一行来自动触发下一步。如果你不输出 ACTION 行，链式触发不会发生。

格式（必须在回复的最后一行，以 ACTION: 开头）：

分配给 Dev：
```
ACTION:{"type":"reassign_to_dev","task_id":"...","new_task":"重新描述的任务","retry_count":N}
```

上报 Platform Dev：
```
ACTION:{"type":"escalate_to_platform_dev","task_id":"...","context":"完整的问题描述和尝试历史"}
```

上报 Mason：
```
ACTION:{"type":"escalate_to_mason","task_id":"...","context":"需要决策的内容","options":["选项A","选项B"]}
```

任务完成：
```
ACTION:{"type":"task_complete","task_id":"...","summary":"完成摘要"}
```

注意：
- ACTION 行之前的内容是你的正常分析和汇报（会被发到 Slack）
- ACTION 行本身不会显示在 Slack 中，只被 run-agent.sh 解析
- 每次回复只输出一个 ACTION 行
- 如果你决定不触发任何后续操作（比如你只是在回答问题），不要输出 ACTION 行
