# EMP_0000 Meta Manager — 长期记忆

## 跨域调度经验

### Cron 部署后必须验证首次执行 (2026-02-28)
- Scout 三档 cron 注册后从未实际触发过，但没有人发现
- 规则：新 cron 部署后，必须安排手动触发一次 + 检查 logs 有输出，确认端到端通路
- 不能只看 `crontab -l` 有条目就认为"已部署"

### 每个自动化 agent 必须有手动触发通路 (2026-02-28)
- `run-agent.sh` 无法在 Claude Code session 内执行（`claude -p` 不支持嵌套）
- 因此每个 cron agent 都应有对应的 `/skill` 作为 Mason 手动触发的替代方案
- 两条路径：cron 自动 + `/skill` 手动，缺一不可

### 跨境架构：大使馆模式 (2026-02-28, Mason 确认)
- **核心思路**：不搬 SocialMesh 到中国，也不拆平台模块。在阿里云部署"中国办事处"(china-hub)，作为 GCP 总部在中国的全权代理
- GCP mason-hub = 总部（战略决策 + 全球平台），阿里云 china-hub = 中国办事处（中国平台执行 + 数据合规）
- 敏感数据绝不出境，只传脱敏聚合数据
- **EMP_1000 China Operations Agent**（未来）= 中国区总管，Manager Agent 的唯一中国对话窗口
  - Manager Agent 不直接跟小红书/微信 Connector 交互，只跟 EMP_1000 对话
  - 平台数量增加不影响 Manager Agent 复杂度
- **跨境通信协议**（标准化 JSON）：
  - 总部→中国：业务目标、营销策略、定价指导（无 PII）
  - 中国→总部：销售统计、库存快照、品类趋势（脱敏聚合）
  - 中国→总部：审批请求（脱敏决策上下文）
  - 总部→中国：审批结果（批准/拒绝 + 理由）
- **演进路线**：Phase 1 阿里云做哑执行网关 → Phase 2 加规则引擎 → Phase 3 部署 EMP_1000
- **可扩展**：未来 japan-hub、korea-hub 用同样模式复制
- 注册路径：素仁轩中国主体 → 商家后台系统（自研）→ 未来转 SaaS 时另注册跨境企业 ERP
- 合规红线：数据不跨平台合并、用户退订删数据、XHS 界面不引导去其他平台

## 晨会模式总结

## Agent 协作 Pattern
