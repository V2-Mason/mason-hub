---
name: approve
description: "审批 Escalation 队列和 Memory Pending 条目。Mason 说 /approve 时触发。"
user_invocable: true
---

# /approve — 批量审批

当 Mason 说 `/approve` 时执行以下步骤：

## Step 1. 加载队列

运行：
```bash
python3 scripts/control/escalation-queue.py --format summary
```

显示 Escalation 队列的 Top 5 优先项。

## Step 2. 检查 Memory Pending

```bash
python3 scripts/memory-router.py --process
```

如果有 pending 条目，显示每条内容和建议的 Pipe 归属。

## Step 3. 逐项审批

对每个需要 Mason 处理的项目：
- 展示：类型 + 内容摘要 + 建议操作
- 等待 Mason 决定：approve / reject / defer / 自定义指令

## Step 4. 执行决策

- **Task failure**: Mason 决定重试/搁置/调整方向 → 更新 task YAML status
- **Memory pending**: Mason 确认 Pipe 归属 → 调用 `python3 scripts/memory-router.py` 路由到正确文件
- **Expired decision**: Mason 确认续期/删除 → 更新 gateway-known-states.yaml

## Step 5. 汇报

```
✅ 审批完成
  - 处理: X 项
  - 批准: Y 项
  - 搁置: Z 项
  - Memory 路由: N 条
```
