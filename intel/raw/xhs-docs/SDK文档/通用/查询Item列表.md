---
title: "查询Item列表"
source_url: "https://xiaohongshu.apifox.cn/api-24865354"
source: "apifox"
category: "通用"
doc_type: "SDK文档"
crawl_date: "2026-03-05T05:00:15.459828+08:00"
---

商品 APIMCP查询Item列表POST/ark/open_api/v3/common_controller调试Run in ApifoxRun in Apifox请求参数Body 参数application/json生成代码示例返回响应🟢200成功application/json生成代码Body生成代码请求示例请求示例ShellJavaScriptJavaSwiftcURLcURL-WindowsHttpiewgetPowerShellcurl --location --request POST 'https://ark.xiaohongshu.com/ark/open_api/v3/common_controller' \
--header 'Content-Type: application/json' \
--data-raw '{
    "pageNo": 1,
    "pageSize": 50,
    "searchParam": {
        "keyword": "null",
        "topCategoryIds": [
            "string"
        ],
        "lvl2CategoryIds": [
            "string"
        ],
        "lvl3CategoryIds": [
            "string"
        ],
        "lvl4CategoryIds": [
            "string"
        ],
        "buyable": "",
        "keywords": [
            "string"
        ],
        "logisticsPlanIds": [
            "string"
        ],
        "createTimeFrom": 1625314893000,
        "createTimeTo": 1625314893000,
        "lastId": "6169406ff1404600095b96ed"
    }
}'响应示例响应示例{
    "currentPage": 1,
    "pageSize": 50,
    "total": 1,
    "itemDetailV3s": [
        {
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
        }
    ]
}【小红书】API开发者 微信交流群用微信扫右侧二维码，加入【小红书】API开发者 交流群，互助沟通扫码加入交流群修改于 2023-08-01 07:38:31上一页删除SKU下一页获取ITEM详情
