# EMP_0009 Long-Term Memory

## 剪辑规则库评审 (2026-03-06 会议)

### 待执行任务
- Phase 2a: voiceover_writer.py 注入中文文案三层防御（prompt 约束 + _apply_term_fixes 后处理 + _check_violations 检查清单），~70 行改动
- Phase 2b: assemble.py 字幕排版升级（shadow/精确坐标/干掉 semi_transparent_black），~60 行改动
- Phase 3: 音画对齐 align.py（音频驱动视频，依赖 TTS 调通），新建 ~120 行 + 改 tts_generate.py ~40 行 + 改 assemble.py ~20 行

### 架构决策
- styles/.md 是人可读文档（Mason 审阅用），v1 不改代码，手动维护与 CHANNEL_GUIDES / channel_profiles.json 一致
- GOAL_GUIDES 保持 Python 硬编码（跨渠道，不按渠道文件组织）
- 新旧 EDL schema 用 .get(新字段, .get(旧字段, 默认值)) 兼容，不需要版本号

### 关键代码位置
- styles/ 规则库：`mason-hub/shared/editing_intelligence/styles/`
- 品牌覆盖（含自动替换词典 JSON）：`mason-hub/shared/brands/surenxuan/editing_overrides.md`
- assemble.py 字幕渲染：_normalize_text_overlay() L158-190, _build_drawtext_filter() L437-532
- voiceover_writer.py 文案生成：SYSTEM_PROMPT L24-35, VOICE_STYLES L14-22, write_voiceover() L144+
- channel_profiles.json：mason-hub/shared/editing_intelligence/channel_profiles.json

### 详细文档
- 执行决议: docs/plans/2026-03-06-video-pipeline-style-review.md