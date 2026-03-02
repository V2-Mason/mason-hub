"""
_xhs_enrich_creators.py — Top 帖子作者粉丝量富化

用法: python _xhs_enrich_creators.py <analysis.json> [--top-n 20]

流程:
1. 读分析 JSON，提取 top_posts 去重 user_id
2. 调 XHS profile API 获取粉丝数
3. 存入 xhs_creator 表
4. 输出 enriched JSON（每个 top_post 加 follower_count + account_size）

非阻塞设计：API 失败 → 跳过，输出 base JSON 不受影响
退出码: 0=有富化数据, 1=运行错误, 2=Cookie 过期, 3=全部跳过（无富化数据但非错误）
"""
import argparse
import asyncio
import json
import os
import random
import sqlite3
import time

ACCOUNTS_FILE = '/opt/mediacrawler/accounts.json'
DB_PATH = '/opt/mediacrawler/database/sqlite_tables.db'


def classify_account(fans: int) -> str:
    if fans >= 100000:
        return '大号'
    elif fans >= 10000:
        return '中号'
    else:
        return '小号'


def parse_fans_count(s) -> int:
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


def save_creator(user_id: str, nickname: str, fans: int, data: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_ts = int(time.time() * 1000)

    cur.execute('SELECT id FROM xhs_creator WHERE user_id = ?', (user_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute('''
            UPDATE xhs_creator SET nickname = ?, fans = ?, last_modify_ts = ?,
                   follows = ?, interaction = ?, "desc" = ?, gender = ?
            WHERE user_id = ?
        ''', (
            nickname, str(fans), now_ts,
            str(data.get('follows', 0)),
            str(data.get('interaction', 0)),
            data.get('desc', ''),
            data.get('gender', ''),
            user_id,
        ))
    else:
        cur.execute('''
            INSERT INTO xhs_creator (user_id, nickname, fans, follows, interaction,
                                     "desc", gender, add_ts, last_modify_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, nickname, str(fans),
            str(data.get('follows', 0)),
            str(data.get('interaction', 0)),
            data.get('desc', ''),
            data.get('gender', ''),
            now_ts, now_ts,
        ))

    conn.commit()
    conn.close()


def load_cached_creators(user_ids: list) -> dict:
    """Load already-known creators from DB to avoid redundant API calls."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    placeholders = ','.join('?' * len(user_ids))
    cur.execute(f'''
        SELECT user_id, fans, nickname FROM xhs_creator
        WHERE user_id IN ({placeholders})
          AND last_modify_ts > ?
    ''', user_ids + [int((time.time() - 7 * 86400) * 1000)])  # cache 7 days
    rows = cur.fetchall()
    conn.close()
    return {r[0]: {'fans': parse_fans_count(r[1]), 'nickname': r[2]} for r in rows}


async def fetch_creator_profile(page, cookie_str, a1, ua, user_id: str) -> dict:
    """Call XHS profile API for a single user. Returns {'fans': int, ...} or None."""
    from media_platform.xhs.playwright_sign import sign_with_playwright
    import httpx

    uri = f'/api/sns/web/v1/user/otherinfo?target_user_id={user_id}'
    signs = await sign_with_playwright(page, uri, None, a1, 'GET')

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
        resp = await client.get(f'https://edith.xiaohongshu.com{uri}', headers=headers, timeout=15)

    if resp.status_code == 461:
        print(f'    RATE LIMITED (461) for {user_id}')
        return None

    if resp.status_code != 200:
        print(f'    HTTP {resp.status_code} for {user_id}')
        return None

    data = resp.json()
    if not data.get('success'):
        print(f'    API error: {data.get("msg", "unknown")} for {user_id}')
        return None

    info = data.get('data', {}).get('basic_info', {})
    return {
        'fans': parse_fans_count(info.get('fans', '0')),
        'follows': parse_fans_count(info.get('follows', '0')),
        'interaction': parse_fans_count(info.get('interaction', '0')),
        'desc': info.get('desc', ''),
        'gender': str(info.get('gender', '')),
        'nickname': info.get('nickname', ''),
    }


async def enrich(analysis_path: str, top_n: int):
    from playwright.async_api import async_playwright
    from tools import utils

    # Load analysis JSON
    with open(analysis_path, encoding='utf-8') as f:
        report = json.load(f)

    top_posts = report.get('top_posts', [])
    if not top_posts:
        print('No top_posts in analysis JSON')
        return 3

    # Deduplicate user_ids
    seen = set()
    user_ids = []
    for p in top_posts[:top_n]:
        uid = p.get('user_id', '')
        if uid and uid not in seen:
            seen.add(uid)
            user_ids.append(uid)

    if not user_ids:
        print('No user_ids found in top_posts (run analysis with user_id first)')
        return 3

    print(f'Unique creators to enrich: {len(user_ids)}')

    # Check cache first
    cached = load_cached_creators(user_ids)
    to_fetch = [uid for uid in user_ids if uid not in cached]
    print(f'Cached: {len(cached)}, need API: {len(to_fetch)}')

    creator_data = {}
    for uid, info in cached.items():
        creator_data[uid] = info

    if to_fetch:
        # Load account config
        if not os.path.exists(ACCOUNTS_FILE):
            print(f'WARNING: {ACCOUNTS_FILE} not found, skipping API enrichment')
            to_fetch = []
        else:
            with open(ACCOUNTS_FILE) as f:
                accounts = json.load(f)

            # Use account A by default
            account = accounts.get('A', {})
            cookie_str_raw = account.get('cookie', '')
            if not cookie_str_raw:
                print('WARNING: No cookie for account A, skipping API enrichment')
                to_fetch = []

    if to_fetch:
        ua = account.get('user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
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
            await ctx.add_cookies([{'name': k, 'value': v, 'domain': '.xiaohongshu.com', 'path': '/'}])

        await ctx.add_init_script(path='/opt/mediacrawler/libs/stealth.min.js')
        page = await ctx.new_page()
        await page.goto('https://www.xiaohongshu.com')
        await asyncio.sleep(3)

        all_cookies = await ctx.cookies()
        cookie_str = '; '.join(f'{c["name"]}={c["value"]}' for c in all_cookies)
        a1 = cookie_dict.get('a1', '')

        rate_limited = False
        for i, uid in enumerate(to_fetch):
            if rate_limited:
                break

            print(f'  [{i+1}/{len(to_fetch)}] Fetching profile: {uid}')
            profile = await fetch_creator_profile(page, cookie_str, a1, ua, uid)

            if profile is None:
                print(f'    Skipped (API error)')
                rate_limited = True  # stop on first failure to be safe
                continue

            fans = profile['fans']
            nickname = profile.get('nickname', '')
            print(f'    {nickname}: {fans:,} fans ({classify_account(fans)})')

            creator_data[uid] = {'fans': fans, 'nickname': nickname}
            save_creator(uid, nickname, fans, profile)

            # Random delay 15-30s between calls
            if i < len(to_fetch) - 1:
                delay = random.uniform(15, 30)
                print(f'    Waiting {delay:.0f}s...')
                await asyncio.sleep(delay)

        await browser.close()
        await p.stop()

    # Build enriched output
    enriched_posts = []
    for p in top_posts:
        ep = dict(p)
        uid = p.get('user_id', '')
        if uid in creator_data:
            fans = creator_data[uid]['fans']
            ep['follower_count'] = fans
            ep['account_size'] = classify_account(fans)
        enriched_posts.append(ep)

    # Small account signals: small accounts with high engagement
    small_signals = [
        p for p in enriched_posts
        if p.get('account_size') == '小号'
        and p.get('score', 0) > 0
        and not p.get('fake_flags')
    ]
    small_signals.sort(key=lambda x: x['score'], reverse=True)

    enriched_report = dict(report)
    enriched_report['top_posts'] = enriched_posts
    enriched_report['enrichment'] = {
        'creators_enriched': len(creator_data),
        'creators_from_cache': len(cached),
        'creators_from_api': len(creator_data) - len(cached),
        'rate_limited': rate_limited if to_fetch else False,
    }
    if small_signals:
        enriched_report['small_account_signals'] = [{
            'title': p['title'],
            'score': p['score'],
            'nickname': p.get('nickname', ''),
            'follower_count': p.get('follower_count', 0),
            'account_size': p.get('account_size', ''),
            'url': p.get('url', ''),
            'pub_date': p.get('pub_date', ''),
            'type': p.get('type', ''),
            'liked': p.get('liked', 0),
            'collected': p.get('collected', 0),
            'save_rate': p.get('save_rate', 0),
        } for p in small_signals[:10]]

    # Output enriched JSON
    out_path = analysis_path.replace('.json', '_enriched.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_report, f, ensure_ascii=False, indent=2)

    enriched_count = sum(1 for p in enriched_posts if 'follower_count' in p)
    print(f'\nEnriched {enriched_count}/{len(enriched_posts)} posts')
    print(f'Small account signals: {len(small_signals)}')
    print(f'Output: {out_path}')

    return 0 if enriched_count > 0 else 3


def main():
    parser = argparse.ArgumentParser(description='XHS creator enrichment')
    parser.add_argument('analysis_json', help='Path to analysis JSON')
    parser.add_argument('--top-n', type=int, default=20, help='Max posts to enrich')
    args = parser.parse_args()

    if not os.path.exists(args.analysis_json):
        print(f'ERROR: {args.analysis_json} not found')
        return 1

    return asyncio.run(enrich(args.analysis_json, args.top_n))


if __name__ == '__main__':
    exit(main() or 0)
