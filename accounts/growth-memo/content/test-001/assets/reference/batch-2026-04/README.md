# Batch Recon 2026-04 — 双赛道 15 账号采集与分析

> 启动日期：2026-04-08
> 目的：通过批量采集和 grid 分析 15 个 UP 主，为 Mason 在"独立开发赛道"和"财经叙事赛道"之间做出明确的赛道选择
> 方法论：基于狗勾 93×6 + 伦巴 29×6 双样本 F 对比的爆款公式分类，新增 `bilibili-dev-content` preset 验证

---

## 账号清单 + Tier 分配

### Tier 1：全量 9 check 网格分析（2 个确定 + 1 个候补）

| 文件夹 | 账号 | 赛道 | 用 preset | 状态 |
|-------|------|------|----------|------|
| `tier1-programmer-yupi/` | 程序员鱼皮 | 独立开发 | dev-content | ⏳ 待采集 |
| `tier1-ezindie/` | @ezindie 小产品变现 | 独立开发 | dev-content | ⏳ 待采集 |
| `tier1-financial-candidate/` | 待 P1-2 决策（巫师 OR 所长林超）| 财经叙事 | dev-content（验证狗勾型）| ⏳ 待 G1 决策 |

### Tier 2a：独立开发赛道 hook 分析（4 个）

| 文件夹 | 账号 | 用 preset |
|-------|------|----------|
| `tier2-he-tongxue/` | 何同学 | dev-content |
| `tier2-yihui-indiedev/` | 熠辉 IndieDev | dev-content |
| `tier2-weisheng-ai/` | 未生 AI | dev-content |
| `tier2-mark-tech/` | 马克的技术工作坊 | dev-content |

### Tier 2b：财经叙事赛道 双 preset 扫描（5 个 + 1 个未升级的候补）

| 文件夹 | 账号 | 用 preset |
|-------|------|----------|
| `tier2-xiaolin-shuo/` | 小Lin说 | **creator + dev-content 双扫** |
| `tier2-xiaoa-finance/` | 小A学财经 | 双扫 |
| `tier2-wuyifei/` | 温义飞的脑洞财经 | 双扫 |
| `tier2-zhinan-finance/` | 直男财经 | 双扫 |
| `tier2-suozhang-linchao/` | 所长林超 | 双扫（如未升级 Tier 1）|
| `tier2-wushi-finance/` | 巫师财经 | 双扫（如未升级 Tier 1）|

### Tier 3：probe only（3 个独立开发小号）

| 文件夹 | 账号 | 产出 |
|-------|------|------|
| `tier3-yuanxiaozhi/` | 袁小智的自由之路 | probe + 单条 hook |
| `tier3-dasheng/` | 大圣 | probe |
| `tier3-xianzhe/` | 羡辙 | probe（确认是否专职 B 站）|

### 跳过

- ~~马克的技术工作坊~~ 实际上保留在 Tier 2a，做 hook 分析以确认避开
- 注：原 V1 计划里的视频播客 3 个（于谦、罗永浩、张小珺）已移除

### Cross-Comparison 输出位置

| 文件 | 内容 |
|------|------|
| `cross-comparison/dev_track_comparison.md` | 独立开发赛道内 4-5 账号的 F 对比 |
| `cross-comparison/finance_track_comparison.md` | 财经赛道 6 账号的 F 对比 |
| `cross-comparison/track_route_matrix.md` | **核心产出**：双赛道 × 双路线 4 象限矩阵 |
| `cross-comparison/audience_to_ups_v2.md` | 5 人群 → 赛道 → 路线 → UP 主 4 层映射 |
| `cross-comparison/mason_track_decision.md` | **核心产出**：Mason 赛道选择决策表 |

---

## 检查点（Gates）

| Gate | 触发时机 | 决策点 |
|------|---------|-------|
| **G1** | Phase 1 全部 probe 完成 | 财经候补升级到 Tier 1 选哪个？是否调整 Tier？|
| **G2** | Phase 2-1 鱼皮 grid 完成 | 鱼皮规律和狗勾重合度 >90% 就停 P2-2/P2-3 |
| **G3** | Phase 3 全部 Tier 2 完成 | 进入 Phase 5 前最后校准 |
| **G4** | Phase 5 全部完成 | Mason 确认赛道决策，是否进 Phase 6 改 ROADMAP |

---

## Preset 文件位置

| Preset | 位置 |
|-------|------|
| `bilibili-creator.md`（伦巴型/财经宏观型）| `~/.claude/skills/creator-hit-factor-grid/presets/bilibili-creator.md` |
| `bilibili-dev-content.md`（狗勾型/知识沉淀型，**新建于 2026-04-08**）| `~/.claude/skills/creator-hit-factor-grid/presets/bilibili-dev-content.md` |

---

## 工作量预估

| Phase | 时间 | GPU 时间 |
|------|------|---------|
| Phase 0（已完成）| 30 min | - |
| Phase 1 probe 15 账号 | 2-3 h | - |
| Phase 2 Tier 1 全量（2-3 个）| 2-4 天 | 5-8 h |
| Phase 3 Tier 2 双扫（9-10 个）| 1-2 天 | 1-2 h |
| Phase 4 Tier 3 probe（3 个）| 1 h | - |
| Phase 5 横向对比 | 1-2 天 | - |
| Phase 6 更新文件 | 30 min | - |
| **合计** | **4-7 天** | **6-10 h GPU** |

---

## 版本

- v0.1 (2026-04-08) Mason 决定财经赛道为潜在主战场，确认双 preset 扫描 6 个财经账号

## P0-2 备注：creator preset 是否需要微调

读完 `bilibili-creator.md` v0.1（2026-04-07 由伦巴 dogfood 验证）后的判断：

**不需要修改 creator preset 文件本身**。理由：
1. 它是为伦巴型设计的，不应该污染它来兼容狗勾型
2. 6 个 check 在伦巴上验证强（C5 +83%, C4 +67%）
3. 财经账号的双 preset 扫正好用它做"伦巴型"参照系
4. 如果在 Tier 2b 跑财经账号时发现某 check 需要调整，应该走 v0.2 升级路径，而不是边跑边改

**唯一可能的微调**（待 Phase 3 数据验证后再做）：
- 如果发现 6 个财经账号都对 C3"你/我代词"有强信号 → 可能需要新增 C7 系列索引（同 dev-content 的 C3）
- 但这个判断要等真数据，不要现在主观加
