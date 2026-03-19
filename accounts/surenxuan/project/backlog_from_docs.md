# 素仁轩 — 从旧文档提取的待办项

> 提取日期: 2026-03-19
> 来源: surenxuan/docs/specs/07, 11 + docs/qa/Operational_Feedback_Issues.md
> 这些项从 archive 前提取，确保不丢失未完成的工作

---

## 来自 11-UI-REVIEW-AND-FIXES（UI 走查）

### P0（数据错误/核心功能）
- [ ] BUG-001: 产品零售价全部为 ¥0（库存页 retail_price 未写入 products 表）
- [ ] BUG-002: 货币符号显示混乱（¥/$/₩ 混用）
- [ ] BUG-003: 库存缺货数据不一致

### P1（功能缺失/流程断裂）
- [ ] FEAT-001: 采购验收流程优化
- [ ] FEAT-002: 采购单状态节点信息录入
- [ ] FEAT-003: 采购单状态可回退
- [ ] FEAT-004: 采购单可编辑和删除

### P2（体验优化）
- [ ] OPT-001: 选品工作台表格增强
- [ ] OPT-002: 选品工作台批次命名
- [ ] OPT-003: 采购单命名
- [ ] OPT-004: 库存管理产品可点击查看详情
- [ ] OPT-005: 数据看板空数据状态优化
- [ ] OPT-006: 采购单详情增加汇率和原价信息

### P3（未来优化）
- [ ] FUTURE-001: 选品工作台与已有库存对比
- [ ] FUTURE-002: 采购到货提醒
- [ ] FUTURE-003: 验收异常报表
- [ ] FUTURE-004: 库存盘点功能
- [ ] FUTURE-005: 采购管理列表筛选和搜索

---

## 来自 Operational_Feedback_Issues（Mason 实操反馈）

- [ ] FIX-19: 清单解析器容错性增强（标题行/合并单元格）
- [ ] FIX-20: 待确认产品原因不透明 + 品类筛选下的显示问题
- [ ] FIX-21: 采购验收增加条码扫描支持
- [ ] FIX-22: 验收损耗交互逻辑优化

---

## 来自 07-DEVELOPMENT-PHASES Phase 5+（未来功能）

> Phase 1-4 已全部完成。Phase 5+ 中仍有价值的功能：

- [ ] NMPA 备案查询集成
- [ ] POS 系统对接
- [ ] 企业微信集成
- [ ] 多供应商支持
- [ ] 线上平台 API 对接（抖音/小红书订单自动同步）
- [ ] 日历导出到 iPhone（.ics 文件）

> 以下功能已由 mason-hub kernel 替代，不再需要：
> ~~Supervisor Agent~~ → mason-hub kernel 编排
> ~~Telegram Bot~~ → mason-hub Slack 通知
> ~~OpenClaw 集成~~ → 已决定不基于 OpenClaw
