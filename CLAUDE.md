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
│     ├── EMP_0007 Content-Tech Domain Manager  ← 二级：内容技术专家 + 品牌调性审核
│     │     │
│     │     └── EMP_0008 SocialMesh 内容运营总监  ← 三级：内容策略 + 项目管理
│     │           │
│     │           ├── EMP_0010 Content Creator   ← 四级：内容生产 + 社区互动
│     │           │
│     │           └── EMP_0009 Content-Tech Dev  ← 四级：业务执行层
│     │
│     ├── EMP_0004 SRE Agent            ← 二级：基础设施运维
│     │
│     └── EMP_0002 Platform Dev         ← 二级：平台基础设施开发
│
└── EMP_0006 斥候 Scout          ← 独立：全域情报搜集（技术/内容/电商/技术选型）
```

### Agent 职责速览
- EMP_0000 Meta Manager — 跨域调度，Mason 的主要 AI 对接人
- EMP_0002 Platform Dev — 平台基础设施开发（~/mason-hub/ 专属）
- EMP_0003 电商 Domain Manager — 电商行业判断和项目间协调
- EMP_0004 SRE Agent — 全局基础设施运维
- EMP_0001 素仁轩 PM — 素仁轩项目管理
- EMP_0005 电商 Dev — 电商业务开发（/opt/surenxuan/ 专属）
- EMP_0006 斥候 Scout — 全域情报搜集（技术/内容趋势/电商/技术选型）
- EMP_0007 Content-Tech Domain Manager — 内容营销和 GEO 优化行业判断 + 品牌调性审核
- EMP_0008 SocialMesh 内容运营总监 — 内容策略、发布排程、效果复盘、调度 Dev + Creator
- EMP_0009 Content-Tech Dev — 内容技术开发（~/socialmesh/ 专属）
- EMP_0010 Content Creator — 多平台内容生产、社区互动（有状态，有品牌风格记忆）

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
| Content-Tech Manager | agents/EMP_0007.md | Content-Tech domain 决策 + 品牌审核 |
| SocialMesh PM / 内容运营总监 | agents/EMP_0008.md | SocialMesh 内容运营 |
| Content Creator | agents/EMP_0010.md | 内容生产（~/socialmesh/ + 记忆文件） |
| Content-Tech Dev | agents/EMP_0009.md | 仅限 ~/socialmesh/ |

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

### GCP (34.68.172.191)
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

## Cron 触发器（GCP 已部署）

| 时间 (CST) | Agent | 任务 |
|------------|-------|------|
| 每日 08:00 | PM (EMP_0001) | 库存巡检 |
| 每日 09:00 | SRE (EMP_0004) | 基础设施日报 |
| 每日 09:30 | cron 脚本 | agent-status-report → Slack |
| 每周一 10:00 | PM (EMP_0001) | 记忆压缩 |
| 每周日 11:00 | cron 脚本 | compact-memory.sh 全量 |
