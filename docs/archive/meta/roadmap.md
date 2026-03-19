# Mason Hub Agent System — 完整演化路线图

**Version:** 1.1
**Date:** 2026-02-27
**Author:** Mason × Claude
**覆盖范围:** 从今天的讨论中提取的所有待办事项、架构决策、和未来方向

---

## 目录

1. 当前系统状态总览
2. 已完成的工作
3. 立即要做的事（端到端验证）
4. 短期待办（1-2 周内）
5. 中期待办（1-3 个月）
6. 长期演化方向（3-6 个月）
7. 架构决策记录
8. 关键文件路径索引

---

## 1. 当前系统状态总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Mason Hub Agent System                         │
│                                                                    │
│  ✅ QA 闭环 (commit ff51bc5)                                      │
│     check-syntax → run-backend-tests → dev-verify-loop             │
│     run-agent.sh bash 层强制验证，最多 3 轮自动修复                  │
│                                                                    │
│  ✅ 四层 Escalation (commit b2c6962)                               │
│     Dev → PM → Platform Dev → Mason                               │
│     PM 最多 2 次重新分配，SRE 横向监控                              │
│                                                                    │
│  ✅ OpenClaw 能力升级 (commit 4b687b7)                             │
│     细粒度执行历史 | 经验记忆层 | 链式触发                           │
│                                                                    │
│  ✅ EMP_0006 斥候 Agent (commit 5d40b08)                           │
│     角色文件 + 4个scout skills + intel目录 + 首次巡逻完成            │
│                                                                    │
│  ⏳ 记忆系统统一（设计完成，待落地）                                  │
│  ❌ 端到端真实任务验证（从未执行过）                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent 状态

| Agent | 角色 | 状态 | Skills |
|-------|------|------|--------|
| EMP_0000 | Meta Manager | ✅ 已更新（含 Escalation 架构总览） | — |
| EMP_0001 | PM | ✅ 已更新（含失败评估、ACTION 输出、重试限制） | check-escalation, run-acceptance-tests, run-backend-tests |
| EMP_0002 | Platform Dev | ✅ 已更新（含 Escalation 接收） | check-syntax, run-backend-tests, dev-verify-loop |
| EMP_0003 | 电商 Domain Manager | ⏳ 角色文件已存在，skills 待定 | — |
| EMP_0004 | SRE | ✅ 已更新（含全局监控 + 链式触发监控） | run-smoke-tests, health-check-full, agent-doctor |
| EMP_0005 | 电商 Dev | ✅ 已更新（含 Escalation 规则 + 经验记录） | check-syntax, run-backend-tests, dev-verify-loop |
| EMP_0006 | 斥候 Scout | ✅ 已创建 + 首次巡逻完成 | scout-github, scout-trending, scout-anthropic, scout-search-topic |

---

## 2. 已完成的工作

### 2.1 QA 闭环（8 个组件）

| 组件 | 文件 | 状态 |
|------|------|------|
| 语法检查 | skills/monitoring/check-syntax.sh | ✅ |
| 后端测试（自动服务管理） | skills/dev-tools/run-backend-tests.sh | ✅ |
| 冒烟测试（阿里云端点） | skills/dev-tools/run-smoke-tests.sh | ✅ |
| 三层验证循环 | skills/dev-tools/dev-verify-loop.sh | ✅ |
| 健康检查 | skills/monitoring/health-check-full.sh | ✅ |
| 验收测试 | skills/dev-tools/run-acceptance-tests.sh | ✅ |
| 文件→测试映射 | skills/dev-tools/test-map.json | ✅ |
| 系统诊断 | skills/monitoring/agent-doctor.sh | ✅ |

### 2.2 四层 Escalation

| 层级 | 机制 | 限制 |
|------|------|------|
| Layer 0: Dev | 3 轮自动修复，bash 强制 | 最多 3 轮/次 |
| Layer 1: PM | 评估分流（A-E 五种类型），check-escalation.sh | 最多 2 次重新分配 |
| Layer 2: Platform Dev | 同 Dev 的 3 轮验证 | 最多 3 轮 |
| Layer 3: Mason | Slack 通知，人工决策 | 无限制 |

最坏情况自动消耗上限：~15 次 claude -p 调用，~216k tokens

### 2.3 OpenClaw 能力升级（Phase 1-3）

| Phase | 内容 | 关键实现 |
|-------|------|---------|
| Phase 1 | 细粒度执行历史 | 每轮 I/O 保存到 logs/tasks/，summary.json 汇总 |
| Phase 2 | 经验记忆层 | lessons.md append-only，bash 注入 prompt，50KB 限制 |
| Phase 3 | 链式触发 | ACTION 输出解析，Dev→PM→Dev 自动循环，CHAIN_DEPTH=10 |

### 2.4 EMP_0006 斥候 Agent

| 组件 | 状态 |
|------|------|
| 角色文件 agents/EMP_0006/config.md | ✅ 已创建 |
| skills/scout/scout-github.sh | ✅ 已创建并测试 |
| skills/scout/scout-trending.sh | ✅ 已创建并测试 |
| skills/scout/scout-anthropic.sh | ✅ 已创建并测试 |
| skills/scout/scout-search-topic.sh | ✅ 已创建并测试 |
| intel/{raw,digests,archive}/ 目录 | ✅ 已创建 |
| intel/watchlist.md | ✅ 已创建（8 项） |
| 首次巡逻 W09 digest | ✅ 已完成并发送 Slack #scout |

### 2.5 设计文档（已产出）

| 文档 | 内容 | 状态 |
|------|------|------|
| agent-system-upgrade-plan.md | 三个 Phase 的完整实施细节 | ✅ 已执行 |
| EMP_0006_scout_design_v2.md | 斥候 agent 设计（含信息流架构） | ✅ 已落地 |

---

## 3. 立即要做的事

### 3.1 🔴 端到端真实任务验证

**优先级：最高。所有架构都还停留在"理论上能跑"的阶段。**

**目标：** 用一个真实业务任务从头到尾跑一次完整链路，验证：
- run-agent.sh 能正确启动 Dev agent
- Dev 改代码后自动跑验证循环
- 验证通过时正确输出 + 记录审计日志 + 记录经验
- 验证失败时正确触发修复循环（最多 3 轮）
- 3 轮都失败时正确恢复代码 + 审计 + 触发 PM

**理想的第一个测试任务：**
- 有明确的代码改动
- 有对应的测试覆盖
- 改动范围小（万一出问题容易回滚）
- 例如：修一个已知的小 bug，或给某个模块加一个简单功能

**验证清单：**

```
□ Dev agent 启动成功
□ 代码改动被正确执行
□ dev-verify-loop.sh 自动运行
□ logs/tasks/ 下生成了 round input/output 文件
□ summary.json 正确生成
□ audit.jsonl 新增记录（含 task_log_dir）
□ lessons.md 追加了经验（成功或失败）
□ Slack 通知发送成功

如果测试失败：
□ 修复循环正确执行（最多 3 轮）
□ git checkout 恢复代码
□ 链式触发 PM 评估（如果启用）
```

### 3.2 处理 GCP 上的未提交改动

agent-doctor 报告显示 warning：
- ~/mason-hub 有未提交改动

**待处理：**
- 审查未提交改动
- 决定 commit 还是 stash
- 保持 git 状态干净，为端到端测试做准备

---

## 4. 短期待办（1-2 周内）

### 4.1 共享知识层激活

**问题：** 原始设计中的 knowledge_base.md 和 decisions.md 存在但没被读取，因为依赖 agent 主动读文件。

**解决方案：** 在 run-agent.sh 中加 case 语句，按 agent 角色自动注入对应层级的知识文件。

```bash
case "$AGENT_ID" in
  "EMP_0005")  # Dev: 项目级 + domain 级
    inject_if_exists "domains/ecommerce/knowledge_base.md"
    inject_if_exists "projects/srx/decisions.md"
    ;;
  "EMP_0001")  # PM: domain 级 + meta 级
    inject_if_exists "domains/ecommerce/knowledge_base.md"
    inject_if_exists "meta/knowledge_base.md"
    ;;
  "EMP_0000")  # Meta Manager: meta 级
    inject_if_exists "meta/knowledge_base.md"
    inject_if_exists "meta/business_principles.md"
    ;;
esac
```

**工作量：** 改 run-agent.sh ~20 行。成本低，价值高——释放原始设计的共享知识能力。

### 4.2 渐进式披露：Slack 汇报加 Level 2 摘要

**问题：** 现在任务汇报只有两种状态——一句话的 Slack 通知（太少）或 audit.jsonl 里的原始 JSON（太多）。缺少中间层。

**解决方案：** Dev agent 完成任务后，Slack 消息包含结构化摘要：

```
✅ 任务 FIX-042 完成
📝 改动：routes/report.py (+12 -3), utils/date.py (+5 -1)
🧪 验证：语法 ✓ | 模块测试 8/8 ✓ | 回归 24/24 ✓
⏱️ 耗时：1 轮通过，47 秒
💰 Token：12.3k
```

失败时：
```
⚠️ 任务 FIX-042 修复失败（PM 第 1/2 次分配）
📝 尝试改动：routes/report.py (+8 -2)
❌ 失败点：模块测试 test_report.py::test_date_range — TypeError
🔄 3 轮尝试均失败，代码已恢复
📋 根因推测：date_range 函数被多模块共享
```

**工作量：** 改 run-agent.sh 的 Slack 通知逻辑 ~30 行。

### 4.3 Slack 频道规划

当前可能只有 #srx-dev 一个频道。需要创建：

| 频道 | 用途 | 谁发 | 谁看 |
|------|------|------|------|
| #srx-dev | Dev 任务通知、验证结果 | EMP_0005, run-agent.sh | Mason, PM |
| #mason-alerts | 紧急事项、Escalation 到 Mason 的通知 | 所有 agent | Mason |
| #scout | 情报简报 | EMP_0006 | EMP_0000, Mason |

---

## 5. 中期待办（1-3 个月）

### 5.1 记忆系统统一

**问题：** 系统中有两套记忆设计（原始三层架构 + Phase 2 lessons），大部分原始设计没有生效。需要统一。

**融合架构：**

```
Layer 1（执行历史，已实现）：
  audit.jsonl + logs/tasks/ — 不注入 prompt，供 PM/SRE 读取

Layer 2（文件记忆，✅ 已实现）：
  lessons.md — 个人经验，bash 注入（✅ 已实现）
  knowledge_base.md — 共享知识，bash 注入（✅ 已激活 commit 9885082）
  decisions.md — 项目决策，bash 注入（✅ 已激活 commit 9885082）

Layer 3（语义搜索，✅ 已实现）：
  ChromaDB + sentence-transformers（~/mason-hub/.venv/）
  memory-store.py 写入 / memory-search.py 查询
  run-agent.sh 自动判断：lessons >10KB 时用 Layer 3，否则 Layer 2
  当 Layer 3 不可用时 fallback 到 Layer 2 全量注入
```

**触发 Layer 3 的信号：**
- lessons.md 超过 10KB
- 全量注入导致 token 消耗明显升高
- Agent 频繁"忘记"之前踩过的坑

**技术选型：**
- 向量数据库：ChromaDB（轻量级，Python，本地运行）
- 嵌入模型：all-MiniLM-L6-v2（~25MB，本地运行，不需要 API）
- 实现方式：Python 脚本（memory-search.py + memory-store.py），bash 调用

**关键设计原则：** 任何记忆机制都必须是 bash 层面强制注入的，不依赖 agent 自觉执行。可靠性优先于灵活性。

### 5.2 记忆衰减（Compaction）— 来自 Beads 的启发

**问题：** lessons.md 和 audit.jsonl 会随时间无限增长。旧经验淹没新经验，token 消耗持续升高。

**设计（参考 Beads 的 semantic memory decay）：**

信息随时间逐步衰减——近的详细，远的概要：

```
新鲜（7 天内）：完整保留
  ## 2026-02-27: test_report 模块
  - 这个模块的测试需要数据库里至少有 3 条 product 记录
  - conftest.py 的 seed_data fixture 可以解决这个问题
  - 修改 routes/report.py 时注意 date_range 参数可能为 None
  - 第一次修改时忘了处理 None 导致 TypeError
  - 第二轮修复后发现 sales 模块也用了同一个函数

中期（7-30 天）：保留关键信息
  ## 2026-02-20: test_report 模块
  - 需要 seed 数据（≥3 条 product）
  - date_range 可能为 None
  - 与 sales 模块共享函数，改动需谨慎

远期（30 天+）：AI 总结替换
  ## [COMPACTED] test_report: 需要seed数据,date_range可能None,与sales模块共享函数
```

**实现：** ✅ skills/agent-ops/compact-memory.sh 已创建
- 输入：agent ID（或 all）+ --dry-run
- 按日期阈值分类 sections（7d/30d）
- 中期用 claude -p 压缩为关键信息
- 远期用 claude -p 压缩为单行 [COMPACTED]
- 同时归档 logs/tasks/ 超过 30 天的文件到 logs/archive/
- audit.jsonl 超过 500 行时分离旧记录到 archive/
- SRE (EMP_0004) skills 已添加 compact-memory

### 5.3 上下文预算机制 — 来自 Beads `bd ready` 的启发

**问题：** 随着知识库和经验积累，全量注入 prompt 的 token 成本越来越高。Agent 不需要所有信息，只需要与当前任务相关的信息。

**设计（渐进式披露在 prompt 注入中的应用）：**

```bash
MAX_CONTEXT_TOKENS=4000  # 经验 + 知识的 token 预算

# 按优先级注入，超出预算时从低优先级开始裁剪
Priority 0（必须）: 当前任务描述
Priority 1（高）:   语义相关的经验（top-5）或 compact 后的 lessons
Priority 2（中）:   本模块近期 decisions
Priority 3（低）:   共享 knowledge_base
Priority 4（最低）: 全局架构原则
```

**触发信号：** 当 prompt 总 token 超过模型上下文窗口的 30% 时。

### 5.4 EMP_0003 电商 Domain Manager 增强

**角色定位：** 电商业务线的管理者，负责：
- K-Beauty 行业情报搜集（上传到 #scout）
- 业务需求拆解和优先级排序
- 管理 EMP_0005 (Dev) 的业务方向
- 与斥候 (EMP_0006) 协作提供行业上下文

**优先级：** 在端到端验证稳定后增强

### 5.5 SRE Agent 增强 — ✅ 已实现

- ✅ agent-status-report.sh 已创建（7 section 报告：调用统计、失败列表、token 趋势、记忆状态、skills 健康、系统资源、任务日志）
- ✅ compact-memory.sh 已加入 SRE skills
- ✅ agent-doctor.sh 已在 skills 中（之前实现）
- EMP_0004 skills: run-smoke-tests, health-check-full, agent-doctor, agent-status-report, compact-memory

---

## 6. 长期演化方向（3-6 个月）

### 6.1 任务依赖图 — 来自 Beads 的启发

**问题：** 当前任务是扁平的——PM 分配一个任务给 Dev，Dev 做完或失败。没有任务之间的依赖关系。

**Beads 的思路：** 维护任务之间的 DAG（有向无环图），支持 blocks、related、parent-child、discovered-from 四种依赖类型。Agent 在启动时查询 `bd ready`（没有阻塞项的任务），立即知道该做什么。

**对你的系统的价值：**
- PM 评估失败时，能看到"这个任务失败了，而且它阻塞了另外 3 个任务"
- Dev 开始任务时，知道哪些前置任务已经完成
- 任务可以有层次：Epic → Task → Sub-task

**可能的实现路径：**
- 选项 A：直接用 Beads CLI（`bd init` + `bd create` + `bd ready`）
- 选项 B：自建简化版（JSONL 存储任务依赖，shell 脚本查询）
- 选项 C：在 audit.jsonl 中加 task dependency 字段

**评估时机：** 当任务数量和复杂度增长到手动管理困难时

### 6.2 从 run-agent.sh 迁移到 Claude Code 原生 Agent 系统

**信号：** 当你发现 run-agent.sh 越来越难维护，每次加新功能都要改 bash 逻辑，链式触发的 edge case 越来越多。

**前提条件：**
- Claude Code 原生 agent 系统成熟（session 管理、hooks、plugin 分发）
- MCP 在 agent 调用中可用（解锁 claude-mem 等语义搜索能力）
- everything-claude-code 等生态工具稳定

**迁移意味着：**
- 不再需要 run-agent.sh 的 bash 层强制验证（原生 hooks 替代）
- 不再需要链式触发的 bash 逻辑（原生 agent-send 替代）
- 不再需要手动注入 prompt（原生 context injection 替代）

**风险：** 过早迁移会让你在两个不成熟的系统之间挣扎

### 6.3 多语言情报能力（斥候扩展）

- 韩语来源：韩国美妆行业新闻
- 中文来源：国内电商政策、行业报告
- 需要评估翻译能力或多语言搜索

### 6.4 完全自主运营（Phase 4 愿景）

```
Mason 设定战略方向
  → Meta Manager 拆解为季度目标
    → Domain Managers 规划执行策略
      → PM 拆解任务
        → Dev 执行 + 自动验证
          → 斥候持续搜集情报
            → SRE 全局监控
              → Mason 只在 Layer 3 介入

24/7 运行，Mason 从 "operator" 变为 "approver"
```

---

## 7. 架构决策记录

### D-001: bash 层强制优于 agent 自觉

**决策：** 所有关键流程（验证循环、记忆注入、Escalation 触发）在 bash 层面强制执行，不依赖 agent "记得"要做。

**理由：** Agent 在 claude -p 单次调用中可能跳过角色文件里写的步骤。bash 强制保证可靠性。

**代价：** 灵活性受限。Agent 不能动态决定跳过或调整验证步骤。

### D-002: append-only 记忆而非可读写记忆

**决策：** Agent 只能向自己的 lessons.md 追加内容，不能修改或删除。角色文件（EMP_*.md）不可被 agent 修改。

**理由：** 防止 agent 改错自己的"大脑"。OpenClaw 允许 agent 修改自己的 SKILL.md，但这在无人值守的环境中有风险。

**代价：** Agent 不能"忘记"错误的经验。需要人工清理。用 compaction 机制部分缓解。

### D-003: 链式触发而非实时 session 通信

**决策：** Agent 间通信通过 run-agent.sh 递归调用（链式触发），不搞实时 session 通信。

**理由：** 不需要 gateway 基础设施。每次调用是独立的 claude -p，token 消耗可计算、可限制。

**代价：** 每次 agent 切换都丢失对话上下文。需要通过 audit.jsonl 和 task logs 传递上下文。

### D-004: PM 重试次数限制

**决策：** PM 对同一任务最多重新分配给 Dev 2 次。超过后强制 escalate 给 Platform Dev。

**理由：** 防止 token 黑洞。不加限制的话，PM 可能反复把任务丢回 Dev，每次消耗 3 轮 × API token。

**总计上限：** Dev 9 轮 + PM 3 次 + Platform Dev 3 轮 = ~15 次调用后必定交给 Mason。

### D-005: 行业情报由 Domain Manager 搜集，不由斥候搜集

**决策：** 斥候 (EMP_0006) 只负责技术/工具情报 + 汇聚/交叉分析。行业细分领域的情报由对应的 Domain Manager 搜集。

**理由：** Domain Manager 懂行业上下文，搜集的情报质量更高。斥候的核心价值是跨域关联，不是每个领域都懂一点。

### D-006: 记忆衰减（Compaction）设计

**决策：** 参考 Beads 的 semantic memory decay，对 lessons.md 和 audit.jsonl 做时间维度的渐进式衰减。

**规则：**
- 7 天内：完整保留
- 7-30 天：保留关键信息
- 30 天+：AI 总结替换，标记 [COMPACTED]

**理由：** 解决 lessons.md 无限增长和 token 消耗问题。核心信息保留，细节随时间衰减。

### D-007: 上下文预算机制

**决策：** run-agent.sh 注入 prompt 时设置 token 预算，按优先级分层注入，超出预算从低优先级裁剪。

**理由：** 来自 Beads 的 `bd ready` 思想——只给 agent 它现在需要的信息。渐进式披露在 prompt 注入中的应用。

---

## 8. 关键文件路径索引

### Agent 角色文件
```
~/mason-hub/agents/
  EMP_0000.md — Meta Manager
  EMP_0001.md — PM
  EMP_0002.md — Platform Dev
  EMP_0003.md — 电商 Domain Manager
  EMP_0004.md — SRE
  EMP_0005.md — 电商 Dev
  EMP_0006.md — 斥候 Scout ✅
```

### Skills 脚本
```
~/mason-hub/skills/
  # QA 闭环
  check-syntax.sh           ✅
  run-backend-tests.sh      ✅
  run-smoke-tests.sh        ✅
  dev-verify-loop.sh        ✅
  health-check-full.sh      ✅
  run-acceptance-tests.sh   ✅
  agent-doctor.sh           ✅
  check-escalation.sh       ✅
  test-map.json             ✅

  # 斥候情报
  scout-github.sh           ✅
  scout-trending.sh         ✅
  scout-anthropic.sh        ✅
  scout-search-topic.sh     ✅

  # 运维
  compact-memory.sh         ✅ (5.2 记忆衰减)
  agent-status-report.sh    ✅ (5.5 SRE 全局状态报告)
```

### 记忆系统
```
~/mason-hub/memory/
  EMP_0005_lessons.md — Dev 经验          ✅
  EMP_0002_lessons.md — Platform Dev 经验  ✅
  chroma_db/          — 向量数据库        ✅

~/mason-hub/scripts/
  memory-store.py     — ChromaDB 写入      ✅
  memory-search.py    — ChromaDB 语义搜索  ✅

~/mason-hub/meta/
  knowledge_base.md   — 全局知识库        ✅ (待注入激活)
  business_principles.md — 业务原则       ⏳
  roadmap.md          — 本文件            ✅

~/mason-hub/domains/ecommerce/
  knowledge_base.md   — 电商领域知识库    ✅ (待注入激活)
```

### 日志系统
```
~/mason-hub/logs/
  audit.jsonl          — 任务级审计日志    ✅
  tasks/               — 每轮详细日志      ✅
    {task_id}_round{N}_input.txt
    {task_id}_round{N}_output.json
    {task_id}_summary.json
  archive/             — 归档              ⏳
```

### 情报系统
```
~/mason-hub/intel/
  raw/                 — 原始情报          ✅
  digests/             — 情报简报          ✅ (W09 已生成)
  archive/             — 归档              ✅
  watchlist.md         — 关注列表(8项)     ✅
```

### 基础设施
```
~/mason-hub/scripts/
  run-agent.sh         — 核心：agent 调度 + 验证循环 + 链式触发

~/surenxuan/           — 电商系统代码（GCP 开发环境）
~/surenxuan/backend/tests/
  test_smoke.py
  conftest.py
  pytest.ini
```

### Git 仓库
```
代码真相源：git@github.com:V2-Mason/surenxuan.git
开发环境：GCP (mason-hub at 34.63.188.198)
生产环境：阿里云 106.14.44.68（SSH 待修复）
```

---

## 附录 A：外部参考项目评估

| 项目 | Stars | 与 Mason Hub 的关系 | 可用时机 |
|------|-------|---------------------|----------|
| OpenClaw | — | 参考了记忆设计、NEVER 规则、进度汇报 | 已借鉴完毕 |
| everything-claude-code | 53.6k | Claude Code 配置合集，迁移后可集成 | 现在可个人使用，迁移后全面集成 |
| Beads (steveyegge) | 17.4k | git-backed 任务图 + 记忆衰减 | 参考了 compaction 思想，考虑直接用 CLI |
| claude-mem | 31.3k | MCP 语义搜索记忆 | 等 MCP 在 -p 模式可用时评估 |
| claude-plugins-official | 8.5k | Anthropic 官方插件目录 | 🔴 立即调研 |
| Claude Agent SDK | 5.0k | 原生 agent 编排 | 🔴 评估迁移路径 |
| claude-forge | 250 | oh-my-zsh for Claude Code | 🔴 架构对标参考 |

## 附录 B：渐进式披露在系统中的应用点

| 应用点 | 设计 | 状态 |
|--------|------|------|
| Escalation 信息量 | 成功时一句话，失败时逐层展开 | ✅ 自然存在 |
| Slack 汇报层次 | Level 1 通知 → Level 2 摘要 → Level 3 完整日志 | ✅ format_slack_message() |
| 记忆注入 | 相关经验 → 模块 decisions → 共享知识 → 全局原则 | ✅ 预算控制 + Layer 3 |
| 记忆衰减 | 新鲜完整 → 中期保留关键 → 远期 AI 总结 | ✅ compact-memory.sh |
| SRE 监控 | 状态总览 → 告警摘要 → 详细分析 | ✅ agent-status-report.sh |
| Agent 角色加载 | 简单任务轻量 prompt → 复杂任务完整 prompt | ⏳ 长期 |
