---
name: standup
description: "Mason 每日感知面板：昨日回顾 + 今日待办，一屏看完"
---

# /standup — 每日感知面板

Mason 的晨间一屏总览：昨天做了什么，今天要做什么。

---

## 1. 昨日回顾

两个数据源拼出完整画面：

### 1a. Daily Note (做了什么 + 决策 + 学到)
- 读 `~/vault/daily/` 昨天的文件 (YYYY-MM-DD.md)
- 每个时间段提取一行摘要
- 如果没有昨日 daily note，标注 "昨日无 daily note"

### 1b. Git Log (代码变更)
- `git log --since="24 hours ago" --oneline`
- 每个 commit 一句话，去重（和 daily note 重复的不重复列）

## 2. Routine 检查

- **growth-feed**: 昨天 `~/.growth/records/` 中是否有记录
- **aigc-collect**: 昨天 `~/vault/references/aigc-inspiration/` 中是否有文件
- 连续漏 2 天以上时加提醒

## 3. 今日待办

- 读 `tasks/NOW.md`，列出所有未完成任务
- 按优先级排序 (P0 > P1 > P2)
- 如果有 Email Patrol 报告 (`data/patrol-logs/YYYY-MM-DD-patrol.md`)，末尾加一行摘要（几封待处理）

## 4. 执行转化率 (一行)

- 统计 `tasks/NOW.md` 中 `[ ]` 总数 = 待办
- 统计 `tasks/NOW.md` 中 `[x]` 总数 = 已完成
- 输出: `转化率: done/total (X%)`
- 这个数字追踪的是"当前焦点里的完成进度"，不是 backlog 全量

---

## 输出格式

```
晨会 YYYY-MM-DD

昨日:
  14:00 全局回顾 + 项目重组
  15:00 桌面整理
  16:00 内容创作 Skill 调研
  + 14 commits (CC Native 迁移, Email Patrol 全栈)

Routine:
  growth-feed: ok | aigc-collect: missed (3 天)

今日待办:
  P0: 验证 CC Agent 系统
  P1: SocialMesh 功能补全 / Email Patrol 调优
  Patrol: 3 封待处理

转化率: 2/15 (13%)
```

不超过 20 行。不检查服务器、不更新 SYSTEM_MAP、不追踪成本。
