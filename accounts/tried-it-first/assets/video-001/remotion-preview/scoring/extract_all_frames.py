#!/usr/bin/env python3
"""Extract properties from ALL 33 reference frames → all_frames_data.json

Usage:
    python scoring/extract_all_frames.py
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REF_DIR = Path("C:/Users/hangn/projects/mason-hub/accounts/surenxuan/content/anua-promo/source/original-frames")
OUTPUT = SCRIPT_DIR / "all_frames_data.json"

sys.path.insert(0, str(SCRIPT_DIR))
from extract_properties import extract_properties


def main():
    frames = sorted(REF_DIR.glob("correct-frame-*.jpg"))
    if not frames:
        print("ERROR: No reference frames found", file=sys.stderr)
        sys.exit(1)

    # 原片 10 秒，33 帧 → 约每 0.3 秒一帧 → 约每 9 帧 (@ 30fps)
    # Remotion 视频 9 秒 @ 30fps = 270 帧
    # 映射：ref frame N → remotion frame (N-1) * (270/33) ≈ (N-1) * 8.18
    data = {"total_ref_frames": len(frames), "remotion_fps": 30, "remotion_duration_frames": 270, "frames": []}

    for i, ref_path in enumerate(frames):
        ref_num = i + 1
        remotion_frame = round(i * (270 / 33))

        print(f"  [{ref_num:02d}/33] frame {remotion_frame:3d} ...", file=sys.stderr, end="")
        props = extract_properties(str(ref_path))

        # Normalize positions and sizes to 0-1 range
        if "error" not in props:
            w, h = props["image_size"]["w"], props["image_size"]["h"]
            normalized_cards = []
            for card in props["cards"]:
                normalized_cards.append({
                    "x_norm": round(card["x"] / w, 4),
                    "y_norm": round(card["y"] / h, 4),
                    "w_norm": round(card["w"] / w, 4),
                    "h_norm": round(card["h"] / h, 4),
                    "color": card["color"],
                    "x_px": card["x"],
                    "y_px": card["y"],
                    "w_px": card["w"],
                    "h_px": card["h"],
                })

            entry = {
                "ref_frame": ref_num,
                "remotion_frame": remotion_frame,
                "ref_file": ref_path.name,
                "image_size": props["image_size"],
                "background_color": props["background_color"],
                "num_cards": props["num_cards"],
                "cards": normalized_cards,
            }
        else:
            entry = {"ref_frame": ref_num, "remotion_frame": remotion_frame, "error": props["error"]}

        data["frames"].append(entry)
        print(f" {props.get('num_cards', '?')} cards", file=sys.stderr)

    OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nSaved {len(data['frames'])} frames to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
