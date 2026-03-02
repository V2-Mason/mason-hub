"""
two_tier_crawl.py — 两层采集 + 拟人化浏览 + 多账号隔离

用法: python two_tier_crawl.py --account A --keywords "k1,k2" [--top-n 10] [--pages 1]

第一层: 搜索 API 广撒网（标题+互动数据），存库
第二层: 仅对互动分最高的 Top N 调详情 API（正文+标签+图片）

拟人化:
- 启动后先逛首页，模拟真实用户
- 搜索间随机延迟 30-90 秒
- 详情间模拟阅读 10-30 秒
- 所有延迟加随机抖动

退出码: 0=正常, 1=运行错误, 2=Cookie 过期
"""

import argparse
import asyncio
import json
import random
import sqlite3
import time
from typing import Dict, List

ACCOUNTS_FILE = '/opt/mediacrawler/accounts.json'
DB_PATH = '/opt/mediacrawler/database/sqlite_tables.db'


# ===== 拟人化延迟 =====

async def human_delay(min_s: float, max_s: float, label: str = ""):
    delay = random.uniform(min_s, max_s)
    if label:
        print(f'    [{label}] {delay:.1f}s')
    await asyncio.sleep(delay)


# ===== 数字解析 =====

def parse_count(s) -> int:
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
    return liked + collected * 3 + comment * 5 + shared * 8


# ===== 数据库操作 =====

def save_search_results(notes: List[Dict], keyword: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved = 0
    for note in notes:
        note_card = note.get('note_card', {})
        user = note_card.get('user', {})
        interact = note_card.get('interact_info', {})
        note_id = note.get('id', '')
        xsec_token = note.get('xsec_token', '')

        if note.get('model_type') != 'note':
            continue

        cover_url = ''
        image_list = note_card.get('image_list', [])
        if image_list:
            cover_url = image_list[0].get('url', '')

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
                note_id, note_type, title, '', '',
                0, 0,
                user.get('user_id', ''), user.get('nickname', ''), user.get('avatar', ''),
                liked, collected, comment, shared,
                '', cover_url, '',
                now_ts, note_url, keyword, xsec_token, now_ts
            ))
            saved += 1

    conn.commit()
    conn.close()
    return saved


def update_note_detail(note_id: str, detail: Dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    user = detail.get('user', {})
    interact = detail.get('interact_info', {})
    image_list = detail.get('image_list', [])
    tag_list = detail.get('tag_list', [])
    video = detail.get('video', {})

    video_url = ''
    if video:
        media = video.get('media', {})
        stream = media.get('stream', {})
        for codec in ['h264', 'h265']:
            streams = stream.get(codec, [])
            if streams:
                video_url = streams[0].get('master_url', '')
                break

    img_urls = []
    for img in image_list:
        url = img.get('url_default', '') or img.get('url', '')
        if url:
            img_urls.append(url)

    tags = [t.get('name', '') for t in tag_list if t.get('type') == 'topic']
    now_ts = int(time.time() * 1000)

    cursor.execute('''
        UPDATE xhs_note SET
            "desc" = ?, video_url = ?, time = ?, last_update_time = ?,
            user_id = ?, nickname = ?, avatar = ?,
            liked_count = ?, collected_count = ?, comment_count = ?, share_count = ?,
            image_list = ?, tag_list = ?, last_modify_ts = ?
        WHERE note_id = ?
    ''', (
        detail.get('desc', ''), video_url,
        detail.get('time', 0), detail.get('last_update_time', 0),
        user.get('user_id', ''), user.get('nickname', ''), user.get('avatar', ''),
        str(interact.get('liked_count', '0')), str(interact.get('collected_count', '0')),
        str(interact.get('comment_count', '0')), str(interact.get('share_count', '0')),
        ','.join(img_urls), ','.join(tags), now_ts,  # ip_location 不采集 — Mason 明确要求
        note_id,
    ))

    conn.commit()
    conn.close()


def get_top_notes(keyword_list: List[str], top_n: int) -> List[Dict]:
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
            'note_id': note_id, 'title': title, 'score': score,
            'xsec_token': xsec_token or '', 'liked': liked, 'collected': collected,
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n]


# ===== 拟人化浏览 =====

async def warm_up_session(page):
    print('  Warming up...')
    await human_delay(3, 8, 'homepage')

    scrolls = random.randint(1, 3)
    for i in range(scrolls):
        scroll_y = random.randint(300, 800)
        await page.evaluate(f'window.scrollBy(0, {scroll_y})')
        await human_delay(2, 6, 'browsing')

    await page.evaluate('window.scrollTo(0, 0)')
    await human_delay(1, 3)
    print('  Warm-up done')


async def check_login(page, cookie_str, a1, ua):
    from media_platform.xhs.playwright_sign import sign_with_playwright
    import httpx

    uri = '/api/sns/web/v1/user/selfinfo'
    signs = await sign_with_playwright(page, uri, None, a1, 'GET')

    headers = {
        'User-Agent': ua,
        'Cookie': cookie_str,
        'X-S': signs['x-s'],
        'X-T': signs['x-t'],
        'X-S-Common': signs['x-s-common'],
        'X-B3-Traceid': signs['x-b3-traceid'],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(f'https://edith.xiaohongshu.com{uri}', headers=headers, timeout=15)

    if resp.status_code != 200:
        return False, f'HTTP {resp.status_code}'

    data = resp.json()
    if data.get('success') and data.get('data'):
        nickname = data['data'].get('nickname', '?')
        print(f'  Login OK: {nickname}')
        return True, nickname

    return False, data.get('msg', 'unknown')


# ===== 主流程 =====

async def run(account_id: str, keywords: str, top_n: int, pages: int):
    from playwright.async_api import async_playwright
    from media_platform.xhs.playwright_sign import sign_with_playwright
    from tools import utils
    import httpx
    import os

    # --- 加载账号配置 ---
    if not os.path.exists(ACCOUNTS_FILE):
        print(f'ERROR: {ACCOUNTS_FILE} not found')
        return 1

    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)

    if account_id not in accounts:
        print(f'ERROR: Account "{account_id}" not found (available: {list(accounts.keys())})')
        return 1

    account = accounts[account_id]
    cookie_str_raw = account.get('cookie', '')
    if not cookie_str_raw:
        print(f'ERROR: Account "{account_id}" has no cookie')
        return 2

    ua = account.get('user_agent',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    viewport = account.get('viewport', {'width': 1440, 'height': 900})

    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]

    print(f'=== Two-Tier Crawl ===')
    print(f'Account: {account_id} ({account.get("name", "?")})')
    print(f'Keywords: {keyword_list}')
    print(f'Pages/keyword: {pages}, Top-N: {top_n}')
    print()

    # --- 启动浏览器（账号独立指纹）---
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str_raw)

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(
        user_agent=ua,
        viewport=viewport,
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
    )

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
        return 1

    all_cookies = await ctx.cookies()
    cookie_str = '; '.join(f'{c["name"]}={c["value"]}' for c in all_cookies)
    a1 = cookie_dict.get('a1', '')

    print('Browser ready')

    # --- Cookie 有效性检测 ---
    print()
    print('--- Cookie check ---')
    valid, msg = await check_login(page, cookie_str, a1, ua)
    if not valid:
        print(f'  Cookie EXPIRED: {msg}')
        await browser.close()
        await p.stop()
        return 2

    # --- 逛首页 ---
    await warm_up_session(page)
    print()

    # --- 第一层：搜索 ---
    print('=== TIER 1: Search ===')
    total_saved = 0
    total_found = 0

    for ki, keyword in enumerate(keyword_list):
        for pg in range(1, pages + 1):
            print(f'  [{ki+1}/{len(keyword_list)}] "{keyword}" page {pg}')

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
                'User-Agent': ua,
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
                    if resp.status_code in (461, 471):
                        print(f'    STOP: Rate limited')
                        break
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
                print(f'    Found {len(notes)}, saved {saved} new')

                if not data.get('data', {}).get('has_more', False):
                    print(f'    No more results')
                    break

            except Exception as e:
                print(f'    Search error: {e}')
                continue

            # 翻页延迟：模拟浏览搜索结果
            await human_delay(5, 15, 'reading results')

        # 关键词间延迟：模拟想下一个要搜什么
        if ki < len(keyword_list) - 1:
            await human_delay(30, 90, 'between keywords')

    print(f'\nTier 1: found {total_found}, saved {total_saved} new')
    print()

    # --- 第二层：Top N 深挖 ---
    print(f'=== TIER 2: Detail (Top {top_n}) ===')
    top_notes = get_top_notes(keyword_list, top_n)

    detail_ok = 0
    detail_fail = 0

    if not top_notes:
        print('No new notes to deep-dive')
    else:
        print(f'Top {len(top_notes)} by score:')
        for i, n in enumerate(top_notes):
            print(f'  {i+1}. [{n["score"]:>8}] {n["title"][:40]}  (赞{n["liked"]} 藏{n["collected"]})')

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
                'User-Agent': ua,
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
                    print(f'  FAIL [{note_id}]: HTTP {resp.status_code}')
                    detail_fail += 1
                    if resp.status_code in (461, 471):
                        print(f'  STOP: Rate limited')
                        break
                    await human_delay(5, 15, 'cooldown')
                    continue

                data = resp.json()
                if not data.get('success') or not data.get('data', {}).get('items'):
                    msg = data.get('msg', 'no items')
                    print(f'  FAIL [{note_id}]: {msg}')
                    detail_fail += 1
                    if data.get('code') == 300011:
                        print(f'  STOP: Rate limited')
                        break
                    await human_delay(5, 15, 'cooldown')
                    continue

                detail = data['data']['items'][0].get('note_card', {})
                update_note_detail(note_id, detail)

                tags = [t.get('name', '') for t in detail.get('tag_list', []) if t.get('type') == 'topic']
                print(f'  OK   [{note_id}]: +desc({len(detail.get("desc", ""))}字) +tags({",".join(tags[:3])})')
                detail_ok += 1

            except Exception as e:
                print(f'  ERROR [{note_id}]: {e}')
                detail_fail += 1

            # 模拟阅读笔记
            await human_delay(10, 30, 'reading note')

        print(f'\nTier 2: {detail_ok} OK, {detail_fail} failed')

    # --- 清理 ---
    await browser.close()
    await p.stop()

    # --- 汇总 ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM xhs_note')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM xhs_note WHERE "desc" IS NOT NULL AND "desc" != ""')
    with_detail = cursor.fetchone()[0]
    conn.close()

    print(f'\n=== Summary ===')
    print(f'DB total: {total} notes ({with_detail} with detail)')
    print(f'This run: +{total_saved} search, {detail_ok}/{top_n} detail')

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', required=True, help='Account ID (A, B, ...)')
    parser.add_argument('--keywords', required=True, help='Comma-separated keywords')
    parser.add_argument('--top-n', type=int, default=10)
    parser.add_argument('--pages', type=int, default=1)
    args = parser.parse_args()

    exit_code = asyncio.run(run(args.account, args.keywords, args.top_n, args.pages))
    exit(exit_code or 0)
