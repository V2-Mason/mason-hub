---
title: "物流服务订阅状态变更 msg_logistic_service_subscribe_status_change"
source_url: "https://open.xiaohongshu.com/document/developer/file/290"
file_id: "290"
category: "履约消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:14.101566+08:00"
---

## 物流服务订阅状态变更

### Tag名称

msg_logistic_service_subscribe_status_change

### 触发场景

  * 商家订购物流服务时，订阅单状态变更消息通知



### 参数说明

参数名称| 参数类型| 参数描述  
---|---|---  
sellerId| string| 商家ID  
sellerName| string| 商家名称  
sellerPhone| string| 商家电话号码  
status| int| 订购状态，1 生效中 2 冻结 3 失效 4 申请中 5 申请拒绝 6 申请通过 7 订购失败  
subscribeId| string| 订阅单ID  
subscribeResourceCode| long| 订阅资源编码  
subscribeTime| long| 订阅时间(毫秒)  
  
  

