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

## 产品边界经验
（待积累）
