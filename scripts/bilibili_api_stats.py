import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

import urllib.request, json, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# AV号转BV号工具函数 (bilibili官方算法)
def av_to_bv(av_id):
    table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
    tr = {v: i for i, v in enumerate(table)}
    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608
    av = int(av_id)
    av = (av ^ xor) + add
    r = list("BV1  4 1 7  ")
    for i in range(6):
        r[s[i]] = table[av // 58**i % 58]
    return "".join(r)

VIDEOS = [
    {"id": "av13090918", "bvid": None, "title": "演说家 怼马丁 完整版", "category": "A类"},
    {"id": "BV1zL4y1472e", "bvid": "BV1zL4y1472e", "title": "舌战群儒 一个人怒怼一群人", "category": "A类"},
    {"id": "av12938458", "bvid": None, "title": "演说家 大学生为什么考研 完整版", "category": "A类"},
    {"id": "BV1xx411H7bp", "bvid": "BV1xx411H7bp", "title": "演说家 强怼主持人", "category": "A类"},
    {"id": "BV1YQ4y1t7Qc", "bvid": "BV1YQ4y1t7Qc", "title": "生化环材四大天坑", "category": "B类"},
    {"id": "BV1CCFszFEX6", "bvid": "BV1CCFszFEX6", "title": "土木没人报了", "category": "B类"},
    {"id": "BV1gm4y1i7zW", "bvid": "BV1gm4y1i7zW", "title": "哪种人适合报生化环材", "category": "B类"},
    {"id": "BV1Hx41157Ws", "bvid": "BV1Hx41157Ws", "title": "衡水中学讲座", "category": "C类"},
    {"id": "BV1yC4y1v7P9", "bvid": "BV1yC4y1v7P9", "title": "2024考研讲座完整版", "category": "C类"},
    {"id": "BV1fE41187Dd", "bvid": "BV1fE41187Dd", "title": "7分钟解读34所985", "category": "C类"},
]

def fetch_stats(bvid=None, avid=None):
    if bvid:
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    elif avid:
        url = f"https://api.bilibili.com/x/web-interface/view?aid={avid}"
    else:
        return None

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    })
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        d = json.loads(r.read())
    if d.get("code") != 0:
        return {"error": d.get("message", "unknown")}
    data = d["data"]
    stat = data.get("stat", {})
    owner = data.get("owner", {})
    return {
        "bvid": data.get("bvid"),
        "title": data.get("title"),
        "view": stat.get("view"),
        "like": stat.get("like"),
        "favorite": stat.get("favorite"),
        "danmaku": stat.get("danmaku"),
        "coin": stat.get("coin"),
        "share": stat.get("share"),
        "uploader": owner.get("name"),
        "duration": data.get("duration"),
        "pubdate": data.get("pubdate"),
    }

results = []

for v in VIDEOS:
    vid_id = v["id"]
    bvid = v["bvid"]
    avid = None

    if vid_id.startswith("av"):
        avid = vid_id[2:]

    print(f"Fetching {vid_id}...", flush=True)
    try:
        if bvid:
            stat = fetch_stats(bvid=bvid)
        else:
            stat = fetch_stats(avid=avid)

        if stat and "error" not in stat:
            results.append({
                "id": vid_id,
                "category": v["category"],
                "title_hint": v["title"],
                "actual_title": stat.get("title"),
                "uploader": stat.get("uploader"),
                "view": stat.get("view"),
                "like": stat.get("like"),
                "favorite": stat.get("favorite"),
                "danmaku": stat.get("danmaku"),
                "coin": stat.get("coin"),
                "bvid": stat.get("bvid"),
            })
            print(f"  OK: view={stat.get('view'):,} like={stat.get('like')} fav={stat.get('favorite')} danmaku={stat.get('danmaku')} up={stat.get('uploader')}", flush=True)
        else:
            err = stat.get("error") if stat else "no data"
            results.append({"id": vid_id, "category": v["category"], "title_hint": v["title"], "error": err})
            print(f"  ERROR: {err}", flush=True)
    except Exception as e:
        results.append({"id": vid_id, "category": v["category"], "title_hint": v["title"], "error": str(e)})
        print(f"  EXCEPTION: {e}", flush=True)

    time.sleep(0.5)

print("\n=== RESULTS JSON ===")
print(json.dumps(results, ensure_ascii=False, indent=2))
