"""通过 greenvideo.cc 下载社交媒体视频（无水印）

用法：
  python download.py <url> [--platform xhs|douyin|ins|tiktok] [--output-dir ./]

流程：
  1. 打开 greenvideo.cc/{platform} 页面
  2. 粘贴链接，点击"开始"
  3. 等待解析完成，提取下载链接
  4. 下载视频到本地
"""
import argparse
import os
import re
import sys
import time
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


PLATFORM_URLS = {
    'xhs': 'https://greenvideo.cc/xiaohongshu',
    'douyin': 'https://greenvideo.cc/douyin',
    'ins': 'https://greenvideo.cc/ins',
    'tiktok': 'https://greenvideo.cc/tiktok',
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
    return None


def extract_download_url(page, source_url, platform):
    """在 greenvideo.cc 解析视频并提取下载链接"""
    site_url = PLATFORM_URLS.get(platform)
    if not site_url:
        raise ValueError(f"Unknown platform: {platform}")

    print(f"Opening {site_url} ...")
    page.goto(site_url, wait_until='networkidle', timeout=30000)
    time.sleep(2)

    # Find input field and paste URL
    input_sel = 'input[type="text"], input[type="url"], input[type="search"], textarea'
    page.wait_for_selector(input_sel, timeout=10000)
    input_el = page.query_selector(input_sel)
    input_el.fill(source_url)
    time.sleep(0.5)

    # Click start/parse button
    # Try common button patterns
    btn = (page.query_selector('button:has-text("开始")') or
           page.query_selector('button:has-text("解析")') or
           page.query_selector('button:has-text("Start")') or
           page.query_selector('button:has-text("Download")') or
           page.query_selector('button[type="submit"]'))

    if not btn:
        raise RuntimeError("Cannot find parse/start button")

    btn.click()
    print("Parsing...")

    # Wait for download link to appear (poll for up to 30s)
    download_url = None
    for _ in range(30):
        time.sleep(1)
        # Look for download links/buttons that appeared after parsing
        links = page.query_selector_all('a[href*=".mp4"], a[download], a:has-text("下载"), a:has-text("Download")')
        for link in links:
            href = link.get_attribute('href')
            if href and ('mp4' in href or 'video' in href):
                download_url = href
                break
        if download_url:
            break

        # Also check for video elements that loaded
        videos = page.query_selector_all('video source[src]')
        for v in videos:
            src = v.get_attribute('src')
            if src:
                download_url = src
                break
        if download_url:
            break

    if not download_url:
        # Try intercepting network requests as fallback
        raise RuntimeError("Could not find download URL after 30s")

    # Handle relative URLs
    if download_url.startswith('//'):
        download_url = 'https:' + download_url
    elif download_url.startswith('/'):
        download_url = 'https://greenvideo.cc' + download_url

    return download_url


def download_file(url, output_path):
    """下载文件到本地"""
    print(f"Downloading to {output_path} ...")
    resp = requests.get(url, stream=True, timeout=120, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://greenvideo.cc/',
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


def make_filename(source_url, platform):
    """生成文件名: YYYY-MM-DD_{platform}_{id}.mp4"""
    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Extract ID from URL
    path = urlparse(source_url).path
    note_id = path.rstrip('/').split('/')[-1]
    # Clean non-alphanumeric
    note_id = re.sub(r'[^a-zA-Z0-9]', '', note_id)[:20]

    return f"{date_str}_{platform}_{note_id}.mp4"


def main():
    parser = argparse.ArgumentParser(description='Download social media videos via greenvideo.cc')
    parser.add_argument('url', help='Source video URL (XHS, Douyin, INS, TikTok)')
    parser.add_argument('--platform', choices=['xhs', 'douyin', 'ins', 'tiktok'],
                        help='Platform (auto-detected from URL if not specified)')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--output', help='Output filename (auto-generated if not specified)')
    args = parser.parse_args()

    platform = args.platform or detect_platform(args.url)
    if not platform:
        print(f"ERROR: Cannot detect platform from URL. Use --platform.", file=sys.stderr)
        return 1

    print(f"Platform: {platform}")
    print(f"Source: {args.url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            download_url = extract_download_url(page, args.url, platform)
            print(f"Download URL: {download_url[:80]}...")
        finally:
            browser.close()

    # Download
    os.makedirs(args.output_dir, exist_ok=True)
    filename = args.output or make_filename(args.url, platform)
    output_path = os.path.join(args.output_dir, filename)
    download_file(download_url, output_path)

    # Output metadata as JSON for pipeline consumption
    import json
    meta = {
        'source_url': args.url,
        'platform': platform,
        'local_path': os.path.abspath(output_path),
        'filename': filename,
        'file_size': os.path.getsize(output_path),
    }
    meta_path = output_path.replace('.mp4', '_meta.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Metadata: {meta_path}")

    return 0


if __name__ == '__main__':
    exit(main())
