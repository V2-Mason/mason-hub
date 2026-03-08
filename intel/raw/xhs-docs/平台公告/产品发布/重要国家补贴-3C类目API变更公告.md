---
title: "【重要】国家补贴-3C类目API变更公告"
source_url: "https://open.xiaohongshu.com/document/developer/file/322"
file_id: "322"
category: "产品发布"
doc_type: "平台公告"
crawl_date: "2026-03-05T04:19:53.750129+08:00"
---

# 1、业务场景

        由于国补政策要求3C类目商品在签收前，需要进行验机拍照服务并回传相关信息。为了符合国家补贴-3C类目相关的交易要求，平台对此类订单涉及相关api新增相关字段，请务必关注并及时对接来保障国家补贴3C类目正常交易。

# 2、业务流程

![](https://qimg.xiaohongshu.com/odin/1041017g31je587ul3206bbea2o9000000000010bcvong)

## 2.1 与顺丰签约微派服务（国补3C类目验机指定服务）

参加国家补贴-3C类目的商家，均需要和顺丰完成线下的微派服务协议签署。后续产生微派服务任务，由商家自行和顺丰线下对账&结算

## 2.2 完成本次API改造对接

参加国家补贴-3C类目的商家，需完成本次相关api对接后，国补3C商品才允许审核通过。

## 2.3 本次API变动说明

顺序| API/消息| 变更类型| 变更说明  
---|---|---|---  
说明1| 订单API： order.getOrderDetail订单详情接口| 已有出参新增字段| ● 订单维度下新增subsidyWpServiceCode，表示该订单对应的“国补顺丰微派任务编码”，后续取号时必传  
● 订单维度下新增subsidySkuIdentifyCodeRequiredInfo，标识该订单的商品的序列号信息的传递条件  
手机类目，需传输sNCode、barCode、iMEI1Code、iMEI2Code  
智能手表（有通话功能的），需传输sNCode、barCode、iMEI1Code  
笔记本、平板、智能手环、智能手表（无通话功能的），需传输sNCode、barCode  
注意：IMEI1、IMEI2需按准确顺序回传  
说明2| 物流API： express.createEbillOrders批量取号接口| 入参拓展字段变更| 说明：取号时以下字段非必填，但必传subsidyWpServiceCode，即国补顺丰微派任务编码  
● extraInfo扩展字段里面新增四个参数  
1.微派任务编码：wpServiceCode（订单详情回传）  
2.SN码：sn  
3.IMEI1编码：imei1  
4.IMEI2编码：imei2  
说明3| 订单API： order.orderDeliver订单发货| 已有入参字段说明| ●skuIdentifyCodeInfo国补订单序列号，本次3C类目国补订单按照订单详情api的序列号要求回传  
即：subsidySkuIdentifyCodeRequiredInfo，在发货时的传递条件  
手机类目，需传输sNCode、barCode、iMEI1Code、iMEI2Code  
智能手表（有通话功能的），需传输sNCode、barCode、iMEI1Code  
笔记本、平板、智能手环、智能手表（无通话功能的），需传输sNCode、barCode  
注意：IMEI1、IMEI2需按准确顺序回传  
说明4| 物流API： express.queryEbillOrder查询面单| 出参拓展字段变更| ● extraInfo扩展字段里面新增四个参数  
1.微派任务编码：wpServiceCode  
2.SN码：sn  
3.IMEI1编码：imei1  
4.IMEI2编码：imei2  
  
# 3、常见问题解答

**Q1：取号时要传SN等信息吗？**

A1：非必填，但“subsidyWpServiceCode“取号时必传，表示该订单对应的“国补顺丰微派任务编码”，订单详情中已下发

  


**Q2：发货时要传SN等信息吗？**

A2：国家要求必填，具体不同品类的要求见说明1

  


**Q3：只能使用顺丰取号 &发货吗？**

A3：是，目前商家均需要线下和顺丰签署”微派任务协议“，并在取号和发货时仅可使用顺丰

  


**Q4：现在能使用PC端/APP端千帆工作台发货吗？**

A4：目前不支持，仅支持通过ERP进行电子面单取号和发货

  


**Q5：能支持批量发货、合并发货等吗？**

A4：目前不支持
