# 素仁轩 — Code Agent 详细规格

> 提取自原 surenxuan/docs/specs/04-AGENT-SPECS.md (2026-02)
> 编排层 EMP 配备见: kernel/deployments/surenxuan.yaml
> 以下是执行层 Python agent 的内部设计细节

---

## data_coo_agent.py（数据 COO）

**定位**: 数据底座和运营监控中枢。不直接与用户交互，通过 Web 界面间接。

**Memory 类型**:
| memory_type | 用途 | 示例 |
|---|---|---|
| business_insight | 经营洞察（供其他 Agent 读取） | current_bestsellers, seasonal_trend, budget_status |

**触发的事件**: PRODUCT_STOCKED, INVENTORY_LOW, INVENTORY_STOCKOUT, CUSTOMER_DORMANT, CUSTOMER_FOLLOWUP_DUE, CUSTOMER_REPURCHASE_DUE, RISK_DETECTED, REPORT_READY, PRODUCT_EXPIRING

**订阅的事件**: SALE_RECORDED（扣库存 + 更新财务 + 更新客户 + 安排跟进）

**LLM 场景**: 周报/月报的 AI 分析和策略建议；补货和滞销处理建议

---

## selection_agent.py（选品清单助手）

**定位**: 供货清单的"翻译官+筛选器"。仅在上传新清单时激活。

**运行模式**: Pipeline（顺序流水线）：解析 → 翻译 → 分类 → 计算 → 过滤 → 输出

**Memory 类型**:
| memory_type | 用途 | 示例 |
|---|---|---|
| translation_cache | 翻译缓存 | key:이니스프리 → value:{cn:"悦诗风吟"} |
| classification_rule | 分类学习 | key:绿茶+精华 → value:{l1:"护肤",l2:"精华"} |
| brand_mapping | 品牌名映射 | key:이니스프리 → value:{cn:"悦诗风吟",en:"Innisfree"} |

**LLM 场景**: 韩文→中文翻译（缓存未命中）；产品分类（规则未匹配）；特殊化妆品判断

---

## content_agent.py（内容营销引擎）

**定位**: 营销总监+设计师+客服培训师。最复杂的 Agent。

**运行模式**: Generator + Critic（文案生成）：Generator 生成 → Critic 检查合规 → 不通过反馈修改 → 最多 3 轮

**Memory 类型**:
| memory_type | 用途 | 示例 |
|---|---|---|
| channel_style | 渠道风格偏好 | key:wechat_pyq → value:{tone:"亲切口语化", avg_length:150} |
| prompt_template | 图片 Prompt 模板 | key:skincare_scene_natural → value:{template:"...", satisfaction:4.2} |
| compliance_rule | 合规审核规则 | key:forbidden_claims → value:{rules:[...]} |
| content_performance | 内容效果记忆 | key:wechat_pyq_product_intro → value:{avg_likes:25, best_time:"20:00"} |
| product_faq | 产品知识库 | key:green_tea_serum_sensitivity → value:{answer:"...", source:"customer_feedback"} |

**订阅的事件**: CUSTOMER_FOLLOWUP_DUE（生成话术建议）, CUSTOMER_DORMANT（生成唤醒建议）

**LLM 场景**: 文案生成、合规审核、Copilot 推荐、图片生成、录屏 OCR

---

## 通用规范

每个 Agent 必须有：
1. `AgentMemoryStore` 实例
2. `ContextBuilder` 方法（为 LLM 调用构建上下文）
3. 清晰的输入/输出接口
4. API 用量记录（每次 LLM 调用记录 tokens 和 cost）

成本控制：
- 可缓存操作先查 Memory
- 批量合并翻译请求
- 简单任务用便宜模型，复杂任务用智能模型
