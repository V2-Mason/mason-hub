"""
Probe GenJi是真想教会你AI (mid=491266931) full video list and save to _dictionary/.
Uses yt-dlp for BV list + view API for metadata.
"""
import json
import subprocess
import requests
import time
from pathlib import Path

OUT_PATH = Path("accounts/growth-memo/content/test-001/assets/reference/_dictionary/genji_new_probe.json")

ACCOUNT = {
    "name": "GenJi是真想教会你AI",
    "mid": 491266931,
    "space_url": "https://space.bilibili.com/491266931/video",
}


def get_bvid_list():
    """Use yt-dlp --flat-playlist to get all BVIDs.
    Falls back to cached /tmp/genji_bvids.txt if yt-dlp is rate-limited.
    """
    proc = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "%(id)s", ACCOUNT["space_url"]],
        capture_output=True, text=True, timeout=120
    )
    bvids = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("BV"):
            bvids.append(line)

    # Fallback: use cached list (Windows Temp path)
    if not bvids:
        cache_candidates = [
            Path("C:/Users/hangn/AppData/Local/Temp/genji_bvids.txt"),
            Path("/tmp/genji_bvids.txt"),
        ]
        for cache_path in cache_candidates:
            if cache_path.exists():
                print(f"[fallback] using cached {cache_path}")
                with cache_path.open("r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("BV"):
                            bvids.append(line)
                break
    return bvids


def get_video_metadata(bvid):
    """Get title/view/pubdate/duration/reply from view API."""
    r = requests.get(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    data = r.json()
    if data.get("code") != 0:
        return None
    d = data["data"]
    return {
        "bvid": bvid,
        "title": d.get("title", ""),
        "desc": d.get("desc", ""),
        "view": d["stat"]["view"],
        "like": d["stat"]["like"],
        "reply": d["stat"]["reply"],
        "favorite": d["stat"]["favorite"],
        "coin": d["stat"]["coin"],
        "share": d["stat"]["share"],
        "duration": d.get("duration", 0),
        "pubdate": d.get("pubdate", 0),
    }


def main():
    print(f"[probe] yt-dlp flat-playlist...")
    bvids = get_bvid_list()
    print(f"[ok] got {len(bvids)} BVIDs")

    videos = []
    for i, bvid in enumerate(bvids):
        try:
            meta = get_video_metadata(bvid)
            if meta:
                videos.append(meta)
                print(f"  [{i+1}/{len(bvids)}] {bvid}: {meta['view']:>10} views, {meta['title'][:40]}")
            time.sleep(1.8)
        except Exception as e:
            print(f"  [{i+1}/{len(bvids)}] {bvid}: ERROR {e}")
            time.sleep(3)

    # Sort by view desc
    videos.sort(key=lambda v: -v["view"])

    output = {
        "schema_version": "1.0",
        "generated": "2026-04-08",
        "account": ACCOUNT,
        "total_videos": len(videos),
        "source": "yt-dlp --flat-playlist + view API (anonymous)",
        "notes": "Archived for round2 mine_evidence.py. Genji 是 Mason 定位最接近的参照系, 所有 video 在 round2 需要挖评论.",
        "videos": videos,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n[OK] saved to {OUT_PATH}")
    print(f"[OK] {len(videos)} videos archived")
    if videos:
        print(f"[OK] top video: {videos[0]['title'][:50]} ({videos[0]['view']:,} views)")


if __name__ == "__main__":
    main()
