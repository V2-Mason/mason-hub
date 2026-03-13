# Agent 设计模板 — 四层身份证

> 所有新 Agent 必须先填此模板，EMP_0012 审核通过后才能开始写代码。
> 现有 Agent 逐步补齐缺失字段。

---

## Agent 身份

| 字段 | 值 |
|------|---|
| ID | EMP_XXXX |
| 角色 | |
| 汇报给 | （Manager 是谁） |
| 工作目录 | |
| Lane | ecommerce / socialmesh / platform / 无 |

---

## 一、触发条件（什么时候运行）

### 时间触发（cron）
| 时间 | 任务 | 描述 |
|------|------|------|
| | | |

### 事件触发（监听哪些事件）
| 事件 | 来源 | 我做什么 |
|------|------|---------|
| | | |

### 手动触发
| 命令 / skill | 谁来触发 | 场景 |
|-------------|---------|------|
| | | |

---

## 二、前置条件（运行前检查什么）

### 权限
- MASON_AUTHORITY 层级: Layer N / "直接做" / "做完通知" / "必须确认"

### 上游依赖
| 依赖 | 检查方式 | 不满足时怎么办 |
|------|---------|--------------|
| | | |

### 系统状态
- SYSTEM_MAP 要求哪条能力线状态为 active:
- 其他前置条件:

---

## 三、输出契约（产出什么、写到哪里）

### 产出物
| 产出 | 格式 | 写入位置 | 示例 |
|------|------|---------|------|
| | | | |

### 汇报格式
写入 `/data/reports/YYYY-MM-DD/` 的结构化 JSON:
```json
{
  "agent_id": "EMP_XXXX",
  "task_id": "",
  "timestamp": "",
  "status": "success|failed|partial",
  "level": 0,
  "summary": "",
  "changes": [],
  "blockers_found": [],
  "blockers_resolved": []
}
```

---

## 四、下游通知（完成后触发什么）

### 事件发射
| 我完成的动作 | 写入的事件 | 下游谁消费 |
|-------------|-----------|-----------|
| | | |

### 汇报级别判定
| 场景 | Level | 通知方式 |
|------|-------|---------|
| 正常完成，无异常 | 0 | 只写日志 |
| 改变了系统状态 | 1 | 写 report，briefing 呈现 |
| 失败 2 次 / 状态变化 | 2 | 直接发 Slack |
| 涉及红线 / 需要决策 | 3 | Slack + /standup 待确认 |

### 升级规则
| 条件 | 升级给谁 | 方式 |
|------|---------|------|
| 连续 3 次失败 | Manager | |
| 涉及硬性红线 | Mason | Level 3 |
| 超出我的职责范围 | Manager | |

---

## 五、自评估配置（v1.1 §9 — 可选）

```yaml
self_eval:
  enabled: true | false        # 是否启用交付前自评
  max_iterations: 3            # 最多自我修正几次
  criteria:                    # 评估维度
    - "Output completeness: 是否覆盖所有任务要求?"
    - "Logical consistency: 有无矛盾或遗漏?"
    - "Granularity: 每个步骤是否可直接执行?"
  on_fail: refine              # 不合格时: refine（自修正）
  on_3x_fail: seek_new_skill   # 3 次失败: 触发 Scout 搜索新技能
```

## 六、运行时配置（v1.1 §6 — 可选）

```yaml
runtime:
  type: llm | pipeline | script | hybrid
  engine: claude-api | comfyui | python-script
  timeout: 600                 # 最大执行秒数
  model_routing:               # 不同阶段用不同模型
    execution: sonnet           # 日常执行（快、便宜）
    reflection: opus            # 自评估（深度推理）
```

---

## 审核清单（EMP_0012 检查）

- [ ] 四个层都填了，没有空白
- [ ] 触发条件至少有一种明确的触发方式
- [ ] 前置条件覆盖了权限 + 上游依赖 + 系统状态
- [ ] 输出契约明确了格式和写入位置
- [ ] 下游通知声明了事件和消费者
- [ ] 升级规则覆盖了失败/超时/越权三种场景
- [ ] 与 SYSTEM_MAP 的能力线对应关系明确
