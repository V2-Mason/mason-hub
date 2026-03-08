---
title: "创建SKU"
source_url: "https://xiaohongshu.apifox.cn/api-24854921"
source: "apifox"
category: "商品"
doc_type: "SDK文档"
crawl_date: "2026-03-05T05:00:15.459194+08:00"
---

商品 APIMCP创建SKUPOST/ark/open_api/v3/common_controller调试Run in ApifoxRun in Apifox请求参数Body 参数application/json生成代码示例返回响应🟢200成功application/json生成代码Body生成代码请求示例请求示例ShellJavaScriptJavaSwiftcURLcURL-WindowsHttpiewgetPowerShellcurl --location --request POST 'https://ark.xiaohongshu.com/ark/open_api/v3/common_controller' \
--header 'Content-Type: application/json' \
--data-raw '{
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
    "barcode": "RedTest20200507001"
}'响应示例响应示例{
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
}【小红书】API开发者 微信交流群用微信扫右侧二维码，加入【小红书】API开发者 交流群，互助沟通扫码加入交流群修改于 2023-08-01 07:13:17上一页删除ITEM下一页更新SKU
