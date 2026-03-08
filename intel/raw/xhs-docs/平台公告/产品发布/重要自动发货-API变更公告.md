---
title: "【重要】自动发货-API变更公告"
source_url: "https://open.xiaohongshu.com/document/developer/file/329"
file_id: "329"
category: "产品发布"
doc_type: "平台公告"
crawl_date: "2026-03-05T04:19:56.082809+08:00"
---

# 自动发货-API变更公告

## 1、业务场景

   针对电子资源类虚拟商品，商家均为固定的网盘链接发货。为方便商家发货，保障消费者及时收到链接，平台针对电子资源类目商品搭建自动发货链路，支持商家在发品时设定该商品对应的发货网盘链接和需要发品相关内容文案，用户支付后平台自动发出链接，无需商家主动操作发货。

## 2、业务流程

  1. 电子资源类目商品，商家发品时需维护自动发货链接&自动发货内容说明
  2. 订单产生后，无需调用发货接口进行发货，平台自动推进订单到已发货状态



## 3、本次API变动说明

顺序| API/消息| 变更类型| 变更说明  
---|---|---|---  
说明1| 公共 API：common.getDeliveryRule批量获取发货时间规则| 新增出参字段| 新增supportFulfillmentWays字段，表示当前支持的履约方式  
· 如果是虚拟资料类目，该值仅包含AUTO_DELIVERY，表示仅支持自动发货，必须传发货内容和发货链接  
· 非虚拟资料类目，该值为空，按普通链路发品即可  
说明2| 商品 API：product.createItemAndSku创建商品Item+Sku（新）  
product.updateItemAndSku更新商品Item+Sku（新）  
product.getDetailSkuList、product.searchItemList、product.getItemInfo查询接口| 新增入参字段| · item新增fulfillmentType字段，表示履约方式，针对虚拟资料类商品，如果履约规则要求仅支持自动发货，则需要传入对应类型的履约方式启用自动发货  
· sku新增deliveryInfo字段，包含发货内容说明和发货链接，对于开启自动发货的商品，必须传入该字段  
· 查询接口会相应在Item和Sku模型上会新增履约方式和发货内容字段，以供回填  
说明3| 订单API： order.getOrderDetail订单详情接口| 新增出参字段| 订单详情的simpleDeliveryOrderList节点下新增expressUrlProofList字段，表示发货链接列表信息，类型是List<String>格式，其仅在电子资源自动发货订单场景中下发自动发货链接信息，目前仅支持一条发货链接  
说明4| 订单API： order.modifyOrderExpressInfo修改运单接口| 新增入参字段| 新增expressUrlProofList字段，表示发货链接列表信息，类型是List<String>格式，其仅在电子资源自动发货订单场景中支持传入自动发货链接信息，目前仅支持一条发货链接  
  
  

