# agent.log 结构化日志 Schema

> Owner: EMP_0002 (Platform Dev)
> 生效日期: 2026-03-12

## 概述

`logs/agent.log` 是 JSONL 格式的 Agent 执行日志，每行一个 JSON 对象。
所有写入通过 `run-agent.sh` 的 `log_structured()` 函数，禁止直接 `echo >> agent.log`。

## 基础字段（所有事件必有）

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | ISO 8601 UTC 时间 |
| `agent_id` | string | Agent 标识，如 `EMP_0001` |
| `task_id` | string | 任务 ID，格式 `task_{agent}_{epoch}` |
| `event_type` | string | 事件类型，见下表 |
| `elapsed_s` | number | 自任务开始已过秒数 |
| `message` | string | 人类可读描述（≤500 字符） |

## 事件类型 (event_type)

| 类型 | 含义 | 扩展字段 |
|------|------|---------|
| `start` | 任务开始 | `work_dir`, `has_verify`, `task_type`, `chain_depth` |
| `info` | 信息性（如轮次开始） | `round`, `max_rounds` |
| `output` | Agent 产出 | `round`, `output_bytes`, `duration` |
| `verify` | 验证结果 | `round`, `exit_code` |
| `error` | 错误 | 自由扩展 |
| `crash` | 异常退出 | — |

## 扩展字段

通过 `log_structured` 的 `key=value` 参数添加，数字自动识别，其余为字符串。

## 日志轮转

- 每次 `run-agent.sh` 启动时检查 `agent.log` 大小
- 超过 1MB → 重命名为 `agent.log.{timestamp}` 并 gzip
- 保留最近 5 个归档

## 查询工具

```bash
scripts/log-query.sh --stats              # 统计摘要
scripts/log-query.sh --agent EMP_0001     # 按 agent
scripts/log-query.sh --type error         # 按类型
scripts/log-query.sh --since 2026-03-12   # 按日期
scripts/log-query.sh --task-id task_xxx   # 按任务
scripts/log-query.sh --tail 50            # 最近 N 条
```

## 与 audit.jsonl 的关系

| 文件 | 粒度 | 用途 |
|------|------|------|
| `agent.log` | 事件级（start/output/verify/error） | 执行过程追踪 |
| `audit.jsonl` | 任务级（一个任务一条） | 成本/结果审计 |
| `logs/tasks/` | 完整原始 JSON | Debug 用原始 claude 输出 |
