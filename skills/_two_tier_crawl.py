"""
two_tier_crawl.py — 两层采集：搜索广撒网 + 详情精准深挖
用法: python two_tier_crawl.py --keywords "关键词1,关键词2" [--top-n 10] [--pages 1]

第一层: 搜索 API 获取大量笔记基本信息（标题+互动数据），直接存库
第二层: 对互动分最高的 Top N 条调 Feed API 获取完整内容（正文+标签+图片）
"""

import argparse
import asyncio
import json
import re
import sqlite3
import time
from typing import Dict, List, Optional

# --- 数字解析 ---
def parse_count(s) -> int:
    """解析小红书互动数字: '1.2万' → 12000, '10万+' → 100000"""
    if s is None:
        return 0
    s = str(s).strip().replace('+', '')
    if '万' in s:
        return int(float(s.replace('万', '')) * 10000)
    if '亿' in s:
        return int(float(s.replace('亿', '')) * 100000000)
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0

def interaction_score(liked, collected, comment, shared) -> int:
    """互动评分: 赞 + 藏×3 + 评×5 + 转×8"""
    return liked + collected * 3 + comment * 5 + shared * 8

# --- DB 操作 ---
DB_PATH = '/opt/mediacrawler/database/sqlite_tables.db'

def save_search_results(notes: List[Dict], keyword: str) -> int:
    """保存搜索结果到 xhs_note 表（desc/tag_list 为空，后续 Top N 会补充）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved = 0
    for note in notes:
        note_card = note.get('note_card', {})
        user = note_card.get('user', {})
        interact = note_card.get('interact_info', {})
        note_id = note.get('id', '')
        xsec_token = note.get('xsec_token', '')

        # 跳过非笔记类型（hot_query 等）
        if note.get('model_type') != 'note':
            continue

        # 提取发布日期
        corner_tags = note_card.get('corner_tag_info', [])
        publish_text = ''
        for tag in corner_tags:
            if tag.get('type') == 'publish_time':
                publish_text = tag.get('text', '')

        # 封面图
        cover_url = ''
        image_list = note_card.get('image_list', [])
        if image_list:
            cover_url = image_list[0].get('url', '')

        # 检查是否已存在
        cursor.execute('SELECT note_id FROM xhs_note WHERE note_id = ?', (note_id,))
        existing = cursor.fetchone()

        liked = str(interact.get('liked_count', '0'))
        collected = str(interact.get('collected_count', '0'))
        comment = str(interact.get('comment_count', '0'))
        shared = str(interact.get('shared_count', '0'))
        note_type = note_card.get('type', 'normal')
        title = note_card.get('display_title', '')
        note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_search"
        now_ts = int(time.time() * 1000)

        if existing:
            # 更新互动数据（可能有变化）
            cursor.execute('''
                UPDATE xhs_note SET
                    liked_count = ?, collected_count = ?, comment_count = ?, share_count = ?,
                    last_modify_ts = ?, xsec_token = ?
                WHERE note_id = ?
            ''', (liked, collected, comment, shared, now_ts, xsec_token, note_id))
        else:
            cursor.execute('''
                INSERT INTO xhs_note (
                    note_id, type, title, "desc", video_url, time, last_update_time,
                    user_id, nickname, avatar,
                    liked_count, collected_count, comment_count, share_count,
                    ip_location, image_list, tag_list, last_modify_ts,
                    note_url, source_keyword, xsec_token, add_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                note_id, note_type, title, '', '',  # desc/video_url 留空
                0, 0,  # time/last_update_time 留空（搜索结果没有精确时间戳）
                user.get('user_id', ''), user.get('nickname', ''), user.get('avatar', ''),
                liked, collected, comment, shared,
                '', cover_url, '',  # ip_location/tag_list 留空
                now_ts, note_url, keyword, xsec_token, now_ts
            ))
            saved += 1

    conn.commit()
    conn.close()
    return saved

def update_note_detail(note_id: str, detail: Dict):
    """用 Feed API 返回的完整数据更新已有记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    user = detail.get('user', {})
    interact = detail.get('interact_info', {})
    image_list = detail.get('image_list', [])
    tag_list = detail.get('tag_list', [])
    video = detail.get('video', {})

    # 提取视频 URL
    video_url = ''
    if video:
        media = video.get('media', {})
        stream = media.get('stream', {})
        for codec in ['h264', 'h265']:
            streams = stream.get(codec, [])
            if streams:
                video_url = streams[0].get('master_url', '')
                break

    # 提取图片 URL 列表
    img_urls = []
    for img in image_list:
        url = img.get('url_default', '') or img.get('url', '')
        if url:
            img_urls.append(url)

    # 提取标签
    tags = [t.get('name', '') for t in tag_list if t.get('type') == 'topic']

    now_ts = int(time.time() * 1000)

    cursor.execute('''
        UPDATE xhs_note SET
            "desc" = ?,
            video_url = ?,
            time = ?,
            last_update_time = ?,
            user_id = ?,
            nickname = ?,
            avatar = ?,
            liked_count = ?,
            collected_count = ?,
            comment_count = ?,
            share_count = ?,
            ip_location = ?,
            image_list = ?,
            tag_list = ?,
            last_modify_ts = ?
        WHERE note_id = ?
    ''', (
        detail.get('desc', ''),
        video_url,
        detail.get('time', 0),
        detail.get('last_update_time', 0),
        user.get('user_id', ''),
        user.get('nickname', ''),
        user.get('avatar', ''),
        str(interact.get('liked_count', '0')),
        str(interact.get('collected_count', '0')),
        str(interact.get('comment_count', '0')),
        str(interact.get('share_count', '0')),
        detail.get('ip_location', ''),
        ','.join(img_urls),
        ','.join(tags),
        now_ts,
        note_id,
    ))

    conn.commit()
    conn.close()

def get_top_notes(keyword_list: List[str], top_n: int) -> List[Dict]:
    """从本次采集的笔记中选出互动分最高的 Top N（只选 desc 为空的，即还没深挖过的）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(keyword_list))
    cursor.execute(f'''
        SELECT note_id, title, liked_count, collected_count, comment_count, share_count, xsec_token
        FROM xhs_note
        WHERE source_keyword IN ({placeholders})
          AND ("desc" IS NULL OR "desc" = '')
        ORDER BY last_modify_ts DESC
    ''', keyword_list)

    rows = cursor.fetchall()
    conn.close()

    scored = []
    for row in rows:
        note_id, title, liked, collected, comment, shared, xsec_token = row
        score = interaction_score(
            parse_count(liked), parse_count(collected),
            parse_count(comment), parse_count(shared)
        )
        scored.append({
            'note_id': note_id,
            'title': title,
            'score': score,
            'xsec_token': xsec_token or '',
            'liked': liked,
            'collected': collected,
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n]


# --- 主流程 ---
async def run(keywords: str, top_n: int, pages: int):
    from playwright.async_api import async_playwright
    from media_platform.xhs.playwright_sign import sign_with_playwright
    from tools import utils
    import httpx

    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
    print(f'=== Two-Tier Crawl ===')
    print(f'Keywords: {keyword_list}')
    print(f'Pages per keyword: {pages}')
    print(f'Top N for detail: {top_n}')
    print()

    # --- 启动浏览器 ---
    from config import base_config as config
    cookie_dict = utils.convert_str_cookie_to_dict(config.COOKIES)

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context()

    for k, v in cookie_dict.items():
        await ctx.add_cookies([{'name': k, 'value': v, 'domain': '.xiaohongshu.com', 'path': '/'}])

    await ctx.add_init_script(path='/opt/mediacrawler/libs/stealth.min.js')
    page = await ctx.new_page()
    await page.goto('https://www.xiaohongshu.com')
    await asyncio.sleep(3)

    has_mnsv2 = await page.evaluate('() => typeof window.mnsv2')
    if has_mnsv2 != 'function':
        print(f'ERROR: mnsv2 not loaded (type: {has_mnsv2})')
        await browser.close()
        await p.stop()
        return

    all_cookies = await ctx.cookies()
    cookie_str = '; '.join(f'{c["name"]}={c["value"]}' for c in all_cookies)
    a1 = cookie_dict.get('a1', '')

    print('Browser ready, mnsv2 loaded')
    print()

    # --- 第一层：搜索 ---
    print('=== TIER 1: Search ===')
    total_saved = 0
    total_found = 0

    for keyword in keyword_list:
        for pg in range(1, pages + 1):
            print(f'  Searching: "{keyword}" page {pg}...')

            search_data = {
                'keyword': keyword,
                'page': pg,
                'page_size': 20,
                'search_id': utils.get_search_id() if hasattr(utils, 'get_search_id') else '',
                'sort': 'general',
                'note_type': 0,
                'ext_flags': [],
                'image_formats': ['jpg', 'webp', 'avif'],
            }

            uri = '/api/sns/web/v1/search/notes'
            signs = await sign_with_playwright(page, uri, search_data, a1, 'POST')

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/json;charset=UTF-8',
                'Origin': 'https://www.xiaohongshu.com',
                'Referer': 'https://www.xiaohongshu.com/',
                'Cookie': cookie_str,
                'X-S': signs['x-s'],
                'X-T': signs['x-t'],
                'X-S-Common': signs['x-s-common'],
                'X-B3-Traceid': signs['x-b3-traceid'],
            }

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f'https://edith.xiaohongshu.com{uri}',
                        content=json.dumps(search_data, separators=(',', ':'), ensure_ascii=False),
                        headers=headers,
                        timeout=15,
                    )

                if resp.status_code != 200:
                    print(f'    Search failed: HTTP {resp.status_code}')
                    continue

                data = resp.json()
                if not data.get('success'):
                    print(f'    Search failed: {data.get("msg", "unknown")}')
                    continue

                items = data.get('data', {}).get('items', [])
                notes = [item for item in items if item.get('model_type') == 'note']
                total_found += len(notes)

                saved = save_search_results(items, keyword)
                total_saved += saved
                print(f'    Found {len(notes)} notes, saved {saved} new')

                if not data.get('data', {}).get('has_more', False):
                    print(f'    No more results for "{keyword}"')
                    break

            except Exception as e:
                print(f'    Search error: {e}')
                continue

            # 页间延迟
            await asyncio.sleep(2)

        # 关键词间延迟
        await asyncio.sleep(3)

    print(f'\nTier 1 done: found {total_found}, saved {total_saved} new')
    print()

    # --- 第二层：Top N 深挖 ---
    print(f'=== TIER 2: Detail (Top {top_n}) ===')
    top_notes = get_top_notes(keyword_list, top_n)

    if not top_notes:
        print('No new notes to deep-dive')
    else:
        print(f'Top {len(top_notes)} by interaction score:')
        for i, n in enumerate(top_notes):
            print(f'  {i+1}. [{n["score"]:>8}] {n["title"][:40]}  (赞{n["liked"]} 藏{n["collected"]})')

        detail_ok = 0
        detail_fail = 0

        for n in top_notes:
            note_id = n['note_id']
            xsec_token = n['xsec_token']

            feed_data = {
                'source_note_id': note_id,
                'image_formats': ['jpg', 'webp', 'avif'],
                'extra': {'need_body_topic': 1},
                'xsec_source': 'pc_search',
                'xsec_token': xsec_token,
            }

            uri = '/api/sns/web/v1/feed'
            signs = await sign_with_playwright(page, uri, feed_data, a1, 'POST')

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/json;charset=UTF-8',
                'Origin': 'https://www.xiaohongshu.com',
                'Referer': 'https://www.xiaohongshu.com/',
                'Cookie': cookie_str,
                'X-S': signs['x-s'],
                'X-T': signs['x-t'],
                'X-S-Common': signs['x-s-common'],
                'X-B3-Traceid': signs['x-b3-traceid'],
            }

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f'https://edith.xiaohongshu.com{uri}',
                        content=json.dumps(feed_data, separators=(',', ':'), ensure_ascii=False),
                        headers=headers,
                        timeout=15,
                    )

                if resp.status_code != 200:
                    print(f'  FAIL [{note_id}]: HTTP {resp.status_code} - {resp.text[:100]}')
                    detail_fail += 1
                    await asyncio.sleep(3)
                    continue

                data = resp.json()
                if not data.get('success') or not data.get('data', {}).get('items'):
                    msg = data.get('msg', 'no items')
                    print(f'  FAIL [{note_id}]: {msg}')
                    detail_fail += 1

                    # 如果是风控，停止深挖
                    if data.get('code') == 300011 or resp.status_code in (461, 471):
                        print(f'  STOP: Rate limited, skipping remaining details')
                        break

                    await asyncio.sleep(3)
                    continue

                detail = data['data']['items'][0].get('note_card', {})
                detail['note_id'] = note_id
                detail['xsec_token'] = xsec_token
                update_note_detail(note_id, detail)

                desc_preview = detail.get('desc', '')[:50]
                tags = [t.get('name', '') for t in detail.get('tag_list', []) if t.get('type') == 'topic']
                print(f'  OK   [{note_id}]: +desc({len(detail.get("desc", ""))}字) +tags({",".join(tags[:3])})')
                detail_ok += 1

            except Exception as e:
                print(f'  ERROR [{note_id}]: {e}')
                detail_fail += 1

            # 详情请求间延迟（关键：避免风控）
            await asyncio.sleep(5)

        print(f'\nTier 2 done: {detail_ok} OK, {detail_fail} failed')

    # --- 清理 ---
    await browser.close()
    await p.stop()

    # --- 统计 ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM xhs_note')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM xhs_note WHERE "desc" IS NOT NULL AND "desc" != ""')
    with_detail = cursor.fetchone()[0]
    conn.close()

    print(f'\n=== Summary ===')
    print(f'Database total: {total} notes ({with_detail} with full detail)')
    print(f'This run: {total_saved} new from search, top {top_n} deep-dived')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keywords', required=True, help='Comma-separated keywords')
    parser.add_argument('--top-n', type=int, default=10, help='Top N notes to fetch detail for')
    parser.add_argument('--pages', type=int, default=1, help='Pages per keyword')
    args = parser.parse_args()

    asyncio.run(run(args.keywords, args.top_n, args.pages))
