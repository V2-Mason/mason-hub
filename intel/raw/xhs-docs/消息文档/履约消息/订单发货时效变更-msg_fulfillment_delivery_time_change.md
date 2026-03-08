---
title: "订单发货时效变更 msg_fulfillment_delivery_time_change"
source_url: "https://open.xiaohongshu.com/document/developer/file/118"
file_id: "118"
category: "履约消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:13.293662+08:00"
---

## 订单发货时效变更

### Tag名称

msg_fulfillment_delivery_time_change

### 触发场景

  * 商家创建报备单，向平台提交影响发货时效的申请



### 参数说明

参数名称| 参数类型| 参数描述  
---|---|---  
orderId| string| 订单号  
promiseLastShipTime| long| 变更后的 最晚发货日期  
updateTime| long| 更新时间（毫秒）  
  
  

