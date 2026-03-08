---
title: "API 接口"
source_url: "https://developers.weixin.qq.com/doc/store/shop/API/"
category: "API"
doc_type: "开发者文档"
platform: "wechat-store"
crawl_date: "2026-03-05T05:11:29.046002+08:00"
---

通用
接口名称	请求路径	描述
获取接口调用凭据	/cgi-bin/token	本接口用于获取获取全局唯一后台接口调用凭据（Access Token），token 有效期为 7200 秒，开发者需要进行妥善保存，使用注意事项请参考此文档
获取稳定版接口调用凭据	/cgi-bin/stable_token	本接口用于获取获取全局唯一后台接口调用凭据（Access Token），token 有效期为 7200 秒，但此接口和 getAccessToken 互相隔离，
查询API调用额度	/cgi-bin/openapi/quota/get	本接口用于查询服务端接口的的每日调用接口的额度，调用次数，频率限制
重置指定API调用次数	/cgi-bin/openapi/quota/clear	本接口使用 access_token 来重置指定接口的每日调用次数
重置API调用次数	/cgi-bin/clear_quota	本接口是通过access_token清空服务端接口的每日调用接口次数
使用AppSecret重置API调用次数	/cgi-bin/clear_quota/v2	本接口是通过AppSecret清空服务端接口的每日调用接口次数
网络通信检测	/cgi-bin/callback/check	为了帮助开发者排查回调连接失败的问题，提供这个网络检测的API
获取微信API服务器IP	/cgi-bin/get_api_domain_ip	该接口用于获取微信 api 服务器 ip 地址（开发者服务器主动访问 api.weixin.qq.com 的远端地址）
获取微信推送服务器IP	/cgi-bin/getcallbackip	该接口用于获取微信推送服务器 ip 地址（向开发者服务器推送信息的微信服务器来源地址）
查询rid信息	/cgi-bin/openapi/rid/get	本接口用于查询调用服务端接口报错返回的rid详情信息，辅助开发者高效定位问题
上传图片	/shop/ec/basics/img/upload	本接口可用于上传图片，上传后获取 media_id 支持其他接口使用
上传资质图片	/shop/ec/basics/qualification/upload	本接口用于上传资质图片
通过mediaid获取数据	/channels/ec/basics/media/get	可通过该接口传入media_id获取数据
店铺管理
接口名称	请求路径	描述
获取店铺基本信息	/channels/ec/basics/info/get	通过该接口可获取店铺的基本信息
获取店铺H5链接	/channels/ec/basics/shop/h5url/get	通过该接口可以获取微信小店的店铺H5链接，支持传入企业微信参数
获取店铺二维码	/channels/ec/basics/shop/qrcode/get	通过该接口可以获取微信小店的店铺二维码，支持传入企业微信参数
获取店铺口令	/channels/ec/basics/shop/taglink/get	通过该接口可以获取微信小店的店铺微信口令，支持传入企业微信参数
主页管理
商品排序
接口名称	请求路径	描述
获取主页展示商品列表	/channels/ec/store/window/product/list/get	通过该接口可获取微信小店主页对用户展示的商品列表
重新排序主页展示商品	/channels/ec/store/window/product/reorder	可通过该接口改变小店主页展示商品的排序
隐藏小店主页商品	/channels/ec/store/window/product/hide	可通过该接口将小店主页展示的商品设置隐藏或者取消隐藏，隐藏后的商品不会下架，仍可以通过其他渠道购买
置顶小店主页商品	/channels/ec/store/window/product/settop	可通过该接口将小店主页展示的某个商品设置置顶或者取消置顶
主页背景图
接口名称	请求路径	描述
提交背景图申请	/channels/ec/basics/homepage/background/apply/submit	通过该接口提交主页背景图申请，审核通过后背景图会展示在店铺主页
查询背景图	/channels/ec/basics/homepage/background/get	通过该接口可查询当前生效的背景图和流程中的申请
清空主页背景图并撤销流程中的申请	/channels/ec/basics/homepage/background/remove	通过该接口可清空当前生效的主页背景图并撤销流程中的申请
撤销主页背景图申请	/channels/ec/basics/homepage/background/apply/cancel	通过该接口可撤销流程中的主页背景图申请
精选展示位
接口名称	请求路径	描述
提交精选展示位申请	/channels/ec/basics/homepage/banner/apply/submit	通过该接口提交精选展示位申请，审核通过后会展示在店铺主页
查询精选展示位	/channels/ec/basics/homepage/banner/get	通过该接口可查询当前生效的精选展示位和流程中的申请
清空精选展示位并撤销流程中的申请	/channels/ec/basics/homepage/banner/remove	通过该接口可清空当前生效的精选展示位并撤销流程中的申请
撤销精选展示位申请	/channels/ec/basics/homepage/banner/apply/cancel	通过该接口可撤销流程中的精选展示位申请
商品分类
接口名称	请求路径	描述
获取在店铺主页展示的商品分类	/channels/ec/store/classification/tree/get	通过该接口可获取在店铺主页展示的商品分类
获取分类关联的商品ID列表	/channels/ec/store/classification/tree/product/get	通过该接口可获取分类关联的商品ID列表
商品分类由2部分数据组成，分别是分类树和分类商品
商品管理
商品
接口名称	请求路径	描述
添加商品	/channels/ec/product/add	通过该接口可对商品添加微信小店
删除商品	/channels/ec/product/delete	可通过该接口删除微信小店商品（包括赠品）
获取商品	/channels/ec/product/get	可通过指定商品ID获取商品具体信息
获取商品列表	/channels/ec/product/list/get	可通过该接口获取微信小店的商品列表
更新商品	/channels/ec/product/update	该接口用于对微信小店内商品信息的更新
免审更新商品	/channels/ec/product/auditfree	针对已上架的商品，通过本接口可以进行免审核更新，接口只更新线上版本的数据，不影响编辑中的草稿数据
上架商品	/channels/ec/product/listing	通过该接口可将商品（包括非卖赠品）上架到微信小店
下架商品	/channels/ec/product/delisting	可通过该接口将商品（包括非卖赠品）从微信小店下架
撒回商品审核	/channels/ec/product/audit/cancel	该接口用于撤销微信小店商品（包括非卖赠品）审核申请，将商品（包括非卖赠品）状态从审核中改为未审核
获取商品H5短链	/channels/ec/product/h5url/get	通过该接口可以获取微信小店的商品H5短链，支持传入企业微信参数
获取商品口令	/channels/ec/product/taglink/get	通过该接口可以获取微信小店的商品微信口令，支持传入企业微信参数
获取商品二维码	/channels/ec/product/qrcode/get	通过该接口可以获取微信小店的商品二维码，支持传入企业微信参数
获取商品的移动应用跳转scheme码	/channels/ec/product/scheme/get	通过该接口可以获取微信小店的商品在移动应用中跳转scheme码
类目推荐	/channels/ec/product/category/classify	可通过商品标题和商品主图, 获取商品类目推荐信息
商品立即开售	/channels/ec/product/begintimingsale	设置了定时开售的商品改为立刻开售
取消商品开售	/channels/ec/product/canceltimingsale	设置了定时开售的商品取消开售
站内外商品属性映射	/channels/ec/product/externalproductmapping	根据入参类目和站外属性/站外属性值、站外类目名称，返回启用的站内外属性映射中的站内属性/站内属性值
发品前校验	/channels/ec/product/categoryprecheck	发品前校验接口，支持发品前查询店铺发品资质
获取商品上架策略	/channels/ec/product/auditstrategy/get	-
设置商品上架策略	/channels/ec/product/auditstrategy/set	-
获取商品提审限额	/channels/ec/product/getauditquota	1. 每个小店调用接口新增、更新商品次数会合并计算频率限制，详细说明可见：上架商品；
2. 总配额与商品审核通过率相关，建议发品前先调用商品发布规则相关接口获取
商品属性映射及推荐	/channels/ec/product/externalproductmappingnew	根据入参类目和多个站外属性/站外属性值、站外类目名称、商品标题、主图、详情图，返回多个启用的站内外属性映射中的站内属性/站内属性值
商品品牌推荐	/channels/ec/product/productbrandrecommend	根据商品标题、类目和主图等信息，从店铺当前有资质的品牌列表（可通过品牌资质相关接口管理）里推荐匹配的品牌信息，供发品时填入（发品接口的对应字段为brand_id
库存
接口名称	请求路径	描述
获取库存	/channels/ec/product/stock/get	通过该接口可以获取微信小店的商品库存信息
批量获取库存信息	/channels/ec/product/stock/batchget	通过该接口可以根据商品ID获取当前商品下所有sku的库存
获取库存流水	/channels/ec/product/stock/getflow	通过该接口可以获取视频号小店的商品库存流水
快速更新库存	/channels/ec/product/stock/update	可通过该接口快速更新微信小店商品的库存
赠品
接口名称	请求路径	描述
添加非卖商品	/channels/ec/product/gift/add	通过该接口可添加非卖商品
更新非卖商品	/channels/ec/product/gift/update	该接口用于对微信小店内非卖商品信息的更新
在售商品转赠品	/channels/ec/product/gift/onsale/set	可通过该接口将小店在售商品转为赠品
获取赠品	/channels/ec/product/gift/get	可通过指定赠品ID获取赠品具体信息
获取赠品列表	/channels/ec/product/gift/list/get	可通过该接口获取微信小店的赠品列表
更新赠品库存	/channels/ec/product/gift/stock/update	可通过该接口更新赠品库存
买赠活动
接口名称	请求路径	描述
创建赠品活动	/channels/ec/product/activity/add	可通过该接口添加买赠活动
删除赠品活动	/channels/ec/product/activity/del	可通过该接口删除买赠活动
停止赠品活动	/channels/ec/product/activity/stop	可通过该接口停止买赠活动
商品限时抢购
接口名称	请求路径	描述
添加限时抢购任务	/channels/ec/product/limiteddiscounttask/add	可通过该接口添加限时抢购任务
获取限时抢购任务列表	/channels/ec/product/limiteddiscounttask/list/get	可通过该接口获取限时抢购任务
停止限时抢购任务	/channels/ec/product/limiteddiscounttask/stop	可通过该接口提前结束限时抢购任务
删除限时抢购任务	/channels/ec/product/limiteddiscounttask/delete	通过该接口可删除已结束的限时抢购任务
收藏管理
店铺收藏
接口名称	请求路径	描述
获取店铺收藏的人数	/channels/ec/favorites/count/get	获取店铺收藏的人数 及 各渠道收藏人数
类目管理
接口名称	请求路径	描述
获取所有类目	/shop/ec/category/all	可通过该接口获取全部的类目信息、类目的资质信息、商品资质信息
获取类目信息	/shop/ec/category/detail	可通过该接口根据叶子类目ID（品类）获取类目的相关信息
申请类目	/channels/ec/category/add	可通过该接口上传类目资质
获取店铺的类目审核单列表	/shop/ec/category/getbizcatflowlist	获取店铺的类目审核单列表
获取店铺的类目审核单详情	/shop/ec/category/getbizcatflowdetail	获取店铺的类目审核单详情
获取店铺的类目权限列表	/shop/ec/category/get_category_relation_list	获取店铺的类目权限列表
获取店铺的类目权限详情	/shop/ec/category/get_category_relation_detail	获取店铺的类目权限详情
撤销类目审核	/shop/ec/category/audit/cancel	该接口可通过审核id来对类目的审核进行撤销
类目规则
接口名称	请求路径	描述
获取保证金类目规则	/shop/ec/category/getcategoryrule	本接口用于获取保证金类目规则
获取发货方式类目规则	/shop/ec/category/getcategoryrule	获取类目规则
获取类目下商品发布规则	/shop/ec/category/getcategoryproductrule	-
订单管理
接口名称	请求路径	描述
获取订单列表	/channels/ec/order/list/get	可通过该接口获取微信小店的订单列表
获取订单详情	/channels/ec/order/get	可通过该接口获取订单的详细信息
订单搜索	/channels/ec/order/search	该接口用于根据传递的条件搜索订单
修改订单价格	/channels/ec/order/price/update	可通过该接口修改订单价格
修改订单备注	/channels/ec/order/merchantnotes/update	可通过该接口修改订单备注
修改订单地址	/channels/ec/order/address/update	可通过该接口对订单地址进行修改，提交修改后将进入「协商」流程，需要买家同意后方可修改成功，具体规则详见：微信小店「代改址协商」使用指南
修改物流信息	/channels/ec/order/deliveryinfo/update	可通过该接口修改物流信息
同意用户修改收货地址申请	/channels/ec/order/addressmodify/accept	可通过该接口同意用户修改收货地址申请
拒绝用户修改收货地址申请	/channels/ec/order/addressmodify/reject	可通过该接口拒绝买家的订单修改收货地址申请
上传生鲜质检信息	/channels/ec/order/freshinspect/submit	可通过该接口给生鲜类质检订单上传商品打包信息
礼物订单新增备注信息	/channels/ec/order/presentnote/add	礼物订单新增备注信息
获取礼物单的子单列表	/channels/ec/order/presentsuborder/get	可通过该接口获取微信小店的礼物单对应的子单列表
获取所有待发货前更换sku待处理请求	/channels/ec/order/preshipmentchangesku/get	获取所有待发货前更换sku待处理请求
同意待发货前更换sku请求	/channels/ec/order/preshipmentchangesku/approve	同意待发货前更换sku请求
拒绝待发货前更换sku请求	/channels/ec/order/preshipmentchangesku/reject	拒绝待发货前更换sku请求
解密订单中的详细收货信息	/channels/ec/order/sensitiveinfo/decode	为保护用户隐私（如收货人昵称、电话号码、详细收货地址），平台订单的收货信息进行了部分隐藏
申请查看订单真实号码	/channels/ec/order/realnumber/apply	如果订单使用了虚拟号，虚拟号不满足需求，可通过该接口提交申请查看真实号
查看订单真实号审核状态	/channels/ec/order/realnumberviewaudit/get	订单申请查看真实号之后，可以获取审核状态
订单再次申请虚拟号	/channels/ec/order/virtualnumber/applyagain	订单虚拟号过期之后，可再次申请一次虚拟号
订单虚拟号延期	/channels/ec/order/virtualnumber/delay	订单虚拟号过期前7天，可通过该接口延期
添加待认证的手机号	/channels/ec/merchant/privatenumber/addphone	【虚拟号拨打实名认证】添加待认证的手机号，并返回运营商实名认证的页面地址
获取短信验证码	/channels/ec/merchant/privatenumber/sendverifycode	【虚拟号拨打实名认证】虚拟号拨打实名认证第一步，获取手机号验证码
获取小店手机号认证状态	/channels/ec/merchant/privatenumber/getphone	【虚拟号拨打实名认证】获取当前手机号的认证状态
资金结算
资金账户
接口名称	请求路径	描述
获取账户余额	/channels/ec/funds/getbalance	可通过该接口获取账户余额
获取结算账户	/channels/ec/funds/getbankacct	可通过该接口获取结算账户
获取资金流水详情	/channels/ec/funds/getfundsflowdetail	可通过该接口获取资金流水详情
获取资金流水列表	/channels/ec/funds/getfundsflowlist	可通过该接口获取资金流水列表
获取提现记录	/channels/ec/funds/getwithdrawdetail	可通过该接口获取提现记录
获取提现记录列表	/channels/ec/funds/getwithdrawlist	可通过该接口获取提现记录列表
修改结算账户	/channels/ec/funds/setbankacct	可通过该接口修改结算账户
商户提现	/channels/ec/funds/submitwithdraw	可通过该接口进行商户提现
查询订单流水列表	/channels/ec/funds/listorderflow	可通过该接口可获取订单的结算信息列表
银行卡
接口名称	请求路径	描述
根据卡号查银行信息	/shop/funds/getbankbynum	该接口可根据卡号查询银行信息
搜索银行列表	/shop/funds/getbanklist	可通过该接口搜索银行列表
查询城市列表	/shop/funds/getcity	可通过该接口查询省份的所有城市
查询大陆银行省份列表	/shop/funds/getprovince	可通过该接口查询大陆银行省份列表
查询支行列表	/shop/funds/getsubbranch	可通过该接口查询支行列表
资金二维码
接口名称	请求路径	描述
获取二维码	/shop/funds/qrcode/get	可通过该接口获取二维码
查询扫码状态	/shop/funds/qrcode/check	可通过该接口查询扫码状态
营销管理
接口名称	请求路径	描述
创建优惠券	/channels/ec/coupon/create	可通过此接口创建优惠券
获取优惠券详情	/channels/ec/coupon/get	通过该接口可获取优惠券详情信息
获取优惠券ID列表	/channels/ec/coupon/get_list	通过此接口可以获取优惠券ID列表
获取用户优惠券详情	/channels/ec/coupon/get_user_coupon	通过此接口可获取用户优惠券详情
获取用户优惠券ID列表	/channels/ec/coupon/get_user_coupon_list	通过此接口可以获取用户优惠券ID列表
更新优惠券内容	/channels/ec/coupon/update	通过该接口可对优惠券内容进行更新
更新优惠券状态	/channels/ec/coupon/update_status	通过此接口可更新优惠券状态
售后管理
接口名称	请求路径	描述
获取售后单列表	/channels/ec/aftersale/getaftersalelist	通过该接口可以获取微信小店的售后单列表
获取售后单	/channels/ec/aftersale/getaftersaleorder	通过该接口可以获取微信小店的售后单
同意售后	/channels/ec/aftersale/acceptapply	通过该接口可以在微信小店售后管理中进行同意售后操作
换货发货	/channels/ec/aftersale/acceptexchangereship	在微信小店售后的换货场景中，收到用户退货后，可以通过该接口进行发货
代用户发起售后	/channels/ec/aftersale/genaftersaleorder	通过该接口，商家可以代用户发起售后
商家获取保障单列表	/channels/ec/aftersale/searchguaranteeorder	通过该接口可以在微信小店售后管理中获取保障单列表
获取保障单详情	/channels/ec/aftersale/getguaranteeorder	通过该接口可以在微信小店售后管理中获取保障单详情
商家同意保障单申请	/channels/ec/aftersale/merchantacceptguarantee	通过该接口可以在微信小店售后管理中进行保障单申请同意操作
商家协商保障单	/channels/ec/aftersale/merchantmodifyguarantee	通过该接口可以在微信小店售后管理中进行保障单协商操作
商家举证保障单	/channels/ec/aftersale/merchantproofguarantee	通过该接口可以在微信小店售后管理中进行保障单举证操作
商家拒绝保障单申请	/channels/ec/aftersale/merchantrefuseguarantee	通过该接口可以在微信小店售后管理中进行保障单申请拒绝操作
商家协商	/channels/ec/aftersale/merchantupdateaftersale	通过该接口可以在微信小店售后管理中进行商家协商操作
获取全量售后原因	/channels/ec/aftersale/reason/get	通过该接口可以获取微信小店的全量售后原因
拒绝售后	/channels/ec/aftersale/rejectapply	通过该接口可以在微信小店售后管理中进行拒绝售后操作
换货拒绝发货	/channels/ec/aftersale/rejectexchangereship	在微信小店售后的换货场景中，收到用户退货后，可以通过该接口拒绝发货
获取拒绝售后原因	/channels/ec/aftersale/rejectreason/get	通过该接口可以获取微信小店的拒绝售后原因
上传退款凭证	/channels/ec/aftersale/uploadrefundcertificate	通过该接口可以将退款凭证上传至微信小店
代用户发起退差价	/channels/ec/aftersale/refundpricediff	通过该接口，商家可以代用户发起退差价
售后单兑换虚拟号	/channels/ec/aftersale/applyvirtualtelnum	可通过该接口用售后单兑换虚拟号
商家客服
接口名称	请求路径	描述
上传多媒体资源	/channels/ec/commkf/cosupload	通过该接口，商家客服可以上传多媒体资源（如图片、视频、文件等）至微信服务器，以便在客服会话中使用
发送消息	/channels/ec/commkf/sendmsg	通过该接口，商家客服可以向指定用户发送客服消息，支持文本、图片、视频等多种消息类型
质检管理
接口名称	请求路径	描述
查询质检仓配置	/channels/ec/qic/inspect/config/get	通过该接口可以查询微信小店的质检仓配置
查询送检配置模板信息	/channels/ec/qic/inspect/submitconfig/get	通过该接口可以查询绑定送检信息需要的配置模板信息，比如质检仓库、质检机构、快递公司、快递产品、保价类型等
打印质检码	/channels/ec/qic/inspect/code/print	绑定完送检信息后，可以通过该接口打印微信小店的质检码
绑定送检信息	/channels/ec/qic/inspect/submit	可以通过该接口绑定微信小店的送检信息
自寄快递送检	/channels/ec/qic/inspect/register_logistics	可以通过该接口登记/修改自寄快递信息，最多可修改三次
纠纷管理
接口名称	请求路径	描述
商家补充纠纷单留言	/channels/ec/aftersale/addcomplaintmaterial	商家通过该接口可以在纠纷单中补充留言
商家举证	/channels/ec/aftersale/addcomplaintproof	商家通过该接口可以在纠纷单中进行举证
获取纠纷单	/channels/ec/aftersale/getcomplaintorder	商家通过该接口可以获取纠纷单详情
物流发货
地址管理
接口名称	请求路径	描述
添加地址	/channels/ec/merchant/address/add	可通过该接口添加地址
获取地址列表	/channels/ec/merchant/address/list	可通过该接口获取地址列表
获取地址详情	/channels/ec/merchant/address/get	可通过该接口获取地址详情
更新地址	/channels/ec/merchant/address/update	可通过该接口更新地址
删除地址	/channels/ec/merchant/address/delete	可通过该接口删除地址
运费模板
接口名称	请求路径	描述
增加运费模版	/channels/ec/merchant/addfreighttemplate	可通过该接口增加运费模板
查询运费模版	/channels/ec/merchant/getfreighttemplatedetail	可通过该接口查询运费模板
获取运费模板列表	/channels/ec/merchant/getfreighttemplatelist	可通过该接口获取运费模板列表
更新运费模版	/channels/ec/merchant/updatefreighttemplate	可通过该接口更新运费模板
电子面单
接口名称	请求路径	描述
获取面单标准模板	/channels/ec/logistics/ewaybill/biz/template/config	可通过该接口获取面单标准模板
新增面单模板	/channels/ec/logistics/ewaybill/biz/template/create	可通过该接口新增面单模板
删除面单模版	/channels/ec/logistics/ewaybill/biz/template/delete	可通过该接口删除面单模板
更新面单模版	/channels/ec/logistics/ewaybill/biz/template/update	可通过该接口更新面单模板
获取面单模板信息	/channels/ec/logistics/ewaybill/biz/template/get	可通过该接口获取面单模板信息
根据模板ID获取面单模板信息	/channels/ec/logistics/ewaybill/biz/template/getbyid	可通过该接囗根据模板id获取面单模板信息
查询开通的电子面单网点/账号信息	/channels/ec/logistics/ewaybill/biz/account/get	可通过该接口查询商家已经开通的网点账号信息，面单账号信息，包括面单账号的状态，库存等等
查询开通的快递公司列表	/channels/ec/logistics/ewaybill/biz/delivery/get	可通过该接口查询商家开通的快递公司列表
电子面单预取号	/channels/ec/logistics/ewaybill/biz/order/precreate	可通过该接口校验电子面单取号接口的参数，并获取全局唯一的ewaybillorderid用于真正取号的接口
电子面单取号	/channels/ec/logistics/ewaybill/biz/order/create	可通过该接口发起电子面单取号
电子面单子件追加	/channels/ec/logistics/ewaybill/biz/order/addsuborder	通过该接口可以对已经取号的电子面单追加子件，目前支持子母单的快递公司有：顺丰速运(SF)、德邦快递(DBKD)、京东快递(JD)、顺心捷达(SXJD)、韵达快运
电子面单取消下单	/channels/ec/logistics/ewaybill/biz/order/cancel	可通过该接口取消已取号的电子面单
查询面单详情	/channels/ec/logistics/ewaybill/biz/order/get	可通过该接口查询电子面单详情
获取打印报文	/channels/ec/logistics/ewaybill/biz/print/get	【小店商家】该接口用于通过商家电子面单获取打印报文
打印成功通知	/channels/ec/logistics/ewaybill/biz/order/print	商家电子面单调用打印组件成功出单后，通知平台出单结果
批量打印通知	/channels/ec/logistics/ewaybill/biz/order/batchprint	商家电子面单调用打印组件成功出单后，批量通知平台出单结果
发货
接口名称	请求路径	描述
订单发货	/channels/ec/order/delivery/send	可通过该接口对订单发货
订单补发货	/channels/ec/order/delivery/compensation	订单商品发货后，因为商品漏发/拆分包裹/坏损/赠品等场景可进行补发
获取快递公司列表	/channels/ec/order/deliverycompanylist/new/get	可通过该接口获取快递公司列表
获取快递公司列表-旧	/channels/ec/order/deliverycompanylist/get	可通过该接口获取快递公司列表（旧）
物流公司虚拟号码
接口名称	请求路径	描述
获取虚拟号码池	/channels/ec/logistics/phonenumberpool/get	可通过该接口获取虚拟号码池
根据运单号获取真实手机号	/channels/ec/logistics/phonenumber/get	该接口用于根据运单号获取真实手机号
根据运单号获取虚拟手机号	/channels/ec/logistics/virtualnumber/get	可通过该接口根据运单号获取虚拟手机号
区域仓库
接口名称	请求路径	描述
创建区域仓库	/channels/ec/warehouse/create	通过该接口可创建区域仓库
查询区域仓库列表	/channels/ec/warehouse/list/get	通过该接口可对区域仓库列表进行查询，查询结果将按照创建时间升序排序
获取区域仓库	/channels/ec/warehouse/get	通过该接口可获取区域仓库信息
修改区域仓库详情	/channels/ec/warehouse/detail/update	通过此接口可对区域仓库详情信息进行修改
批量增加覆盖区域	/channels/ec/warehouse/coverlocations/add	通过该接口区域仓库可进行批量增加覆盖区域操作
批量删除覆盖区域	/channels/ec/warehouse/coverlocations/del	通过该接口区域仓库可进行批量删除覆盖区域操作
获取指定地址下区域仓库的优先级	/channels/ec/warehouse/address/prioritysort/get	通过该接口可获取指定地址下区域仓库的优先级
设置指定地址下区域仓库的优先级	/channels/ec/warehouse/address/prioritysort/set	可通过该接口对指定地址下区域仓库的优先级进行设置
更新区域仓库存数量	/channels/ec/warehouse/stock/update	通过该接口区域仓库可对区域仓库存数量进行更新操作
获取区域仓库存数量	/channels/ec/warehouse/stock/get	通过该接口可获取区域仓库存数量
获取地址行政编码	/channels/ec/basics/addresscode/get	通过该接口可获取地址行政编码信息，最多获取4级地址的行政编码
优选联盟
达人操作
接口名称	请求路径	描述
新增达人	/channels/ec/league/promoter/add	可通过该接口新增店铺合作达人
删除达人	/channels/ec/league/promoter/delete	可通过该接口删除店铺合作达人
获取达人详情信息	/channels/ec/league/promoter/get	可通过该接口获取达人详细信息
获取商店达人列表	/channels/ec/league/promoter/list/get	可通过该接口获取商店达人列表
编辑达人	/channels/ec/league/promoter/upd	可通过该接口编辑达人信息
商品操作
接口名称	请求路径	描述
批量新增联盟商品	/channels/ec/league/item/batchadd	可通过该接口批量新增联盟商品
删除联盟商品	/channels/ec/league/item/delete	可通过该接口删除联盟商品
获取联盟商品详情	/channels/ec/league/item/get	可通过该接口获取联盟商品详情
批量新增联盟机构推广	/channels/ec/league/item/headsupplier/batchadd	可通过该接口批量新增联盟机构推广
获取联盟商品推广列表	/channels/ec/league/item/list/get	可通过该接口获取联盟商品推广列表
更新联盟商品信息	/channels/ec/league/item/upd	可通过该接口更新联盟商品信息
品牌资质
接口名称	请求路径	描述
新增品牌资质	/shop/ec/brand/add	通过该接口可以新增品牌资质
获取品牌库列表	/shop/ec/brand/all	通过该接口可以获取微信小店的品牌库列表
撤回品牌资质审核	/shop/ec/brand/audit/cancel	通过该接口可以撤回品牌资质审核
删除品牌资质	/channels/ec/brand/delete	通过该接口可以删除品牌资质
获取品牌资质申请详情	/channels/ec/brand/get	通过该接口可以获取品牌资质申请详情
获取品牌资质申请列表	/channels/ec/brand/list/get	通过该接口可以获取品牌资质申请列表
更新品牌资质	/channels/ec/brand/update	通过该接口可以更新品牌资质
获取生效中的品牌资质列表	/channels/ec/brand/valid/list/get	通过该接口可以获取生效中的品牌资质列表
代发管理
关联供货商
接口名称	请求路径	描述
获取供货商列表	/channels/ec/supplier/relation/get_supplier_list	本接口用于获取已关联的供货商列表
申请关联供货商	/channels/ec/supplier/relation/invite_supplier	本接口用于商家申请与供货商建立关联
自动分配设置
接口名称	请求路径	描述
获取分配方式	/channels/ec/supplier/relation/get_distribute	本接口用于获取分配方式
设置全店订单手动分配	/channels/ec/supplier/relation/set_manually_distribute	本接口用于设置全店订单手动分配，对新增订单生效
设置全店订单自动分配	/channels/ec/supplier/relation/set_all_distribution	本接口用于设置全店新增订单，自动分配给单一供货商
设置按商品自动分配	/channels/ec/supplier/relation/set_product_distribute	本接口用于设置按商品ID自动分配给指定供货商，对新增订单生效
获取商品对应的自动分配供货商	/channels/ec/supplier/relation/get_product_default_distribute	本接口用于根据商品ID，获取其对应的自动分配供货商
获取按商品自动分配的商品列表	/channels/ec/supplier/relation/get_product_list	本接口用于获取按商品自动分配的商品列表
代发单管理
接口名称	请求路径	描述
分配订单代发	/channels/ec/order/dropship/assign	该接口用于分配订单给供货商代发
取消分配代发单	/channels/ec/order/dropship/cancel	该接口用于取消分配代发单
查询代发单详情	/channels/ec/order/dropship/get	该接口用于查询代发单详情
拉取代发单列表	/channels/ec/order/dropship/list	该接口用于拉取代发单列表
搜索代发单	/channels/ec/order/dropship/search	该接口用于搜索代发单
企业微信
接口名称	请求路径	描述
获取关联账号企微id	/channels/ec/wecom/get_wecom_id	该接口用于获取企业微信在微信小店侧的和，可用于其他API作为查询参数
连接小程序
基础
接口名称	请求路径	描述
获取文件下载链接	/channels/ec/open/get_download_url	通过该接口可获取文件下载链接，使用链接可下载到文件的内容
上传资料	/channels/ec/open/upload	可通过该接口上传文件，用于下单后传给商家进行定制商品发货
合作商家为小程序发放礼物
接口名称	请求路径	描述
查询小店礼物活动列表	/channels/ec/b2c/activity/list/promoter/get	通过该接口查询小店授权送礼活动列表
查询礼物活动详情	/channels/ec/b2c/activity/info/promoter/get	通过该接口查询小店授权送礼活动详情
指定礼物收礼者	/channels/ec/order/presentorder/receiver/set	通过该接口可以指定使用当前小程序发放的小店礼物单的收礼者
创建并发送礼物	/channels/ec/order/presentorder/create	通过该接口创建并发送小店授权送礼商品给指定用户
查询礼物订单列表-旧	/channels/ec/order/presentorderlist/get	通过该接口查询小店授权送礼订单列表
查询礼物订单列表	/channels/ec/order/presentlist/get	可通过该接口获取使用当前小程序发放的小店礼物单列表
查询收礼者订单列表	/channels/ec/order/receiverorderlist/get	通过该接口查询使用当前小程序发放给某位收礼者的小店订单列表
查询礼物订单详情-旧	/channels/ec/order/presentorder/get	通过该接口查询小店授权送礼订单详情
查询礼物订单详情	/channels/ec/order/present/get	通过该接口查询使用当前小程序发放的小店礼物单详情
罗盘商家版
接口名称	请求路径	描述
获取授权视频号列表	/channels/ec/compass/shop/finder/authorization/list/get	通过该接口可获取授权视频号列表
获取带货达人列表	/channels/ec/compass/shop/finder/list/get	通过该接口可获取带货达人列表数据
获取带货数据概览	/channels/ec/compass/shop/finder/overall/get	通过该接口可获取带货数据概览
获取带货达人商品列表	/channels/ec/compass/shop/finder/product/list/get	通过该接口可获取带货达人商品列表
获取带货达人详情	/channels/ec/compass/shop/finder/product/overall/get	通过该接口可获取带货达人详情
获取店铺开播列表	/channels/ec/compass/shop/live/list/get	通过该接口可获取店铺开播列表
获取电商数据概览	/channels/ec/compass/shop/overall/get	通过该接口可获取电商数据概览
获取商品详细信息	/channels/ec/compass/shop/product/data/get	通过该接口可获取商品详细信息
获取商品列表	/channels/ec/compass/shop/product/list/get	通过该接口可获取商品列表
获取店铺人群数据	/channels/ec/compass/shop/sale/profile/data/get	通过该接口可获取店铺人群数据
小店会员
接口名称	请求路径	描述
获取用户积分	/channels/ec/vip/user/score/get	通过该接口可获取用户积分信息
获取用户信息	/channels/ec/vip/user/info/get	通过该接口可获取用户信息
获取用户列表	/channels/ec/vip/user/list/get	通过该接口可获取用户信息列表
获取用户积分流水	/channels/ec/vip/user/score/flowrecord/get	通过该接口可获取用户积分流水明细
小程序会员服务
小店相关
接口名称	请求路径	描述
小店获取关联小程序信息	/channels/ec/vip/v3/wxa/info/get	通过该接口可获取关联的小程序信息
小程序相关
接口名称	请求路径	描述
新增小程序会员信息	/wxa/vip/user/info/add	用户在操作关联入会时，通过该接口可设置小程序的会员信息
更新小程序会员信息	/wxa/vip/user/info/update	该接口用于用户已经关联小店会员后，后续会员信息更新时的同步，比如会员等级从1级到2级
获取小程序会员信息	/wxa/vip/user/info/get	通过该接口可获取小程序的会员信息
获取小程序会员列表	/wxa/vip/user/list/get	通过该接口可获取小程序的会员列表
删除小程序会员信息	/wxa/vip/user/info/delete	通过该接口可删除小程序在关联小店的会员信息
获取小程序已关联小店列表	/wxa/vip/shop/list/get	通过该接口可获取小程序已经关联的小店列表
国补管理
发票管理
接口名称	请求路径	描述
获取国补订单开票信息	/channels/ec/subsidy/query_invoicing_info	1. 必须是使用了国补的订单id
上传国补订单发票信息	/channels/ec/subsidy/upload_invoice_info	1. 必须是使用了国补的订单id
上传国补订单发票文件	/channels/ec/subsidy/upload_invoice_file	为了防止发票文件失效导致审核失败的情况，请使用该接口上传发票文件
