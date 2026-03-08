---
title: "同意待发货前更换sku请求"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/channels-shop-order/api_approvepreshipmentchangesku.html"
category: "订单管理"
doc_type: "API文档"
platform: "wechat-store"
crawl_date: "2026-03-05T05:37:58.166107+08:00"
---

同意待发货前更换sku请求

接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用，具体可参考接口调用指南。

接口英文名：approvepreshipmentchangesku

同意待发货前更换sku请求

相关事件通知： 订单其他信息更新

1. 调用方式
HTTPS 调用
POST https://api.weixin.qq.com/channels/ec/order/preshipmentchangesku/approve?access_token=ACCESS_TOKEN

云调用
本接口不支持云调用。
第三方调用

本接口支持第三方平台代微信小店商家调用。第三方服务商调用模式介绍

该接口所属的权限集 id 为：131

服务商获得其中之一权限集授权后，可通过使用 authorizer_access_token 代微信小店商家进行调用，具体可查看 第三方调用 说明文档。

2. 请求参数
查询参数 Query String Parameters
参数名	类型	必填	示例	说明
access_token	string	是	ACCESS_TOKEN	接口调用凭证，可使用 access_token（微信小店商家）、authorizer_access_token（服务商代调用）
请求体 Request Payload
参数名	类型	必填	示例	说明
order_id	string	是	111111111	订单id

3. 返回参数
返回体 Response Payload
参数名	类型	示例	说明
errcode	number	0	错误码
errmsg	string	ok	错误信息

4. 注意事项

本接口无特殊注意事项

5. 代码示例

请求示例

{
    "order_id":"111111111"
}


返回示例

{
    "errcode": 0,
    "errmsg": "ok"
}


6. 错误码

以下是本接口的错误码列表，其他错误码可参考 通用错误码；调用接口遇到报错，可使用官方提供的 API 诊断工具 辅助定位和分析问题。

错误码	错误描述
41001	缺少 access_token 参数
42001	access_token 超时，请检查 access_token 的有效期，请参考基础支持 - 获取 access_token 中，对 access_token 的详细机制说明
10020277	请求体格式不正确，请检查请求体中各个参数的类型是否正确

7. 适用范围

本接口支持「微信小店」账号类型调用。其他账号类型如无特殊说明，均不可调用。

接口变更日志（1条）
2025 年 12 月 10 日
补充错误码
