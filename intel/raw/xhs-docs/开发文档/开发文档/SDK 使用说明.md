---
title: "SDK 使用说明"
source_url: "https://xiaohongshu.apifox.cn/doc-2810941"
source: "apifox"
category: "开发文档"
doc_type: "开发文档"
crawl_date: "2026-03-05T05:00:15.444412+08:00"
---

开发文档SDK 使用说明SDK使用说明#为便于开发者对接，小红书开放平台提供了SDK包使用，开发者下载SDK后导入服务中，即可使用，目前只支持java版本的SDKJAVA版本SDK下载链接(含依赖)下载地址JAVA版本SDK下载链接(不含依赖)下载地址SDK使用说明：目前SDK根据具体应用场景，分为了OauthClient(授权，包含了code与accessToken的获取与刷新)、CommonClient(通用)、ProductClient(商品)、PackageClient(订单)、InventoryClient(库存)、AfterSaleClient(售后)开发者可以进入sdk查看具体接口，接口名称统一为execute，根据传入的不同request进行区分。以获取库存接口为例： SDK更新记录：  
2021年9月24日：package.getPackageDetail接口返回结构中itemList下增加erpcode字段，oauth.getAccessToken和oauth.refreshToken接口返回字段增加sellerName店铺名  
2021年10月11日：售后审核增加收件人信息，商品详情列表接口返回spu和商品的创建更新时间  
2021年10月20日：商品查询增加字段lastId用于全店扫描，通用接口增加地址信息接口，订单详情增加赠品标识   
2021年11月10日：增加售后拒绝确认收货接口
2022年9月14日：商品发货时间支持新类型
2022年11月5日：商家地址库相关接口升级，具体修改参考商家地址库升级公告
2023年2月7日：支持7无字段设置
2023年3月14日：更新商品3.0版本sdk
2023年4月2日：补充更新接口afterSale.listAfterSaleApi
2023年6月29日：订单详情接口返回新增字段：订单定金，商家承担总优惠金额，平台承担总优惠金额，商家实收，改价总金额，支付方式
2023年7月4日：订单详情接口新增字段deliveryMode, 表示商品是否支持无物流发货【小红书】API开发者 微信交流群用微信扫右侧二维码，加入【小红书】API开发者 交流群，互助沟通扫码加入交流群修改于 2023-08-01 09:28:46上一页应用消息推送下一页发布服务
