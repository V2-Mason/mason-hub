#!/usr/bin/env python3
"""
B站全站搜索 - 使用WBI签名
按播放量/互动排序，输出 TOP N 视频元数据

用法:
  python scripts/bili_global_search.py --keyword "独立开发者" --limit 30
"""
import hashlib
import time
import urllib.parse
import requests
import argparse
import json
import sys
import os

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

def get_mixin_key(orig: str) -> str:
    return "".join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]

def enc_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params["wts"] = curr_time
    params = dict(sorted(params.items()))
    params = {
        k: "".join(c for c in str(v) if c not in "!'()*")
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = wbi_sign
    return params

def get_wbi_keys(session: requests.Session) -> tuple:
    resp = session.get("https://api.bilibili.com/x/web-interface/nav", timeout=10)
    data = resp.json()["data"]
    img_url = data["wbi_img"]["img_url"]
    sub_url = data["wbi_img"]["sub_url"]
    img_key = img_url.rsplit("/", 1)[1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]
    return img_key, sub_key

def load_cookies(session, cookies_file):
    with open(cookies_file, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                session.cookies.set(parts[5], parts[6], domain=parts[0])

def search_global(keyword: str, cookies_file: str, order: str = "click", page: int = 1, page_size: int = 30):
    """
    order: totalrank(综合) / click(最多播放) / pubdate(最新发布) / dm(最多弹幕) / scores(最多评论)
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://search.bilibili.com/",
        "Origin": "https://search.bilibili.com",
    })
    load_cookies(session, cookies_file)

    # 先 hit 一下首页拿 cookie
    session.get("https://www.bilibili.com/", timeout=10)

    img_key, sub_key = get_wbi_keys(session)

    params = {
        "search_type": "video",
        "keyword": keyword,
        "order": order,
        "page": page,
        "page_size": page_size,
        "platform": "pc",
    }

    signed = enc_wbi(params, img_key, sub_key)
    url = "https://api.bilibili.com/x/web-interface/wbi/search/type"
    resp = session.get(url, params=signed, timeout=15)
    data = resp.json()

    if data.get("code") != 0:
        print(f"API Error: code={data.get('code')}, message={data.get('message')}", file=sys.stderr)
        return []

    return data.get("data", {}).get("result", [])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--order", default="click", choices=["totalrank", "click", "pubdate", "dm", "scores"])
    parser.add_argument("--cookies", default="c:/Users/hangn/projects/mason-hub/cookies.txt")
    parser.add_argument("--out", default=None, help="Output JSON file")
    args = parser.parse_args()

    results = search_global(args.keyword, args.cookies, order=args.order, page_size=args.limit)

    if not results:
        print("No results")
        return

    # 清理结果，只保留有用字段
    cleaned = []
    for v in results[:args.limit]:
        cleaned.append({
            "bvid": v.get("bvid"),
            "aid": v.get("aid"),
            "title": v.get("title", "").replace('<em class="keyword">', "").replace("</em>", ""),
            "author": v.get("author"),
            "mid": v.get("mid"),
            "play": v.get("play"),
            "video_review": v.get("video_review"),  # 弹幕数
            "danmaku": v.get("video_review"),
            "favorites": v.get("favorites"),
            "like": v.get("like"),
            "duration": v.get("duration"),
            "pubdate": v.get("pubdate"),
            "description": v.get("description", "")[:200],
            "tag": v.get("tag", ""),
        })

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(cleaned)} results to {args.out}")
    else:
        for v in cleaned:
            print(f'{v["bvid"]} | {v["play"]:>10} plays | {v["like"] or 0:>6} likes | {v["title"][:60]} | @{v["author"]}')

if __name__ == "__main__":
    main()
