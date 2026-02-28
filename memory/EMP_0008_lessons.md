# EMP_0008 SocialMesh PM 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: 先跑通再优化

Image Engine 开发中，pgvector / Scorer / promptag.app 采集三个组件先 defer：
- brute-force cosine similarity 在 500 条模板以内完全够用
- Scorer 需要真实使用数据才有意义，过早加没有反馈可算
- 手动导入可以替代自动采集
不要第一版就把所有组件做完，先让核心链路跑起来。
