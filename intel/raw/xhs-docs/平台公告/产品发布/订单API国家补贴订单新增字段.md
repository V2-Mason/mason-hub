---
title: "订单API国家补贴订单新增字段"
source_url: "https://open.xiaohongshu.com/document/developer/file/316"
file_id: "316"
category: "产品发布"
doc_type: "平台公告"
crawl_date: "2026-03-05T04:19:51.514994+08:00"
---

## 1、业务场景

   为了完善国家补贴订单相关的识别，平台对此类订单新增相关api和字段。请相关的ISV务必关注，及时对接来保障国家补贴字段能正常透出

## 2、相关API和消息

API/消息| 变更类型| 变更说明  
---|---|---  
order.getOrderDetail订单详情接口| 已有出参新增字段| ● 订单维度下新增subsidySupplierId、subsidySupplierName字段，分别表示国家补贴订单供应商id和供应商名称  
● 订单维度下的orderTagList字段，新增COUNTRY_SUBSIDY_SUPPLY_SALE，表示国家补贴供销模式skuList商品维度下新增  
● skuIdentifyCodeInfo字段，表示该国补商品的序列号信息，其结构体分别有sNCode(序列号)、barCode(商品条码)、iMEI1Code(IMEI1码)、iMEI2Code(IMEI2码)  
order.orderDeliver订单发货接口| 已有入参新增字段| 入参新增skuIdentifyCodeInfo字段，用于上传国家补贴订单的序列号信息，其结构体分别有sNCode(序列号)、barCode(69码)、iMEI1Code(IMEI1b码)、iMEI2Code(IMEI2码)  
order.batchBindSkuIdentifyInfo批量上传序列号接口| 新增接口| 新增批量上传序列号接口，支持批量上传国家补贴订单的序列号等信息  
  
  

