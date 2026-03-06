# EMP_0012 Long-Term Memory

## 归属判断案例

### Video Pipeline 归属混乱 (2026-03-03, 首次审计发现)
- Mason 在 mason-hub/skills/video-download/ 快速搭建了 15+ 文件的视频管线，未定义归属
- SocialMesh 已有 image_engine 做图片生成，两套系统功能部分重叠
- 结论待定：Mason 正在评估迁移到 SocialMesh vs 保留在 mason-hub
- 教训：实验项目从第一个文件开始就该有临时归属标签

## Mason 决策偏好
- 反对过早抽象："想不到具体场景，本身就是答案"
- 偏好快速验证：先做出能用的东西，再考虑归属和架构
- 成本敏感：不接受为了"架构优雅"增加维护成本
- 务实主义：短期方案 3（Mason 直接操作）也是合理选择，等稳定后再迁移

## 剪辑规则库架构决策 (2026-03-06 会议)

### 归属判断
- styles/ 规则库放 `mason-hub/shared/editing_intelligence/styles/`（和 channel_profiles.json 同层）
- 它是平台级资产（渠道知识），不是品牌级资产
- 品牌特定内容（语气词典、品牌色）放 `shared/brands/{brand}/editing_overrides.md`
- 应用优先级：品牌覆盖 > 渠道规则 > 全局默认

### 三源归一决策
- 方案 C+（保持分离 + 手动对照），不做自动构建
- 理由：三个消费者（Gemini/FFmpeg/人）要不同格式，强行归一让每个都不舒服
- CHANNEL_GUIDES 擅长叙事性 prompt，JSON 擅长数值参数，.md 擅长人读 — 各有最佳形态
- Mason 反对过早抽象，等规则稳定后再考虑自动化

### 反模式警告
- styles/.md 如果只是 CHANNEL_GUIDES 的 Markdown 版就没有做的必要
- 它必须比现有内容更丰富（do/don't 示例、A/B 测试结论、历史教训）

## 产品边界经验
（待积累）
