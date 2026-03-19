# Agent #0 — 数据COO · QA检查指令

> **角色**：你是K-Beauty工作台的数据COO。你的日常职责是监控系统所有数据的准确性、一致性和完整性。
> **当前任务**：这是你的"上岗前检查"——在正式开始工作之前，你需要全面审查系统的数据健康状况。
> **系统地址**：http://localhost:8000
> **输出**：将检查结果写入 `reports/agent0-data-health-report.md`

---

## 检查方法

你有三种检查手段，应交叉使用以验证数据一致性：

1. **数据库直查**：直接查询SQLite数据库，获取原始数据
2. **API调用**：通过后端API获取数据，验证API返回是否与数据库一致
3. **页面读取**：用Playwright打开页面，读取页面上显示的数据，验证是否与API/数据库一致

**三方数据一致 = 健康。任何两方不一致 = 发现问题。**

---

## 检查项清单

### 第一组：产品数据完整性

先找到SQLite数据库文件位置（通常在项目根目录或data目录下），然后执行以下检查：

```
CHECK-001: 产品零售价完整性
  查询：SELECT COUNT(*) FROM products WHERE retail_price IS NULL OR retail_price = 0
  预期：结果为0（所有产品都应有零售价）
  如果不为0：列出所有零售价为空或0的产品（名称、品牌、SKU）

CHECK-002: 产品成本价完整性
  查询：SELECT COUNT(*) FROM products WHERE cost_price IS NULL OR cost_price = 0
  预期：结果为0
  如果不为0：列出所有成本价为空或0的产品

CHECK-003: 产品品牌完整性
  查询：SELECT COUNT(*) FROM products WHERE brand IS NULL OR brand = ''
  预期：结果为0

CHECK-004: 产品品类完整性
  查询：SELECT COUNT(*) FROM products WHERE category IS NULL OR category = ''
  预期：结果为0

CHECK-005: SKU唯一性
  查询：SELECT sku, COUNT(*) as cnt FROM products GROUP BY sku HAVING cnt > 1
  预期：无重复SKU
  如果有重复：列出所有重复的SKU及对应产品

CHECK-006: SKU格式一致性
  查询：SELECT sku FROM products LIMIT 20
  检查：所有SKU是否遵循统一的命名规则
  记录：发现的SKU格式模式（有几种不同的格式？）
```

### 第二组：库存数据准确性

```
CHECK-007: 库存数量合理性
  查询：SELECT name_cn, brand, current_stock FROM products WHERE current_stock < 0
  预期：无负数库存
  如果有：列出所有负库存产品（这是严重的数据错误）

CHECK-008: 库存状态标签准确性
  从数据库获取：每个产品的current_stock值
  从页面获取：库存管理页面每个产品的"状态"标签（正常/告急/缺货）
  交叉验证：
    current_stock = 0 → 状态应该是"缺货"
    current_stock <= 低库存预警阈值 → 状态应该是"告急"
    current_stock > 低库存预警阈值 → 状态应该是"正常"
  先检查设置页面的"低库存预警(阈)"值是多少

CHECK-009: 看板库存指标验证
  从数据库计算：
    total_sku = SELECT COUNT(*) FROM products（或有库存的产品数）
    normal_count = 状态为正常的产品数
    warning_count = 状态为告急的产品数
    stockout_count = 库存为0的产品数
  从看板页面读取：
    "库存状态"卡片的数字和副标签
  对比是否一致
```

### 第三组：财务数据准确性

```
CHECK-010: 库存总成本验算
  从数据库计算：SELECT SUM(cost_price * current_stock) FROM products WHERE current_stock > 0
  从看板页面读取："库存总成本"卡片的金额
  对比是否一致（允许四舍五入误差 ≤ ¥1）

CHECK-011: 库存零售值验算
  从数据库计算：SELECT SUM(retail_price * current_stock) FROM products WHERE current_stock > 0
  从看板页面读取："库存零售值"卡片的金额
  对比是否一致（允许四舍五入误差 ≤ ¥1）

CHECK-012: 单品毛利率验算
  抽取5个产品，分别计算：
    毛利率 = (retail_price - cost_price) / retail_price
  与选品页面显示的毛利率对比
  检查是否有产品的毛利率低于设置中的最低毛利率(40%)

CHECK-013: 采购单金额验算
  随机选取3个采购单，从数据库查询其明细：
    SELECT SUM(cost_price * quantity) FROM purchase_order_items WHERE purchase_order_id = X
  与采购管理页面显示的总金额对比
```

### 第四组：跨页面数据一致性

```
CHECK-014: 看板品类分布 vs 库存管理
  从看板"库存品类分布"读取：护肤X件、彩妆Y件
  从库存管理页面统计：筛选护肤品类，统计总库存件数
  对比是否一致

CHECK-015: 看板品牌库存 vs 库存管理
  从看板"品牌库存"读取：各品牌的库存数量
  从数据库查询：SELECT brand, SUM(current_stock) FROM products GROUP BY brand
  对比是否一致

CHECK-016: 库存预警区域准确性
  从看板"库存预警"区域读取：告急产品列表和数量
  从库存管理页面读取：筛选"告急"状态的产品
  对比是否一致

CHECK-017: 看板"总客户数" vs 客户管理
  从看板读取："总客户数"和"活跃"数
  从客户管理页面统计：客户列表中的总数
  从数据库查询：SELECT COUNT(*) FROM customers
  三方对比
```

### 第五组：货币和格式一致性

```
CHECK-018: 货币符号统一性
  浏览以下页面，检查所有金额是否都有货币符号¥：
    - 数据看板（所有金额卡片）
    - 选品工作台（成本价、零售价、首批成本）
    - 采购管理列表页（采购金额）
    - 采购单详情页（成本价、小计、合计）
    - 库存管理（零售价）
    - 销售追踪（销售额、毛利润、实际售价）
  记录：是否有裸数字（没有¥符号的金额）
  记录：是否有使用$或₩等其他符号的情况

CHECK-019: 数字格式一致性
  检查所有金额的小数位数是否一致（应该统一为2位小数）
  检查大数字是否有千位分隔符（如¥8,152.56 vs ¥8152.56）
  记录不一致的地方
```

### 第六组：设置参数影响验证

```
CHECK-020: 汇率设置影响验证
  从设置页面读取：韩元汇率值
  从选品页面取一个产品的韩元原价和人民币成本价
  验算：人民币成本价 ≈ 韩元原价 × 汇率
  注意：需要先确认成本价是否还包含了运费分摊等因素

CHECK-021: 加价倍率影响验证
  从设置页面读取：加价倍率
  从选品页面取一个产品的成本价和零售价
  验算：零售价 ≈ 成本价 × 加价倍率
  如果不等：检查零售价是否经过了取整或范围限制

CHECK-022: 库存预警阈值验证
  从设置页面读取：低库存预警阈值和告急库存阈值
  从库存管理中找一个库存数量刚好等于阈值的产品
  检查其状态标签是否正确（边界值测试）
```

---

## 输出格式

将所有检查结果写入 `reports/agent0-data-health-report.md`，格式如下：

```markdown
# Agent #0 数据健康检查报告

**检查时间**：YYYY-MM-DD HH:MM
**系统地址**：http://localhost:8000
**数据库位置**：[实际路径]

## 检查总结

| 指标 | 结果 |
|------|------|
| 总检查项 | 22 |
| 通过 | X |
| 失败 | Y |
| 警告 | Z |

## 发现的问题

### [P0] ISS-数据-001：[问题标题]
- **检查项**：CHECK-XXX
- **预期**：...
- **实际**：...
- **影响**：...
- **建议修复**：...

### [P1] ISS-数据-002：[问题标题]
...

## 通过的检查项

（简要列出所有通过的检查项编号和名称）

## 数据快照

（记录关键数据的当前值，作为基准线）
- 总产品数：X
- 有库存产品数：X
- 库存总成本：¥X
- 库存零售值：¥X
- 总客户数：X
- 总销售记录：X
```

---

## 执行提醒

1. 先找到数据库文件位置，了解数据库的表结构（可能和PRD中的设计有差异）
2. 如果某个表或字段不存在，记录在报告中（说明"PRD设计了但未实现"）
3. 每个检查项无论通过还是失败，都要记录实际数据
4. 截图不是必须的，但如果发现页面显示明显异常，请截图保存到 `reports/screenshots/`
5. 如果发现某个检查项无法执行（比如相关功能还未实现），标记为"N/A - 功能未实现"
