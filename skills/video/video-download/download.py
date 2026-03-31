"""通过 greenvideo.cc 下载社交媒体视频（无水印）

用法：
  python download.py <url> [--platform xhs|douyin|ins|tiktok] [--output-dir ./]

流程：
  1. Playwright 打开 greenvideo.cc，粘贴链接，点"开始"
  2. 拦截 cnSimpleExtract API 响应，提取 CDN 视频链接
  3. 直接 requests 下载视频（不需要操作页面下载按钮）
"""
import argparse
import json
import os
import re
import sys
import time
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


PLATFORM_PAGES = {
    'xhs': 'https://greenvideo.cc/xiaohongshu',
    'douyin': 'https://greenvideo.cc/douyin',
    'ins': 'https://greenvideo.cc/ins',
    'tiktok': 'https://greenvideo.cc/tiktok',
    'bilibili': 'https://greenvideo.cc/bilibili',
    'youtube': 'https://greenvideo.cc/youtube',
    'weibo': 'https://greenvideo.cc/weibo',
}


def detect_platform(url):
    """从 URL 自动检测平台"""
    domain = urlparse(url).netloc.lower()
    if 'xiaohongshu' in domain or 'xhslink' in domain:
        return 'xhs'
    if 'douyin' in domain:
        return 'douyin'
    if 'instagram' in domain:
        return 'ins'
    if 'tiktok' in domain:
        return 'tiktok'
    if 'bilibili' in domain or 'b23.tv' in domain:
        return 'bilibili'
    if 'youtube' in domain or 'youtu.be' in domain:
        return 'youtube'
    if 'weibo' in domain:
        return 'weibo'
    return None


def extract_video_info(source_url, platform):
    """用 Playwright 触发 greenvideo.cc 解析，拦截 API 响应拿视频 URL"""
    site_url = PLATFORM_PAGES.get(platform)
    if not site_url:
        raise ValueError(f"Unknown platform: {platform}")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def capture_response(response):
            if '/api/video/cnSimpleExtract' in response.url:
                try:
                    data = response.json()
                    if data.get('code') == 200:
                        results.append(data)
                except Exception:
                    pass

        page.on('response', capture_response)

        page.goto(site_url, wait_until='networkidle', timeout=30000)
        time.sleep(2)

        # Clean URL (strip tracking params)
        clean_url = source_url.split('?')[0]
        page.fill('input[type=text]', clean_url)
        time.sleep(0.5)

        # Click "开始"
        page.click('button:has-text("开始")')
        time.sleep(8)

        # Try clicking "下载" if it appeared
        dl_btn = page.query_selector('button.n-button--primary-type:has-text("下载")')
        if dl_btn and dl_btn.is_visible():
            dl_btn.click()
            time.sleep(8)

        browser.close()

    if not results:
        raise RuntimeError("No successful API response captured")

    resp = results[-1]
    if resp.get('code') != 200:
        raise RuntimeError(f"API error: {resp.get('message', 'unknown')}")

    info = resp['data']
    title = info.get('displayTitle', '')

    video_url = None
    cover_url = None
    best_quality = 0
    for item in info.get('videoItemVoList', []):
        if item.get('fileType') == 'video' and item.get('canDownload'):
            url = item.get('baseUrl', '')
            if url.startswith('http'):
                # 选最高分辨率：优先用 quality/height/width 字段判断
                raw_q = item.get('quality', 0) or item.get('height', 0) or item.get('width', 0)
                try:
                    q = int(raw_q) if raw_q else 0
                except (ValueError, TypeError):
                    q = 0
                # 如果没有 quality 字段，用 URL 中的线索或文件大小
                if not q:
                    desc = item.get('qualityDesc', '') or item.get('desc', '')
                    if '1080' in desc or '1080' in url:
                        q = 1080
                    elif '720' in desc or '720' in url:
                        q = 720
                    elif '480' in desc or '480' in url:
                        q = 480
                    else:
                        q = 1  # unknown, lowest priority
                if q > best_quality:
                    best_quality = q
                    video_url = url
        elif item.get('fileType') == 'image':
            cover_url = item.get('baseUrl', '')

    if not video_url:
        raise RuntimeError("No downloadable video found in API response")

    return video_url, title, cover_url


def download_file(url, output_path):
    """下载文件到本地"""
    print(f"Downloading to {output_path} ...")
    resp = requests.get(url, stream=True, timeout=120, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    resp.raise_for_status()

    total = int(resp.headers.get('content-length', 0))
    downloaded = 0
    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded * 100 // total
                print(f"\r  {downloaded // 1024}KB / {total // 1024}KB ({pct}%)", end='', flush=True)

    print(f"\nDone: {os.path.getsize(output_path) // 1024}KB")
    return output_path


def make_filename(source_url, platform, title=''):
    """生成文件名: YYYY-MM-DD_{title_short}_{id}.mp4"""
    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')

    path = urlparse(source_url).path
    note_id = path.rstrip('/').split('/')[-1]
    note_id = re.sub(r'[^a-zA-Z0-9]', '', note_id)[:16]

    title_short = re.sub(r'[^\w\u4e00-\u9fff]', '', title)[:20] if title else platform

    return f"{date_str}_{title_short}_{note_id}.mp4"


def main():
    parser = argparse.ArgumentParser(description='Download social media videos via greenvideo.cc')
    parser.add_argument('url', help='Source video URL')
    parser.add_argument('--platform', choices=['xhs', 'douyin', 'ins', 'tiktok', 'bilibili', 'youtube', 'weibo'],
                        help='Platform (auto-detected if not specified)')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--output', help='Output filename')
    args = parser.parse_args()

    platform = args.platform or detect_platform(args.url)
    if not platform:
        print("ERROR: Cannot detect platform. Use --platform.", file=sys.stderr)
        return 1

    print(f"Platform: {platform}")
    print(f"Source: {args.url}")

    video_url, title, cover_url = extract_video_info(args.url, platform)
    print(f"Title: {title}")
    print(f"Video CDN: {video_url[:80]}...")

    os.makedirs(args.output_dir, exist_ok=True)
    filename = args.output or make_filename(args.url, platform, title)
    output_path = os.path.join(args.output_dir, filename)
    download_file(video_url, output_path)

    # Metadata
    meta = {
        'source_url': args.url,
        'platform': platform,
        'title': title,
        'video_url': video_url,
        'cover_url': cover_url,
        'local_path': os.path.abspath(output_path),
        'filename': filename,
        'file_size': os.path.getsize(output_path),
    }
    meta_path = output_path.replace('.mp4', '_meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Metadata: {meta_path}")

    return 0


if __name__ == '__main__':
    exit(main())
