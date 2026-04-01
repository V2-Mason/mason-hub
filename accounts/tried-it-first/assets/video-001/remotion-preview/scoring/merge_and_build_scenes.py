#!/usr/bin/env python3
"""Merge semantic analysis + OpenCV measurements → scene timeline + rich params.

Identifies distinct visual "scenes" (content states) and their frame ranges.
Outputs rich_params.json with everything needed to drive Remotion.

Usage:
    python scoring/merge_and_build_scenes.py
"""
import json
import sys
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent
SEMANTIC = SCRIPT_DIR / "semantic_analysis.json"
OPENCV = SCRIPT_DIR / "all_frames_data.json"
OUTPUT = SCRIPT_DIR / "rich_params.json"


def detect_scenes(frames):
    """Group frames into scenes based on semantic changes."""
    scenes = []
    current_scene = None

    for f in frames:
        sem = f.get("semantic", {})
        cv = f.get("opencv", {})

        # Scene signature = (scene_type, num_cards, left_card_layout, left_card_bg)
        cards = sem.get("cards", [])
        first_card_layout = cards[0].get("layout_type", "?") if cards else "none"
        first_card_bg = cards[0].get("background_color_name", "?") if cards else "none"
        first_card_deco = cards[0].get("decoration_type", "none") if cards else "none"

        sig = (
            sem.get("scene_type", "?"),
            sem.get("num_cards", 0),
            first_card_layout,
            first_card_deco,
        )

        if current_scene is None or sig != current_scene["signature"]:
            # New scene
            if current_scene:
                current_scene["end_frame"] = prev_frame
                scenes.append(current_scene)

            current_scene = {
                "signature": sig,
                "start_frame": f["remotion_frame"],
                "end_frame": f["remotion_frame"],
                "scene_type": sem.get("scene_type", "?"),
                "num_cards": sem.get("num_cards", 0),
                "semantic_samples": [sem],
                "opencv_samples": [cv] if cv else [],
                "ref_frames": [f["ref_frame"]],
            }
        else:
            current_scene["end_frame"] = f["remotion_frame"]
            current_scene["semantic_samples"].append(sem)
            if cv:
                current_scene["opencv_samples"].append(cv)
            current_scene["ref_frames"].append(f["ref_frame"])

        prev_frame = f["remotion_frame"]

    if current_scene:
        current_scene["end_frame"] = prev_frame
        scenes.append(current_scene)

    return scenes


def summarize_scene(scene, index):
    """Create a clean summary of a scene for the output."""
    sem_samples = scene["semantic_samples"]
    cv_samples = scene["opencv_samples"]

    # Get card info from first semantic sample
    first_sem = sem_samples[0]
    cards_info = []
    for card in first_sem.get("cards", []):
        cards_info.append({
            "position": card.get("position", "?"),
            "background_type": card.get("background_type", "?"),
            "background_color_name": card.get("background_color_name", "?"),
            "decoration_type": card.get("decoration_type", "none"),
            "decoration_color": card.get("decoration_color", "none"),
            "layout_type": card.get("layout_type", "?"),
            "has_price_tag": card.get("has_price_tag", False),
            "price_tag_position": card.get("price_tag_position"),
            "has_cta": card.get("has_cta", False),
            "text_blocks": card.get("text_blocks", []),
        })

    # Get OpenCV measurements (average across scene)
    opencv_cards = []
    if cv_samples:
        # Use first sample's card data for layout
        first_cv = cv_samples[0]
        for card in first_cv.get("cards", []):
            opencv_cards.append({
                "x_norm": card.get("x_norm", 0),
                "y_norm": card.get("y_norm", 0),
                "w_norm": card.get("w_norm", 0),
                "h_norm": card.get("h_norm", 0),
                "color": card.get("color", "#000000"),
            })

    # Color keyframes from OpenCV across the scene
    color_keyframes = []
    for cv in cv_samples:
        frame_colors = []
        for card in cv.get("cards", []):
            frame_colors.append(card.get("color", "#000000"))
        if frame_colors:
            # Find the remotion frame for this cv sample
            idx = cv_samples.index(cv)
            if idx < len(scene["ref_frames"]):
                rf = scene["ref_frames"][idx]
                remotion_f = round((rf - 1) * (270 / 33))
                color_keyframes.append({
                    "frame": remotion_f,
                    "colors": frame_colors,
                    "background": cv.get("background_color", "#ffffff"),
                })

    return {
        "scene_index": index,
        "start_frame": scene["start_frame"],
        "end_frame": scene["end_frame"],
        "duration_frames": scene["end_frame"] - scene["start_frame"],
        "scene_type": scene["scene_type"],
        "num_cards": scene["num_cards"],
        "cards_semantic": cards_info,
        "cards_opencv": opencv_cards,
        "color_keyframes": color_keyframes,
        "notable_effects": first_sem.get("notable_effects", "none"),
    }


def main():
    semantic = json.loads(SEMANTIC.read_text())
    opencv = json.loads(OPENCV.read_text())

    # Merge by ref_frame number
    merged = []
    opencv_by_ref = {f["ref_frame"]: f for f in opencv["frames"]}

    for sf in semantic["frames"]:
        ref_num = sf["ref_frame"]
        cv_data = opencv_by_ref.get(ref_num, {})

        merged.append({
            "ref_frame": ref_num,
            "remotion_frame": sf["remotion_frame"],
            "semantic": sf.get("semantic", {}),
            "opencv": cv_data,
        })

    # Detect scenes
    scenes = detect_scenes(merged)
    print(f"Detected {len(scenes)} distinct scenes:", file=sys.stderr)

    scene_summaries = []
    for i, scene in enumerate(scenes):
        summary = summarize_scene(scene, i)
        scene_summaries.append(summary)
        print(
            f"  Scene {i}: f{summary['start_frame']}-f{summary['end_frame']} "
            f"({summary['duration_frames']}f) | {summary['scene_type']} | "
            f"{summary['num_cards']} cards | "
            f"{summary['cards_semantic'][0]['layout_type'] if summary['cards_semantic'] else '?'} / "
            f"{summary['cards_semantic'][0]['decoration_type'] if summary['cards_semantic'] else '?'}",
            file=sys.stderr,
        )

    # Build output
    output = {
        "metadata": {
            "total_scenes": len(scene_summaries),
            "remotion_fps": 30,
            "remotion_duration": 270,
            "transition_frame": None,
        },
        "background_color": "#ffffff",
        "scenes": scene_summaries,
    }

    # Find the 3-card → 1-card transition
    for i, s in enumerate(scene_summaries):
        if i > 0 and scene_summaries[i - 1]["num_cards"] == 3 and s["num_cards"] <= 1:
            output["metadata"]["transition_frame"] = s["start_frame"]
            break

    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nRich params saved to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
