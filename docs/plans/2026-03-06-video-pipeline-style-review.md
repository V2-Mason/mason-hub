# 视频生产线剪辑规则评审 — 最终执行决议

> 日期：2026-03-06
> 发起人：Mason
> 参会：EMP_0008 (SocialMesh PM), EMP_0009 (Content-Tech Dev), EMP_0010 (Content Creator), EMP_0012 (Product Architect)
> 会议记录：docs/plans/2026-03-06-video-pipeline-style-review-meeting-log.md

## 背景

Mason 反馈视频生产线三个痛点：
1. 剪辑风格土，文字排版不好看
2. 口播对不上
3. 中文能力差

参考了 [videocut-skills](https://github.com/Ceeon/videocut-skills) 的架构思路（规则库 + 自更新机制），草拟了 styles/ 规则库方案。

## 决策汇总

### 决策 1：三源归一方案 — 先手动后自动化

**决定**：styles/.md 作为人可读的"审美笔记本"（Mason 审阅用），手动维护与 CHANNEL_GUIDES / channel_profiles.json 的一致性。不急着做自动构建脚本。

**否决的方案**：
- 方案 A（Dev 提议：YAML frontmatter + build_profiles.py 自动生成）— 过早抽象，等规则稳定后再考虑
- 方案 C+（Architect 提议：三源独立 + 对照 checklist）— 方向对，但 v1 不需要形式化的 checklist

**为什么三源存在**：Gemini 需要叙事性文字、FFmpeg 需要数值参数、人需要可读文档 — 三个消费者要不同格式。styles/.md 是给 Mason 看的官方版本，改它然后手动同步到代码。

**styles/ 位置**：`mason-hub/shared/editing_intelligence/styles/`

### 决策 2：音画对齐 — 音频驱动视频，排最后

**决定**：采用音频驱动视频方案（TTS 时长为基准，调整视频 clip 裁剪/速度）。但优先级排最后（Phase 3），因为：
- 依赖 CosyVoice TTS 调通
- 文案规则和字幕排版稳定后再做，否则反复调参

**技术方案**（Dev 提出，待执行）：
- 新建 align.py ~120 行
- 改 tts_generate.py ~40 行
- 改 assemble.py ~20 行

### 决策 3：字幕排版 — 干掉黑底条，换描边+阴影

**决定**：
- P0（立即做）：描边 borderw+bordercolor、阴影 shadowx+shadowy、精确坐标 x/y 覆盖
- P1（后续做）：渐变遮罩、fade_in 动画
- 废弃 semi_transparent_black 默认值

**改动范围**：assemble.py ~60 行（_normalize_text_overlay ~15 行 + _build_drawtext_filter ~40 行）

### 决策 4：中文文案规则 — 三层防御

**决定**：
1. Prompt 约束：BRAND_VOICE_RULES 追加到 voiceover_writer.py 的 SYSTEM_PROMPT
2. 后处理替换：_apply_term_fixes() 在 Qwen 返回后做确定性替换
3. 检查清单：_check_violations() 返回 warnings 字段

**具体规则**：
- 称呼：统一"姐妹们"
- 价格：分场景（种草模糊"百元出头"、带货给区间"六七十块"、详情页报价）
- AI 味替换表扩充：加入"值得一提的是""不得不说""作为一款""无论是...还是""可以说是""一定程度上""毋庸置疑" + 四字成语堆砌 + "让我们一起"
- 品牌约束必须贯穿全管线（当前只在 multicut.py，voiceover_writer.py 缺失）

**改动范围**：voiceover_writer.py ~70 行

## 执行计划

```
Phase 1: styles/.md 第一版（纯文档）         [已完成 2026-03-06]
    |
    v
Phase 2a: 中文文案规则 (voiceover_writer.py)  [待执行，和 2b 并行]
Phase 2b: 字幕排版升级 (assemble.py)          [待执行，和 2a 并行]
    |
    v
Phase 3: 音画对齐 (align.py，依赖 TTS 调通)  [待执行]
```

## 产出物

- styles/ 规则库：`shared/editing_intelligence/styles/`（9 个文件，1513 行）
- 品牌覆盖：`shared/brands/surenxuan/editing_overrides.md`（183 行）

## 关键教训

1. 管线分阶段建设会自然产生多源问题 — 需要定期审计数据源一致性
2. 改动有依赖链（文案→TTS时长→对齐→字幕），要按依赖顺序排优先级，避免反复加工
3. AI 味替换用后处理比 prompt 约束更可靠 — LLM 不 100% 遵守禁用词指令
4. 品牌调性约束必须贯穿管线所有文案生成环节，不只是某一步
