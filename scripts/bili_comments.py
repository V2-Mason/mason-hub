#!/usr/bin/env python3
"""
B站视频评论区抓取 - 用于赛道挖掘的"评论区考古"
用法:
  python scripts/bili_comments.py --bvid BV1uj411h7H2 --limit 50
"""
import requests
import argparse
import json
import time
import sys

def bvid_to_aid(bvid):
    """通过 web API 把 bvid 转 aid"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    r = requests.get(url, timeout=10, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    return r.json()["data"]["aid"]

def get_comments(bvid, max_count=50, cookies_file=None):
    """抓取评论区"""
    aid = bvid_to_aid(bvid)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://www.bilibili.com/video/{bvid}",
    })

    if cookies_file:
        with open(cookies_file, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    session.cookies.set(parts[5], parts[6], domain=parts[0])

    all_comments = []
    page = 1
    while len(all_comments) < max_count:
        url = "https://api.bilibili.com/x/v2/reply/main"
        params = {
            "type": 1,
            "oid": aid,
            "mode": 3,  # 3=按热度
            "next": page - 1,
            "ps": 20,
        }
        r = session.get(url, params=params, timeout=15)
        data = r.json()
        if data.get("code") != 0:
            print(f"  Error: {data.get('message')}", file=sys.stderr)
            break

        replies = data.get("data", {}).get("replies") or []
        if not replies:
            break

        for reply in replies:
            content = reply.get("content", {}).get("message", "")
            like = reply.get("like", 0)
            all_comments.append({
                "like": like,
                "content": content,
            })
            if len(all_comments) >= max_count:
                break

        page += 1
        time.sleep(0.5)
        if page > 10:
            break

    return all_comments

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvid", required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", default=None)
    parser.add_argument("--cookies", default="c:/Users/hangn/projects/mason-hub/cookies.txt")
    args = parser.parse_args()

    comments = get_comments(args.bvid, args.limit, args.cookies)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"bvid": args.bvid, "comments": comments}, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(comments)} comments to {args.out}")
    else:
        for c in comments:
            print(f"[{c['like']:>4}] {c['content']}")

if __name__ == "__main__":
    main()
