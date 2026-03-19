# Cross-Project Data Schemas

Mason 联邦体系的跨项目标准数据格式。所有 connector 的 transforms 必须将项目内部数据转换为这些标准格式。

## 设计原则

1. **最小公约数** — 只定义所有项目都可能用到的字段，项目特有字段放在 `extra` 对象中
2. **向后兼容** — 新增字段不破坏旧版本，所有新字段必须 optional
3. **市场无关** — schema 不假定特定市场/币种，通过 `market` 和 `currency` 字段区分

## 文件列表

| Schema | 描述 | 主要消费者 |
|--------|------|-----------|
| inventory.schema.json | 库存数据 | merchant agent, surenxuan |
| product.schema.json | 商品数据 | 所有项目 |
| price.schema.json | 价格数据 | merchant agent, surenxuan |
| order.schema.json | 订单数据 | surenxuan |
| content.schema.json | 内容数据 | socialmesh, tiktok-viral |

## 版本

当前: v0.1（声明式，无运行时校验）
