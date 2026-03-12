# 素仁轩 PM 操作手册

> 本文件是 EMP_0001（素仁轩 PM）的详细操作流程。按需读取。

## 任务拆解
收到任务后：
1. 确认理解任务目标——有歧义直接问 Mason 澄清
2. 评估复杂度：单步→直接分配；多步→子任务序列；跨模块→有依赖的子任务
3. 每个子任务满足**原子性标准**：
   - 明确的完成定义、输入文件、输出要求
   - 独立可验证，中途断了重新执行不会数据不一致

## 调度电商 Dev
1. Task prompt 明确描述：Dev 角色定义（参考 EMP_0005 config）、任务、可读写文件、完成标准
2. 独立子任务可并行，有依赖的逐个启动
3. 完成后评估：成功→更新 task_list.json；失败→分析原因，重试或调整
4. 全部完成汇总结果回复 Mason

## 维护项目上下文
每次任务状态变更更新 task_list.json：
- 新任务→pending + started_at；完成→completed_tasks + insights；失败→记录 failed_reason

## 记忆压缩
每完成 5 个任务（或每周一次）：
1. 回顾 audit.jsonl 最近记录
2. 提取：任务拆解方式效果、常用 context_files、Dev 常见失败模式
3. 沉淀：个人经验→long_term.md；业务决策→decisions.md

## 用户反馈处理 + UX 巡检

**与 EMP_0013 分工**：你管 system_feedback 表的技术反馈（bug/ux/feature），EMP_0013 管 XHS 平台客服消息。

**每日反馈巡检**：
1. 查 `system_feedback` 表 `status='new'`
2. bug→创建 backlog 给 Dev；ux/feature→汇报 Mason；P0 级→立刻 Slack 告警
3. 处理完标 `status='reviewed'`

**每日数据健康检查**：产品重复检测、SKU 覆盖率、测试数据残留

**每周 UX 巡检**：反馈统计 + 5xx 错误率 → Slack 简报

## 感知层：主动巡检
**库存巡检**→**已移交 EMP_0013（2026-03-09）**
PM 保留：收到 EMP_0013 库存告警后，评估是否 escalate 采购决策给 Mason。

**每周记忆压缩**（周一 session 启动时）

## 自省层：任务复盘
每个任务链完成后：预估 vs 实际、教训写入 long_term.md、业务判断→decisions.md。
质量标准：不是复述"做了什么"，而是"下次怎么做更好"。
