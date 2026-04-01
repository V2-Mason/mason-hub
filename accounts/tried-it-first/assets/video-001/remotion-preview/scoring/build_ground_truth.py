#!/usr/bin/env python3
"""Build ground truth from reference frames using OpenCV.

Usage:
    python scoring/build_ground_truth.py
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FRAME_MAP = SCRIPT_DIR / "frame_map.json"
OUTPUT = SCRIPT_DIR / "ground_truth.json"

sys.path.insert(0, str(SCRIPT_DIR))
from extract_properties import extract_properties


def main():
    frame_map = json.loads(FRAME_MAP.read_text())
    ref_dir = Path(frame_map["reference_dir"])

    ground_truth = {"frames": []}

    for pair in frame_map["pairs"]:
        ref_path = ref_dir / pair["reference"]
        if not ref_path.exists():
            print(f"SKIP: {ref_path} not found", file=sys.stderr)
            continue

        print(f"Processing {pair['phase']} (frame {pair['remotion_frame']})...", file=sys.stderr)
        opencv_data = extract_properties(str(ref_path))

        ground_truth["frames"].append({
            "remotion_frame": pair["remotion_frame"],
            "reference": pair["reference"],
            "phase": pair["phase"],
            "opencv": opencv_data,
        })

    OUTPUT.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print(f"Ground truth saved: {len(ground_truth['frames'])} frames", file=sys.stderr)


if __name__ == "__main__":
    main()
