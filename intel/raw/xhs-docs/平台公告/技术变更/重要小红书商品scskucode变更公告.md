---
title: "【重要】小红书商品scskucode变更公告"
source_url: "https://open.xiaohongshu.com/document/developer/file/262"
file_id: "262"
category: "技术变更"
doc_type: "平台公告"
crawl_date: "2026-03-05T04:20:21.135993+08:00"
---

致亲爱的小红书开放平台合作伙伴：

目前小红书商品体系改造计划将scskucode（对应后台小红书编码）下线，预计最终下线日期3.31日。涉及到的接口有商品接口、订单接口、售后接口，下线后入参、出参均不带有scskucode，为保证后续下线流程平稳可控，对服务商业务无影响，现提前对服务商进行周知，收集服务商的使用方式：

1、 若已有企业微信群，请群内将涉及到scskucode的使用方式、是否存储scskucode进行说明

2、 若未加入企业微信群，请发送邮件到[songbinlin@xiaohongshu.com](<songbinlin@xiaohongshu.com>)

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
  
如有使用scskucode，请服务商于2023年11月19日前将通过微信群/邮件将使用的方式告知小红书研发，方便后续小红书研发提供对应的替代方案，以便服务商进行后续相应的改造。

  


小红书开放平台

2023年11月06日

  


  


  

