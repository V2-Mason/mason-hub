"""Fetch XHS helper articles about 专业号 (professional accounts)."""
import asyncio
import json
from playwright.async_api import async_playwright

NOISE = {
    "首页", "买手专区", "课程中心", "规则中心", "专题直播", "认证讲师",
    "千帆", "您好，", "请登录",
    "Copyright © 2014-2022 行吟信息科技（上海）有限公司",
}

TARGET_CATS = [
    (254, "专业号认证"),
    (253, "专业号身份/行业相关"),
    (249, "如何升级成为专业号"),
    (248, "号店一体介绍"),
]


async def main():
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

        for cid, cname in TARGET_CATS:
            url = f"https://school.xiaohongshu.com/helper/list?ctg={cid}"
            print(f"\n### {cname} (ctg={cid}) ###")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(4)

            links = await page.evaluate(
                """() => {
                const results = [];
                const seen = new Set();
                const allLinks = document.querySelectorAll('a[href*="helper/detail"]');
                for (const a of allLinks) {
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
                aid = lnk["href"].split("/")[-1]
                print(f"\n  [{aid}] {lnk['text']}")
                try:
                    await page.goto(
                        lnk["href"], wait_until="domcontentloaded", timeout=12000
                    )
                    await asyncio.sleep(3)
                    content = await page.evaluate(
                        """() => {
                        let best = '';
                        const sels = ['[class*="detail"]', '[class*="content"]', 'main'];
                        for (const sel of sels) {
                            for (const el of document.querySelectorAll(sel)) {
                                const t = (el.innerText || '').trim();
                                if (t.length > best.length && t.length > 30) best = t;
                            }
                        }
                        return best || (document.body.innerText || '');
                    }"""
                    )
                    lines = [
                        l.strip()
                        for l in content.split("\n")
                        if l.strip() and l.strip() not in NOISE
                    ]
                    for line in lines[:20]:
                        if len(line) > 3:
                            print(f"    {line[:150]}")
                except Exception as e:
                    print(f"    Error: {e}")
                await asyncio.sleep(1)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
