---
title: "【重要】小红书商品scskucode变更推迟公告"
source_url: "https://open.xiaohongshu.com/document/developer/file/269"
file_id: "269"
category: "技术变更"
doc_type: "平台公告"
crawl_date: "2026-03-05T04:20:24.174734+08:00"
---

致亲爱的小红书开放平台合作伙伴：

目前小红书商品体系改造计划将scskucode（对应后台小红书编码）下线，预计最终下线日期从3.31日延迟至7.31日。涉及到的接口有商品接口、订单接口、售后接口，下线后入参、出参均不带有scskucode。

  


涉及接口如下

method| 接口功能  
---|---  
product.getDetailSkuList| sku列表查询  
product.createSkuV2| 创建sku  
product.updateSkuV2| 更新sku  
product.getItemInfo| 获取商品详情  
order.getOrderDetail| 获取订单详情  
afterSale.getAfterSaleDetail| 获取售后详情（旧）  
afterSale.getAfterSaleInfo| 获取售后详情（新）  
  
  


小红书开放平台

2023年03月05日

  

