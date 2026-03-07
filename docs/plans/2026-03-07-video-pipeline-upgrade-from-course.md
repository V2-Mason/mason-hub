# 视频管线升级计划 — 基于"产品短视频三板斧"课程

**日期**: 2026-03-07
**来源**: Bilibili BV17r421A71u（37 集，奈导产品短视频全流程教学）
**目标**: 将课程中经过验证的方法论内化到 AI 视频生成管线，提升成片质量

---

## 背景

当前管线流程：
```
gemini_analyze → localize → shooting_script → storyboard → videogen(Seedance)
→ multicut(Gemini EDL) → voiceover_writer(Qwen) → tts_generate(CosyVoice)
→ assemble(ffmpeg)
```

核心问题（Mason 反馈）：视频成片不流畅，像机械拼接而非完整故事。

课程核心结论："产品短视频的本质是赚取用户的耐心，靠的是持续的变化。"

---

## Phase 1: 脚本层改进（投入小，效果直接）

### 1.1 脚本结构公式库
**改动文件**: `shooting_script.py`
**对应课程**: P28（五大万能公式）、P31-P33（实战案例）

当前状态：prompt 没有明确的结构公式选择，Gemini 自由发挥。
改进：新增 `STRUCTURE_FORMULAS` dict，包含 5 个公式模板：

| 公式 | 适用场景 | 结构 |
|------|---------|------|
| 痛点型 | 功能性产品（面霜/清洁机） | 痛点 + 方案 + 场景 + 介绍 |
| 结果型 | 效果明显的产品（精华/美容仪） | 结果 + 好奇 + 卖点 + 场景 |
| 反转型 | 有话题性的产品（新奇特） | 反转 + 争议 + 解释 + 结果 |
| 悬念型 | 知识/教程类内容 | 悬念 + 揭秘 + 介绍 |
| 困境型 | 生活场景强的产品（便携/居家） | 困境 + 问题 + 方案 + 结果 |

prompt 中加入：根据产品类型自动选择公式，或由 localized_analysis 指定。

### 1.2 卖点口语化强制转换
**改动文件**: `shooting_script.py` prompt
**对应课程**: P27（精准提炼卖点）、P31（卖点口语化）

当前状态：卖点直接从 analysis 复制，经常是书面语。
改进：在 prompt 中增加规则——每个卖点必须有两个版本：
- 技术版："长效续航 3000mAh"
- 口语版："充一次电能用两个月"

射入 voiceover 的只能用口语版。课程的金句："用更少的形容词，更多的量词"。

### 1.3 五感设计层
**改动文件**: `shooting_script.py` prompt，新增 `sensory_design` 字段到 shot schema
**对应课程**: P03（放大五感）

当前状态：shot 只有 `frame_description`，纯视觉。
改进：每个 shot 新增 `sensory_channel` 字段：
- visual: 直接看到的（默认）
- auditory: ASMR/产品声音（如开盖声、喷雾声）
- tactile: 触觉可视化（按压回弹、水珠滑落、布料搓揉）
- olfactory: 嗅觉可视化（水果入水、花瓣飘落、蒸汽升腾）

这个字段影响：
- videogen prompt（告诉 Seedance 画面重点是触感还是声效场景）
- assemble 音效层（auditory 类镜头自动标记需要 SFX）

---

## Phase 2: 剪辑层改进（解决"不流畅"核心问题）

### 2.1 multicut 配音重生成（Mason 已确认的方向）
**改动文件**: `multicut.py`, `voiceover_writer.py`, `tts_generate.py`
**对应课程**: P20（BGM 分段重组）

当前问题：所有 cut 共用一条 TTS，镜头重编排后音画不同步。
改进：
1. `multicut.py` EDL 输出新增 `voiceover_full_text` 字段（不只是 hint，而是完整配音文案）
2. `voiceover_writer.py` 支持从 EDL 的 voiceover_full_text 直接生成 TTS segments
3. `tts_generate.py` 每个 cut 独立生成一条 TTS
4. 流程变为：multicut → 每个 cut 生成独立配音 → assemble 用匹配的配音

### 2.2 节奏对比控制
**改动文件**: `multicut.py` prompt
**对应课程**: P15-P17（剪辑思维/心跳理论）

当前问题：EDL 中每个 clip 时长趋于均匀，缺乏节奏变化。
改进：在 MULTICUT_PROMPT 中增加"心跳节奏"规则：

```
## 节奏控制规则（必须遵守）

1. 相邻两个 timeline item 的有效时长不能相同（±0.5s 以内算相同）
2. 每个 cut 至少有一次"节奏跳跃"：连续 2-3 个快切（<2s）后接一个长镜头（>4s）
3. 5 种对比维度必须至少使用 3 种：
   - 快/慢（clip 时长变化）
   - 动/静（运动镜头 vs 固定镜头）
   - 大/小（景别跳跃：全景→特写）
   - 色彩（冷暖切换）
   - 长/短（clip 长度变化）
4. Hook 段（前 5 秒）的平均 clip 时长必须 < 2s
5. 效果展示段可以有一个 >4s 的"呼吸镜头"
```

### 2.3 音效层（SFX Track）
**新增文件**: `sfx_generate.py`
**改动文件**: `assemble.py`
**对应课程**: P21（声音表达/音效分类）

当前问题：成片只有 TTS + BGM，缺少音效层，镜头之间"粘合力"不够。
改进：

SFX 分 5 类（对应课程）：
1. 环境音效（ambient）：室内白噪、窗外鸟鸣
2. 氛围音效（mood）：悬念感、惊喜感
3. 动作音效（action）：开盖声、涂抹声、ASMR
4. 强调音效（emphasis）：数据出现时的"叮"
5. 转场音效（transition）：whoosh、风声

实现方案：
- 建立 SFX 素材库（`~/mason-hub/shared/sfx/`），按类别组织
- multicut EDL 的 timeline item 新增 `sfx_hints: [{type, description, time_in, time_out}]`
- assemble.py 新增 SFX track：根据 sfx_hints 匹配素材库中的音效文件，混入音频

### 2.4 J-Cut / L-Cut 音画错位
**改动文件**: `assemble.py`
**对应课程**: P21（J-Cut & L-Cut）、P36（拉片实战验证）

当前问题：每个 clip 的音频和视频严格对齐在同一时间点，剪辑痕迹明显。
改进：

在 EDL timeline item 中新增 `audio_offset_seconds` 字段：
- 正值 = L-Cut（前一段音频延续到当前画面）
- 负值 = J-Cut（当前音频提前进入上一段画面）
- 默认 0（无错位）

multicut prompt 指导 Gemini：
- 场景切换时优先使用 L-Cut（上一句话说完前画面已切到下一个场景）
- 悬念/揭秘时使用 J-Cut（下一段的声音提前 0.3-0.5s 进入）

assemble.py 在 voiceover track 做时间偏移处理。

---

## Phase 3: 输入质量改进（长期，提升上限）

### 3.1 竞品拉片反馈循环
**新增文件**: `video_teardown.py`
**对应课程**: P34-P37（像素级拉片方法论 + 3 个实战）

当前问题：管线是单向的，没有"对标爆款→提取参数→反哺生成"的闭环。
改进：

用 Gemini 视频理解能力做自动拉片：
1. 输入：一条爆款视频 URL/文件
2. Gemini 分析输出（结构化 JSON）：
   - 每个镜头的时长、景别、运镜、构图
   - BGM 风格和转折点
   - 节奏密度图（每秒切换频率）
   - 花字类型和出现时机
   - 开头 hook 类型
   - 文案结构公式
3. 输出直接作为 shooting_script 的约束输入

这样从"参考视频 → 本地化分析 → 脚本"变成了"参考视频 → 拉片参数 → 约束脚本生成"，更精准。

### 3.2 Hook 视觉设计库
**改动文件**: `shooting_script.py`, `multicut.py`
**对应课程**: P18（8 种 Hook 手法）

当前问题：hook 只在文案层面设计（痛点句），缺少视觉 hook。
改进：

新增 `HOOK_VISUAL_TEMPLATES`：

| Hook 类型 | 视觉描述 | 适用产品 |
|-----------|---------|---------|
| 沉浸式 | ASMR 特写 + 同步声音，无 BGM | 有满足声音的产品 |
| 破坏式 | 切/砸/撕相关物品 | 有坚固/保护卖点 |
| 冲击式 | 慢动作泼洒/碰撞/挤压 | 液态/弹性产品 |
| 拆箱式 | 快节奏拆包装 <5s | 高颜值包装 |
| 突然出现 | 产品从画面外滑入 | 外观好看的产品 |
| 产品互动 | 手部使用产品特写 | 日用品 |
| 痛点再现 | 3 个快切展示问题场景 | 解决痛点的产品 |
| 难以置信 | 反常识演示 | 有独特功能的产品 |

shooting_script prompt 根据产品类型推荐 hook 类型，生成对应的第一个 shot 描述。

### 3.3 花字分类处理
**改动文件**: `assemble.py` `_build_drawtext_filters()`
**对应课程**: P22（字幕包装 4 类型）

当前问题：所有 text_overlay 样式相同。
改进：

EDL 的 text_overlay 新增 `subtitle_type` 字段：
- `explanatory`（说明型）：小字，淡入淡出，配 pop 音效
- `emphasis`（强调型）：大字，弹入动画，配 hit 音效
- `supplementary`（解释型）：更小字，低透明度，不遮挡画面
- `entertainment`（娱乐型）：emoji 风格，弹跳动画

每种类型有预设的 font_size_scale、animation、color scheme。

---

## Phase 4: 色彩和布光指导（提升 AI 生成画面质量）

### 4.1 色彩心理学映射
**改动文件**: `shooting_script.py` prompt
**对应课程**: P08（色彩构建与运用）

在 prompt 中加入色彩指导规则：
- 高端/科技产品 → 黑色系背景，蓝色氛围光
- 美妆/护肤 → 暖调，柔光，莫兰迪色系
- 食品 → 暖黄色调，高饱和
- 居家好物 → 自然光，低饱和背景 + 暖色产品

这些直接写入 frame_description，指导 Seedance 生成。

### 4.2 构图指导
**改动文件**: `shooting_script.py` shot schema
**对应课程**: P06（九大构图手法）

新增 `composition` 字段到 shot schema：
- center（中心构图）→ 单品展示
- rule_of_thirds（三分线）→ 人+产品
- diagonal（对角线）→ 长条形产品
- symmetry（对称）→ 对比展示
- leading_lines（引导线）→ 使用场景
- foreground_bokeh（前景虚化）→ 增加纵深

写入 videogen prompt，指导 Seedance 的画面构图。

---

## 优先级排序

| 优先级 | 改动 | 预期效果 | 工作量 |
|--------|------|---------|--------|
| P0 | 2.1 配音重生成 | 解决最大痛点：音画不同步 | 中 |
| P0 | 2.2 节奏对比控制 | 解决"机械感"问题 | 小（改 prompt） |
| P1 | 1.1 结构公式库 | 脚本质量提升 | 小（改 prompt） |
| P1 | 1.2 卖点口语化 | 配音自然度提升 | 小（改 prompt） |
| P1 | 2.4 J/L-Cut | 消除剪辑痕迹 | 中 |
| P2 | 2.3 音效层 | 沉浸感大幅提升 | 大（需要素材库） |
| P2 | 1.3 五感设计 | 画面"证据力"提升 | 小（改 prompt） |
| P2 | 3.3 花字分类 | 字幕专业度提升 | 中 |
| P3 | 3.1 拉片反馈循环 | 对标精度提升 | 大（新模块） |
| P3 | 3.2 Hook 视觉库 | 前 5 秒留存率提升 | 小 |
| P3 | 4.1-4.2 色彩/构图 | AI 画面质量提升 | 小（改 prompt） |

---

## 建议执行顺序

**Sprint 1（本周）**: P0 — 配音重生成 + 节奏对比控制
→ 直接解决"不流畅"问题，最小改动最大效果

**Sprint 2（下周）**: P1 — 结构公式 + 卖点口语化 + J/L-Cut
→ 脚本和剪辑层同步提升

**Sprint 3（之后）**: P2 — 音效层 + 五感设计 + 花字分类
→ 需要建 SFX 素材库，工作量较大

**Sprint 4（按需）**: P3 — 拉片循环 + Hook 库 + 色彩构图
→ 锦上添花，提升上限
