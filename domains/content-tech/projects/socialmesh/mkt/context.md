# 品牌上下文引用

> 品牌上下文由 Account Manager (EMP_0011) 维护，不在项目目录内重复定义。
> 所有品牌相关信息从 brief 文件读取。

## 品牌 Brief 位置

当前服务的品牌：
- **素仁轩** → `shared/brands/surenxuan/brief.md`

## 读取规则

- EMP_0008（内容运营总监）：每次做内容策略前读取 brief
- EMP_0010（Creator）：每次写内容前读取 brief
- 如发现 brief 信息不足或需要更新，反馈给 Account Manager，不自行补充

## 为什么不在这里定义品牌

品牌上下文集中管理在 `shared/brands/` 下，好处：
1. 单一 source of truth — 不会出现多处定义不一致
2. Account Manager 统一维护 — 修改有明确责任人
3. 跨项目复用 — 同一品牌的不同项目读同一份 brief
