"""
_xhs_collect_comments.py — Top 帖子评论采集

用法: python _xhs_collect_comments.py --account MAIN [--top-n 10] [--max-comments 20]

流程:
1. 从 xhs_note 取互动分最高的 top-n 帖子（需要有 xsec_token）
2. 对每个帖子调评论 API，采集一级评论（含子评论数）
3. 存入 xhs_note_comment 表（已有表，复用 schema）

非阻塞: API 失败/限流 → 停止，已采集的数据保留
退出码: 0=成功, 1=运行错误, 2=Cookie 过期, 3=无数据可采
"""
import argparse
import asyncio
import json
import os
import random
import sqlite3
import time
from typing import Dict, List

ACCOUNTS_FILE = '/opt/mediacrawler/accounts.json'
DB_PATH = '/opt/mediacrawler/database/sqlite_tables.db'


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


def get_top_notes_for_comments(top_n: int) -> List[Dict]:
    """Get top N notes by interaction score that have xsec_token."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute('''
        SELECT note_id, title, liked_count, collected_count,
               comment_count, share_count, xsec_token
        FROM xhs_note
        WHERE xsec_token IS NOT NULL AND xsec_token != ''
    ''').fetchall()
    conn.close()

    scored = []
    for r in rows:
        liked = parse_count(r['liked_count'])
        collected = parse_count(r['collected_count'])
        comment = parse_count(r['comment_count'])
        shared = parse_count(r['share_count'])
        score = liked + collected * 3 + comment * 5 + shared * 8
        scored.append({
            'note_id': r['note_id'],
            'title': r['title'] or '',
            'score': score,
            'comment_count': comment,
            'xsec_token': r['xsec_token'],
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n]


def get_existing_comment_ids(note_id: str) -> set:
    """Get already-collected comment IDs for a note."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT comment_id FROM xhs_note_comment WHERE note_id = ?', (note_id,))
    ids = {r[0] for r in cur.fetchall()}
    conn.close()
    return ids


def save_comments(note_id: str, comments: List[Dict]) -> int:
    """Save comments to xhs_note_comment table. Returns count of new comments saved."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_ts = int(time.time() * 1000)
    saved = 0

    for c in comments:
        comment_id = c.get('id', '')
        if not comment_id:
            continue

        # Check if already exists
        cur.execute('SELECT id FROM xhs_note_comment WHERE comment_id = ?', (comment_id,))
        if cur.fetchone():
            continue

        user_info = c.get('user_info', {})
        sub_comment_count = c.get('sub_comment_count', 0)
        # parent_comment_id: empty for top-level, set for sub-comments
        parent_comment_id = c.get('target_comment', {}).get('id', '')

        # like_count from API
        like_count = str(c.get('like_count', '0'))

        # create_time is in milliseconds
        create_time = c.get('create_time', 0)

        # pictures
        pictures = ''
        pic_list = c.get('pictures', [])
        if pic_list:
            pictures = ','.join(p.get('url_default', '') or p.get('url', '')
                                for p in pic_list if p)

        cur.execute('''
            INSERT INTO xhs_note_comment (
                comment_id, note_id, content, create_time, like_count,
                sub_comment_count, parent_comment_id,
                user_id, nickname, avatar, ip_location, pictures,
                add_ts, last_modify_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comment_id, note_id,
            c.get('content', ''),
            create_time,
            like_count,
            sub_comment_count,
            parent_comment_id,
            user_info.get('user_id', ''),
            user_info.get('nickname', ''),
            user_info.get('image', ''),
            '',  # ip_location — 不采集
            pictures,
            now_ts, now_ts,
        ))
        saved += 1

    conn.commit()
    conn.close()
    return saved


async def fetch_comments_page(page, cookie_str, a1, ua, note_id, xsec_token, cursor=''):
    """Fetch one page of comments for a note. Returns (comments_list, cursor, has_more) or (None, '', False)."""
    from media_platform.xhs.playwright_sign import sign_with_playwright
    import httpx

    params = {
        'note_id': note_id,
        'cursor': cursor,
        'top_comment_id': '',
        'image_formats': 'jpg,webp,avif',
        'xsec_token': xsec_token,
    }

    uri = '/api/sns/web/v2/comment/page'
    signs = await sign_with_playwright(page, uri, params, a1, 'GET')

    headers = {
        'User-Agent': ua,
        'Cookie': cookie_str,
        'Referer': 'https://www.xiaohongshu.com/',
        'X-S': signs['x-s'],
        'X-T': signs['x-t'],
        'X-S-Common': signs['x-s-common'],
        'X-B3-Traceid': signs['x-b3-traceid'],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f'https://edith.xiaohongshu.com{uri}',
            headers=headers, params=params, timeout=15)

    if resp.status_code in (461, 471):
        print(f'    RATE LIMITED ({resp.status_code})')
        return None, '', False

    if resp.status_code != 200:
        print(f'    HTTP {resp.status_code}')
        return None, '', False

    data = resp.json()
    if not data.get('success'):
        print(f'    API error: {data.get("msg", "unknown")}')
        return None, '', False

    result = data.get('data', {})
    comments = result.get('comments', [])
    next_cursor = result.get('cursor', '')
    has_more = result.get('has_more', False)

    return comments, next_cursor, has_more


async def collect(account_id: str, top_n: int, max_comments: int):
    from playwright.async_api import async_playwright
    from tools import utils

    # --- Load account ---
    if not os.path.exists(ACCOUNTS_FILE):
        print(f'ERROR: {ACCOUNTS_FILE} not found')
        return 1

    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)

    account = None
    for acct_id in [account_id, 'MAIN']:
        acct = accounts.get(acct_id, {})
        if acct.get('cookie', ''):
            account = acct
            print(f'Using account: {acct_id} ({acct.get("name", "?")})')
            break

    if not account:
        print('ERROR: No account with valid cookie')
        return 2

    cookie_str_raw = account['cookie']
    ua = account.get('user_agent',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

    # --- Get top notes ---
    notes = get_top_notes_for_comments(top_n)
    if not notes:
        print('No notes with xsec_token found')
        return 3

    print(f'Top {len(notes)} notes to collect comments from:')
    for i, n in enumerate(notes):
        print(f'  {i+1}. [{n["score"]:>8}] {n["title"][:40]} (评论数: {n["comment_count"]})')
    print()

    # --- Browser setup ---
    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str_raw)

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(
        user_agent=ua,
        viewport={'width': 1440, 'height': 900},
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
    )

    for k, v in cookie_dict.items():
        await ctx.add_cookies([{
            'name': k, 'value': v,
            'domain': '.xiaohongshu.com', 'path': '/'}])

    await ctx.add_init_script(path='/opt/mediacrawler/libs/stealth.min.js')
    page = await ctx.new_page()
    await page.goto('https://www.xiaohongshu.com',
                    wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(5)

    all_cookies = await ctx.cookies()
    cookie_str = '; '.join(f'{c["name"]}={c["value"]}' for c in all_cookies)
    a1 = cookie_dict.get('a1', '')

    # --- Collect comments ---
    total_saved = 0
    total_notes_done = 0
    rate_limited = False

    for i, note in enumerate(notes):
        if rate_limited:
            break

        note_id = note['note_id']
        xsec_token = note['xsec_token']
        print(f'[{i+1}/{len(notes)}] {note["title"][:40]}')

        existing_ids = get_existing_comment_ids(note_id)
        if existing_ids:
            print(f'  Already have {len(existing_ids)} comments, fetching new ones')

        cursor = ''
        note_comments = []
        page_num = 0

        while len(note_comments) < max_comments:
            page_num += 1
            comments, cursor, has_more = await fetch_comments_page(
                page, cookie_str, a1, ua, note_id, xsec_token, cursor)

            if comments is None:
                rate_limited = True
                break

            if not comments:
                break

            note_comments.extend(comments)
            print(f'  Page {page_num}: {len(comments)} comments')

            if not has_more or not cursor:
                break

            # Delay between pages
            await asyncio.sleep(random.uniform(3, 8))

        if note_comments:
            saved = save_comments(note_id, note_comments)
            total_saved += saved
            print(f'  Total: {len(note_comments)} fetched, {saved} new saved')
            total_notes_done += 1
        elif not rate_limited:
            print(f'  No comments found')
            total_notes_done += 1

        # Delay between notes
        if i < len(notes) - 1 and not rate_limited:
            delay = random.uniform(10, 25)
            print(f'  Waiting {delay:.0f}s...')
            await asyncio.sleep(delay)

    await browser.close()
    await p.stop()

    # --- Summary ---
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM xhs_note_comment')
    total_comments = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT note_id) FROM xhs_note_comment')
    notes_with_comments = cur.fetchone()[0]
    conn.close()

    print(f'\n=== Comment Collection Summary ===')
    print(f'Notes processed: {total_notes_done}/{len(notes)}')
    print(f'New comments saved: {total_saved}')
    print(f'DB total: {total_comments} comments across {notes_with_comments} notes')
    if rate_limited:
        print(f'WARNING: Stopped early due to rate limiting')

    return 0 if total_saved > 0 else 3


def main():
    parser = argparse.ArgumentParser(description='XHS comment collection')
    parser.add_argument('--account', default='MAIN', help='Account ID')
    parser.add_argument('--top-n', type=int, default=10, help='Number of top notes to collect comments from')
    parser.add_argument('--max-comments', type=int, default=20, help='Max comments per note')
    args = parser.parse_args()

    return asyncio.run(collect(args.account, args.top_n, args.max_comments))


if __name__ == '__main__':
    exit(main() or 0)
