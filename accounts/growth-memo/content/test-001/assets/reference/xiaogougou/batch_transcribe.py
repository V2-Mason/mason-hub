"""
Batch transcribe selected xiaogougou videos using faster-whisper turbo + DirectML.
Outputs one JSON per video in transcripts/ directory.
"""
import json, time, os, sys, csv
from pathlib import Path
from faster_whisper import WhisperModel

BASE = Path(__file__).parent
AUDIO_DIR = BASE / "audio"
TRANSCRIPT_DIR = BASE / "transcripts"
TRANSCRIPT_DIR.mkdir(exist_ok=True)

# 30 selected videos (tier "选")
SELECTED_BVS = [
    # A. 平台深度分析
    "BV1RZd6YDECz",   # 小红书从0起步(上)
    "BV1wsL8zkE7b",   # 小红书从0起步(下)
    "BV1T14y1H7RT",   # 小红书如何做爆款
    "BV1ZV4y1A7tC",   # 小红书7条入局赛道
    "BV1nh4y1Q7GP",   # 为什么不建议新手做抖音
    "BV17ir6BLEJM",   # 一口气说完2025抖音
    "BV1zs4y1f7Kz",   # 2022百大洞察(上)
    "BV1hM4y1B7Jk",   # 2022百大洞察(下)
    "BV12UfdY9EjM",   # 从百大看B站2024
    "BV1D6KezyEpd",   # 视频号9亿流量池
    "BV14GA6z7E7H",   # 2025主流社交平台
    "BV1X94y1m73C",   # 哪个平台容易赚钱
    # B. 恰饭/变现方法论
    "BV1JF411L7NJ",   # 恰饭方法论01
    "BV1Nv4y1w78c",   # 恰饭方法论02
    "BV1U54y1o7eg",   # 恰饭方法论03
    "BV165411Q75G",   # 恰饭方法论04
    "BV1oG4y1K71f",   # 保姆级实操恰饭视频
    # C. MCN/达人营销
    "BV1ocsqzCEtY",   # 2025达人营销新变局
    "BV1dxeDzTEHR",   # 金主不喜欢头部达人
    "BV1MwJDzXEnT",   # 金主卷不动短视频
    "BV1Ca411W746",   # MCN签约教程
    "BV1Ua411n7DW",   # 几百万粉没饭可恰
    # D. 账号运营/内容策略
    "BV1cezXBEE9A",   # 523个爆火账号涨粉密码
    "BV1VyCrB2EF3",   # 找冷门高潜赛道
    "BV1m9tQzLEDT",   # 不擅长但赚钱的赛道
    "BV1Ma411u7qn",   # 想做全职UP主
    "BV1Ad2yB2EGA",   # 内容分层四步法
    # E. 行业宏观
    "BV15U75zZETJ",   # AI成为标配网红还剩什么
    "BV1UgU6BmEfS",   # 突破内卷终极蓝海
    "BV1Do4y1T7CF",   # 对话15位从业者
    # F. 个人经历
    "BV1verUYuEBC",   # 花8万总结经验
]

def load_video_meta():
    """Load metadata from video_list.tsv"""
    meta = {}
    with open(BASE / "video_list.tsv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # skip header
        for row in reader:
            bv, title, dur, date, views = row
            meta[bv] = {
                "bv": bv,
                "title": title,
                "duration": int(dur),
                "date": date,
                "views": int(views),
            }
    return meta

def transcribe_one(model, bv, meta_info):
    """Transcribe a single audio file, return result dict."""
    audio_path = AUDIO_DIR / f"{bv}.mp3"
    if not audio_path.exists():
        print(f"  SKIP: {audio_path} not found")
        return None

    t0 = time.time()
    segments_raw, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    segments = []
    full_text_parts = []
    for seg in segments_raw:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        full_text_parts.append(seg.text.strip())

    elapsed = time.time() - t0
    result = {
        **meta_info,
        "language_detected": info.language,
        "language_probability": round(info.language_probability, 3),
        "transcribe_time_sec": round(elapsed, 1),
        "transcribe_rtf": round(elapsed / meta_info["duration"], 3) if meta_info["duration"] > 0 else None,
        "segment_count": len(segments),
        "full_text": "\n".join(full_text_parts),
        "segments": segments,
    }
    return result

def main():
    meta = load_video_meta()

    # Filter to selected BVs that have audio
    todo = []
    for bv in SELECTED_BVS:
        if bv not in meta:
            print(f"WARNING: {bv} not in video_list.tsv, skipping")
            continue
        audio_path = AUDIO_DIR / f"{bv}.mp3"
        if not audio_path.exists():
            print(f"WARNING: {audio_path} not found, skipping")
            continue
        out_path = TRANSCRIPT_DIR / f"{bv}.json"
        if out_path.exists():
            print(f"SKIP (already done): {bv} - {meta[bv]['title'][:30]}")
            continue
        todo.append(bv)

    if not todo:
        print("All selected videos already transcribed!")
        return

    total_dur = sum(meta[bv]["duration"] for bv in todo)
    print(f"\n=== Batch Transcription ===")
    print(f"Videos to transcribe: {len(todo)}")
    print(f"Total audio duration: {total_dur//3600}h{(total_dur%3600)//60}m")
    print(f"Model: turbo (faster-whisper + DirectML)")
    print(f"Estimated time: ~{total_dur * 0.24 / 60:.0f} min\n")

    print("Loading turbo model...")
    model = WhisperModel("turbo", device="auto", compute_type="float32")
    print("Model loaded.\n")

    completed = 0
    total_transcribe_time = 0
    for bv in todo:
        info = meta[bv]
        dur_min = info["duration"] / 60
        print(f"[{completed+1}/{len(todo)}] {bv} | {info['title'][:40]}... | {dur_min:.0f}m")

        result = transcribe_one(model, bv, info)
        if result is None:
            continue

        out_path = TRANSCRIPT_DIR / f"{bv}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        total_transcribe_time += result["transcribe_time_sec"]
        completed += 1
        print(f"  Done in {result['transcribe_time_sec']:.0f}s (RTF {result['transcribe_rtf']:.3f}x) | {result['segment_count']} segments")

    print(f"\n=== Complete ===")
    print(f"Transcribed: {completed}/{len(todo)}")
    print(f"Total transcribe time: {total_transcribe_time/60:.1f} min")
    print(f"Total audio: {total_dur/60:.0f} min")
    print(f"Overall RTF: {total_transcribe_time/total_dur:.3f}x")

if __name__ == "__main__":
    main()
