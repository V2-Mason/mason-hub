---
title: "订单状态变更 msg_fulfillment_status_change"
source_url: "https://open.xiaohongshu.com/document/developer/file/115"
file_id: "115"
category: "履约消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:11.070181+08:00"
---

## 订单状态变更

### Tag名称

msg_fulfillment_status_change

### 触发场景

  * 用户支付后，订单触发风控
  * 支付后，跨境商品清关
  * 用户支付后，订单走完风控，等待操作
  * 卖家对部分商品发货
  * 卖家对全部商品发货
  * 买家确认收货或系统自动确认收货，且母订单状态变为「已完成」
  * 售后完成，订单关闭



### 参数说明

参数名称| 参数类型| 参数描述  
---|---|---  
orderId| string| 订单号  
orderStatus| int| 订单状态，1已下单待付款 2已支付处理中 3清关中 4待发货 5部分发货 6待收货 7已完成 8已关闭 9已取消 10换货申请中  
updateTime| long| 更新时间（毫秒）  
  
### 补充说明（重要）

订单消息推送可能会反馈两个状态4：  履约单状态目前“待发货”和“已拣选”都会被转化成status=4的消息，erp可能收到重复的status=4的消息，第一个消息是订单变成待发货的时候 第二个是发货的时候发的。需要isv做好幂等。
