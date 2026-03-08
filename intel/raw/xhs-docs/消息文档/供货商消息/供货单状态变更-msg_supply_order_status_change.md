---
title: "供货单状态变更 msg_supply_order_status_change"
source_url: "https://open.xiaohongshu.com/document/developer/file/348"
file_id: "348"
category: "供货商消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:27.045247+08:00"
---

## 供货单状态变更

### Tag名称

msg_supply_order_status_change

### 触发场景

  * 用户下单
  * 用户支付后，订单触发风控
  * 用户支付后，订单走完风控，等待操作
  * 卖家对部分商品发货
  * 卖家对全部商品发货
  * 买家确认收货或系统自动确认收货，且母订单状态变为「已完成」
  * 售后完成，订单关闭



### 参数说明

参数名称| 参数类型| 参数描述  
---|---|---  
supplyOrderId| string| 供货单号  
supplyOrderStatus| int| 供货单状态，1=待支付，2=已支付，21=已支付待履约，4=待发货，5=配货中，55=部分发货，6=已发货未签收，65=已发货已签收，7=完成，71=关闭，998=已取消  
eventTime| long| 事件时间（毫秒）  
  
### 补充说明（重要）

5=配货中状态，是发货时供货单状态从4变更到55或6的中间临时态，一般不会卡在该状态，可以近似视作为待发货状态
