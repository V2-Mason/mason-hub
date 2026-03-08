---
title: "订单详情中itemlist和skulist如何理解？"
source_url: "https://open.xiaohongshu.com/document/developer/file/142"
file_id: "142"
category: "订单"
doc_type: "SDK文档"
crawl_date: "2026-03-05T04:19:38.247975+08:00"
---

一个订单中，itemList是用户下单的商品情况，一个订单可能包含多个item skuList是一个item的具体信息，例如：

  * 如果这个商品是组合品，skuList就是各个子商品普通单品的信息
  * 如果这个商品是渠道商品，skuList里就是渠道商品对应普通单品的信息
  * 如果这个商品是多包组，skuList里就是多包组商品对应普通单品的信息
  * 如果这个商品是普通单品，那么skulist里的itemid和外层的itemid就是一样的



【总结】：skuList中的一定是各种商品对应的普通单品的信息
