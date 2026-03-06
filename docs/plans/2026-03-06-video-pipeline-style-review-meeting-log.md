# 视频生产线剪辑规则评审 — 会议记录

> 日期：2026-03-06 21:15-21:52 CST
> 主持：Session Operator (Meta Manager 代理)
> 参会：EMP_0008, EMP_0009, EMP_0010, EMP_0012

---

## 会前准备

- 参考项目：[videocut-skills](https://github.com/Ceeon/videocut-skills)（Claude Code Skills 视频剪辑 Agent）
- 借鉴三个架构模式：用户习惯目录（可进化规则库）、Skill 分层、自更新机制
- 草拟了 styles/ 7 个规则文件（字幕/转场/渠道/色彩/文案/音画对齐/自更新日志）

## 议题与发言

### 议题 1：三源归一

**EMP_0008 (SocialMesh PM)**：
- styles/.md 应该是运营层 source of truth，但不应直接驱动代码
- 推荐数据流：styles/.md → 派生 CHANNEL_GUIDES + VOICE_STYLES + channel_profiles.json
- v1 先手动保持一致，跑 2-3 轮再自动化
- 发现 VOICE_STYLES 和 CHANNEL_GUIDES 已经有漂移风险

**EMP_0009 (Content-Tech Dev)**：
- 三套数据源各服务不同消费者，不能简单合并
- 提出 YAML frontmatter + build_profiles.py 方案（~80 行新脚本 + 改 multicut.py ~15 行）
- GOAL_GUIDES 保持 Python 硬编码（跨渠道，不按渠道文件组织）

**EMP_0012 (Product Architect)**：
- styles/ 放 mason-hub/shared/editing_intelligence/（和 channel_profiles.json 同层）
- 推荐方案 C+（保持分离 + 对照 checklist），反对自动构建（过早抽象）
- 三个消费者需要不同格式，强行归一让每个都不舒服
- 警告：如果 styles/.md 只是 CHANNEL_GUIDES 的 Markdown 版就没有做的必要，必须比现有内容更丰富

**Mason 决策**：先手动维护，styles/.md 作为"审美笔记本"，不急自动化。

---

### 议题 2：音画对齐

**EMP_0008**：
- 明确支持音频驱动视频
- 核心论点：口播是信息载体（90%+ 信息通过旁白+字幕获取），画面是辅助
- 当前流程是"被动适配"（voiceover_writer 塞话进固定时长），导致口播对不上
- 产品聚焦版和公众号版无口播，保持视频驱动

**EMP_0009**：
- 分析了当前 tts_generate.py 的处理方式（atempo 加速/apad 补静音）
- 提出 align.py 方案：clip 降速下限 0.7x，超出物理时长冻结最后一帧
- 改动量：新建 align.py ~120 行，改 tts_generate.py ~40 行，改 assemble.py ~20 行

**Mason 决策**：音频驱动视频，但排最后（依赖 TTS + 文案稳定）。

---

### 议题 3：字幕排版升级

**EMP_0008**：
- P0 优先做：字幕位置精确控制、多行文字换行、描边+阴影组合
- P1：渐变遮罩、字幕动画
- 重要补充：最大问题可能不是 ffmpeg 参数，而是 Gemini 生成的 text_overlays 文案本身就土

**EMP_0009**：
- border(borderw+bordercolor) 已支持，shadow 需加 ~5 行
- 精确坐标需改 pos_map ~10 行
- 渐变遮罩 ~25 行，建议 v2
- 新旧 EDL 用 .get() fallback 兼容，不需要版本号
- 总改动 ~60 行

**Mason 决策**：P0 描边+阴影+精确坐标，P1 渐变遮罩+动画。

---

### 议题 4：中文文案规则

**EMP_0010 (Content Creator)**：
- VOICE_STYLES 和禁用词有冲突（"绝了" vs "绝绝子"），需精确到词形
- 补充 8 条遗漏的 AI 味表达（"值得一提的是""不得不说""作为一款"等）
- 称呼规范太死板，建议按渠道分三级 — Mason 决定先统一"姐妹们"
- 价格模糊化会影响转化，建议分场景 — Mason 采纳
- Hook 模板只有痛点条件句一种，不够，补充了反常识/数字锚点/场景还原/负面切入/时间紧迫/争议对比 6 种
- voiceover_writer.py 缺 chars-per-second 校验

**EMP_0008**：
- 渠道语气不只是词汇层面，还有句式结构差异
- 每个渠道至少给 3-5 个正面范例句 + 反面范例句
- AI 味优先级排序：连接词 > 填充句式 > 四字成语 > "让我们一起" > 过度使用"的" > 无意义修饰词
- 品牌调性约束只在 multicut.py 生效，voiceover_writer.py 完全缺失 — 必须贯穿

**EMP_0009**：
- 三层防御方案：prompt 约束 + 后处理替换 + 检查清单
- 后处理比 prompt 约束更可靠（确定性，不增加 token 成本）
- 改动量 ~70 行

**Mason 决策**：三层防御，称呼统一"姐妹们"，价格分场景。

---

## 优先级讨论

各方排序对比：

| 排序 | Dev | PM | Architect |
|------|-----|-----|-----------|
| 1 | 中文文案（改动最小） | 音频驱动（最大痛点） | 写文档不改代码 |
| 2 | 三源归一 | AI 味清洗 | 字幕参数 |
| 3 | 字幕排版 | 字幕排版 | TTS 对齐 |
| 4 | 音画对齐 | 三源归一 | 自更新机制 |

**Mason 决策**：按依赖链排序 — 文档 → 中文文案+字幕并行 → 音画对齐。

---

## 会后执行

- Phase 1 (styles/.md 第一版)：已由 EMP_0009 完成，9 个文件 + 1 个品牌覆盖文件
- Phase 2a/2b/3：待执行
