"""合并小红书开放平台所有文档为一份完整 MD

来源 1: intel/raw/xhs-docs/小红书开放平台API完整文档.md (apifox, 114 API 端点)
来源 2: intel/raw/xhs-docs/ 下爬取的 239 个分文件 (开发文档/SDK/消息/公告)

输出: intel/processed/小红书开放平台-完整规则文档.md
"""

import os
import datetime

BASE = os.path.expanduser('~/mason-hub/intel/raw/xhs-docs')
OUT_DIR = os.path.expanduser('~/mason-hub/intel/processed')
OUT_FILE = os.path.join(OUT_DIR, '小红书开放平台-完整规则文档.md')

# 定义文档结构（按目录映射到章节）
SECTIONS = [
    ('一、开发指南', '开发文档/开发文档', [
        '新手指南', '应用开发', '应用测试',
        '授权流程（自研）', '授权流程（软件服务商）',
        '授权流程-新自研商家', '授权流程-新三方服务商',
        '签名算法', '系统参数说明', '接口限流说明',
        '应用消息推送', 'SDK 使用说明', 'SDK使用说明',
        '发布服务', '上架服务市场',
    ]),
    ('二、API 调用场景', '开发文档/API调用场景', None),  # None = 全部包含
    ('三、数据加解密', '开发文档/数据加解密', None),
    ('四、电子面单', '开发文档/电子面单', None),
    ('五、规则中心', '开发文档/规则中心', None),
    ('六、SDK 文档 — 商品', 'SDK文档/商品', None),
    ('七、SDK 文档 — 订单', 'SDK文档/订单', None),
    ('八、SDK 文档 — 售后', 'SDK文档/售后', None),
    ('九、SDK 文档 — 通用', 'SDK文档/通用', None),
    ('十、消息文档 — 商品消息', '消息文档/商品消息', None),
    ('十一、消息文档 — 履约消息', '消息文档/履约消息', None),
    ('十二、消息文档 — 售后消息', '消息文档/售后消息', None),
    ('十三、消息文档 — 供货商消息', '消息文档/供货商消息', None),
    ('十四、消息文档 — 授权消息', '消息文档/授权消息', None),
    ('十五、平台公告 — 产品发布', '平台公告/产品发布', None),
    ('十六、平台公告 — 技术变更', '平台公告/技术变更', None),
    ('十七、平台公告 — 其他公告', '平台公告/其他公告', None),
]


def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        return f'[读取失败: {e}]'


def list_md_files(dirpath, ordered_names=None):
    """列出目录下所有 .md 文件，按指定顺序或字母排序"""
    if not os.path.isdir(dirpath):
        return []

    files = [f for f in os.listdir(dirpath) if f.endswith('.md')]

    if ordered_names:
        # 按指定顺序排，未列出的追加到末尾
        name_set = set(ordered_names)
        ordered = []
        for name in ordered_names:
            fname = name + '.md'
            if fname in files:
                ordered.append(fname)
        # 追加剩余
        for f in sorted(files):
            if f not in ordered:
                ordered.append(f)
        return ordered
    else:
        return sorted(files)


def build_document():
    lines = []

    # Header
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M ET')
    lines.append('# 小红书开放平台 — 完整规则文档')
    lines.append('')
    lines.append(f'> 合并生成时间: {now}')
    lines.append('> 数据来源:')
    lines.append('>   1. [小红书开放平台 API 文档](https://xiaohongshu.apifox.cn) — 114 个 API 端点详情')
    lines.append('>   2. [小红书开放平台官网](https://open.xiaohongshu.com) — 开发文档/SDK/消息/公告/规则')
    lines.append('')
    lines.append('---')
    lines.append('')

    # TOC
    lines.append('## 目录')
    lines.append('')
    for title, _, _ in SECTIONS:
        anchor = title.replace(' ', '-').replace('—', '-').replace('、', '')
        lines.append(f'- [{title}](#{anchor})')
    lines.append('- [十八、API 端点详细参考](#十八API-端点详细参考)')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Sections from crawled files
    for title, subdir, ordered_names in SECTIONS:
        dirpath = os.path.join(BASE, subdir)
        md_files = list_md_files(dirpath, ordered_names)

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

    # Section: API Reference from 完整文档
    lines.append('# 十八、API 端点详细参考')
    lines.append('')
    lines.append('> 以下内容来自 [xiaohongshu.apifox.cn](https://xiaohongshu.apifox.cn)，包含 114 个 API 端点的完整参数和返回值说明。')
    lines.append('')

    api_doc_path = os.path.join(BASE, '小红书开放平台API完整文档.md')
    api_content = read_file(api_doc_path)
    # Skip the header (first few lines up to first ---) since we have our own
    parts = api_content.split('---', 2)
    if len(parts) >= 3:
        # Skip header and TOC, keep the API content
        lines.append(parts[2].strip())
    else:
        lines.append(api_content)

    lines.append('')

    return '\n'.join(lines)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print('合并小红书文档...')
    doc = build_document()

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(doc)

    size_kb = os.path.getsize(OUT_FILE) / 1024
    line_count = doc.count('\n') + 1
    print(f'完成: {OUT_FILE}')
    print(f'大小: {size_kb:.0f} KB, {line_count} 行')


if __name__ == '__main__':
    main()
