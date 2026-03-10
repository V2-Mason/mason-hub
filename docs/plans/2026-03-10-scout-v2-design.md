# Scout v2 — Engine 架构进化方案

> 日期: 2026-03-10
> 状态: 已实现（2026-03-10）
> 参考: BettaFish (github.com/666ghj/BettaFish) 多 Engine 架构
> 原则: 保留 BettaFish 的结构，适配我们的约束（CLI / markdown / 低成本）

---

## 核心思路

BettaFish 有 5 个 Engine，每个 Engine 是一个独立的职责单元：

| BettaFish Engine | 职责 | 我们的对应物 |
|-----------------|------|-------------|
| **MindSpider** | 爬虫调度 + 话题提取 | TrendRadar + 9 Scout 脚本 + MediaCrawler |
| **QueryEngine** | 广度搜索 + 反思补搜 | scout-*.sh（但没有反思） |
| **MediaEngine** | 多模态内容理解 | XHS 分析脚本（但没有图片/视频理解） |
| **InsightEngine** | 私有数据库挖掘 | mirror SQLite + sales API + 历史情报 |
| **ForumEngine** | 多源交叉验证 | 不存在 |
| **ReportEngine** | IR → 结构化报告 | 不存在（现在是 echo 拼 markdown） |

**进化策略：不重写，而是给现有组件穿上 Engine 的骨架。**

---

## 架构映射

```
BettaFish 原版（常驻 Web 服务，5 子进程并行）:

  ┌──────────┐  ┌──────────┐  ┌───────────┐
  │QueryEngine│  │MediaEngine│  │InsightEngine│
  │(Streamlit) │  │(Streamlit) │  │(Streamlit)  │
  └─────┬─────┘  └─────┬─────┘  └──────┬──────┘
        │              │               │
        └──────────┬───┘───────────────┘
                   ▼
           ┌──────────────┐
           │ ForumEngine  │  (日志监控 + 主持人 LLM)
           └──────┬───────┘
                  ▼
           ┌──────────────┐
           │ ReportEngine │  (IR → HTML/PDF)
           └──────────────┘


Scout v2（cron 触发，串行管道，CLI 输出）:

  ┌──────────────────────────────────────────────────────┐
  │ SpiderEngine (采集调度)                                │
  │                                                      │
  │  TrendRadar (已有)     → news.db / rss.db             │
  │  9 Scout 脚本 (已有)   → intel/raw/*.md               │
  │  MediaCrawler (已有)   → mirror/sqlite_tables.db      │
  │                                                      │
  │  + TopicExtractor (新) → data/scout_topics.json       │
  │    读热榜 + RSS → LLM 提取本周话题和搜索关键词            │
  └──────────────────────────┬───────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────┐
  │ QueryEngine (搜索 + 反思)                              │
  │                                                      │
  │  scout-*.sh 初搜 (已有)                                │
  │                                                      │
  │  + ReflectionNode (新)                                │
  │    LLM 评估覆盖度 → 生成补充关键词 → 再搜一轮            │
  │    最多 1 轮补搜，输出追加到 intel/raw/                  │
  └──────────────────────────┬───────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────┐
  │ InsightEngine (内部数据挖掘)                            │
  │                                                      │
  │  + PrivateDataMiner (新)                              │
  │    读 mirror/sqlite_tables.db (XHS 笔记 167 条)       │
  │    读 sales API (素仁轩销售数据)                        │
  │    读历史情报 (intel/processed/scout_normalized.jsonl)  │
  │    LLM: "结合内部数据，这些外部情报对我们意味着什么"        │
  │    输出: 每条情报附加 internal_context 字段              │
  └──────────────────────────┬───────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────┐
  │ ForumEngine (交叉验证)                                 │
  │                                                      │
  │  + CrossValidator (新)                                │
  │    按话题聚类 → LLM 标注共识/分歧/置信度                 │
  │    单条情报标注 confidence: single_source               │
  │    输出: intel/validated/YYYY-MM-DD.jsonl              │
  └──────────────────────────┬───────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────┐
  │ ReportEngine (报告生成)                                │
  │                                                      │
  │  + ReportIR (新)                                      │
  │    validated JSONL → IR dataclass → markdown 渲染      │
  │    输出: intel/reports/YYYY-MM-DD.md                   │
  │    Slack: 🔴 级摘要推送                                │
  └────────────────────────────────────────────────────── ┘
```

---

## 目录结构进化

```
当前:
  skills/scout-*.sh          ← 9 个独立脚本，平铺
  data/pipelines/scout-normalize.py
  intel/raw/                 ← 原始情报
  intel/processed/           ← JSONL
  intel/digests/             ← 手写周报

Scout v2:
  intel/
  ├── engines/               ← 新增：Engine 代码
  │   ├── __init__.py
  │   ├── config.yaml        ← 统一配置（LLM / 阈值 / 关键词领域）
  │   ├── spider.py          ← SpiderEngine: TopicExtractor
  │   ├── query.py           ← QueryEngine: ReflectionNode
  │   ├── insight.py         ← InsightEngine: PrivateDataMiner
  │   ├── forum.py           ← ForumEngine: CrossValidator
  │   ├── report.py          ← ReportEngine: IR + 渲染
  │   └── pipeline.py        ← 管道编排（串联 5 个 Engine）
  │
  ├── raw/                   ← 不变：Scout 脚本原始输出
  ├── processed/             ← 不变：scout_normalized.jsonl
  ├── validated/             ← 新增：交叉验证后的 JSONL
  └── reports/               ← 新增：结构化周报 markdown

  skills/scout-*.sh          ← 不动：继续作为 SpiderEngine 的采集器
  tools/trendradar/          ← 不动：继续作为 SpiderEngine 的数据源
  data/mirror/               ← 不动：InsightEngine 读取
```

---

## 每个 Engine 详细设计

### SpiderEngine — 采集调度 + 话题提取

**对应 BettaFish**: MindSpider (BroadTopicExtraction + DeepSentimentCrawling)

**已有部分（不改）**:
- TrendRadar: 11 热榜 + 17 RSS，cron */30
- 9 个 scout-*.sh: GitHub API 搜索
- MediaCrawler: XHS 笔记采集

**新增: TopicExtractor**

BettaFish 用 DeepSeek 从 13 平台热榜提取 100 关键词/天，存入 daily_topics 表。
我们的版本：

```python
# spider.py — TopicExtractor

def extract_topics():
    """从 TrendRadar 热榜 + RSS 提取本周搜索话题"""

    # 1. 读 TrendRadar 最近 3 天热榜
    titles = read_trendradar_titles(days=3)  # SELECT title, source FROM entries

    # 2. 读 RSS 最近 3 天
    rss_titles = read_rss_titles(days=3)

    # 3. 读 Radar 关注率（哪些话题 Mason 在意）
    focus_rates = read_focus_rates()  # from tracker.db

    # 4. LLM 提取
    prompt = f"""从以下热榜和 RSS 标题中，提取与这些领域相关的搜索关键词：
    - 跨境电商 / 韩国护肤 / 小红书运营
    - AI 工具 / Agent 框架 / 内容自动化
    - 供应链 / 物流 / 合规

    Mason 近期关注度高的话题：{high_focus_topics}
    Mason 近期标记"无用"的话题：{dismissed_topics}

    每个关键词输出：
    {{"keyword": "...", "domain": "ecom|tech|content", "priority": "high|medium",
      "search_source": "github|web", "reason": "为什么值得搜"}}
    """

    topics = call_llm(prompt)

    # 5. 合并固定关键词（保底）+ 去重
    merged = merge_with_fixed_keywords(topics)

    # 6. 写入
    save_json("data/scout_topics.json", merged)
    return merged
```

**与 BettaFish 的差异**:
- BettaFish 每天跑，我们每周跑（情报频率不需要每天）
- BettaFish 存 MySQL，我们存 JSON 文件（够用）
- 新增：读 Radar 关注率做个性化（BettaFish 没有反馈回路到话题提取）

---

### QueryEngine — 搜索 + 反思

**对应 BettaFish**: QueryEngine (5 节点管道: 结构规划→初搜→总结→反思循环→格式化)

**已有部分（不改）**:
- 9 个 scout-*.sh 做初搜
- scout-normalize.py 做结构化

**新增: ReflectionNode**

BettaFish 的反思循环：搜完 → LLM 评估是否充分 → 不够则换关键词重搜 → 最多 N 轮。
我们的版本：

```python
# query.py — ReflectionNode

def reflect_and_supplement(raw_results: list[dict], topics: list[dict]):
    """评估搜索覆盖度，补搜盲区"""

    # 1. 按领域统计覆盖
    coverage = count_by_domain(raw_results)  # {"ecom": 5, "tech": 12, "content": 0}

    # 2. LLM 评估
    prompt = f"""本周情报搜索结果统计：
    {coverage}

    本周应覆盖的话题：
    {topics}

    请评估：
    1. 哪些领域结果充分（≥3 条）
    2. 哪些领域是盲区（0-1 条但本周有重要事件）
    3. 对每个盲区，给出 2 个精准搜索关键词

    输出 JSON: {{"covered": [...], "gaps": [{{"domain": "...", "keywords": [...]}}]}}
    """

    assessment = call_llm(prompt)

    # 3. 补搜（最多 1 轮）
    if assessment["gaps"]:
        for gap in assessment["gaps"]:
            for kw in gap["keywords"]:
                result = run_scout_search(kw, source=gap.get("source", "github"))
                append_to_raw(result)

        # 重新 normalize
        run_normalize()

    return assessment  # 传给 ReportEngine 做元数据
```

**与 BettaFish 的差异**:
- BettaFish 用 Tavily 付费搜索（6 种），我们用 GitHub API（免费）+ scout-search-topic.sh
- BettaFish 每段落多轮反思，我们整体一轮（成本控制）
- 新增：补搜结果标记 `source: "reflection"`，报告里能看出哪些是补搜来的

---

### InsightEngine — 内部数据挖掘

**对应 BettaFish**: InsightEngine（私有数据库 + 历史分析）

**这是 BettaFish 有而我们完全没有的 Engine。**

BettaFish 的 InsightEngine 挖掘私有数据库，把内部数据和外部情报关联。我们有大量内部数据没被情报系统利用：

```python
# insight.py — PrivateDataMiner

def enrich_with_internal_data(validated_items: list[dict]):
    """用内部数据给外部情报加上下文"""

    # 1. 读内部数据源
    xhs_notes = read_mirror_db("SELECT * FROM xhs_note ORDER BY create_time DESC LIMIT 50")
    sales_data = call_srx_api("/api/sales/summary")  # 已有 JWT 认证
    historical_intel = read_jsonl("intel/processed/scout_normalized.jsonl")

    # 2. 对每条情报，LLM 关联内部数据
    enriched = []
    for item in validated_items:
        prompt = f"""外部情报：
        {item['title']}: {item['summary']}

        我们的内部数据：
        - XHS 笔记库：{len(xhs_notes)} 条，最近话题：{top_xhs_topics}
        - 销售数据：{sales_summary}
        - 历史情报中相关条目：{find_related(historical_intel, item)}

        请分析：
        1. 这条情报和我们的业务有什么具体关联？
        2. 我们的数据是否验证或反驳了这条情报？
        3. 如果要行动，具体影响哪个业务环节？

        输出 JSON: {{"relevance": "high|medium|low", "internal_context": "...",
                     "action_impact": "..."}}
        """

        context = call_llm(prompt)
        item["internal_context"] = context
        enriched.append(item)

    return enriched
```

**与 BettaFish 的差异**:
- BettaFish 用 SQL 查私有数据库，我们用 SQLite mirror + API
- 新增：和历史情报关联（BettaFish 没有情报时序记忆）
- 新增：relevance 评分——不是所有情报都和我们有关，LLM 帮过滤

**这个 Engine 的价值最大**：当前 Scout 产出的情报是「通用信息」，加了 InsightEngine 后变成「对素仁轩/Mason 意味着什么」。

---

### ForumEngine — 交叉验证

**对应 BettaFish**: ForumEngine（主持人 LLM 协调多 Agent 辩论）

BettaFish 的实现其实很粗糙（日志文件通信，无真正辩论）。我们做更务实的版本：

```python
# forum.py — CrossValidator

def cross_validate(enriched_items: list[dict]):
    """多源情报交叉验证"""

    # 1. 按话题聚类
    clusters = cluster_by_topic(enriched_items)  # 相似标题归为一组

    validated = []
    for topic, items in clusters.items():
        if len(items) >= 2:
            # 2. 多源验证
            prompt = f"""关于「{topic}」有 {len(items)} 条来自不同来源的情报：

            {format_items(items)}

            作为情报分析主持人，请：
            1. 共识：多个来源一致认为什么
            2. 分歧：来源之间有什么矛盾或不一致
            3. 置信度：high（3+来源一致）/ medium（2来源一致）/ low（有矛盾）
            4. 综合判断：一句话结论

            输出 JSON
            """

            validation = call_llm(prompt)
            for item in items:
                item["confidence"] = validation["confidence"]
                item["consensus"] = validation["consensus"]
                item["dissent"] = validation.get("dissent", "")
                validated.append(item)
        else:
            # 单源情报
            items[0]["confidence"] = "single_source"
            items[0]["consensus"] = ""
            items[0]["dissent"] = ""
            validated.append(items[0])

    save_jsonl("intel/validated/YYYY-MM-DD.jsonl", validated)
    return validated
```

**与 BettaFish 的差异**:
- BettaFish 是 3 个 Agent 并行产出 → 主持人综合（进程级并行）
- 我们是单条情报多来源聚类 → LLM 综合（单进程串行）
- 更务实：不搞 SocketIO 日志通信，直接传数据结构

---

### ReportEngine — IR 报告生成

**对应 BettaFish**: ReportEngine（模板选择→章节生成→IR 组装→HTML 渲染）

```python
# report.py — ReportIR + MarkdownRenderer

@dataclass
class IntelItem:
    id: str
    title: str
    summary: str
    url: str
    priority: str           # red / yellow
    confidence: str         # high / medium / low / single_source
    relevance: str          # high / medium / low (from InsightEngine)
    internal_context: str   # InsightEngine 产出
    consensus: str          # ForumEngine 产出
    dissent: str
    source: str
    action: str
    owner: str

@dataclass
class Section:
    topic: str
    confidence: str
    items: list[IntelItem]
    consensus: str
    dissent: str
    action_summary: str

@dataclass
class ReportIR:
    date: str
    period: str                    # "2026-W11"
    sections: list[Section]        # 按话题分组，🔴 在前
    data_sources: list[str]        # 溯源列表
    search_meta: dict              # 覆盖率、补搜统计
    confidence_distribution: dict  # high: N, medium: N, ...
    total_items: int

    def render_markdown(self) -> str:
        """渲染为 Mason 阅读的 markdown 周报"""
        lines = []
        lines.append(f"# 情报周报 — {self.period}")
        lines.append(f"> 生成时间: {self.date}")
        lines.append(f"> 数据来源: {', '.join(self.data_sources)}")
        lines.append(f"> 情报总数: {self.total_items} 条")
        lines.append(f"> 置信度: {self.confidence_distribution}")
        lines.append(f"> 搜索覆盖: {self.search_meta}")
        lines.append("")

        # 🔴 高优先级
        red_sections = [s for s in self.sections
                       if any(i.priority == "red" for i in s.items)]
        if red_sections:
            lines.append("## 🔴 需要行动")
            for s in red_sections:
                lines.append(f"### {s.topic} — 置信度: {s.confidence}")
                if s.consensus:
                    lines.append(f"**共识**: {s.consensus}")
                if s.dissent:
                    lines.append(f"**分歧**: {s.dissent}")
                for item in s.items:
                    lines.append(f"- [{item.title}]({item.url})")
                    if item.internal_context:
                        lines.append(f"  **与我们的关联**: {item.internal_context}")
                if s.action_summary:
                    lines.append(f"**建议行动**: {s.action_summary}")
                lines.append("")

        # 🟡 值得了解
        yellow_sections = [s for s in self.sections
                          if s not in red_sections]
        if yellow_sections:
            lines.append("## 🟡 值得了解")
            for s in yellow_sections:
                lines.append(f"### {s.topic}")
                for item in s.items:
                    lines.append(f"- [{item.title}]({item.url}) — {item.summary[:80]}")
                lines.append("")

        # 元数据
        lines.append("## 📊 搜索元数据")
        lines.append(f"| 维度 | 数值 |")
        lines.append(f"|------|------|")
        for k, v in self.search_meta.items():
            lines.append(f"| {k} | {v} |")

        return "\n".join(lines)

    def render_slack_summary(self) -> str:
        """渲染为 Slack 推送的精简摘要（只有 🔴）"""
        ...

    def to_json(self) -> str:
        """序列化为 JSON，供下游机器消费"""
        ...
```

**与 BettaFish 的差异**:
- BettaFish: LLM 选模板 → WeasyPrint 渲染 HTML/PDF → SocketIO 流式推送
- 我们: 固定模板 → Python 字符串渲染 markdown → 写文件 + Slack
- 更简单但够用。如果未来要 HTML，加一个 `render_html()` 方法即可，IR 不用改

---

## 管道编排

```python
# pipeline.py

def run_scout_v2_pipeline():
    """Scout v2 完整管道 — 每周一深度巡逻触发"""

    config = load_config("intel/engines/config.yaml")

    # ═══ Phase 1: SpiderEngine ═══
    log("Phase 1: 采集 + 话题提取")
    topics = spider.extract_topics()              # 新增：从热榜提取关键词

    # 跑现有 scout 脚本（用新关键词）
    run_existing_scouts(topics)                    # 调用 skills/scout-*.sh

    # ═══ Phase 2: QueryEngine ═══
    log("Phase 2: 反思搜索")
    raw_results = normalize.run()                  # 已有：scout-normalize.py
    search_meta = query.reflect_and_supplement(raw_results, topics)

    # ═══ Phase 3: InsightEngine ═══
    log("Phase 3: 内部数据关联")
    enriched = insight.enrich_with_internal_data(raw_results)

    # ═══ Phase 4: ForumEngine ═══
    log("Phase 4: 交叉验证")
    validated = forum.cross_validate(enriched)

    # ═══ Phase 5: ReportEngine ═══
    log("Phase 5: 报告生成")
    ir = report.build_ir(validated, search_meta, topics)

    # 输出
    md_path = ir.render_markdown()                 # → intel/reports/YYYY-MM-DD.md
    ir.to_json()                                   # → intel/reports/YYYY-MM-DD.json

    # Slack 推送 🔴 级
    if ir.has_red_items():
        slack_notify(ir.render_slack_summary())

    log(f"完成: {ir.total_items} 条情报, {len(ir.sections)} 个话题")
```

---

## 统一配置

```yaml
# intel/engines/config.yaml

llm:
  provider: dashscope          # GCP 本地调
  model: deepseek-chat
  api_key_env: DASHSCOPE_API_KEY
  max_tokens: 4096
  temperature: 0.3             # 分析任务用低温度

spider:
  trendradar_db: ~/mason-hub/tools/trendradar/output/news/
  rss_db: ~/mason-hub/tools/trendradar/output/rss/
  lookback_days: 3
  fixed_keywords_file: data/scout_keywords_fixed.json   # 保底关键词
  domains:
    - name: ecom
      description: "跨境电商、韩国护肤、小红书运营"
    - name: tech
      description: "AI 工具、Agent 框架、Claude/Anthropic"
    - name: content
      description: "内容自动化、视频生成、社交媒体趋势"

query:
  max_reflection_rounds: 1      # 最多补搜 1 轮
  min_coverage_per_domain: 3    # 每领域至少 3 条才算覆盖

insight:
  mirror_db: data/mirror/sqlite_tables.db
  sales_api: http://106.14.44.68:8000
  historical_intel: intel/processed/scout_normalized.jsonl
  sales_auth_env: SRX_API_EMAIL,SRX_API_PASSWORD

forum:
  min_cluster_size: 2           # ≥2 条才做交叉验证

report:
  output_dir: intel/reports/
  validated_dir: intel/validated/
  slack_channel: "#scout"
```

---

## 成本估算

| Engine | LLM 调用/周 | 成本/周 | 月成本 |
|--------|------------|---------|--------|
| SpiderEngine (TopicExtractor) | 1 | ¥0.01 | ¥0.04 |
| QueryEngine (ReflectionNode) | 1 | ¥0.01 | ¥0.04 |
| InsightEngine (PrivateDataMiner) | 5-10 | ¥0.10 | ¥0.40 |
| ForumEngine (CrossValidator) | 3-5 | ¥0.05 | ¥0.20 |
| ReportEngine | 0 | ¥0 | ¥0 |
| **合计** | **10-17** | **¥0.17** | **~¥0.70** |

---

## 实施路径

按 BettaFish 的依赖顺序，从底层往上建：

| Step | Engine | 内容 | 工时 |
|------|--------|------|------|
| 1 | ReportEngine | IR dataclass + markdown 渲染，用现有 JSONL 验证 | ~2h |
| 2 | ForumEngine | 交叉验证，输出 validated JSONL | ~2h |
| 3 | SpiderEngine | TopicExtractor，从热榜提取关键词 | ~2h |
| 4 | QueryEngine | ReflectionNode，评估盲区 + 补搜 | ~2h |
| 5 | InsightEngine | 内部数据关联（mirror DB + sales API） | ~3h |
| 6 | pipeline.py + config.yaml + cron | 串联 + 注册 | ~1h |

**总计 ~12h，3-4 个 session。**

每 Step 独立可用：
- Step 1 完成 → 现有 JSONL 就能出结构化报告
- Step 1-2 完成 → 报告带置信度
- Step 1-4 完成 → 完整搜索+验证+报告（无内部数据关联）
- Step 1-5 完成 → 全部 Engine 就绪

---

## 改动范围

**不改的**:
- skills/scout-*.sh（9 个脚本）
- tools/trendradar/
- data/pipelines/scout-normalize.py
- data/mirror/
- cron 现有条目

**新增的**:
- intel/engines/ 目录（6 个 Python 文件 + 1 个 config.yaml）
- intel/validated/ 目录
- intel/reports/ 目录
- data/scout_topics.json（自动生成的关键词）

**修改的**:
- EMP_0006.md 的 weekly-deep-patrol → 改为调用 pipeline.py
- data_catalog.yaml → 注册新数据集
- CLAUDE.md cron 表 → 新增条目
