#!/usr/bin/env python3
"""
B站官方号视频搜索工具 — 使用WBI签名

用法:
  python scripts/bili_search.py --mid 456664753 --keyword "DeepSeek"
  python scripts/bili_search.py --mid 48968347 --keyword "AI"
"""

import hashlib
import time
import urllib.parse
import requests
import argparse
import json
import sys
import os

# WBI签名混淆表 (固定值)
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
    # 过滤特殊字符
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

def search_user_videos(mid: int, keyword: str, cookies_file: str, page_size: int = 10):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": f"https://space.bilibili.com/{mid}/",
        "Origin": "https://space.bilibili.com",
    })

    # 加载cookies
    with open(cookies_file, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                session.cookies.set(parts[5], parts[6], domain=parts[0])

    # 获取wbi keys
    img_key, sub_key = get_wbi_keys(session)

    # 构建请求参数
    params = {
        "mid": mid,
        "keyword": keyword,
        "ps": page_size,
        "pn": 1,
        "order": "pubdate",
        "platform": "web",
    }

    # WBI签名
    signed_params = enc_wbi(params, img_key, sub_key)

    # 发送请求
    url = "https://api.bilibili.com/x/space/wbi/arc/search"
    resp = session.get(url, params=signed_params, timeout=10)
    data = resp.json()

    if data["code"] != 0:
        print(f"API Error: code={data['code']}, message={data.get('message', 'unknown')}", file=sys.stderr)
        return []

    vlist = data.get("data", {}).get("list", {}).get("vlist", [])
    return vlist

def main():
    parser = argparse.ArgumentParser(description="搜索B站用户空间视频")
    parser.add_argument("--mid", type=int, required=True, help="用户UID")
    parser.add_argument("--keyword", type=str, required=True, help="搜索关键词")
    parser.add_argument("--cookies", type=str, default="c:/Users/hangn/projects/mason-hub/cookies.txt")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    results = search_user_videos(args.mid, args.keyword, args.cookies, args.limit)

    if not results:
        print("No results found")
        return

    for v in results:
        print(f'{v["bvid"]} | {v["title"]} | {v["length"]} | {v["play"]} plays')

if __name__ == "__main__":
    main()
