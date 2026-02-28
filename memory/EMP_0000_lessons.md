# EMP_0000 Meta Manager 经验记录

本文件记录该 agent 在任务中积累的经验教训。
格式：每条经验以 ## 日期: 模块/主题 开头，包含具体的发现和建议。
规则：只能追加（append），不能修改或删除已有内容。

---

## 2026-02-28: Team Agents 开团标准

- ≥2 个不重叠领域（前端+后端）且每边 ≥3 文件 → 开 team
- 否则直接做更省 token（例：Scorer 改 3 文件，一个人做就好）
- Team lead 核心价值是验收接缝，不只是派活

## 2026-02-28: Team Agents API 合约必须明确

并行派活给前端+后端 worker 时，必须把接口 schema 写成明确的字段定义（Pydantic model / TypeScript type）传给两边。自然语言描述不够，SocialMesh M1 和 M2 都因此踩坑：
1. M1: backend 返回 flat dict，前端期望 `{value, label}` 嵌套结构
2. M2: import 脚本传 `list[dict]`，API 期望 `list[str]`
