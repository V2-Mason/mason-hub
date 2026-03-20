# 执行引擎设计 — Agent ≠ LLM Session

> 日期: 2026-03-19
> 决策者: Mason
> 状态: 设计中
> 触发: restaurant-ops项目中发现的架构认知升级

## 背景

在设计restaurant-ops（餐厅代运营自动化）时，产生了一个关键问题：

> "如果agent需要24/7自动运行，Max Plan的Claude Code能用吗？还是必须用API？"

这个问题暴露了mason-hub当前架构中一个未被明确的假设：**每个agent任务都需要LLM**。

## 当前模型

mason-hub的dispatcher已经通过`claude -p`一次性session实现了自动化：

```
dispatcher.sh (cron每小时)
  → 扫描backlog
  → 过四道安全门
  → run-agent.sh → claude -p "执行任务..."
  → 写汇报
```

**这个模型的隐含假设：每个任务 = 一次claude -p调用 = 一次LLM session。**

### 当前模型的问题

| 问题 | 影响 |
|------|------|
| GCP 3.8G内存，每个session ~500MB | 并发限制，每次只能跑1个任务 |
| 每个任务都启动LLM session | 很多任务其实不需要LLM |
| Max Plan使用条款灰色地带 | `claude -p`自动化调用可能有合规风险 |
| 每次session无状态 | 重复加载context，浪费token/时间 |
| 无法区分轻重任务 | 数据采集和策略分析用同样的执行方式 |

## 核心认知升级

**Agent = 组织角色 + 决策规则 + 在必要时调用LLM**

不是：Agent = LLM Session

大部分agent的大部分工作不需要LLM：

| Agent | 需要LLM的工作 | 不需要LLM的工作 |
|-------|-------------|---------------|
| EMP_0005 电商Dev | 复杂bug分析、代码review | 格式化、lint、测试执行、部署 |
| EMP_0004 SRE | 异常根因分析 | health check、cron管理、日志轮转 |
| EMP_0014 Data Engineer | 数据质量异常分析 | 数据同步、格式转换、管道执行 |
| EMP_0010 Content Creator | 内容生成、选题策划 | 排期发布、图片裁剪 |
| EMP_0006 斥候Scout | 趋势分析、竞品解读 | 爬虫执行、数据采集 |
| EMP_0013 店铺运营 | 定价建议、活动策划 | 库存检查、订单处理、数据录入 |

## 新设计：三层执行引擎

```
┌─────────────────────────────────────────────────┐
│                mason-hub 组织架构                 │
│   (agents.yaml / protocols / authority / memory)  │
│                   不变                            │
└──────────────────────┬──────────────────────────┘
                       │
         ┌─────────────┼──────────────────┐
         │             │                  │
   确定性执行层      LLM判断层          交互层
   (Python/Bash)    (API调用)       (Claude Code)
         │             │                  │
   - 定时任务      - 内容生成         - Mason审核
   - 数据同步      - 异常根因分析      - 策略讨论
   - health check  - 评论分类回复      - 架构决策
   - 格式转换      - 报告叙述生成      - 新任务定义
   - 规则引擎      - 趋势分析
   - API调用       - 代码review
   - 文件操作
         │             │                  │
    24/7自动跑      按需调用           Mason在时
    成本: $0       成本: 按token      成本: Max Plan
```

### 确定性执行层（Deterministic Layer）

**不需要LLM的任务，用纯Python/Bash执行。**

```
dispatcher.sh
  ├── 任务类型 = "script" → 直接执行Python/Bash脚本
  │     不启动claude -p，零LLM成本
  │     适用：数据采集、health check、文件操作、规则引擎
  │
  └── 任务类型 = "llm_required" → 调用LLM判断层
```

改造点：在`autonomous_tasks.yaml`中给每个任务加`execution_type`字段：

```yaml
- id: health-check
  agent: EMP_0014
  execution_type: script          # ← 新字段
  script: "bash data/pipelines/data_health_check.sh"
  llm_fallback: false             # 失败也不需要LLM

- id: content-generate
  agent: EMP_0010
  execution_type: llm_required    # ← 需要LLM
  llm_backend: api_sonnet         # 用哪个模型
  llm_budget: 0.05                # 单次预算上限（美元）

- id: review-analysis
  agent: EMP_0013
  execution_type: hybrid          # ← 数据采集不需要，分析需要
  script: "python scripts/collect_reviews.py"  # 先跑脚本
  llm_trigger: "script_output_not_empty"       # 有数据才调LLM
  llm_backend: api_haiku
```

### LLM判断层（LLM Judgment Layer）

**只有需要"判断"的工作才调用LLM。**

两种调用方式：

| 方式 | 适用场景 | 成本 |
|------|---------|------|
| API (anthropic SDK) | 自动化调用、24/7、批量处理 | 按token |
| Claude Code (`claude -p`) | Mason在时的复杂任务 | Max Plan |

**模型选择原则：**

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 分类/标签（评论分类、情感分析） | Haiku | 快、便宜，简单判断够用 |
| 内容生成（文案、报告） | Sonnet | 质量和成本平衡 |
| 复杂推理（根因分析、策略） | Opus 或 Claude Code | 需要深度思考 |

### 交互层（Interactive Layer）

**Mason在电脑前时，用Claude Code (Max Plan)。**

适用：
- 需要Mason判断的决策项
- 新任务的定义和拆解
- 架构设计讨论
- 复杂调试

## 对现有组件的改造

### dispatcher.sh 改造

```bash
# 当前逻辑（所有任务都走claude -p）:
run-agent.sh $AGENT_ID "$TASK_DESCRIPTION"

# 新逻辑（按execution_type分流）:
case $EXECUTION_TYPE in
  "script")
    # 直接执行脚本，不启动LLM
    bash "$SCRIPT_PATH"
    ;;
  "llm_required")
    # 调用API（不是claude -p）
    python scripts/llm_execute.py --task "$TASK_ID" --backend "$LLM_BACKEND"
    ;;
  "hybrid")
    # 先跑脚本，有输出再调LLM
    OUTPUT=$(bash "$SCRIPT_PATH")
    if [ -n "$OUTPUT" ]; then
      python scripts/llm_execute.py --task "$TASK_ID" --input "$OUTPUT"
    fi
    ;;
  "interactive")
    # 等Mason在时用Claude Code处理
    echo "$TASK_ID" >> /data/pending_interactive.txt
    ;;
esac
```

### autonomous_tasks.yaml 改造

每个任务增加执行配置：

```yaml
execution:
  type: script | llm_required | hybrid | interactive
  script: "path/to/script.sh"      # script和hybrid类型必填
  llm_backend: api_haiku | api_sonnet | api_opus | claude_code
  llm_budget: 0.05                  # 单次预算上限（美元）
  llm_trigger: "条件表达式"          # hybrid类型：什么时候需要LLM
  batch_eligible: true              # 能否和其他任务合并batch调用
```

### agents.yaml 改造

每个Agent增加执行偏好：

```yaml
agents:
  EMP_0005:
    name: 电商Dev
    execution_profile:
      primary_mode: script           # 主要执行方式
      llm_usage: low                 # LLM使用频率 low/medium/high
      preferred_backend: api_haiku   # 大部分判断用haiku够了
      interactive_tasks:             # 这些任务走交互层
        - "架构设计"
        - "复杂bug调试"

  EMP_0010:
    name: Content Creator
    execution_profile:
      primary_mode: llm_required     # 内容生成必须LLM
      llm_usage: high
      preferred_backend: api_sonnet
      batch_eligible: true           # 可以攒一周的内容一起生成
```

## 成本估算

### 当前模型（全部claude -p）
- 每小时dispatcher跑一次 → 每天~14次
- 每次启动一个claude -p session → 不确定Max Plan的合规边界
- 内存限制导致只能串行

### 新模型（三层分流）
| 层 | 任务占比 | 成本 |
|----|---------|------|
| 确定性层 | ~60% | $0 |
| LLM判断层 | ~25% | $10-50/月（主要用haiku/sonnet） |
| 交互层 | ~15% | Max Plan（已有） |

**预估月度API成本：$20-50，随业务规模线性增长但增速慢。**

## 进一步优化：Batch模式

对于不紧急的LLM任务，可以攒起来批量处理：

```
每小时检查 → 积累LLM任务到queue
每天2次（9AM/6PM）→ 批量执行LLM任务
紧急任务（危机关键词等）→ 立即执行
```

好处：
- 减少API调用次数（overhead）
- 可以合并相似任务（如"分析5条评论" vs 分别分析5次）
- Mason在的时候可以用Claude Code批量处理，省API费

## 与restaurant-ops的关系

restaurant-ops是第一个按这个新模型设计的联邦节点：

```
restaurant-ops Pipeline → 三层执行引擎
├── 内容发布（定时排期）→ 确定性层（纯Python）
├── 数据采集（各平台API）→ 确定性层（纯Python）
├── 异常检测（规则引擎）→ 确定性层（纯Python）
├── 内容生成 → LLM判断层（API Sonnet）
├── 评论分类+回复 → LLM判断层（API Haiku）
├── 月报生成 → LLM判断层 或 交互层
└── 广告策略调整 → 交互层（Mason参与）
```

如果验证成功，可以反向应用到mason-hub现有的所有agent。

## 实施计划

### Phase 1: 标记（1h）
- [ ] 给autonomous_tasks.yaml的每个任务加execution_type
- [ ] 给agents.yaml的每个agent加execution_profile

### Phase 2: dispatcher分流（2-3h）
- [ ] dispatcher.sh支持按execution_type分流
- [ ] 新增llm_execute.py（封装API调用）
- [ ] 新增pending_interactive.txt（等Mason处理的任务队列）

### Phase 3: restaurant-ops验证（随项目推进）
- [ ] restaurant-ops按三层模型运行
- [ ] 记录实际API成本
- [ ] 验证哪些任务真的需要LLM

### Phase 4: 全局推广（Phase 3验证后）
- [ ] 将现有agent任务迁移到新模型
- [ ] 减少不必要的claude -p调用
- [ ] 成本和效率对比报告

---

## 关键认知

> **Agent的价值在于组织架构（谁做什么、怎么协调），不在于是否每步都用LLM思考。**
>
> 一个成熟的Agent系统，大部分工作是确定性代码在跑，LLM只在需要"判断"时介入。
> 这不是降级，是进化 —— 从"所有事都需要AI想"到"AI只在该想的时候想"。
