---
name: solve
description: 发现问题/Gap 时的完整解决流程。适用于任何非 trivial 的问题——bug、架构缺陷、性能瓶颈、流程缺失。强制走完 13 步，不能跳步直接执行。
user_invocable: true
---

# /solve — 问题解决全流程

> **触发时机**：发现问题/Gap、用户报 bug、系统告警、审计发现异常
> **类型**：Rigid — 严格按步骤执行，不跳步

## Phase 1: 定义问题

### Step 1. 问题陈述
用一句话描述问题：**什么**在**什么条件下**产生了**什么不期望的结果**。

```
问题：[具体描述]
发现方式：[用户报告 / 监控告警 / 审计发现 / 代码审查]
影响范围：[哪些 agent / account / 流程受影响]
```

### Step 2. 问题定级

按三个维度打分（1-3），计算优先级：

| 维度 | 1 (低) | 2 (中) | 3 (高) |
|------|--------|--------|--------|
| **Severity** | 不影响核心功能 | 降级但可用 | 功能不可用/数据错误 |
| **Urgency** | 下周处理即可 | 今天需要处理 | 现在必须处理 |
| **Impact/Effort** | 修复成本高收益低 | 成本收益平衡 | 小修复大收益 |

```
Priority Score = Severity × Urgency × Impact = [X]
- 18-27: 🔴 立即处理
- 8-17:  🟡 本轮计划
- 1-7:   🟢 Defer（记录到 backlog）
```

### Step 3. 决定 scope

- 🔴 立即处理 → 继续 Phase 2
- 🟡 本轮计划 → 继续 Phase 2
- 🟢 Defer → 写入 `tasks/backlog.md` 并标注定级结果，**停止**

## Phase 2: 方案设计

### Step 4. 列出 2-3 种解决方案

每个方案必须包含：

```
方案 A: [名称]
- 做法：[具体做什么]
- 优点：[为什么好]
- 缺点：[风险/代价]
- 工作量：S / M / L / XL
- 可逆性：可逆 / 部分可逆 / 不可逆
```

**禁止只列一个方案**——只有一个方案说明没想清楚。

### Step 5. 选定方案

向 Mason 呈现 trade-off 对比表，等待确认。
如果 Priority Score ≥ 18 且方案明显唯一 → 可自主选择，但必须记录理由。

## Phase 3: 任务分解

### Step 6. 拆解 Task

每个 task 必须是 **一个人（或一个 agent）在一个 session 内能完成的原子工作**。

```
Task 1: [描述]
  Owner: EMP_XXXX
  Input: [需要什么]
  Output: [产出什么]
  验收标准: [observable, binary, automatable]
```

**验收标准三要素**：
- Observable: 能看到结果（不是"应该没问题"）
- Binary: pass 或 fail，没有"差不多"
- Automatable: 最好能用命令验证（`bash -n`, `python -c`, `curl`）

### Step 7. 依赖分析

```
Task 1 ──(hard dep)──→ Task 3   # 必须先完成 1 才能做 3
Task 2 ──(soft dep)──→ Task 3   # 最好先完成 2，但 3 可以先开始
Task 4                           # independent，可并行
```

### Step 8. 资源约束映射

理论并行度 vs 实际并行度：
- Mason 在线 → dispatcher 不派活（安全门 0b）
- 同 lane 同 agent 互斥
- Max 订阅每天 15% model limit

### Step 9. 排出执行时序

```
Phase A: [task list] → Gate: [检查什么]
Phase B: [task list] → Gate: [检查什么]
...
```

### Step 10. 验收标准 + 回退方案

每个 task：
```
验收：[命令或检查方式]
回退：[如果失败怎么恢复] — 仅不可逆 task 需要
Checkpoint: [在哪里保存恢复点] — 仅不可逆 task 需要
```

## Phase 4: 执行

### Step 11. 执行

- 按时序执行
- 每完成一个 Phase 的所有 task → 过 Gate
- Gate 不通过 → 停下来，不继续

### Step 12. 验收

```
Task X: [actual result] vs [expected result]
  ✅ PASS / ❌ FAIL: [偏差描述]
```

## Phase 5: 学习

### Step 13. 经验提取

**每个有偏差的 task 必须回答**：
1. 预期 vs 实际的偏差是什么？
2. 偏差的根因是什么？（不是"下次注意"）
3. 怎么防止再次发生？（规则/检查/自动化）

经验写入对应 Agent 的 `memory/sessions/{instance_id}.md`。

---

## 快捷模式

**1-2 步的简单问题**可以压缩流程，但至少要有：
- Step 1 (问题陈述) + Step 2 (定级) + Step 10 (验收标准) + Step 13 (经验提取)

**紧急 hotfix (Score ≥ 18)**：
- Step 1 → Step 6（直接拆 task）→ Step 11（执行）→ Step 12-13（验收+学习）
- 方案设计事后补（但必须补）
