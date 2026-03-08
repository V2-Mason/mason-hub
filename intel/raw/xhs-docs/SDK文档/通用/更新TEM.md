---
title: "更新TEM"
source_url: "https://xiaohongshu.apifox.cn/api-24846432"
source: "apifox"
category: "通用"
doc_type: "SDK文档"
crawl_date: "2026-03-05T05:00:15.458731+08:00"
---

商品 APIMCP更新TEMPOST/ark/open_api/v3/common_controller调试Run in ApifoxRun in Apifox请求参数Body 参数application/json生成代码示例返回响应🟢200成功application/json生成代码Body生成代码请求示例请求示例ShellJavaScriptJavaSwiftcURLcURL-WindowsHttpiewgetPowerShellcurl --location --request POST 'https://ark.xiaohongshu.com/ark/open_api/v3/common_controller' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "spu标题",
    "ename": "spuEName",
    "shortName": "spu短标题，不得超过30的长度，其中中文字符占两个长度",
    "brandId": "52dd****7d4b",
    "categoryId": "5a31****9df5",
    "attributes": [
        {
            "propertyId": "5845****325e",
            "name": "测试属性名01",
            "valueId": "test",
            "value": "test",
            "valueList": [
                {
                    "valueId": "test",
                    "value": "test"
                }
            ]
        }
    ],
    "shippingTemplateId": "null",
    "shippingGrossWeight": 100,
    "variantIds": [
        "string"
    ],
    "imageUrls": [
        "string"
    ],
    "videoUrl": "",
    "articleNo": "",
    "imageDescUrls": [
        "string"
    ],
    "transparentImageUrl": "",
    "desc": "",
    "faqs": [
        {
            "question": "",
            "answer": ""
        }
    ],
    "deliveryMode": "",
    "id": "spu标题",
    "updatedFields": [
        "string"
    ]
}'响应示例响应示例{
    "name": "item标题",
    "ename": "itemEName",
    "brandId": "",
    "categoryId": "5a31****9df5",
    "attributes": [
        {
            "propertyId": "5845****325e",
            "name": "测试属性名01",
            "value": "test",
            "valueId": "test",
            "valueList": [
                {
                    "valueId": "test",
                    "value": "test"
                }
            ]
        }
    ],
    "shippingTemplateId": "null",
    "shippingGrossWeight": 100,
    "variantIds": [
        "string"
    ],
    "images": [
        "string"
    ],
    "videoUrl": "",
    "articleNo": "",
    "imageDescriptions": [
        "string"
    ],
    "transparentImage": "",
    "description": "",
    "faq": [
        {
            "question": "",
            "answer": ""
        }
    ],
    "isChannel": "",
    "deliveryMode": "",
    "freeReturn": "",
    "id": "64******412f1f",
    "createTime": "",
    "updateTime": ""
}【小红书】API开发者 微信交流群用微信扫右侧二维码，加入【小红书】API开发者 交流群，互助沟通扫码加入交流群修改于 2023-08-01 07:03:03上一页创建ITEM下一页删除ITEM
