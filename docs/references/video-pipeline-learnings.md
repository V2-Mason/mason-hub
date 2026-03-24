# 视频管线经验 (2026-03-07)

## 成本决策
- **VEO → Seedance 永久切换（Mason 决策）：** VEO 占 Gemini API 成本 96%，Seedance 成本约 1/30
- `config.py` 已改 `VIDEO_ENGINE = 'seedance'` 为默认
- VEO 配额跨模型共享（~10次/天，UTC 重置）

## 核心改进清单（基于"产品短视频三板斧"课程）
1. 配音重生成（per-cut TTS）
2. 心跳节奏（禁止均匀，五维对比）
3. J/L-Cut（audio_offset_seconds）
4. 5 个结构公式（痛点/结果/反转/悬念/困境）
5. 卖点口语化 + 五感设计 + 构图指导 + 色彩心理学
6. SFX 音效层 + 花字分类
7. 拉片反馈循环（video_teardown.py）
8. Hook 视觉库（8种开头类型）

## VEO Prompt 教训
- 不用标签堆叠，写流畅叙事
- 不传 voiceover/text_overlay（中文超出能力）
- camera "固定"必须给默认微运动（否则被安全过滤器拦截）
- props 描述外观不写品牌名

## 多 Agent 并行开发经验
- 按文件区域分工不冲突，按依赖关系分批
- 4 Agent 完成 871 行新增，全部一次通过
- 风险区：assemble.py 改动密集，接口字段名必须事先约定
