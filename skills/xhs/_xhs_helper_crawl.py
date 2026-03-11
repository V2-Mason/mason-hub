"""Crawl XHS helper/list pages (商家帮助中心/招商入驻).

Usage: python3 skills/xhs/_xhs_helper_crawl.py [url]
Default URL: https://school.xiaohongshu.com/helper/list?ctg=438&jumpFrom=zhaoshang
"""
import asyncio
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path("intel/raw/xhs-helper-docs")
ET = timezone(timedelta(hours=-4))  # Mason 标准时区：美东


def sanitize_filename(title):
    title = re.sub(r'[/\\:*?"<>|]', "", title)
    return title.strip()[:80] or "untitled"


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://school.xiaohongshu.com/helper/list?ctg=438&jumpFrom=zhaoshang"
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Target: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # Capture API responses
        api_responses = []

        async def on_response(response):
            if response.status != 200:
                return
            try:
                resp_url = response.url
                # Capture any helper/article related API calls
                if any(kw in resp_url for kw in [
                    "query_article", "helper", "category", "article_detail",
                    "article_list", "query_helper",
                ]):
                    data = await response.json()
                    api_responses.append({
                        "url": resp_url,
                        "data": data,
                    })
                    print(f"  [API] {resp_url[:100]}")
            except Exception:
                pass

        page.on("response", on_response)

        # Navigate to list page
        print("Loading list page...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Extract article links from the page
        links = await page.evaluate("""() => {
            const results = [];
            // Look for links that point to helper detail pages
            const allLinks = document.querySelectorAll('a[href*="helper"], a[href*="detail"], a[href*="article"]');
            for (const a of allLinks) {
                const href = a.href || '';
                const text = (a.innerText || '').trim();
                if (text && text.length > 3 && text.length < 200) {
                    results.push({href, text});
                }
            }
            // Also look for clickable list items
            const items = document.querySelectorAll('[class*="list"] [class*="item"], [class*="article"] [class*="item"], [class*="helper"] [class*="item"]');
            for (const el of items) {
                const text = (el.innerText || '').trim();
                const a = el.querySelector('a');
                const href = a ? a.href : '';
                if (text && text.length > 3) {
                    results.push({href, text});
                }
            }
            return results;
        }""")

        print(f"Found {len(links)} links on list page")
        for lnk in links:
            print(f"  - {lnk['text'][:60]}  →  {lnk['href'][:80]}")

        # Also grab full page text as fallback
        page_text = await page.evaluate("""() => {
            // Get all visible text
            const content = document.body.innerText || '';
            return content;
        }""")

        # Try scrolling to load more content
        print("Scrolling to load more...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1)

        # Re-extract after scroll
        links2 = await page.evaluate("""() => {
            const results = [];
            const allLinks = document.querySelectorAll('a');
            for (const a of allLinks) {
                const href = a.href || '';
                const text = (a.innerText || '').trim();
                if (text && text.length > 5 && text.length < 200 && href.includes('helper')) {
                    results.push({href, text});
                }
            }
            return results;
        }""")
        if len(links2) > len(links):
            links = links2
            print(f"After scroll: {len(links)} links")

        # Visit each article detail page
        results = []
        seen_urls = set()

        for i, lnk in enumerate(links):
            href = lnk["href"]
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            print(f"\n[{i+1}/{len(links)}] {lnk['text'][:60]}")
            print(f"  URL: {href}")

            try:
                await page.goto(href, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(4)

                # Extract content from detail page
                detail = await page.evaluate("""() => {
                    let title = '';
                    // Try multiple title selectors
                    for (const sel of ['h1', 'h2', '[class*="title"]', '[class*="header"] [class*="text"]']) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const t = (el.innerText || '').trim();
                            if (t.length > 3 && t.length < 200) {
                                title = t;
                                break;
                            }
                        }
                    }

                    let content = '';
                    // Try content selectors
                    for (const sel of [
                        '[class*="detail-content"]', '[class*="article-content"]',
                        '[class*="rich-text"]', '[class*="content-wrap"]',
                        '[class*="helper-detail"]', '[class*="content"]',
                        'article', 'main',
                    ]) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const text = (el.innerText || '').trim();
                            if (text.length > content.length && text.length > 50) {
                                content = text;
                            }
                        }
                    }

                    if (content.length < 100) {
                        content = (document.body.innerText || '').trim();
                    }

                    return {title, content, url: window.location.href};
                }""")

                if detail["content"] and len(detail["content"]) > 50:
                    results.append({
                        "title": detail["title"] or lnk["text"],
                        "content": detail["content"],
                        "url": detail["url"],
                        "source_text": lnk["text"],
                    })
                    print(f"  ✓ {len(detail['content'])} chars")
                else:
                    print(f"  ✗ Too short ({len(detail.get('content', ''))} chars)")

            except Exception as e:
                print(f"  Error: {e}")

            await asyncio.sleep(1.5)

        await browser.close()

    # Save results
    print(f"\n=== Results: {len(results)} articles ===")

    # Save raw API captures
    if api_responses:
        api_file = BASE_DIR / "_api_captures.json"
        api_file.write_text(json.dumps(api_responses, ensure_ascii=False, indent=2))
        print(f"API captures: {api_file}")

    # Save page text (list page)
    if page_text:
        list_file = BASE_DIR / "_list_page_text.txt"
        list_file.write_text(page_text)
        print(f"List page text: {list_file}")

    # Save individual articles
    for res in results:
        safe_title = sanitize_filename(res["title"])
        out_path = BASE_DIR / f"{safe_title}.md"
        now = datetime.now(ET).isoformat()

        md = f"""---
title: "{res['title']}"
url: "{res['url']}"
crawl_date: "{now}"
source: "dom"
---

{res['content']}
"""
        out_path.write_text(md, encoding="utf-8")
        print(f"  Saved: {out_path}")

    # Save index
    index = {
        "url": url,
        "crawl_date": datetime.now(ET).isoformat(),
        "articles": [
            {"title": r["title"], "url": r["url"], "size": len(r["content"])}
            for r in results
        ],
        "api_captures": len(api_responses),
    }
    (BASE_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))

    if not results and not api_responses:
        print("\n⚠ No content found. The page might need login or different approach.")
        print(f"List page text preview:\n{page_text[:500]}")


if __name__ == "__main__":
    asyncio.run(main())
