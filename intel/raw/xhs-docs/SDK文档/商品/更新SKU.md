---
title: "更新SKU"
source_url: "https://xiaohongshu.apifox.cn/api-24860774"
source: "apifox"
category: "商品"
doc_type: "SDK文档"
crawl_date: "2026-03-05T05:00:15.459394+08:00"
---

商品 APIMCP更新SKUPOST/ark/open_api/v3/common_controller调试Run in ApifoxRun in Apifox请求参数Body 参数application/json生成代码示例返回响应🟢200成功application/json生成代码Body生成代码请求示例请求示例ShellJavaScriptJavaSwiftcURLcURL-WindowsHttpiewgetPowerShellcurl --location --request POST 'https://ark.xiaohongshu.com/ark/open_api/v3/common_controller' \
--header 'Content-Type: application/json' \
--data-raw '{
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
    "id": "100",
    "updatedFields": [
        "string"
    ]
}'响应示例响应示例{
    "spuData": {
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
        "isChannel": "",
        "deliveryMode": "",
        "id": "spu标题",
        "createTime": "",
        "updateTime": ""
    },
    "itemData": {
        "spuId": "spu标题",
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
        "specImageUrl": "http://img.xiaohongshu.com/items/123456789",
        "barcode": "RedTest20200507001",
        "id": "6123**5132",
        "skucode": "spu标题",
        "logisticsName": "red_auto",
        "buyable": true,
        "unionItemDetails": [
            {
                "id": "607***450",
                "name": "口红",
                "skuCode": "690***466",
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
}【小红书】API开发者 微信交流群用微信扫右侧二维码，加入【小红书】API开发者 交流群，互助沟通扫码加入交流群修改于 2023-08-01 07:30:13上一页创建SKU下一页删除SKU
