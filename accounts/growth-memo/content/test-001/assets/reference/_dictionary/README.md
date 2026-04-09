# Mason 需求词典 (Needs Dictionary)

**位置**: `accounts/growth-memo/content/test-001/assets/reference/_dictionary/`
**用途**: 跨 session 的需求挖掘记忆库, 让评论挖掘从"一次性劳动"变成"可循环工作流"
**建立日期**: 2026-04-08 (在 round2 开始前建立)

---

## 为什么需要这个

**之前的问题:**
- 每次挖需都是从零开始
- 不知道哪些关键词已经用过
- 不知道哪些视频已经爬过评论
- 评论丢失了原始来源 (哪条评论来自哪个关键词/账号)
- AUDIENCE_PERSONAS.md 一次性生成, 无法增量迭代

**这个词典的目标:**
1. **持久化** — 每次挖需的数据永久沉淀
2. **可溯源** — 每条评论能追到它是从哪里来的
3. **去重** — 下次挖掘时不会重复爬同一视频
4. **自举** — 每轮挖需产生下一轮的候选词 (backlog)
5. **增量** — AUDIENCE_PERSONAS 可以从 v1.0 → v2.0 → v3.0 滚动升级

---

## 4 个核心文件

### 1. `keywords.json` — 关键词池
所有用过的关键词 + 每个词的挖掘历史 + 信号质量评估

### 2. `videos.json` — 视频索引
所有已爬过评论的视频 (BV 号 + 标题 + 播放量 + 来源 + 已收集评论数)
**作用**: 去重 + 溯源

### 3. `comments_raw.jsonl` — 评论原始数据
所有爬到的评论, append-only, 每行一条, 带完整元数据:
```json
{"id": "c001", "bvid": "BV...", "like": 100, "content": "...", "crawled": "2026-04-08", "round": "round2", "source_keyword": "AI 编程", "source_account": null}
```

### 4. `needs_model.md` — 需求模型
从评论里提炼出的"需求清单", 人类可读, 可滚动迭代

---

## 目录结构

```
_dictionary/
├── README.md               ← 本文件
├── keywords.json           ← 关键词池 (jsonl 保证 append 安全)
├── videos.json             ← 视频索引
├── comments_raw.jsonl      ← 评论原始数据 (append-only)
├── needs_model.md          ← 需求模型 (滚动迭代)
├── backlog_next_round.md   ← 下一轮候选 (自举)
└── rounds/                 ← 每一轮的独立产出快照
    ├── 2026-04-06_round1_summary.md
    ├── 2026-04-08_round2_summary.md
    └── ...
```

---

## 工作流: 每一轮挖需的 6 步

```
Step 1: READ
  读 keywords.json / videos.json / needs_model.md / backlog_next_round.md

Step 2: PLAN
  从 backlog 里提取本轮候选
  过滤已用过的 (noise) 关键词
  决定本轮的新路径参数

Step 3: MINE (run mine_evidence.py)
  每爬一条评论立刻 append 到 comments_raw.jsonl
  每搜一个视频立刻 update videos.json
  每关键词跑完 update keywords.json

Step 4: ANALYZE
  从本轮新评论聚类
  发现新需求 / 强化旧需求的置信度

Step 5: MERGE
  新发现 → needs_model.md 加新段
  旧发现 → 更新置信度 + 追加证据

Step 6: BACKLOG
  从本轮新需求提取"未被饱和挖掘"的方向
  写入 backlog_next_round.md
  供下次 round 读取
```

**核心设计原则:**
- 每一轮**增量** (不是重做)
- **backlog_next_round.md 是自举引擎** — 每轮的终点是下一轮的起点
- **comments_raw.jsonl 永不删除** — 只追加, 保证溯源

---

## Round 历史

| Round | 日期 | 关键词数 | 视频数 | 评论数 | 产出 |
|---|---|---|---|---|---|
| round1 | 2026-04-06 | 16 | 301 | 272 | AUDIENCE_PERSONAS.md v1.0 |
| round2 | 2026-04-08 | TBD | TBD | TBD | (进行中) |

---

## 版本

- **v0.1** (2026-04-08) — 词典骨架建立, 开始导入 round1 历史数据
