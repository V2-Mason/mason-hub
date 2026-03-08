---
title: "【重要】ISV电子面单渗透治理通知"
source_url: "https://open.xiaohongshu.com/document/developer/file/263"
file_id: "263"
category: "技术变更"
doc_type: "平台公告"
crawl_date: "2026-03-05T04:20:21.918398+08:00"
---

**致亲爱的小红书开放平台合作伙伴：**

### **一、小红书电子面单渗透**

 _1.电子面单覆盖率要求：_

  * 为了加强平台的商家和消费者隐私数据保护，防止因订单隐私数据泄露导致的损失，小红书平台已经于2023年8月3日对所有平台开发者发布了《【重要】小红书电子面单切换通知》  <https://open.xiaohongshu.com/platformSupport/notice/31/157> ，并提供了对接人员和处理团队进行支持，但部分isv覆盖率未达标，现再次明确对接节点和覆盖率要求，**长期未对接电子面单的isv或覆盖率未达标的isv进行治理，直至完成相应对接和覆盖率要求。另外，自研商家需要在2023年12月29日前完成电子面单对接。**

涉及对象| 时间要求| 电子面单覆盖率要求| 未达标  
---|---|---|---  
ISV| 2023年12月10日| 单应用的电子面单覆盖率需达到 70%| 下掉已有服务市场资源位且三个月内不允许申请资源位  
ISV| 2023年12月20日| 单应用的电子面单覆盖率需达到 95%| 关闭解密接口  
自研商家| 2023年12月29日| 店铺电子面单覆盖率需达到 100%| 关闭解密接口  
  
  * 电子面单覆盖率计算公式=应用使用小红书电子面单取号数/应用调用发货接口次数；ISV关闭解密接口会导致使用该ISV的商家即使申请店铺开白名单，任何场景下都无法再通过该ISV解密进行发货、处理售后等。



 _**2.特别提醒**_

  * 如若有用户不在ISV软件中取号，只是操作发货动作，既推单第三方，需尽快告知上游供货商或wms系统进行小红书平台对接，避免影响平台打单发货



3.对于有代发功能的服务商，如厂家需要使用无店铺电子面单功能，需要服务商将小红书服务市场的授权页面链接从“https://ark.xiaohongshu.com/ark/authorization?redirectUri=回调地址&appId;=应用ID”改为“https://open.xiaohongshu.com/authorization?redirectUri=回调地址&appId;=应用ID”。改造完成后通知厂家注册使用无店铺电子面单。 [https://school.xiaohongshu.com/rule/detail/5d68f4f40000000000000000/650aff6b8b5a0f0019078a06?entry=00020002&jumpFrom;=ark](<https://school.xiaohongshu.com/rule/detail/5d68f4f40000000000000000/650aff6b8b5a0f0019078a06?entry=00020002&jumpFrom=ark>)

### **二、电子面单对接流程和文档**

1.小红书电子面单对接说明【ISV版/WMS】：  
<https://open.xiaohongshu.com/document/developer/file/52>

2.关于对接的常见问题：

<https://open.xiaohongshu.com/help/list/27/140>

### **三、商家侧公告和文档**

  * 商家侧要求10.16完成隐私加密操作，公告如下： [https://school.xiaohongshu.com/helper/detail/1952?entry=00020002&jumpFrom;=ark](<https://school.xiaohongshu.com/helper/detail/1952?entry=00020002&jumpFrom=ark>)



  


最后，请ISV以及合作的WMS服务商、自研商家尽快完成对接，对接过程中遇到疑问，请扫描下方二维码添加业务运营同学企业微信进行咨询。

![](https://qimg.xiaohongshu.com/odin/1041017g30te516snk6069uk2g9qg0000000000tdlcg42)

特此通告  
小红书开放平台  
2023年11月21日
