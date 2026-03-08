---
title: "订单详情中skulist出现skucode相同，但价格不相同的情况"
source_url: "https://open.xiaohongshu.com/document/developer/file/146"
file_id: "146"
category: "订单"
doc_type: "SDK文档"
crawl_date: "2026-03-05T04:19:41.292297+08:00"
---

skulist里面结算金额理论上会是总数除以sku的数量，但是遇到除不尽的情况，同一个skucode在skulist里会出现两次，比如3件一共10元，slulist里有有两个skucode，skucode是一样的，一个是价格3.33的数量2,一个价格3.34的数量1
