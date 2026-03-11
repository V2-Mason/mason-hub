"""Crawl ALL XHS helper center categories and articles."""
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path("intel/raw/xhs-helper-docs")
ET = timezone(timedelta(hours=-4))  # Mason 标准时区：美东

NOISE = {
    "首页", "买手专区", "课程中心", "规则中心", "专题直播", "认证讲师",
    "千帆", "您好，", "请登录",
    "Copyright © 2014-2022 行吟信息科技（上海）有限公司",
}

# Priority categories for a new store owner
PRIORITY_CATS = [
    # 开店入驻
    438, 442, 443, 444,
    # 店铺基础
    347, 348, 346, 382,
    # 商品发布
    411, 412, 413,
    # 订单履约
    400, 397, 436,
    # 财务结算
    354, 355,
    # 店铺管理/商品管理/物流发货/营销/数据/售后
    240, 239, 243, 242, 241, 245,
    # 客服
    333, 334,
    # 活动促销
    351,
    # 广告推广
    435,
    # 店铺数据
    433, 432, 431,
    # 平台秩序
    284, 285, 286, 287,
    # 内容发布
    269, 270,
    # 直播
    272, 273, 343, 344,
]


def sanitize(title):
    title = re.sub(r'[/\\:*?"<>|]', "", title)
    return title.strip()[:80] or "untitled"


async def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Load category tree
    api_file = BASE_DIR / "_api_captures.json"
    api_data = json.loads(api_file.read_text())
    cats = api_data[0]["data"]["data"]

    # Build flat list: {id: {name, parent_name}}
    cat_map = {}
    for cat in cats:
        for child in cat.get("children", []):
            cat_map[child["id"]] = {
                "name": child["categoryName"],
                "parent": cat["categoryName"],
            }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # Init session
        await page.goto(
            "https://school.xiaohongshu.com/helper/list?ctg=438",
            wait_until="domcontentloaded", timeout=30000,
        )
        await asyncio.sleep(3)

        all_articles = []  # {cat_id, cat_name, parent_name, title, href}
        seen_hrefs = set()

        for cid in PRIORITY_CATS:
            info = cat_map.get(cid)
            if not info:
                continue
            url = f"https://school.xiaohongshu.com/helper/list?ctg={cid}"
            print(f"\n【{info['parent']} > {info['name']}】(ctg={cid})")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                await asyncio.sleep(3)

                # Scroll to load
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 600)")
                    await asyncio.sleep(0.5)

                links = await page.evaluate(
                    """() => {
                    const results = [];
                    const seen = new Set();
                    for (const a of document.querySelectorAll('a[href*="helper/detail"]')) {
                        const href = a.href || '';
                        const text = (a.innerText || '').trim();
                        if (text && text.length > 3 && !seen.has(href)) {
                            seen.add(href);
                            results.push({href, text});
                        }
                    }
                    return results;
                }"""
                )

                for lnk in links:
                    if lnk["href"] not in seen_hrefs:
                        seen_hrefs.add(lnk["href"])
                        all_articles.append({
                            "cat_id": cid,
                            "cat_name": info["name"],
                            "parent_name": info["parent"],
                            "title": lnk["text"],
                            "href": lnk["href"],
                        })
                        print(f"  + {lnk['text'][:60]}")

            except Exception as e:
                print(f"  Error: {e}")

            await asyncio.sleep(0.5)

        print(f"\n=== Total: {len(all_articles)} unique articles ===")
        print("Fetching details...")

        results = []
        for i, art in enumerate(all_articles):
            print(f"  [{i+1}/{len(all_articles)}] {art['title'][:50]}", end="")
            try:
                await page.goto(
                    art["href"], wait_until="domcontentloaded", timeout=10000
                )
                await asyncio.sleep(2.5)

                content = await page.evaluate(
                    """() => {
                    let best = '';
                    const sels = [
                        '[class*="detail"]', '[class*="content"]',
                        '[class*="article"]', 'main'
                    ];
                    for (const sel of sels) {
                        for (const el of document.querySelectorAll(sel)) {
                            const t = (el.innerText || '').trim();
                            if (t.length > best.length && t.length > 30) best = t;
                        }
                    }
                    return best || (document.body.innerText || '');
                }"""
                )

                # Clean noise
                lines = content.split("\n")
                clean = [
                    l.strip() for l in lines
                    if l.strip() and l.strip() not in NOISE
                ]
                content_clean = "\n".join(clean)

                if len(content_clean) > 30:
                    results.append({**art, "content": content_clean})
                    print(f" ✓ {len(content_clean)}c")
                else:
                    print(f" ✗ empty")

            except Exception as e:
                print(f" ERR: {e}")

            await asyncio.sleep(1)

        await browser.close()

    # Save
    print(f"\n=== Saving {len(results)} articles ===")

    # Group by parent > cat
    by_group = {}
    for r in results:
        key = f"{r['parent_name']}/{r['cat_name']}"
        by_group.setdefault(key, []).append(r)

    # Save merged doc
    out_path = Path("intel/processed/小红书电商帮助中心-完整文档.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    parts = [
        "# 小红书电商帮助中心 — 完整文档\n",
        f"> 爬取时间: {datetime.now(ET).isoformat()}",
        f"> 共 {len(results)} 篇帮助文档\n",
        "---\n",
        "## 目录\n",
    ]

    for group, articles in sorted(by_group.items()):
        parts.append(f"### {group}\n")
        for a in articles:
            parts.append(f"- {a['title']}")
        parts.append("")

    parts.append("---\n")

    for group, articles in sorted(by_group.items()):
        parts.append(f"\n# {group}\n")
        for a in articles:
            parts.append(f"\n## {a['title']}\n")
            parts.append(a["content"])
            parts.append("\n---\n")

    merged = "\n".join(parts)
    out_path.write_text(merged, encoding="utf-8")
    print(f"\nMerged: {out_path}")
    print(f"  {merged.count(chr(10))} lines, {len(merged.encode())/1024:.0f} KB")

    # Save index
    index = {
        "crawl_date": datetime.now(ET).isoformat(),
        "total_articles": len(results),
        "categories": {
            group: [{"title": a["title"], "url": a["href"]}
                    for a in articles]
            for group, articles in sorted(by_group.items())
        },
    }
    (BASE_DIR / "helper_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    asyncio.run(main())
