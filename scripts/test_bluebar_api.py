"""
Test if B站 blue-bar (ad/sponsor) info can be scraped anonymously.
Tries multiple methods: view API, view/detail API, HTML page scrape.
"""
import requests
import re
import time
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# Known sponsor and non-sponsor videos
TEST_BVIDS = [
    ("BV1tKwFzKEQe", "Genji - 百大教AI变现 (新号, 可能含商单)"),
    ("BV1HQwDzqEw3", "Genji - 百万up工作流"),
    ("BV17d4y177HW", "狗勾 - 品牌营销案例视频 (讲金主的)"),
    ("BV1sQBPBmEGU", "鱼皮 - 色情直播事件 (纯事件, 非恰饭)"),
]


def test_html_scrape(bvid, desc):
    print(f"\n=== {bvid}: {desc} ===")
    url = f"https://www.bilibili.com/video/{bvid}/"
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"  status: {r.status_code}, length: {len(r.text)}")
    if r.status_code != 200:
        return

    html = r.text

    # 1. Look for __INITIAL_STATE__ JSON dump (contains everything)
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", html)
    if m:
        print(f"  __INITIAL_STATE__ found, length = {len(m.group(1))}")
        try:
            state = json.loads(m.group(1))
            # Walk the state looking for ad/sponsor fields
            def walk(obj, path=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        kp = f"{path}.{k}" if path else k
                        klower = k.lower()
                        if any(w in klower for w in ["ad", "sponsor", "charge", "commercial", "brand", "promo", "cc_mark"]):
                            print(f"    [{kp}] = {str(v)[:100]}")
                        walk(v, kp)
                elif isinstance(obj, list) and obj and isinstance(obj[0], (dict, list)):
                    for i, item in enumerate(obj[:3]):
                        walk(item, f"{path}[{i}]")
            walk(state)
        except Exception as e:
            print(f"  JSON parse error: {e}")

    # 2. Look for specific ad markers in the raw HTML (cc_mark is the blue-bar indicator)
    markers = [
        "cc_mark", "chargePanel", "ad_info", "commercialType",
        "business_info", "isCommercial",
    ]
    for marker in markers:
        idx = html.find(marker)
        if idx >= 0:
            ctx = html[max(0, idx-30):idx+150]
            ctx = ctx.replace("\n", " ").replace("\\", "")
            print(f"  [{marker}] @ {idx}: {ctx[:180]}")


def test_view_api(bvid, desc):
    r = requests.get(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
        headers=HEADERS, timeout=10,
    )
    data = r.json()
    if data.get("code") != 0:
        print(f"  view API ERROR: {data.get('message')}")
        return
    d = data["data"]
    # cc_mark field often indicates ad declaration
    if "cc_mark" in d:
        print(f"  cc_mark = {d['cc_mark']}")
    if "dm_score" in d:
        print(f"  dm_score = {d['dm_score']}")
    # Check description for sponsor keywords
    desc_text = d.get("desc", "")
    if desc_text:
        sponsor_words = ["赞助", "合作", "推广", "特约", "本期由", "广告合作", "本视频为", "官方邀请"]
        for word in sponsor_words:
            if word in desc_text:
                idx = desc_text.find(word)
                ctx = desc_text[max(0, idx-20):idx+80].replace("\n", " ")
                print(f"  desc sponsor keyword '{word}': ...{ctx}...")


def main():
    for bvid, desc in TEST_BVIDS:
        test_view_api(bvid, desc)
        test_html_scrape(bvid, desc)
        time.sleep(2)


if __name__ == "__main__":
    main()
