import asyncio
import json
import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

VIDEOS = [
    {"id": "av13090918", "url": "https://www.bilibili.com/video/av13090918/", "title": "演说家 怼马丁 完整版"},
    {"id": "BV1zL4y1472e", "url": "https://www.bilibili.com/video/BV1zL4y1472e/", "title": "舌战群儒 一个人怒怼一群人"},
    {"id": "av12938458", "url": "https://www.bilibili.com/video/av12938458/", "title": "演说家 大学生为什么考研 完整版"},
    {"id": "BV1xx411H7bp", "url": "https://www.bilibili.com/video/BV1xx411H7bp/", "title": "演说家 强怼主持人"},
    {"id": "BV1YQ4y1t7Qc", "url": "https://www.bilibili.com/video/BV1YQ4y1t7Qc/", "title": "生化环材四大天坑"},
    {"id": "BV1CCFszFEX6", "url": "https://www.bilibili.com/video/BV1CCFszFEX6/", "title": "土木没人报了"},
    {"id": "BV1gm4y1i7zW", "url": "https://www.bilibili.com/video/BV1gm4y1i7zW/", "title": "哪种人适合报生化环材"},
    {"id": "BV1Hx41157Ws", "url": "https://www.bilibili.com/video/BV1Hx41157Ws/", "title": "衡水中学讲座"},
    {"id": "BV1yC4y1v7P9", "url": "https://www.bilibili.com/video/BV1yC4y1v7P9/", "title": "2024考研讲座完整版"},
    {"id": "BV1fE41187Dd", "url": "https://www.bilibili.com/video/BV1fE41187Dd/", "title": "7分钟解读34所985"},
]

async def get_stats(page, video):
    vid_id = video["id"]
    url = video["url"]
    print(f"[{vid_id}] Fetching {url}", flush=True)

    result = {
        "id": vid_id,
        "title_hint": video["title"],
        "url": url,
        "plays": None,
        "likes": None,
        "favorites": None,
        "danmaku": None,
        "uploader": None,
        "error": None,
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Try to get stats via API endpoint embedded in page
        # First try DOM selectors

        # Uploader
        try:
            uploader = await page.query_selector(".up-name, .username, [class*='up-name'], .name")
            if uploader:
                result["uploader"] = (await uploader.inner_text()).strip()
        except:
            pass

        # Try multiple selectors for play count
        play_selectors = [
            ".view-text",
            "[class*='play'] .num",
            ".video-stat .view",
            "span[class*='view']",
            ".bpx-player-ctrl-play",
            "[data-key='view']",
        ]
        for sel in play_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    txt = (await el.inner_text()).strip()
                    if txt:
                        result["plays"] = txt
                        break
            except:
                pass

        # Try via initial state JSON in page
        content = await page.content()

        import re

        # Extract __INITIAL_STATE__
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', content, re.DOTALL)
        if m:
            try:
                state = json.loads(m.group(1))
                stat = state.get("videoData", {}).get("stat", {})
                if stat:
                    result["plays"] = stat.get("view")
                    result["likes"] = stat.get("like")
                    result["favorites"] = stat.get("favorite")
                    result["danmaku"] = stat.get("danmaku")

                owner = state.get("videoData", {}).get("owner", {})
                if owner:
                    result["uploader"] = owner.get("name")
            except Exception as e:
                result["error"] = f"parse_state_error: {e}"

        # Fallback: try window.__playinfo__
        if result["plays"] is None:
            m2 = re.search(r'window\.__playinfo__\s*=\s*(\{.*?\})\s*</script>', content, re.DOTALL)
            # not useful for stats, skip

        # Try meta tags or aria
        if result["plays"] is None:
            # Look for stat data in script tags
            scripts = await page.query_selector_all("script")
            for script in scripts:
                try:
                    sc = await script.inner_text()
                    if '"view"' in sc and '"like"' in sc:
                        m3 = re.search(r'"view"\s*:\s*(\d+)', sc)
                        if m3:
                            result["plays"] = int(m3.group(1))
                        m4 = re.search(r'"like"\s*:\s*(\d+)', sc)
                        if m4:
                            result["likes"] = int(m4.group(1))
                        m5 = re.search(r'"favorite"\s*:\s*(\d+)', sc)
                        if m5:
                            result["favorites"] = int(m5.group(1))
                        m6 = re.search(r'"danmaku"\s*:\s*(\d+)', sc)
                        if m6:
                            result["danmaku"] = int(m6.group(1))
                        if result["plays"]:
                            break
                except:
                    pass

        print(f"[{vid_id}] plays={result['plays']} likes={result['likes']} fav={result['favorites']} danmaku={result['danmaku']} up={result['uploader']}", flush=True)

    except Exception as e:
        result["error"] = str(e)
        print(f"[{vid_id}] ERROR: {e}", flush=True)

    return result


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = await context.new_page()

        results = []
        for video in VIDEOS:
            r = await get_stats(page, video)
            results.append(r)
            await asyncio.sleep(1)

        await browser.close()

        # Output JSON
        print("\n=== JSON_RESULTS_START ===", flush=True)
        print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)
        print("=== JSON_RESULTS_END ===", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
