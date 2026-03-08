---
title: "充值订单即将超期取消通知 msg_fulfillment_soon_cancel"
source_url: "https://open.xiaohongshu.com/document/developer/file/338"
file_id: "338"
category: "履约消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:14.704306+08:00"
---

## 充值订单即将超期取消通知

### Tag名称

msg_fulfillment_soon_cancel

### 触发场景

  * 针对虚拟充值类订单，订单即将超时自动退时通知商家



### 参数说明

**参数名称**| **参数类型**| **参数描述**  
---|---|---  
orderId| string| 订单号  
soonCancelTime| long| 超时自动退时间，时间戳，单位ms  
  
  

