"""
微信小店文档爬虫 — 基于 Playwright 发现的 URL 批量抓取

用法:
  python skills/_wechat_store_docs_crawl.py [--source all|dev|growth] [--limit N]

两个源:
  1. dev: developers.weixin.qq.com/doc/store/ — API 文档 (534 URLs)
  2. growth: store.weixin.qq.com/chengzhang/ — 成长中心 (41 URLs)

前置: 先运行 _wechat_discover_urls.py 生成 discovered_urls.json

输出: intel/raw/wechat-store-docs/
"""

import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path("intel/raw/wechat-store-docs")
INDEX_FILE = BASE_DIR / "index.json"
HASH_FILE = BASE_DIR / ".content_hashes.json"
URLS_FILE = BASE_DIR / "discovered_urls.json"
ET = timezone(timedelta(hours=-4))  # Mason 标准时区：美东

_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-first-run",
    "--no-default-browser-check",
]

# Category mapping from URL path segments
DEV_CATEGORY_MAP = {
    "API": {
        "channels-shop-product": "商品管理",
        "channels-shop-order": "订单管理",
        "channels-shop-aftersale": "售后管理",
        "channels-shop-delivery": "物流管理",
        "funds": "资金管理",
        "coupon": "营销",
        "brand": "品牌资质",
        "storemanage": "店铺管理",
        "homepage": "主页管理",
        "league": "优选联盟",
        "member": "会员管理",
        "compass": "数据分析",
        "warehouse": "区域仓",
        "dropship": "代发管理",
        "complain": "投诉管理",
        "quality-inspection": "品质检测",
    },
    "notify": "回调通知",
    "product": "功能介绍",
    "dev_before": "开发前必读",
    "linkstore": "店铺接入",
    "Example_description_of_Qualification_license": "资质说明",
}


def sanitize_filename(title: str) -> str:
    title = re.sub(r'[/\\:*?"<>|]', '', title)
    return title.strip()[:80] or "untitled"


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def classify_dev_url(url: str) -> tuple:
    """Return (doc_type, category, subcategory) from URL path."""
    path = url.replace("https://developers.weixin.qq.com/doc/store/shop/", "")
    parts = path.strip("/").split("/")

    if not parts:
        return "开发者文档", "通用", ""

    section = parts[0]

    if section == "API" and len(parts) > 1:
        api_cat = parts[1]
        sub = DEV_CATEGORY_MAP.get("API", {}).get(api_cat, api_cat)
        return "API文档", sub, "/".join(parts[2:])
    elif section in DEV_CATEGORY_MAP:
        cat = DEV_CATEGORY_MAP[section]
        if isinstance(cat, dict):
            return "开发者文档", section, ""
        return "开发者文档", cat, "/".join(parts[1:])
    else:
        return "开发者文档", "通用", path


async def crawl_with_playwright(links: list, out_base: str, source_label: str, limit: int = 0):
    """Generic Playwright crawl for a list of {url, title} dicts."""
    index = load_json(INDEX_FILE)
    if "pages" not in index:
        index["pages"] = []
    hashes = load_json(HASH_FILE)
    stats = {"ok": 0, "empty": 0, "error": 0, "skipped": 0}

    if limit > 0:
        links = links[:limit]

    print(f"Crawling {len(links)} URLs from {source_label}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=_STEALTH_ARGS)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        for i, link in enumerate(links):
            url = link["url"]
            title = link.get("title", "untitled").strip()

            # Skip external/invalid URLs
            if not url.startswith("http"):
                continue

            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=15000)
                if resp and resp.status == 404:
                    continue

                await asyncio.sleep(1.5)

                # Extract content with multiple selectors
                body = ""
                for selector in [
                    ".content-doc",        # WeChat dev docs
                    ".markdown-section",   # Alternative
                    ".doc-content",
                    "article",
                    ".wiki-content",       # Growth center
                    ".content-area",
                    "main .content",
                    "main",
                ]:
                    try:
                        el = await page.query_selector(selector)
                        if el:
                            body = await el.inner_text()
                            if len(body) > 50:
                                break
                    except Exception:
                        continue

                # Fallback: get page title if we don't have one
                if not title or title == "untitled":
                    try:
                        h1 = await page.query_selector("h1")
                        if h1:
                            title = (await h1.inner_text()).strip()
                    except Exception:
                        pass
                    if not title:
                        title = await page.title()

                if len(body) < 30:
                    stats["empty"] += 1
                    if (i + 1) % 50 == 0:
                        print(f"  [{i+1}/{len(links)}] ... ({stats['ok']} ok, {stats['empty']} empty)")
                    continue

                # Hash check
                h = content_hash(body)
                hash_key = url
                if hashes.get(hash_key) == h:
                    stats["skipped"] += 1
                    continue

                hashes[hash_key] = h
                stats["ok"] += 1

                # Determine output path
                if "developers.weixin.qq.com" in url:
                    doc_type, category, sub = classify_dev_url(url)
                    out_dir = BASE_DIR / "开发者文档" / doc_type / category
                else:
                    doc_type = "成长中心"
                    category = "通用"
                    out_dir = BASE_DIR / "成长中心"

                out_dir.mkdir(parents=True, exist_ok=True)
                safe_title = sanitize_filename(title)
                file_path = out_dir / f"{safe_title}.md"

                now = datetime.now(ET).isoformat()
                md = f"""---
title: "{title}"
source_url: "{url}"
category: "{category}"
doc_type: "{doc_type}"
platform: "wechat-store"
crawl_date: "{now}"
---

{body}
"""
                file_path.write_text(md, encoding="utf-8")

                index["pages"].append({
                    "status": "ok",
                    "title": title,
                    "source_url": url,
                    "category": category,
                    "doc_type": doc_type,
                    "path": str(file_path),
                    "size": len(body),
                    "crawl_date": now,
                })

                if (i + 1) % 20 == 0:
                    print(f"  [{i+1}/{len(links)}] {stats['ok']} ok, {stats['empty']} empty, {stats['error']} err")

            except Exception as e:
                stats["error"] += 1
                if "Timeout" not in str(e):
                    print(f"  ERROR [{title[:30]}]: {e}")

            # Polite delay
            await asyncio.sleep(1.0)

        await browser.close()

    # Save
    now = datetime.now(ET).isoformat()
    index[f"crawl_end_{source_label}"] = now
    index["stats"] = {
        "ok": len([p for p in index["pages"] if p.get("status") == "ok"]),
    }
    save_json(INDEX_FILE, index)
    save_json(HASH_FILE, hashes)

    print(f"\n=== {source_label} Crawl Complete ===")
    print(f"OK: {stats['ok']}, Empty: {stats['empty']}, Error: {stats['error']}, Skipped: {stats['skipped']}")
    return stats


async def run(source: str = "all", limit: int = 0):
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Load discovered URLs
    if not URLS_FILE.exists():
        print(f"ERROR: {URLS_FILE} not found. Run _wechat_discover_urls.py first.")
        return

    urls = json.loads(URLS_FILE.read_text())

    # Initialize index
    if not INDEX_FILE.exists():
        save_json(INDEX_FILE, {
            "platform": "微信小店",
            "crawl_start": datetime.now(ET).isoformat(),
            "pages": [],
        })

    print(f"=== 微信小店文档爬虫 ===")
    print(f"Source: {source}, Limit: {limit or 'unlimited'}")
    print(f"Output: {BASE_DIR}/\n")

    if source in ("all", "dev"):
        dev_links = urls.get("dev_docs", {}).get("links", [])
        print(f"--- 开发者文档 ({len(dev_links)} URLs) ---")
        await crawl_with_playwright(dev_links, "开发者文档", "dev", limit=limit)

    if source in ("all", "growth"):
        growth_links = urls.get("growth_center", {}).get("links", [])
        print(f"\n--- 成长中心 ({len(growth_links)} URLs) ---")
        await crawl_with_playwright(growth_links, "成长中心", "growth", limit=limit)

    # Final stats
    index = load_json(INDEX_FILE)
    total = len(index.get("pages", []))
    print(f"\n=== 完成 ===")
    print(f"Total docs: {total}")


def main():
    parser = argparse.ArgumentParser(description="微信小店文档爬虫")
    parser.add_argument("--source", default="all", choices=["all", "dev", "growth"])
    parser.add_argument("--limit", type=int, default=0, help="每个源最多抓取N个URL（0=不限）")
    args = parser.parse_args()

    asyncio.run(run(source=args.source, limit=args.limit))


if __name__ == "__main__":
    main()
