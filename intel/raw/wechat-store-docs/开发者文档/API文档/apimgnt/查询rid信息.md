---
title: "查询rid信息"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/apimgnt/api_getridinfo.html"
category: "apimgnt"
doc_type: "API文档"
platform: "wechat-store"
crawl_date: "2026-03-05T05:14:15.049400+08:00"
---

查询rid信息

 调试诊断

接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用，具体可参考接口调用指南。

接口英文名：getRidInfo

本接口用于查询调用服务端接口报错返回的rid详情信息，辅助开发者高效定位问题。

适用的账号类型如下：公众号/服务号/小程序/小游戏/微信小店/带货助手/视频号助手/联盟带货机构/移动应用/网站应用/多端应用/第三方平台。

1. 调用方式
HTTPS 调用
POST https://api.weixin.qq.com/cgi-bin/openapi/rid/get?access_token=ACCESS_TOKEN


支持加密请求： 本接口支持服务通信二次加密和签名，可有效防止数据篡改与泄露。查看详情

云调用
本接口不支持云调用。
第三方调用

本接口支持第三方平台使用 component_access_token 自己调用，同时还支持代微信小店商家调用。第三方服务商调用模式介绍

服务商获得任意权限集授权后，即可通过使用 authorizer_access_token 代微信小店商家进行调用，具体可查看 第三方调用 说明文档。

2. 请求参数
查询参数 Query String Parameters
参数名	类型	必填	说明
access_token	string	是	接口调用凭证，可使用 access_token（微信小店商家）、component_access_token（服务商）、authorizer_access_token（服务商代调用）
请求体 Request Payload
参数名	类型	必填	说明
rid	string	是	调用接口报错返回的rid

3. 返回参数
返回体 Response Payload
参数名	类型	说明
errcode	number	返回码
errmsg	string	错误信息
request	object	该rid对应的请求详情

Res.request Object Payload

该rid对应的请求详情

参数名	类型	说明
invoke_time	number	发起请求的时间戳
cost_in_ms	number	请求毫秒级耗时
request_url	string	请求的URL参数
request_body	string	post请求的请求参数
response_body	string	接口请求返回参数
client_ip	string	接口请求的客户端ip

4. 注意事项

1、由于查询rid信息属于开发者私密行为，因此仅支持同账号的查询。举个例子，rid=1111，是小程序账号A调用某接口出现的报错，那么则需要使用小程序账号A的access_token调用当前接口查询rid=1111的详情信息，如果使用小程序账号B的身份查询，则出现报错，错误码为xxx。公众号、第三方平台账号等账号的接口同理。

2、如果是第三方服务商代公众号/服务号/小程序/小游戏/微信小店/带货助手/视频号助手查询调用 api返回的rid，则使用同一账号的authorizer_access_token调用即可。

3、rid的有效期只有7天，即只可查询最近7天的rid，查询超过7天的rid会出现报错，错误码为76001

4、”/xxx/sns/xxx“这类接口不支持使用该接口，会出现76022报错。

5. 代码示例

请求示例

{
  "rid": "61725984-6126f6f9-040f19c4"
}


返回示例

{
  "errcode": 0,
  "errmsg": "ok",
  "request": {
    "invoke_time": 1635156704,
    "cost_in_ms": 30,
    "request_url": "access_token=50_Im7xxxx",
    "request_body": "",
    "response_body": "{\"errcode\":45009,\"errmsg\":\"reach max api daily quota limit rid: 617682e0-09059ac5-34a8e2ea\"}",
    "client_ip": "113.xx.70.51"
  }
}


6. 错误码

以下是本接口的错误码列表，其他错误码可参考 通用错误码；调用接口遇到报错，可使用官方提供的 API 诊断工具 辅助定位和分析问题。

错误码	错误描述	解决方案
0	ok	ok
76001	rid not found	rid不存在
76002	rid is error	rid为空或者格式错误
76003	could not query this rid,no permission	当前账号无权查询该rid，该rid属于其他账号调用所产生
76004	rid time is error	rid过期，仅支持持续7天内的rid

7. 适用范围
本接口在不同账号类型下的可调用情况：
小程序	公众号	服务号	小游戏	微信小店	联盟带货机构	带货助手	小店供货商	第三方平台	移动应用	网站应用	视频号助手	多端应用
✔	✔	✔	✔	✔	✔	✔	✔	〇	✔	✔	✔	✔
✔：该账号可调用此接口。
〇：第三方平台可使用 component_access_token 调用，是否支持代微信小店商家调用需看本文档 调用方式 部分。
