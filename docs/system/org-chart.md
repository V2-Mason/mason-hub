# 组织架构 + Agent 加载规则

> 从 CLAUDE.md 移出。Session Operator 按需读取，不需要每条消息都带。

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
│     │     └── EMP_0013 店铺运营      ← 三级：XHS 店铺日常运营
│     │
│     │     └── EMP_0015 数据分析师    ← 三级：执行分析框架，产出业务洞察
│     │
│     ├── EMP_0008 SocialMesh 内容运营总监  ← 二级：内容策略 + 项目管理
│     │     │
│     │     ├── EMP_0010 Content Creator   ← 三级：内容生产 + 社区互动
│     │     │
│     │     └── EMP_0009 Content-Tech Dev  ← 三级：业务执行层
│     │
│     ├── EMP_0004 SRE Agent            ← 二级：基础设施运维 + 数据管道监控
│     │
│     ├── EMP_0002 Platform Dev         ← 二级：平台基础设施开发
│     │
│     └── EMP_0014 Data Engineer        ← 二级：数据中台（管道/存储/加工/目录）
│
├── EMP_0011 Account Manager     ← 独立：品牌上下文管理，桥接品牌与内容团队
│
├── EMP_0006 斥候 Scout          ← 独立：全域情报搜集（技术/内容/电商/技术选型）
│
└── EMP_0012 Product Architect   ← 独立：产品定义、归属判断、边界管理
```

## Agent 职责速览

- EMP_0000 Meta Manager — 跨域调度，Mason 的主要 AI 对接人
- EMP_0002 Platform Dev — 平台基础设施开发（~/mason-hub/ 专属）
- EMP_0003 电商 Domain Manager — 电商行业判断和项目间协调
- EMP_0004 SRE Agent — 全局基础设施运维
- EMP_0001 素仁轩 PM — 素仁轩项目管理
- EMP_0005 电商 Dev — 电商业务开发（/opt/surenxuan/ 专属）
- EMP_0006 斥候 Scout — 全域情报搜集（技术/内容趋势/电商/技术选型）
- ~~EMP_0007 Content-Tech Domain Manager~~ — 已归档
- EMP_0008 SocialMesh 内容运营总监 — 内容策略、发布排程、效果复盘
- EMP_0009 Content-Tech Dev — 内容技术开发（~/socialmesh/ 专属）
- EMP_0010 Content Creator — 多平台内容生产、社区互动
- EMP_0011 Account Manager — 品牌上下文管理
- EMP_0012 Product Architect — 产品参谋，按需激活
- EMP_0013 店铺运营 — XHS 店铺日常运营
- EMP_0014 Data Engineer — 数据中台建设与维护
- EMP_0015 数据分析师 — 执行四维判断框架+五方法论

## Agent Teams 角色加载规则

当你作为 Agent Team 的 teammate 被启动时，根据角色名称读取对应配置文件：

| 角色关键词 | 配置文件 | 工作边界 |
|-----------|---------|---------|
| Meta Manager | agents/EMP_0000/config.md | 跨 domain 协调，不直接执行 |
| 素仁轩 PM | agents/EMP_0001/config.md | 素仁轩项目管理 |
| Platform Dev | agents/EMP_0002/config.md | 仅限 ~/mason-hub/ |
| 电商 Manager | agents/EMP_0003/config.md | 电商 domain 决策 |
| SRE | agents/EMP_0004/config.md | 系统监控和运维 |
| 电商 Dev | agents/EMP_0005/config.md | 仅限 /opt/surenxuan/ |
| SocialMesh PM | agents/EMP_0008/config.md | SocialMesh 内容运营 |
| Content Creator | agents/EMP_0010/config.md | 内容生产 |
| Content-Tech Dev | agents/EMP_0009/config.md | 仅限 ~/socialmesh/ |
| Account Manager | agents/EMP_0011/config.md | 品牌上下文管理 |
| Product Architect | agents/EMP_0012/config.md | 归属判断、边界定义 |
| 店铺运营 | agents/EMP_0013/config.md | XHS 店铺日常运营 |
| Data Engineer | agents/EMP_0014/config.md | 数据中台 |
| 数据分析师 | agents/EMP_0015/config.md | 执行分析框架 |

**加载流程**：识别角色 → 读取对应 config.md 完整内容 → 遵守职责和边界

## Agent 基础设施能力

### 记忆语义搜索
- ChromaDB + all-MiniLM-L6-v2，零 API 成本
- 手动：`~/mason-hub/.venv/bin/python3 scripts/memory-search.py "查询" --scope all --format text`
- 重建：`~/mason-hub/.venv/bin/python3 scripts/memory-store.py --rebuild`

### Lane Queue（并发锁）
- 3 lane：ecommerce / socialmesh / platform
- 手动：`scripts/lane-lock.sh status` / `scripts/lane-lock.sh cleanup`

### Semantic Snapshot（网页内容提取）
- `python3 skills/semantic_snapshot.py "URL" --max-chars 6000`

## Cron 触发器（GCP）

| 时间 (ET) | Agent | 任务 |
|------------|-------|------|
| 每日 20:00 | PM (EMP_0001) | 库存巡检 |
| 每日 21:00 | SRE (EMP_0004) | 基础设施日报 |
| 每日 21:15 | cron 脚本 | 数据健康检查 → Slack |
| 每日 21:30 | cron 脚本 | agent-status-report → Slack |
| 每周二/五 10:00 | SocialMesh PM (EMP_0008) | XHS 数据采集+分析 |
| 每周一 22:00 | PM (EMP_0001) | 记忆压缩 |
| 每周三 02:00 | cron 脚本 | 自优化周期 |
| 每周日 23:00 | cron 脚本 | compact-memory.sh 全量 |
| 每月 1 日 22:00 | cron 提醒 | XHS 帮助中心文档刷新 |
