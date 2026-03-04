"""合并微信小店开发者文档为一份完整 MD

来源: intel/raw/wechat-store-docs/ 下爬取的 208 个分文件
输出: intel/processed/微信小店-完整规则文档.md
"""

import os
import datetime

BASE = os.path.expanduser('~/mason-hub/intel/raw/wechat-store-docs')
OUT_DIR = os.path.expanduser('~/mason-hub/intel/processed')
OUT_FILE = os.path.join(OUT_DIR, '微信小店-完整规则文档.md')

# 文档结构：两套 API 目录（API/ 精简版 + API文档/ 完整版）+ 开发者文档
SECTIONS = [
    # 通用介绍
    ('一、平台介绍', '开发者文档/开发者文档/通用', None),
    ('二、API 接口总览', '开发者文档/开发者文档/API', None),

    # API文档（完整版，按业务模块）
    ('三、接口凭据与通用管理', '开发者文档/API文档/apimgnt', [
        '通用', '获取接口调用凭据', '获取稳定版接口调用凭据',
        '查询API调用额度', '重置API调用次数', '使用AppSecret重置API调用次数',
        '重置指定API调用次数', '查询rid信息',
        '获取微信API服务器IP', '获取微信推送服务器IP', '网络通信检测',
        '上传图片', '通过mediaid获取数据',
    ]),
    ('四、类目管理', '开发者文档/API文档/channels-shop-category', [
        '类目管理', '获取所有类目', '获取类目信息',
        '申请类目', '撤销类目审核',
        '获取店铺的类目权限列表', '获取店铺的类目权限详情',
        '获取店铺的类目审核单列表', '获取店铺的类目审核单详情',
    ]),
    ('五、类目规则', '开发者文档/API文档/category-rule', None),
    ('六、商品管理', '开发者文档/API文档/商品管理', [
        '商品管理', '获取商品列表', '获取商品', '更新商品', '免审更新商品',
        '删除商品', '上架商品', '下架商品', '撒回商品审核',
        '发品前校验', '获取商品上架策略', '设置商品上架策略', '获取商品提审限额',
        '类目推荐', '商品品牌推荐', '商品属性映射及推荐', '站内外商品属性映射',
        '获取商品H5短链', '获取商品二维码', '获取商品口令', '获取商品的移动应用跳转scheme码',
        '取消商品开售',
        # 库存
        '库存', '获取库存', '快速更新库存', '批量获取库存信息', '获取库存流水',
        # 限时抢购
        '商品限时抢购', '添加限时抢购任务', '获取限时抢购任务列表', '删除限时抢购任务',
        # 赠品
        '赠品', '获取赠品列表', '获取赠品', '更新赠品库存', '在售商品转赠品', '添加非卖商品', '更新非卖商品',
        # 买赠活动
        '买赠活动', '创建赠品活动', '停止赠品活动',
    ]),
    ('七、订单管理', '开发者文档/API文档/订单管理', [
        '订单管理', '订单搜索', '获取订单详情',
        '解密订单中的详细收货信息', '申请查看订单真实号码',
        '修改订单价格', '修改订单地址', '修改订单备注', '修改物流信息',
        '同意用户修改收货地址申请', '拒绝用户修改收货地址申请',
        '同意待发货前更换sku请求', '拒绝待发货前更换sku请求', '获取所有待发货前更换sku待处理请求',
        '订单再次申请虚拟号', '订单虚拟号延期',
        '上传生鲜质检信息', '获取礼物单的子单列表',
    ]),
    ('八、售后管理', '开发者文档/API文档/售后管理', [
        '售后管理', '拒绝售后', '获取拒绝售后原因', '获取全量售后原因',
        '商家协商', '上传退款凭证', '换货发货', '换货拒绝发货',
        '代用户发起退差价',
        '商家获取保障单列表', '获取保障单详情', '商家拒绝保障单申请', '商家举证保障单',
    ]),
    ('九、物流管理', '开发者文档/API文档/物流管理', [
        '发货', '物流发货', '订单发货', '订单补发货',
        '获取快递公司列表', '获取快递公司列表-旧',
        '获取运费模板列表', '更新运费模版',
        '电子面单', '电子面单取号', '电子面单取消下单', '电子面单子件追加',
        '新增面单模板', '更新面单模版', '删除面单模版',
        '打印成功通知', '批量打印通知',
        '添加地址', '更新地址', '删除地址',
        '物流公司虚拟号码', '获取虚拟号码池', '根据运单号获取虚拟手机号', '根据运单号获取真实手机号',
        '修改物流信息',
    ]),
    ('十、资金管理', '开发者文档/API文档/资金管理', [
        '资金账户', '获取账户余额', '获取资金流水列表', '获取资金流水详情',
        '获取结算账户', '修改结算账户',
        '商户提现', '获取提现记录', '获取提现记录列表',
        '资金二维码', '获取二维码', '查询扫码状态',
        '查询订单流水列表',
        '查询大陆银行省份列表', '查询城市列表', '查询支行列表', '搜索银行列表',
    ]),
    ('十一、品牌资质', '开发者文档/API文档/品牌资质', [
        '品牌资质', '新增品牌资质', '更新品牌资质', '删除品牌资质', '撤回品牌资质审核',
        '获取品牌库列表', '获取品牌资质申请列表',
    ]),
    ('十二、营销（优惠券）', '开发者文档/API文档/营销', None),
    ('十三、数据分析（罗盘）', '开发者文档/API文档/数据分析', None),
    ('十四、客服', '开发者文档/API文档/kf', None),
    ('十五、主页管理', '开发者文档/API文档/主页管理', None),
    ('十六、优选联盟', '开发者文档/API文档/优选联盟', None),
    ('十七、小程序+小店', '开发者文档/API文档/miniandstore', None),

    # API/ 精简版（接口列表汇总）
    ('十八、API 精简接口列表', '开发者文档/API/商品管理', None),
    ('', '开发者文档/API/订单管理', None),
    ('', '开发者文档/API/售后管理', None),
    ('', '开发者文档/API/物流管理', None),
    ('', '开发者文档/API/资金管理', None),
    ('', '开发者文档/API/品牌资质', None),
    ('', '开发者文档/API/营销', None),
]


def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        return f'[读取失败: {e}]'


def list_md_files(dirpath, ordered_names=None):
    if not os.path.isdir(dirpath):
        return []
    files = [f for f in os.listdir(dirpath) if f.endswith('.md')]
    if ordered_names:
        name_set = {n + '.md' for n in ordered_names}
        ordered = [n + '.md' for n in ordered_names if (n + '.md') in files]
        for f in sorted(files):
            if f not in ordered:
                ordered.append(f)
        return ordered
    return sorted(files)


def build_document():
    lines = []
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M CST')

    lines.append('# 微信小店 — 完整规则文档')
    lines.append('')
    lines.append(f'> 合并生成时间: {now}')
    lines.append('> 数据来源: [微信小店开发者文档](https://developers.weixin.qq.com/doc/store/)')
    lines.append('')
    lines.append('---')
    lines.append('')

    # TOC
    lines.append('## 目录')
    lines.append('')
    for title, _, _ in SECTIONS:
        if title:
            anchor = title.replace(' ', '-').replace('—', '-').replace('、', '').replace('（', '').replace('）', '')
            lines.append(f'- [{title}](#{anchor})')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Sections
    for title, subdir, ordered_names in SECTIONS:
        dirpath = os.path.join(BASE, subdir)
        md_files = list_md_files(dirpath, ordered_names)

        if title:
            lines.append(f'# {title}')
            lines.append('')

        if not md_files:
            lines.append(f'*（目录 {subdir} 无内容）*')
            lines.append('')
            continue

        for fname in md_files:
            filepath = os.path.join(dirpath, fname)
            content = read_file(filepath)
            doc_title = fname.replace('.md', '')

            lines.append(f'## {doc_title}')
            lines.append('')
            lines.append(content)
            lines.append('')
            lines.append('---')
            lines.append('')

    return '\n'.join(lines)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print('合并微信小店文档...')
    doc = build_document()

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(doc)

    size_kb = os.path.getsize(OUT_FILE) / 1024
    line_count = doc.count('\n') + 1
    print(f'完成: {OUT_FILE}')
    print(f'大小: {size_kb:.0f} KB, {line_count} 行')


if __name__ == '__main__':
    main()
