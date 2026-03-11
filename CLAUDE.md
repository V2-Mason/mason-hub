# Mason Hub — 工作规范

## 授权边界（所有 Agent 必读）

**必须在 session 启动时读取 `MASON_AUTHORITY.md` + `SYSTEM_MAP.md`**：
- `MASON_AUTHORITY.md` — 什么可以自主做、什么必须问 Mason
- `SYSTEM_MAP.md` — 当前系统受力分析（四条能力线状态 + 耦合 + 推荐行动）

核心规则：
- 授权范围内 → 直接做完，commit 记录
- 授权范围外 → 收集所有待决策项，一次性问，不要逐个打断
- 3 步以上的任务 → 先输出执行计划确认单，Mason 说"执行"后再动手

## Token 消耗记录规范
- 每次 Claude API 调用必须经过 api_logger.log_api_call() 记录
- 日志路径：~/mason-hub/logs/api_usage.jsonl
- 每日 01:00 ET (05:00 UTC) 自动生成消耗报告到 #system-alerts
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
- EMP_0012 Product Architect — 产品参谋，按需激活，帮 Mason 问对问题（归属判断/边界定义），不主动扫描不管理
- EMP_0013 店铺运营 — XHS 店铺日常运营（客服/评分/售后/合规/对账）
- EMP_0014 Data Engineer — 数据中台建设与维护（管道/存储/加工/目录/SDK）
- EMP_0015 数据分析师 — 执行四维判断框架+五方法论，持续产出分析结论

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
| Product Architect | agents/EMP_0012.md | 按需激活，归属判断、边界定义（不管理、不审计） |
| 店铺运营 | agents/EMP_0013.md | XHS 店铺日常运营（客服/评分/售后/合规/对账） |
| Data Engineer | agents/EMP_0014.md | 数据中台（管道/存储/加工/目录/SDK） |
| 数据分析师 | agents/EMP_0015.md | 执行分析框架，产出业务洞察 |

**加载流程**：
1. 识别自己被分配的角色名称
2. 读取对应 .md 文件的**完整内容**（不得简化）
3. 遵守该文件中定义的所有职责、边界、汇报关系
4. 在团队协作中只做自己职责范围内的事

**禁止行为**：
- 不得跨越工作目录边界
- 不得替代其他角色做决策
- 不得忽略配置文件中的"明确禁止"条款

## Agent 基础设施能力（所有 Agent 共享）

### 1. 记忆语义搜索
所有通过 `run-agent.sh` 启动的 agent 自动获得跨 agent 语义记忆召回能力。
- 底层：ChromaDB + all-MiniLM-L6-v2 本地向量索引，零 API 成本
- 索引范围：所有 agent 的 long_term.md + lessons + decisions + 全局记忆（共 134 个文档块）
- 自动触发：每次 agent 启动时根据任务描述搜索 top-5 相关记忆注入 context
- 手动搜索：`~/mason-hub/.venv/bin/python3 scripts/memory-search.py "查询内容" --scope all --format text`
- 重建索引：`~/mason-hub/.venv/bin/python3 scripts/memory-store.py --rebuild`
- 自动维护：每周日 compact-memory.sh 后自动增量更新索引

### 2. Lane Queue（并发锁）
防止同域 agent 并发操作导致竞态条件。通过 `run-agent.sh` 自动获取/释放。
- 3 个 lane：`ecommerce`（EMP_0001/0003/0005/0013）、`socialmesh`（EMP_0008/0009/0010）、`platform`（EMP_0002/0004/0014）
- 跨域 agent（Meta Manager/Scout/Account Manager/Product Architect）不需要锁
- 锁自动超时释放（默认 20 分钟），agent 崩溃不会死锁
- 链式执行自动继承锁（PM → Dev 不会重复获取）
- 手动查看：`scripts/lane-lock.sh status`
- 手动清理：`scripts/lane-lock.sh cleanup`

### 3. Semantic Snapshot（网页内容提取）
将网页转换为紧凑 markdown，比原始 HTML 压缩 10x+，节省 token。
- 用法：`python3 skills/semantic_snapshot.py "URL" --max-chars 6000`
- 三种模式：article（文章提取）、table（表格保留）、interactive（aria tree 解析）
- `--no-js`：不启动浏览器，用 requests+BeautifulSoup（更快更轻）
- `--json`：输出带元数据的 JSON（URL/标题/压缩率/提取模式）
- 已注册到 EMP_0001/0006/0008/0013 的 skills 列表

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
| `/commit` | 智能提交：先更新 backlog + 记忆 + lesson，再 git commit |
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

### 铁律 4: 收工必须写 Lesson（2026-03-09 Mason 指定）
- 每个 Agent session 结束前，**必须**更新自己的记忆文件（`agents/memory/EMP_XXXX/long_term.md` 或 `lessons.md`）
- **必须使用标准格式**：参照 `shared/templates/lesson_format.md`
- 记录内容：本次做了什么、发现了什么、踩了什么坑、backlog 有什么过时
- **Gap 类型是强制字段** — 不勾选就不算 lesson 写完：
  - 🔧 配置错误 → 立刻修
  - 🏗️ 系统能力缺失 → 填触发动作，EMP_0012 triage
  - 📄 文档更新 → 更新对应文件
  - 🔗 集成缺失 → 填触发动作，EMP_0012 triage
  - 📚 纯知识 → 留存即可
- 🏗️ 和 🔗 类型必须填写触发动作（任务描述 + 建议 Owner + 验收条件），EMP_0000 晨会检查后 ping EMP_0012
- Team agent 模式下，每个 teammate 关闭前必须写 lesson，team lead 负责检查
- Session Operator 在 sprint 结束后汇总各 agent lesson 到全局 MEMORY.md
- **不写 lesson 就不能关闭 agent** — shutdown_request 前 team lead 应确认 lesson 已写入且 gap 类型已勾选

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

| 时间 (ET) | Agent | 任务 |
|------------|-------|------|
| 每日 20:00 | PM (EMP_0001) | 库存巡检 |
| 每日 21:00 | SRE (EMP_0004) | 基础设施日报 |
| 每日 21:15 | cron 脚本 | 数据健康检查 → Slack |
| 每日 21:30 | cron 脚本 | agent-status-report → Slack |
| 每周二/五 10:00 | SocialMesh PM (EMP_0008) | XHS 数据采集+分析 |
| 每周一 22:00 | PM (EMP_0001) | 记忆压缩 |
| 每周三 02:00 | cron 脚本 | 自优化周期（读数据→Gate 1→分析→Gate 2→Slack） |
| 每周日 23:00 | cron 脚本 | compact-memory.sh 全量 |
| 每月 1 日 22:00 | cron 提醒 | XHS 帮助中心文档刷新提醒 → Slack（手动触发） |
