---
title: "获取用户优惠券ID列表"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/coupon/api_getusercouponlist.html"
category: "营销"
doc_type: "API文档"
platform: "wechat-store"
crawl_date: "2026-03-05T05:56:31.721320+08:00"
---

获取用户优惠券ID列表

接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用，具体可参考接口调用指南。

接口英文名：getusercouponlist

通过此接口可以获取用户优惠券ID列表。

相关事件通知：

用户优惠券过期通知
优惠券返还通知
优惠券核销通知

1. 调用方式
HTTPS 调用
POST https://api.weixin.qq.com/channels/ec/coupon/get_user_coupon_list?access_token=ACCESS_TOKEN

云调用

调用方法：channels.ec.coupon.getUserCouponList

出入参和 HTTPS 调用相同，调用方式可查看 云调用 说明文档。

第三方调用

本接口支持第三方平台代微信小店商家调用。第三方服务商调用模式介绍

该接口所属的权限集 id 为：132

服务商获得其中之一权限集授权后，可通过使用 authorizer_access_token 代微信小店商家进行调用，具体可查看 第三方调用 说明文档。

2. 请求参数
查询参数 Query String Parameters
参数名	类型	必填	示例	说明
access_token	string	是	ACCESS_TOKEN	接口调用凭证，可使用 access_token（微信小店商家）、authorizer_access_token（服务商代调用）
请求体 Request Payload
参数名	类型	必填	说明	枚举
openid	string	是	用户openid	-
status	number	否	优惠券状态，不填时获取所有优惠券，填时获取特定状态优惠券	枚举值
page	number	是	页码	-
page_size	number	是	页大小	-
page_ctx	string	是	翻页上下文，第一次请求填空，后续请求值为上次请求的返回	-

3. 返回参数
返回体 Response Payload
参数名	类型	说明
errcode	number	错误码
errmsg	string	错误信息，errcode为0不返回
user_coupon_list	objarray	优惠券列表
page_ctx	string	翻页上下文

Res.user_coupon_list(Array) Object Payload

优惠券列表

参数名	类型	说明
user_coupon_id	number	用户优惠券ID
coupon_id	number	优惠券ID

4. 枚举信息

Body.status Enum

优惠券状态，不填时获取所有优惠券，填时获取特定状态优惠券

枚举值	枚举字段	枚举解释
100	COUPON_USER_STATUS_VALID	生效中
101	COUPON_USER_STATUS_EXPIRED	已过期
102	COUPON_USER_STATUS_USED	已使用

5. 注意事项
每次请求的页码间隔不能超过10；
第一次请求的页码要小于10，或者是最后一页；
一页最大200。

6. 代码示例

请求示例

{
    "openid": "OPENID",
    "status": 100,
    "page": 1,
    "page_size": 20,
    "page_ctx": "THE_PAGE_CTX"
}


返回示例

{
    "errcode": 0,
    "user_coupon_list": [
        {
            "user_coupon_id": "109694341",
            "coupon_id": "12639900"
        }
    ],
    "total_num": 1,
    "page_ctx": "THE_PAGE_CTX_NEW"
}


7. 错误码

以下是本接口的错误码列表，其他错误码可参考 通用错误码；调用接口遇到报错，可使用官方提供的 API 诊断工具 辅助定位和分析问题。

错误码	错误描述
40003	OpenID不正确
10021001	优惠券状态不对
10021036	分页拉优惠券列表，页码与上次请求相差过大
10021037	优惠券不存在

8. 适用范围

本接口支持「微信小店」账号类型调用。其他账号类型如无特殊说明，均不可调用。
