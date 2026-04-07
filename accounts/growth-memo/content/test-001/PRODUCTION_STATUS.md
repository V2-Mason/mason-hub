# 成长备忘录 #001 — 生产完工度地图

> 标题：《全世界都在卷 AI，但我只想睡个好觉》
> 脚本：[video-001-script-v6.md](../video-001-script-v6.md)
> 总时长：约 7 分 25 秒（7 幕）
> 最后更新：2026-04-07

---

## 完工度清单

| # | 元素 | 状态 | 备注 |
|---|------|------|------|
| 1 | 脚本 v6 | done | 7 幕 / 7:25 / 三梗 + 三金句，调性"深夜独白" |
| 2 | Act 1 素材 (0:03-0:12) | done | 5 hero + 17 fill = 22 clips, [CUT_SHEET](assets/ae-templates/act1_news_multiscreen/CUT_SHEET.md) |
| 3 | **Act 1 AE 模板灌素材** | **done (脚本化)** | 6 个 ExtendScript 完整管线就绪 |
| 4 | **Act 1 climax 6s mp4** | **done v1** | output/act1_mosaic_climax_*.mp4 (旧版,4 个特写快切) |
| 5 | Act 1 climax v2 (Meta+Amazon) | **进行中** | mp4 已重切, fill+stretch 脚本就绪, 待 Mason 跑流程 |
| 6 | Act 2-7 素材 | **空** | 每幕脚本里都有详细 visual brief 但未采集 |
| 7 | 旁白音频 | **占位** | output/narration.mp3 仅 72KB（4月2日测试桩） |
| 8 | 呼吸球动画（第 5 幕核心视觉）| **空** | 多圈交叉 → 融合成不规则球体 → 呼吸起伏 |
| 9 | 黑悟空死亡画面（第 1 幕）| **空** | 标志性视觉 #1 |
| 10 | 头号玩家摘眼镜（第 4 幕）| **空** | 标志性视觉 #2 — 全片最强情绪点 |
| 11 | Opus 毒品包装（第 3 幕）| **空** | 标志性视觉 #3 — 截图传播点 |
| 12 | 文字卡（金句 ×3）| **空** | "用进步逃避结果" / "你在追一个活的东西" / "不是 AI 在驾驭你" |
| 13 | BGM / 音效 | **空** | |
| 14 | 整片剪辑合成 | **未开始** | |

---

## Act 1 制作工具链 (2026-04-07 完成)

完整 ExtendScript 脚本管线在 [scripts/](assets/ae-templates/act1_news_multiscreen/scripts/):

| 脚本 | 用途 | 状态 |
|------|------|------|
| `1_inspect_template.jsx` | 探查 AE 模板结构,输出 inspect_output.txt | ✅ |
| `2_mapping.json` | panel→clip 映射数据 (40 panel + 4 hero) | ✅ |
| `3_fill_template_v2.jsx` | 灌素材 (clip_start 字段, 不静音, 不调色) | ✅ |
| `4_render_template.jsx` | 渲染 (Test/Climax/Full/WorkArea 4 模式) | ✅ |
| `5_recut_timeline.jsx` | 重排 Render comp timeline (废弃, 改用 stretch+extract) | ⚠️ |
| `6_stretch_closeups.jsx` | 拉长 4 个特写, 后续后移 (v5: 2 个 clip 模式) | ✅ |
| `7_mute_everything.jsx` | 暴力静音所有 layer (备用) | ✅ |
| `8_extract_workarea.jsx` | 提取 work area 成新 comp (嵌套, 非破坏性) | ✅ |
| `diagnose_filled_layers.jsx` | 验证画质 (Display% 计算) | ✅ |

详见 [[methodology/ae-template-batch-workflow]]

## 重要发现 (2026-04-07)

### 1. AE 多屏模板的 4 个 hero 槽位
模板里的 4 个特写 close-up 槽位是 **Media 05/08/07/09 Precomp** (注意是这个顺序),按时间顺序:
- Media 05 → 12.00s
- Media 08 → 12.42s
- Media 07 → 12.83s
- Media 09 → 13.25s

每个原本 0.42 秒长。模板的 mosaic 高潮是 Scene 05 (13.75-16.75s)。

### 2. hero mp4 的真实长度 (CUT_SHEET 里的 ffmpeg 已切过)
从 [CUT_SHEET](assets/ae-templates/act1_news_multiscreen/CUT_SHEET.md) 标的 in/out 范围,Mason 之前用 ffmpeg 切过精华段:

| Clip | 文件名 | 原始长度 | 含完整句子 |
|------|--------|---------|-----------|
| Meta | 03_en_C2_meta_11000.mp4 | 5.61s | "And happening today, another major tech giant is planning to lay off thousands of its workers" |
| Amazon | 01_en_C4_amzn_10000.mp4 | 4.00s | "that Amazon is planning to cut 10,000 workers" |
| Google | 02_en_C1_google_12000.mp4 | 7.01s | "Google parent Alphabet ... announced it's cutting 12,000 jobs..." |
| Chegg | 04_en_C6_chegg_crash.mp4 | 6.51s | "Chegg is the first public company to blame AI..." |
| Microsoft | 05_en_C3_msft_10000.mp4 | 5.81s | "10,000 jobs being cut by Microsoft..." |

**2026-04-07 重切**:
- Meta 5.61s → **5.00s** (切掉末尾 0.61s 静音)
- Amazon 4.00s → **3.54s** (切掉末尾 "So..." 下一句开头)
- 原文件备份为 `*.original.mp4`

### 3. Whisper word_timestamps 的精确转录
2026-04-07 跑了 faster-whisper small,得到 Meta + Amazon 的词级时间戳。详见 [CUT_SHEET 附录](assets/ae-templates/act1_news_multiscreen/CUT_SHEET.md)

**Lesson**: 任何"音频里词的时间"问题,第一步就跑 Whisper。详见 [[learnings/whisper-first-for-audio-timing]]

---

## 当前 Act 1 climax v2 方案 (2026-04-07 EOD)

**目标**:8.54 秒 climax 段,2 个完整 layoff 句子

```
12.00 - 17.00s    Meta    "And happening today, another major tech giant
                            is planning to lay off thousands of its workers"
17.00 - 20.54s    Amazon  "that Amazon is planning to cut 10,000 workers"
20.54s +         (Scene 05 mosaic 后移, 当前 work area 不包含)
```

总特写段 **8.54 秒**,跟脚本 v6 第一幕 9 秒接近对齐。

### 决策记录

- ✅ Meta + Amazon **2 个 hero**(不是 4 个)
- ✅ Media 07 + 09 **改为 fill**,且在 stretch 脚本里被 disable
- ✅ 每个 clip 播 mp4 完整长度,不用 clip_start 偏移
- ✅ Hue/Sat -50 调色 **删除**(Mason 要原片颜色)
- ✅ 静音 **删除**(Mason 要听原音)
- ✅ work area 12.00 - 20.54s,不含 mosaic
- ⏳ 过渡到 mosaic 突兀的问题留为 backlog

### 待 Mason 跑的流程

1. 关闭当前 AE 项目(不保存)
2. `File → Open Project → Multiscreen Intro I Mosaic Opener (converted).aep`(干净原始)
3. `File → Scripts → Run` → [3_fill_template_v2.jsx](assets/ae-templates/act1_news_multiscreen/scripts/3_fill_template_v2.jsx)
4. `File → Scripts → Run` → [6_stretch_closeups.jsx](assets/ae-templates/act1_news_multiscreen/scripts/6_stretch_closeups.jsx)
5. Render comp 标 work area: B 12.00, N 20.54
6. `Ctrl+M` 或跑 [4_render_template.jsx](assets/ae-templates/act1_news_multiscreen/scripts/4_render_template.jsx) → WorkArea 按钮
7. 拿 mp4 + 听效果

---

## 卡点诊断 (今天跨天结余)

**今天的核心成果**: Act 1 完整工具链打通(6 个脚本 + 1 个 mp4 已重切)

**今天的核心 lesson**: AE 不是剪辑软件,是合成软件。AE 出原料,PR 拼整片。详见 [[methodology/raw-segment-driven-video-production]]

**还在路径 B 的第 3 步**(Act 1 真素材 → mp4)

**下一步**(按路径 B):
- Act 1 climax v2 mp4 (8.54s) → **手动跑流程出**
- Act 2-7 占位画面 → 还没做
- 旁白录制 → Q2 还没决定
- v0.1 内审版 → 上面三件事完成才能拼

---

## 待决策的 open questions

**Q1**: 路径 A 还是路径 B?(推荐 B,实际上已经在走 B)

**Q2**: 旁白用「自己录」还是「TTS」?
- 自录:质感最对,需安静环境 + 多次重录
- TTS:MiniMax Speech / 阿里 CosyVoice / ElevenLabs 中文,已有候选
- 决策影响下一步:自录 → 切录音稿;TTS → 调接口生成

**Q3** (新): Act 1 climax v2 的过渡到 mosaic 突兀问题怎么办?
- (a) 先不解决,work area 只到 20.54s 不含 mosaic ⭐ 当前方案
- (b) 加 cross dissolve 过渡
- (c) 完全砍掉 mosaic,只要 2 个特写
