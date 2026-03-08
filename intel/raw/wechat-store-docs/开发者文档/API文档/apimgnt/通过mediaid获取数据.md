---
title: "通过mediaid获取数据"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/apimgnt/api_getdatabymediaid.html"
category: "apimgnt"
doc_type: "API文档"
platform: "wechat-store"
crawl_date: "2026-03-05T05:18:40.546006+08:00"
---

通过mediaid获取数据

接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用，具体可参考接口调用指南。

接口英文名：getdatabymediaid

可通过该接口传入media_id获取数据

1. 调用方式
HTTPS 调用
GET https://api.weixin.qq.com/channels/ec/basics/media/get?access_token=ACCESS_TOKEN&media_id=MEDIA_ID

云调用

调用方法：channels.ec.basics.media.get

出入参和 HTTPS 调用相同，调用方式可查看 云调用 说明文档。

第三方调用

本接口支持第三方平台代微信小店商家调用。第三方服务商调用模式介绍

该接口所属的权限集 id 为：129、131

服务商获得其中之一权限集授权后，可通过使用 authorizer_access_token 代微信小店商家进行调用，具体可查看 第三方调用 说明文档。

2. 请求参数
查询参数 Query String Parameters
参数名	类型	必填	示例	说明
access_token	string	是	ACCESS_TOKEN	接口调用凭证，可使用 access_token（微信小店商家）、authorizer_access_token（服务商代调用）
media_id	string	是	-	售后单，纠纷单等接口返回的媒体 id
请求体 Request Payload

无

3. 返回参数
返回体 Response Payload
参数名	类型	说明
errcode	number	错误码
errmsg	string	错误信息

4. 注意事项

本接口无特殊注意事项

5. 代码示例

请求示例

curl 'https://api.weixin.qq.com/channels/ec/basics/media/get?access_token=63_qzMter4gPPEeh&media_id=EN2S_n2fBrt0PDIDtB41Akp6BlnkGJ7nLO9f5RBjDVn59-m50EtN_kq1JUqFzToNxesRzqXOdYCOv1-Nw2olHw'


返回示例

没有报错的情况下返回二进制数据，报错情况下返回json格式的错误信息，请根据回包数据格式分别处理。


6. 错误码

此接口没有特殊错误码，可参考 通用错误码；调用接口遇到报错，可使用官方提供的 API 诊断工具 辅助定位和分析问题。

7. 适用范围

本接口支持「微信小店」账号类型调用。其他账号类型如无特殊说明，均不可调用。
