# Mason Hub — 工作规范

## Token 消耗记录规范
- 每次 Claude API 调用必须经过 api_logger.log_api_call() 记录
- 日志路径：~/mason-hub/logs/api_usage.jsonl
- 每日 11pm CST 自动生成消耗报告到 #system-alerts
- 新增 API 调用点时，必须同步添加 logging
- 子进程 agent 调用（via run-agent.sh）通过 --output-format json 获取精确 token 数据

## 组织架构

```
Mason (人类，最终决策者)
│
├── EMP_0000 Meta Manager        ← 一级：跨 domain 战略协调
│     │
│     ├── EMP_0003 电商 Domain Manager  ← 二级：行业专家
│     │     │
│     │     └── EMP_0001 素仁轩 PM      ← 三级：项目管理
│     │           │
│     │           └── EMP_0005 电商 Dev  ← 四级：业务执行层
│     │
│     ├── EMP_0004 SRE Agent            ← 二级：基础设施运维
│     │
│     └── EMP_0002 Platform Dev         ← 二级：平台基础设施开发
│
└── (Phase 3 预留) 斥候 Agent
```

### Agent 职责速览
- EMP_0000 Meta Manager — 跨域调度，Mason 的主要 AI 对接人
- EMP_0002 Platform Dev — 平台基础设施开发（~/mason-hub/ 专属）
- EMP_0003 电商 Domain Manager — 电商行业判断和项目间协调
- EMP_0004 SRE Agent — 全局基础设施运维
- EMP_0001 素仁轩 PM — 素仁轩项目管理
- EMP_0005 电商 Dev — 电商业务开发（/opt/surenxuan/ 专属）

## Backlog 管理规则

backlog 路径: ~/mason-hub/tasks/backlog.md

1. 每次 Agent 会话开始时，先读取 backlog 了解当前状态
2. 每次 Agent 会话结束前，必须更新 backlog：
   - 完成的任务标记 [x] 并注明日期
   - 新发现的问题添加到对应优先级
   - 调整优先级（如有必要）
3. 所有 Agent 都遵守此规则，不只是 Meta Manager
4. backlog 是项目唯一的 source of truth

## Agent Teams 角色自动加载规则

当你作为 Agent Team 的 teammate 被启动时，根据你被指定的角色名称，**必须**读取对应的完整配置文件并严格遵守：

| 角色关键词 | 配置文件 | 工作边界 |
|-----------|---------|---------|
| Meta Manager | agents/EMP_0000.md | 跨 domain 协调，不直接执行 |
| 素仁轩 PM | agents/EMP_0001.md | 素仁轩项目管理 |
| Platform Dev | agents/EMP_0002.md | 仅限 ~/mason-hub/ |
| 电商 Manager | agents/EMP_0003.md | 电商 domain 决策 |
| SRE | agents/EMP_0004.md | 系统监控和运维 |
| 电商 Dev | agents/EMP_0005.md | 仅限 /opt/surenxuan/ |

**加载流程**：
1. 识别自己被分配的角色名称
2. 读取对应 .md 文件的**完整内容**（不得简化）
3. 遵守该文件中定义的所有职责、边界、汇报关系
4. 在团队协作中只做自己职责范围内的事

**禁止行为**：
- 不得跨越工作目录边界
- 不得替代其他角色做决策
- 不得忽略配置文件中的"明确禁止"条款
