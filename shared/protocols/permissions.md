# Agent 通信权限矩阵

> send_message() 在发送前校验此矩阵。
> 不符合权限的消息拒绝发送，输出错误到 stderr。

## 消息类型权限规则

| type | 允许的 sender | 允许的 receiver | 说明 |
|------|-------------|----------------|------|
| task_assign | EMP_0000 · EMP_0001 · EMP_0003 · EMP_0008 | 任意 EMP | 只有 Manager/PM 能派任务 |
| task_complete | 任意 EMP | 任意 EMP | 无限制 |
| task_failed | 任意 EMP | 直属上级 · EMP_0000 | 失败只报给上级 |
| review_request | 任意 EMP | EMP_0000 · EMP_0012 · 直属上级 | 审核请求有限路由 |
| review_response | EMP_0000 · EMP_0012 | 任意 EMP | 只有审核方能回复 |
| escalate | 任意 EMP | EMP_0000 | 强制路由到 Meta Manager |
| ping | 任意 EMP | 任意 EMP | 无限制 |
| state_update | 任意 EMP | 任意 EMP | 无限制 |
| task_assign_confirm | 任意 EMP | 任意 EMP | 无限制 |

## 越权处理规则

- send_message() 检测到越权：拒绝发送 + 输出 `ERROR: [sender] 无权向 [receiver] 发送 [type] 消息`
- 越权尝试写入 logs/audit.jsonl，type: permission_violation
