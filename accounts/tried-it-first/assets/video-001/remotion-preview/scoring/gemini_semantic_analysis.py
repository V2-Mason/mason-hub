#!/usr/bin/env python3
"""Gemini semantic analysis of reference frames.

For each frame, Gemini identifies:
- Card internal layout type (single product, grid, plain color)
- Decoration types (stripes, waves, dots, pattern)
- Text elements and their approximate positions
- Scene description
- Content changes between frames

Usage:
    python scoring/gemini_semantic_analysis.py
    → outputs scoring/semantic_analysis.json
"""
import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REF_DIR = Path("C:/Users/hangn/projects/mason-hub/accounts/surenxuan/content/anua-promo/source/original-frames")
OUTPUT = SCRIPT_DIR / "semantic_analysis.json"

PROMPT = """Analyze this video frame precisely. This is from an e-commerce promo video with card-style layouts.

For each visible card, describe:
1. background_type: "solid_color" | "gradient" | "pattern" | "image_collage"
2. background_color_name: simple color name (e.g. "blue", "dark_red", "peach", "white")
3. decoration_type: "none" | "diagonal_stripes" | "wavy_pattern" | "dot_grid" | "chevron" | "mixed"
4. decoration_color: color of decoration elements
5. layout_type: "single_product_center" | "product_with_text" | "grid_2x2" | "full_bleed" | "plain_no_content"
6. has_price_tag: true/false
7. price_tag_position: "top_right" | "top_left" | "bottom_right" | null
8. has_cta: true/false (like "Swipe Up", "Buy Now")
9. text_blocks: list of {"text_hint": "...", "position": "top/center/bottom", "size": "large/medium/small"}

Also describe the overall scene:
- scene_type: "three_cards_side_by_side" | "single_card_centered" | "transition" | "blank"
- background_color: overall background color name
- notable_effects: any glow, shadow, particle effects visible

Return ONLY valid JSON:
{
  "scene_type": "<type>",
  "background_color": "<color>",
  "notable_effects": "<description or none>",
  "num_cards": <int>,
  "cards": [
    {
      "position": "left|center|right|single",
      "background_type": "<type>",
      "background_color_name": "<color>",
      "decoration_type": "<type>",
      "decoration_color": "<color or none>",
      "layout_type": "<type>",
      "has_price_tag": <bool>,
      "price_tag_position": "<position or null>",
      "has_cta": <bool>,
      "text_blocks": [{"text_hint": "...", "position": "...", "size": "..."}]
    }
  ]
}
"""


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for parent in [SCRIPT_DIR] + list(SCRIPT_DIR.parents):
        env_file = parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def analyze_frame(client, types, image_path):
    """Send one frame to Gemini for semantic analysis."""
    img_bytes = Path(image_path).read_bytes()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Try to extract JSON
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: No GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    frames = sorted(REF_DIR.glob("correct-frame-*.jpg"))

    results = {"frames": []}

    for i, ref_path in enumerate(frames):
        ref_num = i + 1
        remotion_frame = round(i * (270 / 33))
        print(f"  [{ref_num:02d}/33] Gemini analyzing {ref_path.name}...", file=sys.stderr, end="", flush=True)

        try:
            analysis = analyze_frame(client, types, ref_path)
            results["frames"].append({
                "ref_frame": ref_num,
                "remotion_frame": remotion_frame,
                "ref_file": ref_path.name,
                "semantic": analysis,
            })
            print(f" {analysis.get('scene_type', '?')} / {analysis.get('num_cards', '?')} cards", file=sys.stderr)
        except Exception as e:
            print(f" ERROR: {e}", file=sys.stderr)
            results["frames"].append({
                "ref_frame": ref_num,
                "remotion_frame": remotion_frame,
                "ref_file": ref_path.name,
                "error": str(e),
            })

        # Rate limit: ~2 req/sec for flash
        time.sleep(0.5)

    OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSemantic analysis saved: {len(results['frames'])} frames → {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
