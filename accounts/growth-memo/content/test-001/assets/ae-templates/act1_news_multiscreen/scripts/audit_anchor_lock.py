"""
audit_anchor_lock.py — Re-audit all Act 1 clips against anchor-lock 5-check standard.

For each clip:
  - ffprobe duration / resolution
  - ffmpeg scene detect at threshold 0.1 (catches B-roll cutaways)
  - faster-whisper word_timestamps (en/zh based on filename prefix)
  - Extract 5 frames (0.1s, 25%, 50%, 75%, end-0.1s) for hidden-cut review

Outputs:
  - audit_results.json — raw measurement data
  - audit_frames/<clip_name>/frame_*.jpg — review frames

Standard:
  C1 single shot   = 0 cuts at threshold 0.1 (frames must be reviewed manually)
  C2 anchor present = manual review of frames
  C3 full sentence  = whisper transcript completes a clause
  C4 company named  = whisper text contains brand keyword
  C5 key data       = whisper text contains digits/percent

We compute C1/C3/C4/C5 automatically and leave C2 + final 5/5 verdict for human.
"""

from pathlib import Path
import json
import re
import subprocess
import sys
import io
from faster_whisper import WhisperModel

# Force UTF-8 stdout so Chinese transcripts don't crash on Windows cp1252
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CLIPS_DIR = ROOT / "clips"
FILL_DIR = ROOT / "fill_clips"
OUT_JSON = ROOT / "audit_results.json"
FRAMES_DIR = ROOT / "audit_frames"

# Brand keywords for C4 (company named) — case-insensitive substring match
BRANDS = [
    "google", "alphabet", "meta", "facebook", "amazon", "amzn",
    "microsoft", "msft", "openai", "anthropic", "claude", "chatgpt",
    "nvidia", "deepseek", "ibm", "chegg", "sora", "gemini", "opus",
    # Chinese
    "谷歌", "字节", "阿里", "腾讯", "百度", "微软", "英伟达", "苹果",
    "华为", "openai", "深度求索", "深度", "智", "万亿",
]

def run(cmd: list[str], input_text: str | None = None) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, input=input_text)
    return p.returncode, p.stdout, p.stderr

def probe_duration(path: Path) -> float:
    rc, out, _ = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ])
    return float(out.strip()) if rc == 0 and out.strip() else 0.0

def probe_resolution(path: Path) -> tuple[int, int]:
    rc, out, _ = run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(path)
    ])
    if rc == 0 and out.strip():
        try:
            w, h = out.strip().split(",")
            return int(w), int(h)
        except Exception:
            pass
    return 0, 0

def detect_scenes(path: Path, threshold: float = 0.1) -> list[float]:
    """Return list of scene change timestamps in seconds."""
    rc, _, err = run([
        "ffmpeg", "-i", str(path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-"
    ])
    timestamps: list[float] = []
    for line in err.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            try:
                timestamps.append(float(m.group(1)))
            except ValueError:
                pass
    return timestamps

def extract_frames(path: Path, duration: float, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    times = [
        max(0.0, 0.1),
        round(duration * 0.25, 3),
        round(duration * 0.50, 3),
        round(duration * 0.75, 3),
        max(0.0, duration - 0.1),
    ]
    saved = []
    for i, t in enumerate(times):
        out_path = out_dir / f"frame_{i+1}_t{t:.2f}s.jpg"
        run([
            "ffmpeg", "-y", "-v", "quiet",
            "-ss", str(t), "-i", str(path),
            "-frames:v", "1", str(out_path)
        ])
        if out_path.exists():
            saved.append(out_path)
    return saved

def transcribe(model: WhisperModel, path: Path, lang: str) -> dict:
    segments, _info = model.transcribe(
        str(path), word_timestamps=True, language=lang
    )
    words = []
    full_text = []
    for seg in segments:
        full_text.append(seg.text.strip())
        for w in seg.words:
            words.append({
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "word": w.word
            })
    return {
        "text": " ".join(full_text).strip(),
        "words": words,
        "language": lang,
    }

def detect_language(filename: str) -> str:
    lower = filename.lower()
    if lower.startswith("cn_") or "_cn_" in lower:
        return "zh"
    return "en"

def find_brands(text: str) -> list[str]:
    lower = text.lower()
    return sorted({b for b in BRANDS if b.lower() in lower})

def find_numbers(text: str) -> list[str]:
    """Find layoff numbers, percentages, dollar amounts."""
    found = set()
    # numbers like 10,000 / 11,000 / 12,000 / 7,800
    for m in re.finditer(r"\b\d{1,3}(?:,\d{3})+\b", text):
        found.add(m.group(0))
    # percentages
    for m in re.finditer(r"\b\d+(?:\.\d+)?%", text):
        found.add(m.group(0))
    # billion / trillion / million amounts
    for m in re.finditer(r"\b\$?\d+(?:\.\d+)?\s*(?:billion|trillion|million|亿|万|千万)", text, re.I):
        found.add(m.group(0))
    return sorted(found)

def main():
    all_clips: list[tuple[Path, str]] = []
    for p in sorted(CLIPS_DIR.glob("*.mp4")):
        if ".original" in p.name:
            continue
        all_clips.append((p, "hero"))
    for p in sorted(FILL_DIR.glob("*.mp4")):
        all_clips.append((p, "fill"))

    print(f"Found {len(all_clips)} clips to audit.")

    # Resume support: load partial results if present, skip clips already done
    results = []
    done_names: set[str] = set()
    if OUT_JSON.exists():
        try:
            results = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            done_names = {r["name"] for r in results}
            print(f"Resuming from {OUT_JSON.name}: {len(done_names)} already done.")
        except Exception as e:
            print(f"Could not parse existing {OUT_JSON.name}, starting fresh: {e}")
            results = []

    todo_clips = [(p, t) for (p, t) in all_clips if p.name not in done_names]
    print(f"To process: {len(todo_clips)} clips.\n")

    if not todo_clips:
        print("Nothing to do.")
        return

    print("Loading faster-whisper small model...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    print("Model loaded.\n")

    all_clips = todo_clips
    for idx, (path, tier) in enumerate(all_clips, 1):
        print(f"[{idx}/{len(all_clips)}] {path.name} ({tier})")
        duration = probe_duration(path)
        width, height = probe_resolution(path)
        scenes = detect_scenes(path, threshold=0.1)
        lang = detect_language(path.name)

        try:
            tr = transcribe(model, path, lang)
        except Exception as e:
            tr = {"text": "", "words": [], "language": lang, "error": str(e)}

        clip_frames_dir = FRAMES_DIR / path.stem
        frames = extract_frames(path, duration, clip_frames_dir)

        brands_found = find_brands(tr.get("text", ""))
        numbers_found = find_numbers(tr.get("text", ""))

        # Auto checks (manual review needed for C1/C2 confirm)
        c1_auto = (len(scenes) == 0)
        c3_auto = bool(tr.get("text", "").strip())  # has any speech
        c4_auto = bool(brands_found)
        c5_auto = bool(numbers_found)

        result = {
            "name": path.name,
            "path": str(path.relative_to(ROOT)),
            "tier_current": tier,
            "duration": round(duration, 3),
            "resolution": f"{width}x{height}",
            "language": lang,
            "scene_cuts_count": len(scenes),
            "scene_cuts_timestamps": [round(t, 3) for t in scenes],
            "transcript": tr.get("text", ""),
            "words": tr.get("words", []),
            "brands_found": brands_found,
            "numbers_found": numbers_found,
            "auto_checks": {
                "C1_single_shot": c1_auto,
                "C3_has_speech": c3_auto,
                "C4_company_named": c4_auto,
                "C5_key_data": c5_auto,
            },
            "frames": [str(f.relative_to(ROOT)) for f in frames],
        }
        results.append(result)
        # Incremental save after each clip so we can resume on crash
        OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        # Print summary line
        marks = "".join([
            "1" if c1_auto else ".",
            "3" if c3_auto else ".",
            "4" if c4_auto else ".",
            "5" if c5_auto else ".",
        ])
        snippet = (tr.get("text", "")[:60] + "...") if len(tr.get("text", "")) > 60 else tr.get("text", "")
        print(f"    [{marks}] cuts={len(scenes)} brands={brands_found} nums={numbers_found}")
        print(f"    text: {snippet}")
        print()

    print(f"\nDone. Wrote {len(results)} entries to {OUT_JSON}")
    print(f"Frames in {FRAMES_DIR}")

if __name__ == "__main__":
    main()
