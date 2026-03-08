---
title: "买家修改售后申请 msg_after_sale_update"
source_url: "https://open.xiaohongshu.com/document/developer/file/121"
file_id: "121"
category: "售后消息"
doc_type: "消息文档"
crawl_date: "2026-03-05T04:19:16.869214+08:00"
---

## 买家修改售后申请

### Tag名称

msg_after_sale_update

### 触发场景

  * 买家修改售后申请



### 参数说明

参数名称| 参数类型| 参数描述  
---|---|---  
returnsId| string| 售后id  
orderId| string| 订单Id  
returnType| int| 退货类型 1 退货退款 2 换货 3 仅退款(old) 4仅退款(已发货) 5未发货仅退款(未发货取消订单)  
requestFrom| int| 售后发起主体：1 买家申请 2 卖家申请 3 平台客服发起 4 系统修改  
refundFee| number| 退款金额（不包含运费）（单位：元）  
updateTime| long| 更新时间（毫秒）  
  
  

