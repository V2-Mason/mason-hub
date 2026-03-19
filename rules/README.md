# 运营决策规则库

Mason 在实际运营中积累的决策规则。这些规则是未来 merchant agent 产品的"出厂设置"。

## 规则分类

| 标签 | 含义 | 商业化价值 |
|------|------|-----------|
| universal | 所有电商商家都适用 | 高 — 直接成为产品默认值 |
| vertical | 特定品类才适用 | 中 — 垂直版本的差异化 |
| personal | Mason 个人习惯 | 低 — 不可复制 |

## 规则格式

每条规则一个 Markdown 文件，使用 TEMPLATE.md 的格式。

## 命名规范

`{domain}_{action}_{简短描述}.md`

示例:
- `inventory_reorder_threshold.md`
- `pricing_competitor_response.md`
- `content_publish_frequency.md`

## 何时记录

每当你在运营中做出一个可以量化的决策时，记录下来：
- 设定了一个阈值（"库存低于X就补货"）
- 定义了一个规则（"竞品降价超过Y%才跟进"）
- 建立了一个流程（"每周一检查Z"）
