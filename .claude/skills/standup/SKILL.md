---
name: standup
description: "晨会报告：昨日回顾、Routine 检查、今日待办"
---

# /standup — 晨会

三个区块，一屏看完。

---

## 1. 昨日工作回顾

- `git log --since="24 hours ago" --oneline` 获取 commit 记录
- 统计完成了几个任务
- 每个 commit 一句话摘要

## 2. Routine 完成情况

- **growth-feed**: 昨天 `~/.growth/records/` 中是否有记录
- **aigc-collect**: 昨天 `~/vault/references/aigc-inspiration/` 中是否有文件
- 连续漏 2 天以上时加提醒

## 3. 今日待办

- 读取 `tasks/NOW.md`，列出所有未完成的 P0/P1 任务
- 按优先级排序（P0 > P1 > P2）
- 如果没有待办，说"今日无待办任务"

---

## 输出格式

```
晨会 YYYY-MM-DD

昨日: N commits
  - commit summary 1
  - commit summary 2

Routine:
  growth-feed 昨日: ok/missed (连续 N 天未执行)
  aigc-collect 昨日: ok/missed (连续 N 天未执行)

今日待办:
  P0: ...
  P1: ...
```

不超过 20 行。不检查 GCP/阿里云/Gateway/Scout/成本 — 这些要么在 RemoteTrigger 里，要么已归档。