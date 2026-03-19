# EMP_0009 Content-Tech Dev — 工具与资源

## Skills
→ check-syntax
→ run-backend-tests
→ dev-verify-loop

## 关键代码路径（~/socialmesh/）
- backend/
- frontend/src/
- backend/tests/
- backend/config/
- backend/adapters/

## 视频管线代码
- 归属路径：skills/video/video-download/*（当前），迁移后 socialmesh/backend/content/video_pipeline/
- 关键文件：content_pipeline.py、videogen.py、shooting_script.py
- assemble.py 字幕渲染：_normalize_text_overlay() L158-190, _build_drawtext_filter() L437-532
- voiceover_writer.py 文案生成：SYSTEM_PROMPT L24-35, VOICE_STYLES L14-22, write_voiceover() L144+
- channel_profiles.json：mason-hub/shared/editing_intelligence/channel_profiles.json
- sfx_generate.py — SFX 匹配 + ffmpeg 混合
- video_teardown.py — Gemini 自动拉片

## 分析代码
- 归属路径：skills/xhs/xhs-crawl.sh、skills/xhs/xhs-analyze.sh、阿里云分析脚本
- 分析脚本：`skills/xhs/xhs-analyze-viral.py`

## 按需参考
| 文件 | 何时读 |
|------|--------|
| `kernel/standards/protocols/dev-execution.md` | 需要任务执行流程细节时 |
| `docs/plans/2026-03-06-video-pipeline-style-review.md` | 剪辑规则库执行决议 |
| `docs/plans/2026-03-07-video-pipeline-upgrade-from-course.md` | 视频管线升级计划 |

## 禁区
- ~/mason-hub/ 下的任何文件（memory 除外）
- Agent 架构配置
- 其他项目的文件或数据
- 生产配置（除非明确要求）
