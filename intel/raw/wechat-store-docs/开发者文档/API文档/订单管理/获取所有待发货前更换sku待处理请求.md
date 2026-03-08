---
title: "获取所有待发货前更换sku待处理请求"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/channels-shop-order/api_getpreshipmentchangeskuwaithandlelist.html"
category: "订单管理"
doc_type: "API文档"
platform: "wechat-store"
crawl_date: "2026-03-05T05:40:28.168924+08:00"
---

获取所有待发货前更换sku待处理请求

接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用，具体可参考接口调用指南。

接口英文名：getpreshipmentchangeskuwaithandlelist

获取所有待发货前更换sku待处理请求

1. 调用方式
HTTPS 调用
POST https://api.weixin.qq.com/channels/ec/order/preshipmentchangesku/get?access_token=ACCESS_TOKEN

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
page	number	是	1	分页参数
page_size	number	是	100	每一页需要展示的条数

3. 返回参数
返回体 Response Payload
参数名	类型	示例	说明
errcode	number	0	错误码
errmsg	string	ok	错误信息
order_ids	array		等待商家处理的换款请求订单id

4. 注意事项

本接口无特殊注意事项

5. 代码示例

请求示例

{
    "page": 1,
    "page_size": 100
}


返回示例

{
    "errcode": 0,
    "errmsg": "ok",
    "order_ids": [
        "123456789"
    ]
}


6. 错误码

以下是本接口的错误码列表，其他错误码可参考 通用错误码；调用接口遇到报错，可使用官方提供的 API 诊断工具 辅助定位和分析问题。

错误码	错误描述
10020277	请求体格式不正确，请检查请求体中各个参数的类型是否正确

7. 适用范围

本接口支持「微信小店」账号类型调用。其他账号类型如无特殊说明，均不可调用。
