# bilibili-event-driven v0.1 hypothesis — Phase 0.5 Validation

**日期**: 2026-04-08
**Preset**: `~/.claude/skills/creator-hit-factor-grid/presets/bilibili-event-driven.md` (v0.1 hypothesis, 基于程序员鱼皮 N=1 反推)
**Validation 账号**: 何同学 + 马克的技术工作坊
**样本规格**: 每账号 N=10 (Top 5 + Bot 5), 因 Line A 已有 Top 10 转录复用
**Grid 规模**: 6 check × 10 视频 × 2 账号 = 120 格
**判定标准**: 每账号 ≥3/6 (≥50%) check 方向和 hypothesis 一致 AND 2 账号都 PASS → 升级 v1.0

---

## 1. 执行摘要

**结论**: **FAIL — 不升级 v1.0, 需要 v0.2 结构性修正**

| 账号 | 方向一致率 | 判定 |
|---|---|---|
| 何同学 | 2/6 (33%) | FAIL |
| 马克的技术工作坊 | 1/6 (17%) | FAIL |

**核心 hypothesis (4 桶 OR 命中 C1∨C2∨C3) 验证**:
- 鱼皮原始 Δ = +92% (Top 11/12 vs Bot 0/12)
- 何同学 Δ = +20% (Top 1/5 vs Bot 0/5) — 勉强正向但强度崩塌
- 马克 Δ = **-40%** (Top 1/5 vs Bot 3/5) — **完全反向, 桶命中度在马克上是 Bot 特征而非 Top 特征**

**关键发现**:
1. **C6 数字密度**在两个新账号都是强正向信号 (何同学 +80%, 马克 +60%), 但 preset 基于鱼皮标注为"常量"。这是本次 validation 最大的意外发现。
2. **C1 事件时效**在马克上强烈反向 (Bot 60% > Top 20%)。马克 Top 全是"技术讲解/原理" (Claude Code 全攻略 / LLM 到 Agent Skill / Agent 原理), Bot 才是"事件评测" (DeepSeek 之外的 o3-mini/Manus/GPT-4o/Gemini Flash)。
3. **C2 个人故事**在两个新账号全部 0 命中 (10/10 FAIL)。这两个账号都不是"宣告型个人故事"类型。
4. **C3 老 SEO 长尾**在两个新账号全部 0 命中 (10/10 FAIL)。何同学 Bot 全是 2017-2018 老视频, 年份合格但无 SEO 长尾词; 马克整个频道 2025-2026, 没有 ≥3 年陈酿。这证明 C3 是"账号历史资产 check", 不是"内容 check"。
5. **C5 IP 锚点**在马克上 0% (0/10), 说明马克视频标题/开场都没有个人签名, 是"技术知识博主" IP 弱类型, 与强 IP 型 (何同学) 差异巨大。

---

## 2. 样本列表

### 何同学 (tier2-he-tongxue, N=10)

**Top 5** (selected.tsv 前 5, views 降序, 已有转录):

| # | BV | Title | Duration | Date | Views |
|---|---|---|---|---|---|
| 1 | BV1f4411M7QC | 有多快？5G在日常使用中的真实体验 | 453s | 2019-06-06 | 33.7M |
| 2 | BV1W14y1b7Mq | 我做了一个自己打字的键盘... | 536s | 2022-08-12 | 28.3M |
| 3 | BV19v411M7Rs | 我做了苹果放弃的产品... | 467s | 2021-10-17 | 26.0M |
| 4 | BV1JDMQzUEwy | 为了不用倒垃圾，我们做了这个... | 313s | 2025-07-12 | 23.7M |
| 5 | BV1d1vUBUE54 | 我们做了台魔法钢琴… | 851s | 2026-01-01 | 21.8M |

**Bot 5** (video_list.tsv views 升序, 过滤 60 ≤ duration ≤ 7200, 无转录, based on title only):

| # | BV | Title | Duration | Date | Views |
|---|---|---|---|---|---|
| 6 | BV1TW41177Kj | 【体验】真●口叼相机？！ | 144s | 2018-02-19 | 965K |
| 7 | BV1jW411F7NP | 天生骄傲的锤子T1 为什么必然失败？ | 342s | 2018-05-11 | 1.12M |
| 8 | BV17s411g74K | 十年中最经典的5款苹果产品 | 357s | 2018-08-06 | 1.16M |
| 9 | BV1nW411r7ay | 这是全B站最黑的卧室！\| room tour | 237s | 2018-09-21 | 1.30M |
| 10 | BV1MW411b7JH | 【实拍】探密知乎总部！ | 174s | 2017-12-28 | 1.50M |

### 马克的技术工作坊 (tier2-mark-tech, N=10)

**Top 5**:

| # | BV | Title | Duration | Date | Views |
|---|---|---|---|---|---|
| 1 | BV14rzQB9EJj | Claude Code 从 0 到 1 全攻略：MCP/SubAgent/Skill/Hook... | 2684s | 2026-01-25 | 815K |
| 2 | BV1E7wtzaEdq | 从 LLM 到 Agent Skill，一期视频带你打通底层逻辑！ | 1951s | 2026-03-14 | 664K |
| 3 | BV1cGigBQE6n | Agent Skill 从使用到原理，一次讲清 | 1061s | 2025-12-31 | 467K |
| 4 | BV1TSg7zuEqR | Agent 的概念、原理与构建模式 —— 从零打造简化版 Claude Code | 1686s | 2025-07-22 | 367K |
| 5 | BV18rF8e4E9R | DeepSeek-R1 真的那么强吗？客观评测 R1 与 o1 在编程、推理方面 | 1348s | 2025-01-29 | 327K |

**Bot 5** (based on title only):

| # | BV | Title | Duration | Date | Views |
|---|---|---|---|---|---|
| 6 | BV1WhNNedE1C | o3-mini-high编程与推理能力评测 | 1062s | 2025-02-07 | 5349 |
| 7 | BV1F89QYXEgE | Manus案例深度解析 - 以及我对它的看法 | 460s | 2025-03-08 | 6872 |
| 8 | BV1KkoDYiEMj | GPT-4o 图片生成能力评测 - 史上最强文生图模型诞生 | 690s | 2025-03-28 | 7039 |
| 9 | BV1xqoqYaEyB | 把 Gemini Flash 2.0 当 PS 使用的正确方法 | 501s | 2025-03-23 | 8728 |
| 10 | BV1K4Q3Y1EBU | 使用 Cursor 和 Claude3.7 10分钟构建产品原型图和iOS应用 | 439s | 2025-03-14 | 10541 |

---

## 3. 逐格打分表 (120 格)

### 何同学 Grid (6 × 10)

| # | BV | views | C1 事件 | C2 个人故事 | C3 老SEO | C4 炫技 | C5 IP | C6 数字 |
|---|---|---|---|---|---|---|---|---|
| **Top** | | | | | | | | |
| 1 | BV1f4411M7QC | 33.7M | **PASS** 开场锚定"2019 5G 商用元年"事件 | FAIL 评测型无人生节点 | FAIL 无 SEO 长尾词 | FAIL 无反差组合 | **PASS** 标题【何同学】 | **PASS** 开场60s含 5G/4G/OPPO Reno/30公里/600兆 ≥3 |
| 2 | BV1W14y1b7Mq | 28.3M | FAIL 无外部事件 | FAIL "我做了工具"是产出型非人生转折 | FAIL 无 SEO 词 | **PASS** "自己打字的键盘"反差猎奇 | **PASS** 【何同学】 | **PASS** "小拇指/五分钟/五个小时/五十个小时" ≥3 |
| 3 | BV19v411M7Rs | 26.0M | FAIL AirPower 取消 2019 距 2021-10 超 30 天 | FAIL "我做了苹果放弃的产品"产出型 | FAIL 无 SEO 词 | **PASS** "苹果放弃的产品"反差+不可能感 | **PASS** 【何同学】 | **PASS** "两个月/四年前/2017年/5%" ≥3 |
| 4 | BV1JDMQzUEwy | 23.7M | FAIL 无外部事件 | FAIL "我们做了"产出型 | FAIL 超 2022-12-31 | **PASS** "狂奔的垃圾桶"反差+猎奇 | **PASS** 【何同学】 | **PASS** "20个/三个舵轮/12年前" ≥3 |
| 5 | BV1d1vUBUE54 | 21.8M | FAIL 无外部事件 | FAIL 产出型 | FAIL 超 2022-12-31 | **PASS** "魔法钢琴/会发光的乐器"炫技 | **PASS** 【何同学】 | **PASS** "两年/几百年来/四个原型" ≥3 |
| **Bot** | | | | | | | | |
| 6 | BV1TW41177Kj | 965K | FAIL 无触发词 | FAIL 无 | FAIL 无 SEO 词 | **PASS** "真口叼相机"猎奇 | FAIL 标题无【何同学】 | FAIL 标题无数字 |
| 7 | BV1jW411F7NP | 1.12M | FAIL 锤子T1 非 ±30 天 | FAIL 第三人称评测 | FAIL "为什么"不在 SEO 词列表 | FAIL 无 | **PASS** 【何同学】 | FAIL 标题只"T1" 1 个数字 |
| 8 | BV17s411g74K | 1.16M | FAIL 无 | FAIL 无 | FAIL "经典"不在 SEO 词列表 | FAIL 无反差 | **PASS** 【何同学】 | **PASS** "十年/5款" 2 数字, Bot 放宽阈值 |
| 9 | BV1nW411r7ay | 1.30M | FAIL 无 | FAIL 是 room tour vlog (preset 排除) | FAIL 无 SEO 词 | **PASS** "全B站最黑"反差猎奇 (参鱼皮 #10 先例) | **PASS** 【何同学】 | FAIL 标题无数字 |
| 10 | BV1MW411b7JH | 1.50M | FAIL 无 | FAIL 无 | FAIL 无 SEO 词 | **PASS** "探密知乎总部"类"揭秘"C4 信号 | FAIL 标题无【何同学】 | FAIL 无数字 |

### 马克 Grid (6 × 10)

| # | BV | views | C1 事件 | C2 个人故事 | C3 老SEO | C4 炫技 | C5 IP | C6 数字 |
|---|---|---|---|---|---|---|---|---|
| **Top** | | | | | | | | |
| 1 | BV14rzQB9EJj | 815K | FAIL 标题无触发词, 是"全攻略"教程 | FAIL 无 | FAIL 超 2022-12-31 | FAIL "从0到1全攻略"是教程非炫技 | FAIL 无马克签名, 开场无自称 | **PASS** 开场"第一/第二/第三/第四部分"4 数字 |
| 2 | BV1E7wtzaEdq | 664K | FAIL Agent Skill 发布距 2026-03 约 5 月 | FAIL 无 | FAIL 超 | FAIL 是概念讲解 | FAIL 无 | **PASS** "2017年/2022年底/GPT3.5/GPT4/2023" ≥3 |
| 3 | BV1cGigBQE6n | 467K | FAIL 标题无触发词 (开场有 12-18 开放标准事件但 preset PASS 判据要求标题触发词) | FAIL 无 | FAIL 超 | FAIL 概念讲解 | FAIL 无 | **PASS** "2025年10月16号/12月18日/几个部分" ≥3 |
| 4 | BV1TSg7zuEqR | 367K | FAIL 无 | FAIL 无 | FAIL 超 | FAIL "打造简化版 Claude Code"是教程产出非炫技 | FAIL 无 | FAIL 开场60s数字不足 3 个 |
| 5 | BV18rF8e4E9R | 327K | **PASS** 标题"DeepSeek-R1"产品名+事件, 发布距视频 9 天, 开场"最近被刷爆"强锚定, 类比鱼皮 #1"快手事件"模式 | FAIL 无 | FAIL 超 | FAIL 客观评测非炫技 | FAIL 无 | **PASS** "16元/438元/4%/几十分之一" ≥3 |
| **Bot** | | | | | | | | |
| 6 | BV1WhNNedE1C | 5349 | **PASS** o3-mini 发布 2025-01-31 距 2025-02-07 = 7 天, 标题含产品事件 | FAIL 无 | FAIL 超 | FAIL 评测 | FAIL 无 | FAIL 标题只"o3"1 数字 |
| 7 | BV1F89QYXEgE | 6872 | **PASS** Manus 发布 2025-03-06 距视频 2 天, 标题含产品事件 | FAIL "我的看法"非人生节点 | FAIL 超 | FAIL 解析非炫技 | FAIL 无 | FAIL 标题无数字 |
| 8 | BV1KkoDYiEMj | 7039 | **PASS** GPT-4o 图片生成 2025-03-26 距视频 2 天, 产品事件 | FAIL 无 | FAIL 超 | FAIL 评测非炫技 | FAIL 无 | FAIL 标题"4o"1 数字 |
| 9 | BV1xqoqYaEyB | 8728 | FAIL 是"正确方法"教程非事件报道 | FAIL 无 | FAIL 超 | **PASS** "把 X 当 PS 使用"反差应用 | FAIL 无 | FAIL 标题"2.0"1 数字 |
| 10 | BV1K4Q3Y1EBU | 10541 | FAIL 是实操教程非事件 (Claude 3.7 只是工具) | FAIL 无 | FAIL 超 | FAIL "10 分钟 iOS 应用"是实用教程, preset 明确排除 | FAIL 无 | **PASS** "3.7/10 分钟/一行" ≥3 |

---

## 4. 命中率 + Δ + 方向一致率

### 何同学 Check-by-Check

| Check | Top 5 PASS | Bot 5 PASS | Δ (Top−Bot) | 实际方向 | Hypothesis 方向 | 一致? |
|---|---|---|---|---|---|---|
| C1 事件时效 | 1/5 (20%) | 0/5 (0%) | +20% | 正向 (弱) | 正向 | **✓** |
| C2 个人故事 | 0/5 (0%) | 0/5 (0%) | 0% | 常量 | 正向 | ✗ |
| C3 老 SEO | 0/5 (0%) | 0/5 (0%) | 0% | 常量 | 正向 | ✗ |
| C4 炫技创意 | 4/5 (80%) | 3/5 (60%) | +20% | 正向 (弱) | 正向 | **✓** |
| C5 IP 锚点 | 5/5 (100%) | 3/5 (60%) | +40% | 正向 (强) | 常量 | ✗ |
| C6 数字密度 | 5/5 (100%) | 1/5 (20%) | **+80%** | 正向 (极强) | 常量 | ✗ |

**何同学方向一致率**: **2/6 = 33%** → FAIL (未达 ≥50% 门槛)

### 马克 Check-by-Check

| Check | Top 5 PASS | Bot 5 PASS | Δ (Top−Bot) | 实际方向 | Hypothesis 方向 | 一致? |
|---|---|---|---|---|---|---|
| C1 事件时效 | 1/5 (20%) | 3/5 (60%) | **-40%** | **反向 (强)** | 正向 | ✗ |
| C2 个人故事 | 0/5 (0%) | 0/5 (0%) | 0% | 常量 | 正向 | ✗ |
| C3 老 SEO | 0/5 (0%) | 0/5 (0%) | 0% | 常量 | 正向 | ✗ |
| C4 炫技创意 | 0/5 (0%) | 1/5 (20%) | -20% | 反向 (弱) | 正向 | ✗ |
| C5 IP 锚点 | 0/5 (0%) | 0/5 (0%) | 0% | 常量 | 常量 | **✓** |
| C6 数字密度 | 4/5 (80%) | 1/5 (20%) | **+60%** | 正向 (强) | 常量 | ✗ |

**马克方向一致率**: **1/6 = 17%** → FAIL (严重失败)

---

## 5. 桶命中度 Hypothesis 验证

**核心 hypothesis**: Top 视频 C1∨C2∨C3 至少命中 1 桶的比例远高于 Bot (鱼皮 +92%)

### 何同学

| Bucket | N | C1∨C2∨C3 ≥1 命中数 | 比例 |
|---|---|---|---|
| Top | 5 | 1 (仅 #1 5G 通过 C1) | 20% |
| Bot | 5 | 0 | 0% |
| **Δ** | | | **+20%** |

vs 鱼皮 +92%: **强度崩塌 72 个百分点**, 勉强正向但不足以支撑"多桶并行"hypothesis。

### 马克

| Bucket | N | C1∨C2∨C3 ≥1 命中数 | 比例 |
|---|---|---|---|
| Top | 5 | 1 (仅 #5 DeepSeek 通过 C1) | 20% |
| Bot | 5 | 3 (#6 o3-mini, #7 Manus, #8 GPT-4o 都通过 C1) | 60% |
| **Δ** | | | **-40%** |

vs 鱼皮 +92%: **完全反向**, 桶命中度在马克上是 Bot 的特征而非 Top 的特征。Hypothesis **在马克账号上完全不成立**。

### 桶命中度结论

**核心 hypothesis 证伪**:
- 何同学: 强度从 +92% 崩到 +20%, 虽然方向正确但量级不够, 属于边缘观察
- 马克: **方向完全颠倒** (-40%), 说明"事件时效桶"对于马克不是爆款因子而是普通因子。马克的爆款来自"深度技术讲解/基础概念原理", 事件评测型视频反而停留在 Bot。

**关键 insight**: 鱼皮的"事件/个人故事/老 SEO 三桶 OR 命中"模型是**鱼皮账号的个性化特征**, 不是"事件型 dev UP 主"的通用规律。具体:
- 何同学是"炫技猎奇制作 + 数字密集开场"型, 不是"事件/个人/老 SEO"型
- 马克是"深度技术讲解/系列长尾"型, 爆款逻辑更接近"狗勾型系列长尾" (尽管赛道是 AI/编程而非宠物)

---

## 6. 判定结果

**Validation**: **FAIL**
- 何同学 2/6 = 33% < 50% → FAIL
- 马克 1/6 = 17% < 50% → FAIL
- 核心桶命中度 hypothesis 在马克上完全反向
- **preset 不能升级 v1.0**

**archetype 错分诊断**: bilibili-event-driven v0.1 假定 "何同学/马克/未生 AI/Geek4Fun" 是"事件型 dev UP 主"同 archetype, validation 证明:
- 鱼皮 ≠ 何同学 (不同 archetype, 何同学是"高制作 vlog + 数字开场")
- 鱼皮 ≠ 马克 (完全不同, 马克是"系列长尾技术讲解")
- 三个账号是三个独立 archetype, 不能共用一个 preset

---

## 7. v0.2 修正建议

### 选项 A: 拆分成多个 preset (推荐)

本次 validation 证明原 hypothesis "4 桶 OR 命中" 不是跨账号规律, 应拆分:

1. **`bilibili-yupi-specific.md`** (鱼皮专用, 退为 account-specific):
   - 保留 C1/C2/C3/C4 四桶, 明确只适用于鱼皮本人
   - 不再假装是通用 event-driven preset
   - 标记 "N=1 single sample, not generalizable"

2. **`bilibili-he-tongxue-style.md`** (何同学型, 高制作 vlog):
   - 新 hypothesis: **C6 数字密度 (强)** + **C4 炫技反差**(弱) + **C5 IP 锚点**(强)
   - 预期 hit factor: 开场 60s 高数字密度 + 标题含"做了 X 猎奇物"反差
   - 再做 N=1 dogfood (用当前 5+5 做初步支持), 然后找第二个高制作 vlog UP 主做 validation

3. **`bilibili-series-tech-explainer.md`** (马克型, 深度技术讲解):
   - 新 hypothesis: 类似狗勾型系列长尾, C6 数字密度 (强) + "系列/讲清/原理/全攻略"标题词 + 时长 >15 分钟
   - 与 `bilibili-series-evergreen.md` (狗勾型) 对比, 看能否统一

### 选项 B: 修正 v0.1 的 hypothesis 为 "C6 数字密度 + 必要条件" (弱推荐)

如果一定要保留一个"跨 archetype" preset:

- **删除 C1/C2/C3** (三桶 hypothesis 在 2/2 validation 都失败)
- **删除 C4** (在何同学上弱正向, 在马克上反向, 不稳定)
- **删除 C5** (在何同学 +40% 但马克 0%, 不稳定)
- **保留 C6 数字密度** 作为**唯一强信号** (何同学 +80%, 马克 +60%, 2/2 账号方向一致强度大)
- 加入新 check:
  - C7 开场 60s 结构: 何同学的"问题+数字锚"模式 vs 马克的"产品+事件"模式
  - C8 时长区间: 马克 Top 都是 1000-2700s, Bot 都是 460-1100s, 时长可能是一个 hit factor

**问题**: 只有 1 个 check 的 preset 几乎无区分度, 且"数字密度"本身是辅助因子 (鱼皮+伦巴已知强度不同), 单独使用会回到 `bilibili-creator.md` 伦巴型的路径上。

### 选项 C: 放弃 preset, 改做 archetype 分类器 (长期方向)

把 `bilibili-event-driven.md` v0.1 标记为 **反面教材**, 收入 `~/vault/learnings/single-sample-dogfood-pitfall.md`, 说明 **"N=1 反推 hypothesis 即使在 preset 作者眼里很自洽, validation 也会崩"**, 强化"先 archetype 聚类再写 preset"的方法论。

### 推荐方向

**选项 A** (拆分成多个 preset) + **选项 C** (教训归档) 并行:

1. **立即**: 将 v0.1 标注为 **"DEPRECATED — validation FAILED, 详见 event_driven_v0_1_validation.md"**
2. **立即**: 把鱼皮 `bilibili-gougou-specific.md` 旧 preset 思路复用, 新写 `bilibili-yupi-specific.md` (account-specific, 不假装通用)
3. **next session**: 对何同学和马克的数据重新 cluster, 看能否提炼出"高制作 vlog"和"系列技术讲解"两个新 archetype
4. **归档**: Lesson 写入 vault, 强化 Phase 0.5 validation 的必要性 (如果跳过这次 validation, 会直接拿 v0.1 跑 N=97 何同学全量, 浪费大量 token 才发现失灵)

---

## 8. Validation 过程的方法论观察

1. **硬门控起效**: 即使 Mason 已经看过 preset "看起来很漂亮", 按 Phase 0.5 严格走 120 格打分才发现核心 hypothesis 完全反向。信心不能替代数据。
2. **Bot 5 无转录限制**: C6 打分对 Bot 是"标题 ≥2 个数字"放宽判据, 这会让 Bot C6 命中率被高估。如果严格按"开场60s ≥3 个数字", Bot 的 C6 命中率可能更低, Δ 会更大。但当前判据已经足以证明 C6 是强信号。
3. **C1 判据歧义**: 严格按 "标题含触发词" 会让很多"产品名+时效"的视频 FAIL (马克 Top 3 Agent Skill 的 12-18 开放标准就是这种情况)。preset 的"定义"段允许开场锚定, "PASS 判据"段又要求标题触发词, 这个歧义在 v0.2 必须明确。
4. **C3 对新账号结构性失败**: 何同学 2018 老视频年份合格但无 SEO 长尾词, 马克整个频道 <2 年没有老视频。C3 是"账号历史红利"而非"内容质量", 对新账号结构性全 FAIL。preset 在"重要边界"段已经声明, 但这导致 C3 在 validation 中几乎无信息量。

---

## 附: Raw Data 参考

- 何同学 Top 5 转录: `tier2-he-tongxue/full_text.txt` lines 2-1160 (5 个 BV 段落)
- 马克 Top 5 转录: `tier2-mark-tech/full_text.txt` lines 2-3755 (5 个 BV 段落)
- 何同学 Bot 5: 无转录, title only from `tier2-he-tongxue/video_list.tsv`
- 马克 Bot 5: 无转录, title only from `tier2-mark-tech/video_list.tsv`

**报告生成**: 2026-04-08 by preset-validation subagent
**Git**: 不 commit (validation 只读 + 写报告)
