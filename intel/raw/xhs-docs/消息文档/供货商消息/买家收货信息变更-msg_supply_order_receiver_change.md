---
title: "买家收货信息变更 msg_supply_order_receiver_change"
source_url: "https://open.xiaohongshu.com/document/developer/file/349"
file_id: "349"
category: "供货商消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:27.945627+08:00"
---

## 买家收货信息变更

### Tag名称

msg_supply_order_receiver_change

### 触发场景

  * 收货信息被商家修改
  * 收货信息被买家修改
  * 收货信息被平台客服修改



### 参数说明

参数名称| 参数类型| 参数描述  
---|---|---  
supplyOrderId| string| 供货单号  
openAddressId| string| 更新后的收货人信息字符串  
eventTime| long| 事件时间（毫秒）  
  
  

