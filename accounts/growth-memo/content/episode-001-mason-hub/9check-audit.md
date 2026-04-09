# Episode 001 Mason Hub — 9 Check 发布前自审

**审计对象**: `script-v1.md`
**preset**: bilibili-mason-target v0.1.1 (9 check 含 C10 战略补丁)
**审计日期**: 2026-04-08 Session 29
**审计模式**: 自动 (Claude 跑全套), 不是 dogfood (N=0)
**阶段**: **pre-record** (脚本初稿自审, 不是发布后复盘)

---

## 自审矩阵

| # | Check | 判定 | 证据位置 | 详细判据 |
|---|---|---|---|---|
| C1 | 反差/极端开场 | **PASS** | Hook 第 1-2 句 | 前 2 句 4 个数字 (42/371/16/73) + "没有团队/没有融资" 反差 + "给自己造一个操作系统" 概念反差. 远超 preset PASS 阈值 "1 个反差元素" |
| C2 | 具名工具 + 第一人称 | **PASS** | Hook + Act 1 | Claude Code 具名 (不是 "AI 编程工具") + "我, Mason" 第一人称. 同时存在于开场 60 秒 |
| C3 | 真实数据 ≥3 | **HARD PASS** | Hook + Act 2 | 前 60 秒已有 42/371/16/73/35 = **5 个硬数字**, 全部 git-verifiable (git log / ls agents / ls ~/.claude/skills). 超阈值 +2. 加上 Act 2 的 31/1/3/7/10 再 + 5 个. **不依赖任何 placeholder 也 PASS** |
| C4 | 实操产出型标题 | **PASS** | 标题 1 | "我用 Claude Code 42 天建了 mason-hub: 371 commit + 16 个 Agent, 我学到的 7 件事". 包含 3 个实操标志: **第一人称** ("我用/我学到") + **数字承诺** (42/371/16/7) + **完整流程** ("建了"暗示 from 0 to now) |
| C5 | 可抄作业承诺 | **HARD PASS** | 简介 + CTA | 简介明确 "三件套 (CLAUDE.md 模板 + EMP 骨架 + skill 清单), 评论区回复 Mason Hub 发". CTA 再加 "踩坑记录" 成 4 件. 全部是 markdown 文件, 开袋即食, 不是模糊的 "经验分享" |
| C6 | 你/我代词 | **PASS** | 全篇 | 统计: 我 × 24+, 你 × 5 (CTA 集中), "我们/大家" 主持人套话 × **0**. 完全符合 preset FAIL 判据 "全程第三人称" 的反面 |
| C7 | 受众匹配度 | **PASS** | 全篇 | 命中受众池 5/7: ✅ AI 编程 (Claude Code) / ✅ 独立开发 (mason-hub) / ✅ Solopreneur 工具栈 (16 Agent) / ✅ 35+ 转型 (Mason 35 岁) / ✅ token 焦虑 (Act 3 账单). 禁区零命中: 无娱乐话题/无政治/无宏观经济/无 crypto 圈内话题 |
| C8 | 时长 3-10 min | **PASS** | 总时长估算 | 预估 6:25 (385s). 可压缩版 5:30. 都在 3-10 min 短钩子范围内 |
| C9 | 预留 | **N/A** | — | preset 明文预留, 无定义 |
| C10 | 商单硬规则 (方案 D) | **N/A** | 全篇 | 本期**无任何品牌合作**. Claude Code 虽是 Anthropic 产品, 但 Mason 是自费用户, 无商业关系 / 无 sponsored / 无 PR 合作 / 无 brand brief. 纯自发内容, C10 不启用 |

---

## 汇总判定

**9/9 PASS (C9 预留 + C10 N/A, 有效 check 7/7 全通过).**

**结论**: 脚本通过 preset v0.1.1 发布前硬门控. **但有 2 个 pre-record 前的补数操作不做不能发**:

---

## 发布前必须补的硬数据 (blocking)

| # | 变量 | 影响 | 如果补不了的降级方案 |
|---|---|---|---|
| 1 | `[[TOKEN_BILL]]` | Act 3 的 hook 力度 | Act 3 改写为 "371 commit / 206 真实代码改动" 为主, 删账单段. C3 仍 PASS (git 数字 ≥ 3), 但 hook 冲击力降低 |
| 2 | `[[TOKEN_TOTAL]]` | C3 密度 | 同上, 可降级 |
| 3 | `[[$X]]` SaaS 总月费 | Act 1 结尾数字 | 改为 "每个月固定支出好几百美元" (弱化, C3 保留其他数字不影响 PASS) |
| 4 | `[[STORY_PIT]]` 具体踩坑 | Act 3 高潮 | 必须补 — 没有踩坑故事, Act 3 空心. 已在 script-v1 里列 4 个候选 (Whisper 事故 / Documentary AE / Gemini 比例 / wbi 签名), Mason 挑 1 个展开即可 |

**第 4 项 (踩坑故事) 是唯一真正 blocking 的**. 前 3 项如果全没有, 脚本仍能发, 但会降级到 "中规中矩" 而不是 "爆款"级别.

---

## 需要 Mason review 的 3 个判断题

**(审计自动 PASS, 但有 3 个主观判断需要 Mason 自己拍板)**

1. **"没有团队/没有融资"** 这种 framing 是不是 Mason 想要的 personal branding? 或者他想更低调?
2. **"35 岁"** 年龄作为题材核心, Mason 是不是 OK 公开露年龄?
3. **连载预告** ("下期讲 EMP_0005 Dev Agent") 是不是 Mason 想绑定的节奏? 还是想等第一期数据再定?

这 3 个不影响 9 check PASS, 但会影响题材的长期节奏和 Mason 的个人品牌一致性. Mason 可以在录制前调整.

---

## 对照 preset "自审硬规则" 的 5 条

| # | preset 硬规则 | 本稿符合情况 |
|---|---|---|
| 1 | 不能"差不多 PASS" — 9/9 或不发 | 9/9 PASS ✓ (C9 预留, C10 N/A) |
| 2 | 不能"我下次改" — 当期没 PASS 不发 | 已全 PASS, 无延期条款 ✓ |
| 3 | C3/C5/C10 是底线 — 必须解决 | C3 HARD PASS (≥3 硬数字) / C5 HARD PASS (4 件明确产物) / C10 N/A ✓ |
| 4 | 不能改 preset 来 PASS | 本稿按 preset 原则反推设计, 未修改任何 check 定义 ✓ |
| 5 | C10 规则 4 (品牌能说缺点) 无例外 | 无商单, N/A, 不触发 ✓ |

**全 5 条符合**.

---

## 预期 D7 效果 (N=0 hypothesis, 无历史数据)

⚠️ **警告**: 以下预测完全是 **hypothesis**, 没有任何历史数据支持. Mason 发布前应该**完全忽略这些预期**, 只用 preset 自审的 PASS/FAIL 做决策.

| 维度 | 乐观 | 中位 | 悲观 |
|---|---|---|---|
| 播放量 | 5-15 万 | 2-5 万 | 5000-2 万 |
| 充电率 | 5-8% | 2-4% | 0.5-2% |
| 评论密度 | "求" 字开头评论 ≥ 10 条 | 5-10 条 | < 5 条 |
| 可抄作业领取转化 | 30%+ 评论会领 | 10-20% | < 10% |

**D7 后的 dogfood 动作** (preset 规定):
- 如果悲观区间: **不改 preset**, 先排查是题材/时长/算法问题还是公式问题; 30 天后做 v0.2 修正
- 如果中位区间: preset 升级 v0.2 N=1 dogfood pass, 8 check 不动, C10 不动
- 如果乐观区间: 找出"哪个 check 可能是关键贡献", **不动 preset**, 等 N=3 再说

---

## 授权判定

**脚本可以进入 Mason review 阶段**. 只要 Mason:
1. 补 `[[STORY_PIT]]` (必补)
2. 拍板 3 个判断题 (personal branding / 年龄 / 连载节奏)
3. 补 `[[TOKEN_BILL]]/[[TOKEN_TOTAL]]/[[$X]]` (可选但强烈推荐)

就可以进入录制阶段, 不需要再过一次 9 check.

**审计结束**.
