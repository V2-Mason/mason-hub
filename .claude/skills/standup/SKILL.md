---
name: standup
description: "晨会报告：昨日工作回顾、系统健康、今日待办、Scout 情报、成本概览"
---

# /standup — 晨会

执行以下步骤，汇总为一份简洁的晨会报告。

**核心原则**: SYSTEM_MAP.md 是持久化状态，/standup 是增量更新入口。不重建地图，只更新变化的字段。

---

## 0. 读取 SYSTEM_MAP（先读再改）

- 读取 `SYSTEM_MAP.md`，记住每条能力线的**上次状态**
- 后续步骤中发现的信息用于增量更新地图，而不是从头推断

## 1. 昨日工作回顾
- 读取 logs/audit.jsonl 最近 24 小时的记录
- 读取 git log --since="24 hours ago" 获取 commit 记录
- 统计：完成了几个任务、失败了几个、正在进行几个
- 列出每个完成任务的一句话摘要

## 2. 系统健康状态
运行以下检查：
```bash
# GCP 系统状态
uptime
df -h / | tail -1
free -h | head -2

# 检查关键服务
systemctl is-active cron 2>/dev/null || echo "cron: 未运行"

# 检查 crontab 任务是否注册
crontab -l 2>/dev/null | grep -c mason-hub || echo "cron 任务: 0 条"

# 检查阿里云连通性
timeout 5 ssh -o ConnectTimeout=3 root@106.14.44.68 "echo ok" 2>/dev/null && echo "阿里云: ✅ 连通" || echo "阿里云: ❌ 不通"

# 检查 Git 状态
cd ~/mason-hub && git status --short | head -5
cd ~/surenxuan && git status --short | head -5
```

## 3. SYSTEM_MAP 增量更新

基于步骤 1-2 收集到的信息，**增量更新** SYSTEM_MAP.md：

### 自动更新字段（直接改）
- **能力线状态**: 对比上次状态，如果有变化则更新（如 blocked → active）
  - health check 失败 → 对应线可能 blocked
  - cron 正常运行 → 对应线可能 active
  - 无新 commit 且无 blocker → 可能 waiting 或 stable
- **里程碑**: 如果昨日工作推进了里程碑，更新描述
- **阻力来源**: 如果有新 blocker 出现或旧 blocker 解决，更新列表
- **推荐行动**: 基于当前受力分析重新生成
- **硬性等待项**: 检查是否有到期的等待项，标记状态变化

### 检查耦合触发条件
检查是否发生了以下事件，如果是，在对应能力线追加 `⚠️待确认`：
- 新 Agent 创建
- blocker 状态从 blocked → active/stable
- MASON_AUTHORITY.md 有架构级修改

### 不更新的字段
- 耦合关系的具体描述（除非 Mason 已确认）
- 已有的 ⚠️待确认 标记（等 Mason 响应）

### 更新 SYSTEM_MAP.md 文件
- 用 Edit 工具更新变化的字段
- 更新"上次更新"时间戳
- **不要重写整个文件**，只改变化的部分

## 4. 今日待办
- 读取 tasks/backlog.md，列出所有未完成的 P0/P1 任务
- 按优先级排序（P0 > P1 > P2）
- 与 SYSTEM_MAP 的推荐行动交叉验证：推荐行动中的事项应该出现在待办里
- 如果没有待办，说"今日无待办任务"

## 4b. 知行转化率
- 运行 `python3 scripts/backlog-scanner.py --count` 获取可自动执行任务数
- 统计 tasks/backlog.md 中 `[ ]` 的总数（grep -c '\[ \]' tasks/backlog.md）
- 计算转化率 = 可自动执行 / 总未完成 × 100%
- 输出到报告的固定位置（在 API 消耗之前）

## 5. Scout 情报摘要
- 读取 ~/mason-hub/intel/raw/ 目录下最近的情报文件（按日期排序取最新）
- 读取 ~/mason-hub/intel/digests/ 目录下最近一期周度简报
- 汇总：最近有几条新情报，其中 🔴 级几条（重点标注给 Mason）
- 如果 intel/ 目录不存在或为空，显示"暂无情报"
- 🔴 级情报必须逐条列出标题和建议行动

## 6. Gateway 未提交变更检查
- 运行 `git status --short` 检查是否有 Gateway 产生的未提交文件变更（排除 logs/ 和 data/gateway-memory.jsonl 和 data/events/）
- 如果有代码变更（scripts/、skills/、SYSTEM_MAP.md、MASONHUB.md 等）：
  - **执行完整的 /commit 流程**（不是简单 git add + commit）：
    1. EMP_0012 Checklist A 归属判断
    2. 对应 agent 记忆写 lesson（铁律 4）
    3. Gateway 决策广播检查
    4. git commit
  - 在输出中标注："🔧 Gateway 变更已提交: <文件列表> → EMP_XXXX (含 lesson)"
- 如果没有代码变更 → 在报告中标注 "🔧 Gateway 变更: 无代码变更"（不省略此行）

## 7. 成本概览
- 如果 logs/token-usage.log 存在，显示最近 7 天的 API 消耗趋势
- 如果不存在，跳过此项

---

## 输出格式

用简洁的结构化格式输出，一屏能看完。包含以下区块：

```
📋 晨会 2026-XX-XX

昨日：完成 N 个任务，失败 N 个
  ✅ ...
  ✅ ...

系统：GCP ✅ | 阿里云 ✅ | 磁盘 33% | cron 26 条
Git：mason-hub clean | surenxuan clean

受力分析（SYSTEM_MAP 变化）：
  自治线: active（无变化）
  数据线: blocked → active ✦ srx_sales 401 已修复
  内容线: waiting（无变化）
  商业线: waiting（无变化）
  推荐行动: 1. xxx  2. xxx

⚠️ 需要 Mason 确认：
  - 数据线耦合关系：srx_sales blocker 解除，内容线是否解锁？
  - ...
  （如果没有待确认项，省略此区块）

今日待办：
  P1: ...
  P2: ...

🔧 Gateway 变更: 无代码变更 / 已提交 X 个文件 → EMP_XXXX

情报：🔴 x 条 | 🟡 x 条
  🔴 标题 — 建议行动

知行转化率: N/M (X%) — backlog 可自动执行 / 总未完成
API 消耗：本周 $X.XX（日均 $X.XX）
```

### 关键格式规则
- **受力分析区块**: 只显示有变化的线（标记 ✦），无变化的线一行带过
- **需要 Mason 确认区块**: 收集所有 ⚠️待确认 项，集中呈现，不散落在其他区块里。没有待确认项时省略整个区块
- **状态变化用箭头**: `blocked → active` 一目了然
- 整体一屏，不超过 30 行
