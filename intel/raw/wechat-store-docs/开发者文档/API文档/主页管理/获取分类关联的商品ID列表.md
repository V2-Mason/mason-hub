---
title: "获取分类关联的商品ID列表"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/homepage/shoptype/api_getclassificationproductlist.html"
category: "主页管理"
doc_type: "API文档"
platform: "wechat-store"
crawl_date: "2026-03-05T06:04:49.698247+08:00"
---

获取分类关联的商品ID列表

接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用，具体可参考接口调用指南。

接口英文名：GetClassificationProductList

通过该接口可获取分类关联的商品ID列表

商品分类由2部分数据组成，分别是分类树和分类商品。这个接口是获取分类关联的商品ID列表
一个分类最多关联500个商品

1. 调用方式
HTTPS 调用
POST https://api.weixin.qq.com/channels/ec/store/classification/tree/product/get?access_token=ACCESS_TOKEN

云调用
本接口不支持云调用。
第三方调用
本接口不支持第三方平台调用。

2. 请求参数
查询参数 Query String Parameters
参数名	类型	必填	示例	说明
access_token	string	是	ACCESS_TOKEN	接口调用凭证，可使用 access_token
请求体 Request Payload
参数名	类型	必填	说明
req	object	是	-

Body.req Object Payload
参数名	类型	必填	说明
level_1_id	number	是	-
level_2_id	number	是	-
page_context	string	是	-
page_size	number	是	-

3. 返回参数
返回体 Response Payload
参数名	类型	说明
product_ids	numarray	-
page_context	string	拉取下一页用。如果该值为空，表示拉取到最后一页了。

4. 注意事项

本接口无特殊注意事项

5. 代码示例

请求示例


{
    "req": {
        "level_1_id": 1,
        "level_2_id": 0,
        "page_size": 5,
        "page_context": "",
    }
}


返回示例

{
    "errcode":0,
    "errmsg":"ok",
    "resp": {
        "product_ids":[1,2],
        "page_context":""
    }
}


6. 错误码

此接口没有特殊错误码，可参考 通用错误码；调用接口遇到报错，可使用官方提供的 API 诊断工具 辅助定位和分析问题。

7. 适用范围

本接口暂未明确可调用账号类型，或在业务中根据调用传参自行确定是否可调用，请以实际调用情况为准。
