"""
微信小店文档 URL 发现器 — 用 Playwright 抓取导航栏的所有文档链接

用法: python skills/docs-crawl/_wechat_discover_urls.py

输出: intel/raw/wechat-store-docs/discovered_urls.json
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

ET = timezone(timedelta(hours=-4))  # Mason 标准时区：美东
BASE_DIR = Path("intel/raw/wechat-store-docs")

_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-first-run",
    "--no-default-browser-check",
]


async def discover_dev_docs():
    """Visit dev docs and extract all sidebar navigation links."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)

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

        # Start from the main store docs page
        start_urls = [
            "https://developers.weixin.qq.com/doc/store/shop/",
            "https://developers.weixin.qq.com/doc/store/shop/API/channels-shop-product/",
            "https://developers.weixin.qq.com/doc/store/shop/API/channels-shop-order/",
            "https://developers.weixin.qq.com/doc/store/shop/API/channels-shop-aftersale/",
            "https://developers.weixin.qq.com/doc/store/shop/API/channels-shop-delivery/",
            "https://developers.weixin.qq.com/doc/store/summary.html",
        ]

        all_links = {}

        for start_url in start_urls:
            print(f"\nVisiting: {start_url}")
            try:
                await page.goto(start_url, wait_until="networkidle", timeout=20000)
                await asyncio.sleep(2)

                # Extract all sidebar links
                links = await page.eval_on_selector_all(
                    "a[href*='/doc/store/']",
                    """els => els.map(el => ({
                        href: el.href,
                        text: el.innerText.trim()
                    })).filter(l => l.text.length > 0 && l.text.length < 100)"""
                )

                for link in links:
                    href = link["href"].split("#")[0].split("?")[0]  # Remove fragments/params
                    if href and "/doc/store/" in href:
                        all_links[href] = link["text"]

                print(f"  Found {len(links)} links (total unique: {len(all_links)})")

            except Exception as e:
                print(f"  ERROR: {e}")

        # Also try the growth center
        growth_links = {}
        growth_urls = [
            "https://store.weixin.qq.com/chengzhang/home",
        ]

        for url in growth_urls:
            print(f"\nVisiting growth center: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await asyncio.sleep(3)

                # Click through category tabs to load content
                for cat_key in ["growth_center_platform_notice", "growth_center_rule_for_store",
                                "growth_center_manual_for_store"]:
                    try:
                        # Try to navigate to category
                        cat_url = f"https://store.weixin.qq.com/chengzhang/home?category_key={cat_key}"
                        await page.goto(cat_url, wait_until="networkidle", timeout=15000)
                        await asyncio.sleep(3)

                        # Scroll to load more
                        for _ in range(3):
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await asyncio.sleep(1)

                        links = await page.eval_on_selector_all(
                            "a[href]",
                            """els => els.map(el => ({
                                href: el.href,
                                text: el.innerText.trim()
                            })).filter(l => l.href.includes('webdoc') || l.href.includes('wiki'))"""
                        )

                        for link in links:
                            if link["text"] and len(link["text"]) > 2:
                                growth_links[link["href"]] = link["text"]

                        print(f"  {cat_key}: {len(links)} links")

                    except Exception as e:
                        print(f"  ERROR on {cat_key}: {e}")

            except Exception as e:
                print(f"  ERROR: {e}")

        await browser.close()

    # Save results
    result = {
        "discover_date": datetime.now(ET).isoformat(),
        "dev_docs": {
            "count": len(all_links),
            "links": [{"url": url, "title": title} for url, title in sorted(all_links.items())]
        },
        "growth_center": {
            "count": len(growth_links),
            "links": [{"url": url, "title": title} for url, title in sorted(growth_links.items())]
        },
    }

    out_file = BASE_DIR / "discovered_urls.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"\n=== Discovery Complete ===")
    print(f"Dev docs: {len(all_links)} unique URLs")
    print(f"Growth center: {len(growth_links)} unique URLs")
    print(f"Saved to: {out_file}")

    return result


if __name__ == "__main__":
    asyncio.run(discover_dev_docs())
