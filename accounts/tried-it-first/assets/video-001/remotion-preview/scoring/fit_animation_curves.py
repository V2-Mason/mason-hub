#!/usr/bin/env python3
"""Fit animation curves from all_frames_data.json → animation_params.json

Analyzes 33 frames of extracted data to produce exact Remotion parameters:
- Card positions, sizes, colors over time (keyframes)
- Scene change frame (3→1 card transition)
- Background color
- Visibility ranges

Usage:
    python scoring/fit_animation_curves.py
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
INPUT = SCRIPT_DIR / "all_frames_data.json"
OUTPUT = SCRIPT_DIR / "animation_params.json"


def find_scene_change(frames):
    """Find the exact frame where card count drops from 3 to 1."""
    for i in range(1, len(frames)):
        prev = frames[i - 1]["num_cards"]
        curr = frames[i]["num_cards"]
        if prev == 3 and curr == 1:
            # Transition happens between these two frames
            return {
                "last_3card_frame": frames[i - 1]["remotion_frame"],
                "first_1card_frame": frames[i]["remotion_frame"],
                "transition_frame": (frames[i - 1]["remotion_frame"] + frames[i]["remotion_frame"]) // 2,
            }
    return None


def extract_card_timeline(frames, card_index, max_cards=3):
    """Extract position/size/color keyframes for a specific card (0=left, 1=center, 2=right)."""
    keyframes = []
    for f in frames:
        if f["num_cards"] >= max_cards and card_index < len(f["cards"]):
            card = f["cards"][card_index]
            keyframes.append({
                "frame": f["remotion_frame"],
                "x_norm": card["x_norm"],
                "y_norm": card["y_norm"],
                "w_norm": card["w_norm"],
                "h_norm": card["h_norm"],
                "color": card["color"],
            })
    return keyframes


def extract_single_card_timeline(frames):
    """Extract keyframes for the single focused card (after scene change)."""
    keyframes = []
    for f in frames:
        if f["num_cards"] == 1 and len(f["cards"]) == 1:
            card = f["cards"][0]
            keyframes.append({
                "frame": f["remotion_frame"],
                "x_norm": card["x_norm"],
                "y_norm": card["y_norm"],
                "w_norm": card["w_norm"],
                "h_norm": card["h_norm"],
                "color": card["color"],
            })
    return keyframes


def simplify_keyframes(keyframes, tolerance=0.01):
    """Remove redundant keyframes where values barely change."""
    if len(keyframes) <= 2:
        return keyframes

    result = [keyframes[0]]
    for i in range(1, len(keyframes) - 1):
        prev = result[-1]
        curr = keyframes[i]
        # Check if position or size changed significantly
        dx = abs(curr["x_norm"] - prev["x_norm"])
        dy = abs(curr["y_norm"] - prev["y_norm"])
        dw = abs(curr["w_norm"] - prev["w_norm"])
        dh = abs(curr["h_norm"] - prev["h_norm"])
        color_changed = curr["color"] != prev["color"]

        if dx > tolerance or dy > tolerance or dw > tolerance or dh > tolerance or color_changed:
            result.append(curr)

    result.append(keyframes[-1])
    return result


def average_values(keyframes, key):
    """Get average of a numeric key across keyframes."""
    vals = [kf[key] for kf in keyframes]
    return round(sum(vals) / len(vals), 4) if vals else 0


def main():
    data = json.loads(INPUT.read_text())
    frames = data["frames"]

    # --- Scene change detection ---
    scene_change = find_scene_change(frames)
    print(f"Scene change: {scene_change}", file=sys.stderr)

    # --- Background color (should be constant white) ---
    bg_colors = [f["background_color"] for f in frames]
    # Most common
    from collections import Counter
    bg_color = Counter(bg_colors).most_common(1)[0][0]
    print(f"Background: {bg_color}", file=sys.stderr)

    # --- Three-card phase ---
    three_card_frames = [f for f in frames if f["num_cards"] == 3]
    card_timelines = {}
    for ci in range(3):
        name = ["left", "center", "right"][ci]
        kfs = extract_card_timeline(frames, ci)
        kfs_simplified = simplify_keyframes(kfs)
        card_timelines[name] = kfs_simplified
        print(f"Card {name}: {len(kfs)} raw → {len(kfs_simplified)} keyframes", file=sys.stderr)

        # Summary stats
        avg_x = average_values(kfs, "x_norm")
        avg_y = average_values(kfs, "y_norm")
        avg_w = average_values(kfs, "w_norm")
        avg_h = average_values(kfs, "h_norm")
        print(f"  avg pos=({avg_x}, {avg_y}) size=({avg_w}, {avg_h})", file=sys.stderr)

    # --- Single-card phase ---
    single_kfs = extract_single_card_timeline(frames)
    single_kfs_simplified = simplify_keyframes(single_kfs)
    print(f"Single card: {len(single_kfs)} raw → {len(single_kfs_simplified)} keyframes", file=sys.stderr)

    # --- Build output ---
    params = {
        "metadata": {
            "source_frames": data["total_ref_frames"],
            "remotion_fps": data["remotion_fps"],
            "remotion_duration": data["remotion_duration_frames"],
        },
        "background_color": bg_color,
        "scene_change": scene_change,
        "three_card_phase": {
            "frame_range": [0, scene_change["transition_frame"]],
            "cards": card_timelines,
        },
        "single_card_phase": {
            "frame_range": [scene_change["transition_frame"], data["remotion_duration_frames"]],
            "keyframes": single_kfs_simplified,
        },
    }

    OUTPUT.write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(f"\nAnimation params saved to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
