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
│     ├── EMP_0008 SocialMesh 内容运营总监  ← 二级：内容策略 + 项目管理
│     │     │
│     │     ├── EMP_0010 Content Creator   ← 三级：内容生产 + 社区互动
│     │     │
│     │     └── EMP_0009 Content-Tech Dev  ← 三级：业务执行层
│     │
│     ├── EMP_0004 SRE Agent            ← 二级：基础设施运维
│     │
│     └── EMP_0002 Platform Dev         ← 二级：平台基础设施开发
│
├── EMP_0011 Account Manager     ← 独立：品牌上下文管理，桥接品牌与内容团队
│
├── EMP_0006 斥候 Scout          ← 独立：全域情报搜集（技术/内容/电商/技术选型）
│
└── EMP_0012 Product Architect   ← 独立：产品定义、归属判断、边界管理
```

### Agent 职责速览
- EMP_0000 Meta Manager — 跨域调度，Mason 的主要 AI 对接人
- EMP_0002 Platform Dev — 平台基础设施开发（~/mason-hub/ 专属）
- EMP_0003 电商 Domain Manager — 电商行业判断和项目间协调
- EMP_0004 SRE Agent — 全局基础设施运维
- EMP_0001 素仁轩 PM — 素仁轩项目管理
- EMP_0005 电商 Dev — 电商业务开发（/opt/surenxuan/ 专属）
- EMP_0006 斥候 Scout — 全域情报搜集（技术/内容趋势/电商/技术选型）
- ~~EMP_0007 Content-Tech Domain Manager~~ — 已归档，知识沉淀到 knowledge_base.md + shared/mkt/geo-optimization.md
- EMP_0008 SocialMesh 内容运营总监 — 内容策略、发布排程、效果复盘、调度 Dev + Creator（直接向 Meta Manager 汇报）
- EMP_0009 Content-Tech Dev — 内容技术开发（~/socialmesh/ 专属）
- EMP_0010 Content Creator — 多平台内容生产、社区互动（有状态，有品牌风格记忆）
- EMP_0011 Account Manager — 品牌上下文管理，产出 brief，桥接品牌与内容团队
- EMP_0012 Product Architect — 产品参谋，需求澄清/归属判断/边界定义/迭代路径规划

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
| SocialMesh PM / 内容运营总监 | agents/EMP_0008.md | SocialMesh 内容运营 |
| Content Creator | agents/EMP_0010.md | 内容生产（~/socialmesh/ + 记忆文件） |
| Content-Tech Dev | agents/EMP_0009.md | 仅限 ~/socialmesh/ |
| Account Manager | agents/EMP_0011.md | 品牌上下文管理，跨域桥梁 |
| Product Architect | agents/EMP_0012.md | 产品定义、归属判断、边界管理 |

**加载流程**：
1. 识别自己被分配的角色名称
2. 读取对应 .md 文件的**完整内容**（不得简化）
3. 遵守该文件中定义的所有职责、边界、汇报关系
4. 在团队协作中只做自己职责范围内的事

**禁止行为**：
- 不得跨越工作目录边界
- 不得替代其他角色做决策
- 不得忽略配置文件中的"明确禁止"条款

## 基础设施 / 部署

### 阿里云 (106.14.44.68) 部署
- **推荐方式**: `skills/deploy-to-aliyun.sh --git`（使用已配好的 SSH deploy key）
- **备用方式**: `skills/deploy-to-aliyun.sh`（tar+scp，不依赖 git）
- GitHub HTTPS 被 GFW 阻断，阿里云已改用 SSH remote（git@github.com:V2-Mason/surenxuan.git）
- 后端通过 `python main.py` 运行（不是 uvicorn），kill 后会自动重启
- Python 包安装必须用 venv（PEP 668 限制）
- 阿里云没有 rsync

### GCP (34.63.188.198)
- mason-hub 和 surenxuan 都在这里开发
- SSH 能连阿里云（反向不行）
- Python 包安装同样需要 venv（~/mason-hub/.venv/）

## 快捷命令

| 命令 | 功能 |
|------|------|
| `/standup` | 晨会：git log + backlog + 系统状态 → 报告 |
| `/deploy` | 一键部署 surenxuan 到阿里云 |
| `/health` | 全局健康检查（agent + 基础设施 + 阿里云） |
| `/dev-task <描述>` | 启动 EMP_0005 执行开发任务 |
| `/scout` | 斥候情报巡逻 |

## 开发铁律（所有 Agent 必须遵守）

### 铁律 1: 完成前必须验证
- 改完代码后，**必须运行验证命令**（语法检查/测试/实际执行），不能直接说"完成"
- 验证必须是**当次新跑的**，不能引用之前的运行结果
- 禁止使用"应该没问题"、"大概可以"、"看起来对"等措辞 — 要么跑了验证，要么没跑
- 提交 commit 前必须至少跑一次 `python3 -c "import ast; ast.parse(...)"` 或等效语法检查
- 声称"测试通过"必须附带实际输出

### 铁律 2: 修 bug 必须先定位根因
- 不允许"先试试改这个看看" — 必须先追踪数据流、读错误日志、复现问题
- 每次只改一个变量，验证后再改下一个
- 连续 3 次修复失败 → 停下来，质疑是否是架构问题，不要继续硬改
- bug 修复应该附带能复现问题的测试（关键路径）

### 铁律 3: 记忆更新追加不删除
- 新内容加新条目，不替换已有条目
- 更新已有条目只改变化的部分，不重写整块
- 过时内容标注 `→ 已更新 (日期)` 而非删除
- 只有 Mason 明确说"删掉"才能删除记忆条目

### 执行检查点
- 执行多步计划时，每完成 3 个步骤暂停，向 Mason 汇报进度和结果
- 汇报内容：完成了什么、验证结果、下一步计划、发现的问题
- Mason 确认后才继续下一批

### 反"自我合理化"清单
遇到以下想法时必须停下来，不能跳过流程：
- "这个太简单了不需要测试" → 简单的代码也会出 bug
- "我很有信心" → 信心不是证据，跑一遍验证
- "就这一次跳过" → 没有例外
- "已经改了代码应该没问题" → 改了 ≠ 对了
- "Linter 过了就行" → Linter 不是编译器也不是测试
- "之前跑过一次了" → 之前 ≠ 现在

### Code Review
- Team agent 写的代码，完成后应调 code-reviewer agent 做两阶段审查
- 第一阶段：功能是否符合需求（spec review）
- 第二阶段：代码质量（命名/结构/边界处理）
- Code reviewer agent 配置：agents/code-reviewer.md

### 设计文档
- 重要架构决策必须存档到 `docs/plans/YYYY-MM-DD-<topic>.md`
- 设计文档包含：背景、方案选择、最终决策、关键约束
- 不替代 agent memory 和 backlog，但提供完整的决策上下文

## Cron 触发器（GCP 已部署）

| 时间 (CST) | Agent | 任务 |
|------------|-------|------|
| 每日 08:00 | PM (EMP_0001) | 库存巡检 |
| 每日 09:00 | SRE (EMP_0004) | 基础设施日报 |
| 每日 09:30 | cron 脚本 | agent-status-report → Slack |
| 每周二/五 14:00 | SocialMesh PM (EMP_0008) | XHS 数据采集+分析 |
| 每周一 10:00 | PM (EMP_0001) | 记忆压缩 |
| 每周日 11:00 | cron 脚本 | compact-memory.sh 全量 |
