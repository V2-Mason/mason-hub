---
title: "获取ITEM详情"
source_url: "https://xiaohongshu.apifox.cn/api-24868781"
source: "apifox"
category: "商品"
doc_type: "SDK文档"
crawl_date: "2026-03-05T05:00:15.460029+08:00"
---

商品 APIMCP获取ITEM详情POST/ark/open_api/v3/common_controller调试Run in ApifoxRun in Apifox请求参数Body 参数application/json生成代码示例返回响应🟢200成功application/json生成代码Body生成代码请求示例请求示例ShellJavaScriptJavaSwiftcURLcURL-WindowsHttpiewgetPowerShellcurl --location --request POST 'https://ark.xiaohongshu.com/ark/open_api/v3/common_controller' \
--header 'Content-Type: application/json' \
--data-raw '{
    "pageSize": 1,
    "pageNo": 1,
    "itemId": "1"
}'响应示例响应示例{
    "total": "",
    "skuInfos": [
        {
            "itemId": "64ff12f***fd12f1",
            "ipq": 100,
            "originalPrice": 88,
            "price": 80,
            "stock": 5000,
            "logisticsPlanId": "5e37***a9f0",
            "whcode": "C01",
            "priceType": 1,
            "erpCode": "001231",
            "variants": [
                {
                    "id": "5a60***9ce6",
                    "name": "尺码",
                    "value": "36",
                    "valueId": "f423***921f"
                }
            ],
            "deliveryTime": {
                "time": "2021/06/01",
                "type": "ABSOLUTE_TIME"
            },
            "specImage": "http://img.xiaohongshu.com/items/123456789",
            "barcode": "RedTest20200507001",
            "rowNumber": "",
            "id": "6123**5132",
            "scSkucode": "XHSd12f1r1f",
            "logisticsName": "red_auto",
            "buyable": true,
            "unionItemDetails": [
                {
                    "id": "607***450",
                    "name": "口红",
                    "scSkuCode": "690***466",
                    "barcode": "690***452",
                    "ipq": 100,
                    "erpCode": "dq123da"
                }
            ],
            "createTime": "",
            "updateTime": "",
            "name": "",
            "isGift": true
        }
    ],
    "itemInfo": {
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
    },
    "pageNO": "",
    "pageSize": ""
}【小红书】API开发者 微信交流群用微信扫右侧二维码，加入【小红书】API开发者 交流群，互助沟通扫码加入交流群修改于 2023-08-01 07:53:07上一页查询Item列表下一页修改价格
