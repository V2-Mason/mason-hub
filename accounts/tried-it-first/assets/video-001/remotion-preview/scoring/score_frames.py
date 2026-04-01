#!/usr/bin/env python3
"""Score rendered frames against ground truth using deterministic OpenCV comparison.

Usage:
    python scoring/score_frames.py
    # Outputs a single number 0-100 to stdout (for autoresearch Verify)
    # Outputs per-frame breakdown + biggest deviation to stderr
"""
import json
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FRAME_MAP = SCRIPT_DIR / "frame_map.json"
RENDERED_DIR = SCRIPT_DIR / "rendered-frames"
GROUND_TRUTH = SCRIPT_DIR / "ground_truth.json"

sys.path.insert(0, str(SCRIPT_DIR))
from extract_properties import extract_properties


def hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def color_delta_e(hex1, hex2):
    """Euclidean RGB distance, normalized to 0-100."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    dist = math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
    return min(dist / 441 * 100, 100)  # max RGB dist ≈ 441


def score_frame(gt_frame, rendered_props):
    """Score a single rendered frame against ground truth. Returns (score, penalties)."""
    gt = gt_frame["opencv"]
    rd = rendered_props
    penalties = {}

    # --- Visibility ---
    gt_count = gt["num_cards"]
    rd_count = rd["num_cards"]
    if gt_count == 0 and rd_count == 0:
        penalties["visibility"] = 0
    elif gt_count == 0:
        penalties["visibility"] = 100 if rd_count > 0 else 0
    else:
        penalties["visibility"] = abs(gt_count - rd_count) / max(gt_count, rd_count) * 100

    # --- Background color ---
    penalties["background"] = color_delta_e(gt["background_color"], rd["background_color"])

    # --- Card-level: normalize positions to image-relative coordinates ---
    # Ground truth and rendered images may have different resolutions
    gt_w, gt_h = gt["image_size"]["w"], gt["image_size"]["h"]
    rd_w, rd_h = rd["image_size"]["w"], rd["image_size"]["h"]

    position_penalties = []
    size_penalties = []
    color_penalties = []

    n_match = min(len(gt["cards"]), len(rd["cards"]))
    for i in range(n_match):
        gc = gt["cards"][i]
        rc = rd["cards"][i]

        # Position: normalize to 0-1 range, then compute distance
        gx, gy = gc["x"] / gt_w, gc["y"] / gt_h
        rx, ry = rc["x"] / rd_w, rc["y"] / rd_h
        pos_dist = math.sqrt((gx - rx) ** 2 + (gy - ry) ** 2)
        position_penalties.append(min(pos_dist * 300, 100))  # scale: 0.33 distance = 100 penalty

        # Size: normalize to fraction of image area
        gt_frac = (gc["w"] * gc["h"]) / (gt_w * gt_h)
        rd_frac = (rc["w"] * rc["h"]) / (rd_w * rd_h)
        if gt_frac > 0:
            size_diff = abs(gt_frac - rd_frac) / gt_frac * 100
            size_penalties.append(min(size_diff, 100))

        # Color
        color_penalties.append(color_delta_e(gc["color"], rc["color"]))

    # For unmatched cards, add max penalty
    unmatched = abs(len(gt["cards"]) - len(rd["cards"]))
    for _ in range(unmatched):
        position_penalties.append(100)
        size_penalties.append(100)
        color_penalties.append(100)

    penalties["position"] = sum(position_penalties) / max(len(position_penalties), 1)
    penalties["size"] = sum(size_penalties) / max(len(size_penalties), 1)
    penalties["color"] = sum(color_penalties) / max(len(color_penalties), 1)

    # --- Weighted score ---
    score = 100 - (
        penalties["position"] * 0.30 +
        penalties["size"] * 0.20 +
        penalties["color"] * 0.30 +
        penalties["background"] * 0.10 +
        penalties["visibility"] * 0.10
    )

    return max(0, min(100, score)), penalties


def main():
    if not GROUND_TRUTH.exists():
        print("ERROR: ground_truth.json not found. Run build_ground_truth.py first.", file=sys.stderr)
        sys.exit(1)

    ground_truth = json.loads(GROUND_TRUTH.read_text())

    frame_scores = []
    all_penalties = []

    for gt_frame in ground_truth["frames"]:
        remotion_frame = gt_frame["remotion_frame"]
        rendered_path = RENDERED_DIR / f"rendered-frame-{remotion_frame}.png"

        if not rendered_path.exists():
            print(f"WARN: Missing {rendered_path}", file=sys.stderr)
            continue

        rendered_props = extract_properties(str(rendered_path))
        score, penalties = score_frame(gt_frame, rendered_props)

        frame_scores.append(score)
        all_penalties.append((gt_frame["phase"], remotion_frame, score, penalties))

        p = penalties
        print(
            f"  {gt_frame['phase']} (f{remotion_frame}): "
            f"score={score:.0f} | pos={p['position']:.0f} size={p['size']:.0f} "
            f"color={p['color']:.0f} bg={p['background']:.0f} vis={p['visibility']:.0f}",
            file=sys.stderr,
        )

    if not frame_scores:
        print("ERROR: No frames scored", file=sys.stderr)
        sys.exit(1)

    aggregate = sum(frame_scores) / len(frame_scores)

    # Find worst penalty
    worst_phase = ""
    worst_name = ""
    worst_val = 0
    for phase, _, _, penalties in all_penalties:
        for name, val in penalties.items():
            if val > worst_val:
                worst_val = val
                worst_name = name
                worst_phase = phase

    print(f"  WORST: {worst_phase} → {worst_name}={worst_val:.0f}", file=sys.stderr)

    # stdout: single number for autoresearch
    print(int(round(aggregate)))


if __name__ == "__main__":
    main()
