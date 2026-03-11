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

## 视频管线升级 — 11 项改动全部完成 (2026-03-07)

### 来源
- Bilibili 课程 BV17r421A71u（产品短视频三板斧，37 集）→ Gemini 2.5 Pro 逐集分析 → 提炼方法论 → 落地代码
- 计划文档: `docs/plans/2026-03-07-video-pipeline-upgrade-from-course.md`

### Sprint 1 改动（有依赖关系，先做）
1. **配音重生成** — `voiceover_writer.py` 新增 `write_voiceover_from_edl_text(edl)` 从 EDL 的 voiceover_full_text 直接生成 segments；`tts_generate.py` 新增 `generate_tts_per_cut(edl, output_dir)`；`assemble.py` 的 `batch_assemble_edls()` 自动检测并调用
2. **心跳节奏** — `multicut.py` MULTICUT_PROMPT 新增"节奏控制规则（心跳理论）"6 条规则
3. **J/L-Cut** — `multicut.py` timeline item 新增 `audio_offset_seconds`；`assemble.py` 用 adelay/atrim 实现偏移
4. **5 结构公式** — `shooting_script.py` 新增 STRUCTURE_FORMULAS + prompt rule 6
5. **卖点口语化** — `shooting_script.py` prompt voice section rule 6

### Sprint 2 改动（独立模块，并行做）
6. **五感设计** — `shooting_script.py` sensory_channel 字段 + rule 7
7. **构图指导** — `shooting_script.py` composition 字段 + rule 9
8. **色彩心理学** — `shooting_script.py` rule 8
9. **SFX 音效层** — 新建 `sfx_generate.py`（load_sfx_library + match_sfx + generate_sfx_track）；`multicut.py` 新增 sfx_hints；`assemble.py` SFX track 混合（voiceover + SFX amix 1:0.8 → + BGM）
10. **花字分类** — `multicut.py` 新增 subtitle_type；`assemble.py` SUBTITLE_TYPE_PRESETS（4 类预设）
11. **拉片反馈循环** — 新建 `video_teardown.py`（teardown_video + teardown_to_constraints，Gemini 视频理解）
12. **Hook 视觉库** — `shooting_script.py` HOOK_VISUAL_TEMPLATES（8 种）+ rule 10

### 新文件
- `sfx_generate.py` — SFX 匹配 + ffmpeg 混合
- `video_teardown.py` — Gemini 自动拉片（CLI 入口 + argparse）
- `shared/sfx/sfx_library.json` — SFX 素材库结构（tracks 待填充）

### 待完成
- SFX 素材库填充（`shared/sfx/sfx_library.json` tracks 为空）
- 端到端测试验证改进效果

### Commits
- socialmesh `e43f096`: Sprint 1 — 配音重生成 + prompt upgrades (5 files, +336 lines)
- socialmesh `494e629`: Sprint 2 — SFX + subtitle + teardown + hook (5 files, +535 lines)

## 多 Agent 并行开发经验 (2026-03-07)

### 成功模式
- **按文件区域分工**：Agent A 改函数逻辑，Agent B 改 prompt 文本 → 不冲突
- **按依赖关系分批**：Sprint 1（有依赖的先做）→ Sprint 2（独立模块并行）
- 4 个 Agent 完成 871 行新增代码，全部一次通过语法验证

### 风险区域
- `assemble.py` 改动最密集（音频混合 + SFX + J/L-Cut + 花字），多人改容易冲突
- 同一个 prompt（如 MULTICUT_PROMPT）多人加规则 → 需注意不重复不矛盾
- 接口字段名必须事先约定（如 `voiceover_full_text` vs `voiceover_script`）

## SocialMesh P0 Sprint (2026-03-09, Team Sprint)

### Backlog 过时发现
- **图片上传功能已存在**：后端 `/api/content/{id}/images`（上传/列表/删除/重排序）+ 前端 `ImageUpload` 组件（拖拽上传、缩略图、排序、删除）+ publishing.py 发布时自动传图 — 全部已实现
- **内容列表/草稿管理已存在**：ContentEditor.jsx 左侧栏已有内容列表（加载/删除/新建），后端 `/api/content/` CRUD 完整，Dashboard 展示最近 5 条
- 教训：**接到任务先验证现状**，不要假设 backlog 说"未完成"就真的未完成。两个 P0 任务实际上已经在之前的开发中实现了

### 实际改动
- GeoAnalysis.jsx 5 处英文占位标签翻译为中文（其余页面已全部中文）
- publishing.py 发布成功后更新 Content.status = PUBLISHED
- schedule.py 排程时 DRAFT→SCHEDULED，mark-published 时→PUBLISHED
- ContentEditor.jsx 侧栏增加琥珀色「已排程」badge（原有绿色已发布 + 灰色草稿）