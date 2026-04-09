# Episode 001 — Topic Decision (方案 D 下的新选题)

**决策日期**: 2026-04-08 (Session 29)
**决策者**: Claude 自主 (Mason 授权 autonomous mode, 跑完再汇报)
**上位决策**: 方案 D (80% 粉丝经济 + 20% 真工具党评测) + preset bilibili-mason-target v0.1.1 (9 check 含 C10 商单硬规则)

---

## 背景: 为什么要重做选题

旧 Growth Memo #001 (test-001 文件夹) 的题材是"反焦虑 + 边界论" (Act 1-7 结构, hero sequence 已定稿). 在 Session 28 方案 D 决策之后, 这个题材**不再对齐**:

1. **C3 真实数据**: 旧题材是抽象议题, 没有硬数字锚点
2. **C4 实操产出标题**: 旧题材是"评论/解读型", 不是"我做了 X"
3. **C5 可抄作业**: 旧题材没有复刻产物
4. **方案 D 定位**: 80% 粉丝经济要求"真实故事 + 可抄作业", 旧题材是情绪类内容

---

## Round 2 评论挖掘: 决定跳过, 直接用 Round 1 数据

**决策理由**:
- Round 1 已有 272 条去重评论 + 17 个关键词搜索结果 (scripts/recon_*.json) + 8 需求簇 (needs_model.md v1.0)
- Round 1 的 4 个高置信度需求 (5/3/2/8) 已经足够定义第一期题材空间
- 真正的瓶颈不是"更多数据", 而是"把已有需求交叉到 Mason 真实做过的事"
- mine_evidence.py 尚未写, 从 0 写 + 跑 + 分析 ≥ 3 小时, 会挤占脚本写作时间
- B 站 API 有 wbi 签名 + rate limit 风险, 不确定性高

**不挖的后果评估**: 极低. Round 1 数据已经给出明确的"求资料/工程实践/token 焦虑/35+转型"四大需求簇, 这是一个已饱和的信号, 不需要 round 2 验证. Round 2 真正的价值是在**跑了 N 期后的 dogfood 阶段**用真实视频数据更新词典, 而不是在发布前再挖一轮评论.

---

## Mason 真实项目池 (从 git log / agents/ / skills/ / vault 提取)

**全部硬事实, git-verifiable**:

| 维度 | 数字 | 证据 |
|---|---|---|
| mason-hub 起始日 | 2026-02-26 | git log --reverse first commit |
| 至今天跨度 | **42 天** (→ 2026-04-08) | git log range |
| 总 commit 数 | **371** | git log \| wc -l |
| feat/fix/skill commit 数 | 206 | git log --format='%s' \| grep -c |
| 实际开发天数 | **31 天** (74% 出勤率) | distinct commit days |
| Agent (EMP) 数 | **16** (EMP_0000 → EMP_0015) | ls agents/ |
| 已装 skill 数 | **73** | ls ~/.claude/skills/ |
| vault learnings 笔记 | **44** | find vault/learnings -name "*.md" |
| account 板块数 | 5 (growth-memo / socialmesh / surenxuan / tried-it-first / _test) | ls accounts/ |
| Session 数 (social-media-ops) | 29 | session state file |

**其他已有但未量化的成就**:
- CC Native 迁移 (4 个 CC Agent + Hooks + RemoteTrigger)
- Email Patrol MCP Server + Railway 部署 + 首次巡逻扫 440 邮件
- bilibili-creator-dive skill (yt-dlp 绕过 wbi)
- creator-hit-factor-grid skill + 5 个新 preset
- video-clip-select v1→v7 + video-script-breakdown + video-asset-collect + video-production + video-review + video-replication (6 个 video skill)
- AE ExtendScript 批量管线 (6 个脚本)
- Whisper + Vulkan AMD GPU 真修复 (RTF 0.030)
- mason-decision-system
- 5 新 creator-hit-factor preset (event-driven/foreign-compiler/long-science/mainstream-finance/mason-target)
- 方案 D 战略 + 挖需词典 _dictionary/ 骨架 + growth memo revenue model

**待补数字 (Mason 本人提供)**:
- Claude Code 真实 token 账单 ($ 数字)
- Cursor 真实月费 ($ 数字)
- 日均工作时长

---

## 候选题材 (3 个)

### T1 ⭐ 选中 — "我用 Claude Code 42 天建了 mason-hub: 371 commit, 16 个 Agent, 73 个 Skill, 真实账单都在这里"

**C1-C10 预期评分 (发布前 hypothesis)**:

| Check | 预期 | 理由 |
|---|---|---|
| C1 反差开场 | PASS | "42 天, 371 commit, 16 Agent" 3 个数字冲击 |
| C2 具名工具+我 | PASS | Claude Code + Mason 第一人称 |
| C3 真实数据 ≥3 | PASS | 42/371/16/73/31/44 6 个硬数字 (Mason 再加 token 账单) |
| C4 实操标题 | PASS | "我用 X 42 天建了 Y" 第一人称 + 实操动词 |
| C5 可抄作业 | PASS | CLAUDE.md 模板包 + EMP 骨架 + skill 清单 3 件套 |
| C6 你/我代词 | PASS | 天然 |
| C7 受众匹配 | PASS | AI 编程 + 独立开发 + 35+ 转型 + 工具栈 (全中 Mason 主攻 B/D) |
| C8 时长 3-10 min | PASS (计划 5-6 min) | 短钩子 |
| C9 预留 | N/A | — |
| C10 商单硬规则 | N/A | 无品牌合作, 纯自发内容 |

**预期 9/9 PASS (C10 N/A).**

**题材延展性**: 天然连载 — 每期 1 个 EMP Agent 的深度故事 = 16 期. 第 1 期是元故事 (为什么要建), 第 2-16 期各讲一个 Agent.

**命中需求簇**:
- 需求 5 可抄作业 (★★★★★): CLAUDE.md + EMP 骨架 + skill 清单是明确的可抄产物
- 需求 8 工程实践 (★★★): Agent 架构 + Context 管理是高级向读者的核心关切 [214 赞] [109 赞] [53 赞]
- 需求 3 35+ 转型 (★★★★): Mason 本人是主攻人群代表
- 需求 2 token 账单 (★★★★★): 如果 Mason 提供真实账单, 直接命中

**风险**:
- Mason 提供的 token 账单如果太低 (比如 $50/月), hook 冲击力减弱 → 缓解: 用"371 commit"作为替代 hook
- mason-hub 是 meta/infra 类内容, 可能对"想要成品工具"的人群吸引力弱 → 缓解: C5 强制提供即开即用模板包

---

### T2 — "4 天踩坑 AMD GPU 跑 Whisper: 从 PyTorch 到 Vulkan 的 3 次路径错"

| Check | 预期 | 问题 |
|---|---|---|
| C1-C6 | PASS | — |
| C7 受众 | **弱 PASS** | 显卡硬件 + 模型部署是小众话题, 主攻人群 B/D 可能不懂 |
| C8 | PASS | — |
| C10 | N/A | — |

**为什么不选**: C7 弱 (受众错配). 适合作为第 3-5 期的副线, 不适合作为启动期的旗舰.

---

### T3 — "我装了 73 个 Skill, 删了 30 个: 为什么 ezindie 和大 V 都在衰减"

| Check | 预期 | 问题 |
|---|---|---|
| C1-C5 | PASS | — |
| C6 | PASS | — |
| C7 | **弱** | 元反思/选型类话题, 受众池没有直接命中 |
| C8 | PASS | — |
| C10 | N/A | — |

**为什么不选**: C7 弱 + 题材偏元反思, 商业化评分不高, 启动期不适合.

---

## 为什么 T1 胜出

1. **9/9 PASS (C10 N/A)** — 是 3 个候选里唯一预期全 PASS
2. **硬数据 6+ 个锚点** — C3 底线稳如老狗
3. **可抄作业 3 件套是真的** — CLAUDE.md (Mason 真的有) + EMP 骨架 (真的有) + skill 清单 (真的有). 不是空头承诺
4. **受众主攻双命中** — 人群 B (35+ 想转型) + 人群 D (观望者) + 人群 A (在职程序员好奇) 三中
5. **叙事延展性** — 16 期连载的天然结构
6. **方案 D 对齐** — 100% 粉丝经济内容, 无任何商业成分, C10 N/A 完美

---

## Mason 要补的最小化信息 (发布前)

1. Claude Code 真实总 token 消耗 (如果能查)
2. 真实月均账单美元数 ($)
3. Cursor 订阅数 ($, 如果用 Cursor 的话)
4. 日均开发时长 (小时)
5. 1-2 个最印象深刻的踩坑故事 (60-120 字的一小段)

**如果 Mason 提供不了** → 删除 token 账单段, 用 commit/agent/skill 数字填充 hook. C3 仍然 PASS.

---

## 产出文件

- `topic-decision.md` ← 本文件 (决策记录)
- `script-v1.md` ← 完整脚本初稿 (等待 Mason review + token 账单补数)
- `9check-audit.md` ← 9 check 自审矩阵 (发布前硬门控)
