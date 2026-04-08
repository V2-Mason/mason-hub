# Batch Recon 2026-04 — Session State

> **上次 session 结束**：2026-04-08 ~06:15
> **断点阶段**：P2-3 全部转录完成，P2-4 手工 grid 尚未开始
> **下次启动的 P0 动作**：读 `tier1-programmer-yupi/full_text.txt` + 用 `bilibili-dev-content` preset 开始给 57 条鱼皮视频打 9×57 网格

---

## 任务背景（一句话回顾）

Mason 要在"独立开发赛道"和"财经叙事赛道"之间做赛道选择。通过批量采集 14 个 B 站 UP 主的 probe 数据 + 对 4 个 Tier 1 账号跑全量 grid 分析，生成双赛道 × 双路线 4 象限决策矩阵。

**Tier 1 候选升级决策（D 选项，Mason 在 01:40 确认）**：
- 鱼皮 + ezindie（原计划）
- **+ 小Lin 说**（最优财经候补，统计规模最大、风格全面）
- **+ 巫师财经**（最纯净系列化样本，每条标题都【巫师】+ 系列名）

---

## 已完成的 Phase（P0 → P2-3）

### Phase 0：前置准备 ✅
- **P0-1** 新建 `bilibili-dev-content` preset（9 个 check：C1-C9）
  - 位置：`~/.claude/skills/creator-hit-factor-grid/presets/bilibili-dev-content.md`
  - 核心设计：路径 A 故事型（C2 具名+C5 故事开场+C7 实操产出）∨ 路径 B 长尾型（C3 系列索引+C4 长尾查询词）
  - C1 反差开场**预期反向规律**（基于狗勾 F 对比 Δ=-16%）
- **P0-2** 审阅 `bilibili-creator` preset（伦巴型）：不修改，保留作为财经账号双扫参照系
- **P0-3** 建 `batch-2026-04/` 文件夹结构（15 个子目录 + README.md）

### Phase 1：Probe 14 账号 ✅
- **P1-0** 找全 14 账号 UID（通过 web 搜索 + bili API 验证）
- **P1-1a** 袁小智烟雾测试成功（4 视频）
- **P1-1b** 后台批量 probe 12 账号（00:29-01:18，50 分钟）
- **P1-1c** Patch `bili_api.py` 加 `-i` flag + retry 3 个失败账号
  - **Bug**：yt-dlp 单个视频失败会中止整个频道抓取
  - **Fix**：加 `--ignore-errors`，判断"真失败"改用"0 视频返回"
  - 鱼皮 + ezindie + 小Lin 说 retry 成功（01:19-01:40）

### 14 账号 probe 数据汇总（见各 slug 的 probe_summary.md）

| Tier | 账号 | UID | 粉丝 | 视频 | P50 | Max | 活跃 |
|------|------|-----|------|-----|-----|-----|------|
| T1 | 程序员鱼皮 | 12890453 | 877k | 314 | 13万 | 308万 | ✅ 2026-04 |
| T1 | ezindie 小产品变现 | 395127673 | 53k | 147 | 4.7k | 79k | ⚠️ 衰减 |
| T2a | 老师好我叫何同学 | 163637592 | 12.7M | 97 | 600万 | 3370万 | ✅ 2026-03 |
| T2a | Geek4Fun（替代熠辉）| 28860626 | 3k | 12 | - | - | - |
| T2a | 未生 AI | 351969226 | 9k | 29 | - | - | - |
| T2a | 马克的技术工作坊 | 1815948385 | 170k | 30 | 5.5万 | 81万 | ✅ 2026-03 |
| T2b | 小Lin 说 | 520819684 | 7.1M | 177 | 241万 | 998万 | ✅ 2026-03 |
| T2b | 小A学财经 | 531838578 | 198k | 79 | 4.2万 | 67万 | ⚠️ 2024 末停更 |
| T2b | 巫师财经 | 472747194 | 4.18M | 97 | 125万 | 575万 | ✅ 2026-03 |
| T2b | 温义飞今天插旗了吗 | 508709785 | 478k | 255 | 5.5万 | 322万 | ✅ 2026-04 |
| T2b | 所长林超 | 520155988 | 3.62M | 124 | 74万 | 764万 | ❌ 停更 2024-09 |
| T3 | 花果山-大圣 | 26995758 | 47k | 168 | - | - | - |
| T3 | 袁小智的自由之路 | 482466247 | 888 | 4 | 3.2k | 24k | ✅ 2026-03 |

**账号剔除记录**：
- **熠辉 IndieDev**：原计划样本，web 搜索发现是 X/Twitter 账号，B 站无对应。用 Geek4Fun 替代占位（Mason 确认）
- **直男财经**：B 站有"直男 Talk"（UID 522557713）但无法 100% 确认是同一 IP。Mason 决定移除（04-08 ~01:30）
- **羡辙**：知乎活跃但 B 站无主力账号。剔除（Mason 确认）

### Phase 2：Tier 1 采集与转录 ✅（只到 P2-3）

- **P2-0** 写 `sample_tmb.py` 采样器（T19+M19+B19，过滤 <60s 和 >2h）
- **P2-1** 4 账号采样完成：
  - 鱼皮：281 有效 → 57 选定（Top 50万-308万 / Mid 13.7万-15.6万 / Bot 1.1万-3.2万，差距 30x）
  - ezindie：147 有效 → 57 选定（**差距 125x** ⚠️ 证实红利已过）
  - 小Lin 说：177 有效 → 57 选定（Bot 最低 18万 仍高于鱼皮 Top 最低！7.1M 粉效应）
  - 巫师财经：96 有效 → 57 选定（60x 差距）
- **P2-2** 批量下载音频：221/228 mp3 成功（总 135 min，B 站 rate limit）
- **P2-3** Whisper Vulkan GPU 转录：**219/221 成功**（总 102 min）
  - 鱼皮：55 json（13,703 lines full_text）
  - ezindie：51 json（9,567 lines）
  - 小Lin 说：57 json（48,810 lines）
  - 巫师财经：56 json（38,903 lines）
  - **合计 111,983 行**转录文本已备齐

---

## 预期观察（基于 probe 数据的事前假设）

这些是我在跑 grid 之前就能从标题看出的模式。Grid 会验证或证伪：

### 鱼皮：**混合型假设**
- 路径 A 故事："我开业啦！"/ "再见了，腾讯！"/ "我用 OpenClaw 做了个女朋友！"
- 路径 B 长尾："2025 年最新 Java 学习路线" / "Claude Code 源码泄露" / "AI 时代该学啥"
- 偶尔伦巴型热点："突发，快手被色情直播刷屏！"
- **Grid 应该能拆出这三种模式在 Top/Mid/Bot 的分布差异**

### ezindie：**衰减假设**
- 全是"独立开发变现周刊 第 X 期" → C3 系列索引 100% PASS
- 但都是国外案例编译，**C2 具名主角**可能是"国外随机开发者"（狗勾定义算 PASS 但对中国观众无锚感）
- 预期：路径 B SEO 长尾型单一路线，没有路径 A 支撑，所以天花板低

### 小Lin 说：**双路径纯净型**
- "一口气了解 XX" 系列（路径 B SEO 长尾，典型题：洗钱/国债/关税/韩国经济/委内瑞拉）
- C4 长尾查询词命中极强
- 制作精良，双路径可能都强

### 巫师财经：**路径 A 纯净型**
- 【巫师】+ 系列名 + 具名主角（杨幂/蔡徐坤/王一博/伊朗/迪士尼/日本经济）
- 系列：资本与明星 / 巫师经济学 / 网红与资本简史
- C2 具名主角应该 PASS 率极高
- C5 故事开场可能是主力规律

---

## 关键数据文件位置

```
c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference/batch-2026-04/
├── README.md                              # 批次总览
├── SESSION_STATE.md                       # 本文件
├── sample_tmb.py                          # 采样脚本
├── batch_probe.sh + batch_probe.log       # Probe 14 账号
├── retry_failed.sh + retry_failed.log     # Retry 3 账号
├── batch_download_audio.sh + batch_download.log
├── batch_transcribe.sh + batch_transcribe.log
│
├── tier1-programmer-yupi/                 # 55 转录完 ⭐ P2-4a 起点
│   ├── video_list.tsv (314 videos)
│   ├── selected.tsv (57 T19+M19+B19)
│   ├── audio/*.mp3 (56)
│   ├── transcripts/*.json (55)
│   └── full_text.txt (13703 lines)
├── tier1-ezindie/                         # 51 转录完
│   ├── video_list.tsv (147)
│   ├── selected.tsv (57)
│   ├── audio/*.mp3 (51)
│   ├── transcripts/*.json (51)
│   └── full_text.txt (9567 lines)
├── tier2-xiaolin-shuo/                    # 57 转录完 ← Tier 1 升级
│   ├── video_list.tsv (177)
│   ├── selected.tsv (57)
│   ├── audio/*.mp3 (57)
│   ├── transcripts/*.json (57)
│   └── full_text.txt (48810 lines)
├── tier2-wushi-finance/                   # 56 转录完 ← Tier 1 升级
│   ├── video_list.tsv (97)
│   ├── selected.tsv (57)
│   ├── audio/*.mp3 (57)
│   ├── transcripts/*.json (56)
│   └── full_text.txt (38903 lines)
│
├── tier2-he-tongxue/                      # Probe only (P3 hook 分析待做)
├── tier2-yihui-indiedev/                  # Probe only (Geek4Fun)
├── tier2-weisheng-ai/                     # Probe only
├── tier2-mark-tech/                       # Probe only
├── tier2-xiaoa-finance/                   # Probe only
├── tier2-wuyifei/                         # Probe only
├── tier2-suozhang-linchao/                # Probe only (停更)
├── tier3-yuanxiaozhi/                     # Probe only (4 videos)
├── tier3-dasheng/                         # Probe only
└── cross-comparison/                      # 空目录，P5 输出位置
```

**总占用**：4.0 GB（大部分是 mp3 音频）

---

## 下次 Session 的任务序列（P0 起点）

按优先级：

### 第 1 步（P0 必做）：鱼皮 grid（P2-4a）

```
工具：Read full_text.txt + 手工打 9×57 PASS/FAIL 网格
起点：tier1-programmer-yupi/full_text.txt（13703 lines）
preset：~/.claude/skills/creator-hit-factor-grid/presets/bilibili-dev-content.md
输出：tier1-programmer-yupi/analysis/grid.md
硬规则：N=57 一格不能跳，否则整个 skill 作废从头走（参考 creator-hit-factor-grid SKILL.md 第 40-50 行）
```

**重要**：启动第 1 步前先读 `creator-hit-factor-grid/SKILL.md` 的 Phase 0-6 流程，以及 `bilibili-dev-content.md` preset 的 9 个 check 定义。

### 第 2 步：G2 检查点
- 鱼皮 hit_rate 和 patterns 生成完
- 对比狗勾的 F 对比结论
- **决策**：如果鱼皮规律和狗勾重合 >90%，**跳过** P2-4b/c/d，节省 24 小时人工
- 如果不同，继续跑另 3 个账号

### 第 3 步：P2-4b/c/d（如果 G2 不跳）
- ezindie grid（预期：路径 B 单一，C2 对国外主角可能 PASS 率高但无区分力）
- 小Lin 说 grid（双 preset 扫：先用 dev-content，再用 creator 对比）
- 巫师财经 grid（双 preset 扫）

### 第 4 步：P3 Tier 2 hook 分析（5 个 Tier 2a + 5 个 Tier 2b）
- 已完成 probe 但未采集音频：需要先 sample → download → transcribe → hook 分析
- 只看 Top 10 开场 hook，不跑完整 grid

### 第 5 步：P5 横向对比
- `dev_track_comparison.md`：独立开发赛道 4 账号 F 对比
- `finance_track_comparison.md`：财经赛道 6 账号 F 对比
- `track_route_matrix.md`：**核心产出** 双赛道 × 双路线 4 象限矩阵
- `audience_to_ups_v2.md`：5 人群 → 赛道 → 路线 → UP 主 4 层映射
- `mason_track_decision.md`：**核心产出** Mason 赛道选择决策表

### 第 6 步：P6 更新决策文件
- AUDIENCE_PERSONAS.md 给 5 人群加 UP 主字段
- CONTENT_ROADMAP.md 8 板块加参考 UP 主 + 借鉴规律
- 新建 TRACK_SELECTION_V2.md
- 新建 BATCH_RECON_2026_04.md 主报告

---

## 待处理的遗留问题

### 1. Skill patch 是否 commit？

我改了 `~/.claude/skills/bilibili-creator-dive/scripts/bili_api.py`，加了 `-i` flag + 容错判断。修改明确、向后兼容。**待 Mason 确认是否 commit 到 skill 源目录**。

修改摘要（line ~155-195）：
```python
cmd = [..., "-i", ...]  # --ignore-errors

# New: "真失败" 改用 "0 视频返回"
if not out:
    raise BiliAPIError(f"yt-dlp returned 0 videos ...")
if proc.returncode != 0:
    log.warning(f"yt-dlp had errors ... extracted {len(out)} videos")
```

这是 **P0 质量 fix**（没它之前 B 站频道抓取会因单个被删视频整个挂掉），建议 commit。

### 2. Tier 2a/2b 的音频和转录还没跑

P3 只做了 probe。如果走 P2-4 → P3 顺序，P3 时需要重跑一遍音频下载 + whisper（约 2-3 小时 background）。

**优化建议**：下次 session 启动 P2-4a 的同时，**background 启动 Tier 2 的 10 账号批量下载**，时间可以完全并行。

### 3. ezindie / 所长林超 是否 "已过期"

probe 数据显示：
- ezindie 红利已过（P50 只 4.7k）
- 所长林超停更 1.5 年（2024-09 最后更新）

这两个账号的 grid 结论对 Mason **未来决策** 的价值有限（不能抄当前在用的打法）。但作为**历史反面教材**仍然有价值。

**建议**：P2-4b ezindie 降级为 Top 20 hook 分析（不跑全量 grid），节省 6 小时。

---

## Session 结束时的 context 状态

- 原计划 P2-4 手工 grid 需要 2052 个 PASS/FAIL 格子，每个都要读开场 60 秒 + 写原因
- 按当前节奏会快速耗尽剩余 context
- 按 Mason 指令（"转录完后如果 context 消耗太多，做完直接收工"），此处断点

**下次启动前的自检**：
1. 读本文件（SESSION_STATE.md）
2. 读 MEMORY.md 确认 batch-2026-04 指针
3. 读 `creator-hit-factor-grid/SKILL.md` 了解 grid 流程
4. 读 `bilibili-dev-content.md` 了解 9 个 check
5. 读 `tier1-programmer-yupi/selected.tsv` 确认 57 个目标
6. 开始 P2-4a

---

## 版本

- v0.1 (2026-04-08 06:15) 初版。P2-3 全部转录完成后收工。
