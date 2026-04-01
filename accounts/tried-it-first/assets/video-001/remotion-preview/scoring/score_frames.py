#!/usr/bin/env python3
"""Score Remotion rendered frames against reference frames using Gemini Vision.

Usage:
    python scoring/score_frames.py
    # Outputs a single number 0-100 to stdout (for autoresearch Verify)
"""
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FRAME_MAP = SCRIPT_DIR / "frame_map.json"
RENDERED_DIR = SCRIPT_DIR / "rendered-frames"

SCORING_PROMPT = """You are a visual similarity judge comparing animation frames.
The RENDERED frames are from a Remotion (code-based) recreation of the REFERENCE video.
The content/products are different (skincare vs sneakers) — focus on STYLE matching, not content.

For each pair, score these dimensions:
- layout_match (0-100): Card positions, sizes, spacing, overall 3-card composition
- color_match (0-100): Background tones, card background colors, accent colors, overall palette mood
- timing_match (0-100): Animation state — are elements at the right stage? (entered/floating/transitioning/fading)
- effects_match (0-100): Glow, shadows, decorative elements (stripes/dots), visual polish level
- overall_feel (0-100): Would a viewer perceive similar energy/rhythm/style?

Return ONLY valid JSON:
{
  "frame_scores": [
    {
      "phase": "<phase name>",
      "layout_match": <int>,
      "color_match": <int>,
      "timing_match": <int>,
      "effects_match": <int>,
      "overall_feel": <int>,
      "suggestion": "<one-line improvement suggestion for this phase>"
    }
  ],
  "aggregate_score": <int 0-100>,
  "top_priority": "<single most impactful thing to fix next>"
}

Aggregate weights: layout(30%) + color(20%) + timing(25%) + effects(10%) + feel(15%).
Be strict. 50 = roughly similar layout. 80+ = very close. 95+ = nearly identical.
"""


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    # Walk up to find .env
    for parent in [SCRIPT_DIR] + list(SCRIPT_DIR.parents):
        env_file = parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def parse_json_robust(text):
    """Extract JSON from Gemini response (handles markdown fences, trailing commas)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find outermost {}
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                block = text[start : i + 1]
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    fixed = re.sub(r",\s*([}\]])", r"\1", block)
                    return json.loads(fixed)
    raise ValueError("No valid JSON found in Gemini response")


def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: No GEMINI_API_KEY found", file=sys.stderr)
        sys.exit(1)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("ERROR: google-genai not installed. Run: pip install google-genai", file=sys.stderr)
        sys.exit(1)

    frame_map = json.loads(FRAME_MAP.read_text())
    ref_dir = (SCRIPT_DIR / frame_map["reference_dir"]).resolve()

    # Build image pairs
    contents = []
    pair_count = 0
    for pair in frame_map["pairs"]:
        rendered = RENDERED_DIR / f"rendered-frame-{pair['remotion_frame']}.png"
        reference = ref_dir / pair["reference"]
        if not rendered.exists():
            print(f"WARN: Missing rendered: {rendered}", file=sys.stderr)
            continue
        if not reference.exists():
            print(f"WARN: Missing reference: {reference}", file=sys.stderr)
            continue

        contents.append(f"\n--- Phase: {pair['phase']} (frame {pair['remotion_frame']}) ---\nRENDERED:")
        contents.append(
            types.Part.from_bytes(data=rendered.read_bytes(), mime_type="image/png")
        )
        contents.append("REFERENCE:")
        contents.append(
            types.Part.from_bytes(data=reference.read_bytes(), mime_type="image/jpeg")
        )
        pair_count += 1

    if pair_count == 0:
        print("ERROR: No valid frame pairs", file=sys.stderr)
        sys.exit(1)

    contents.append(SCORING_PROMPT)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    result = parse_json_robust(response.text)
    score = result.get("aggregate_score", 0)

    # stdout: only the score (for autoresearch Verify)
    print(score)

    # stderr: details
    for fs in result.get("frame_scores", []):
        print(
            f"  {fs['phase']}: L={fs.get('layout_match',0)} C={fs.get('color_match',0)} "
            f"T={fs.get('timing_match',0)} E={fs.get('effects_match',0)} F={fs.get('overall_feel',0)} "
            f"| {fs.get('suggestion','')}",
            file=sys.stderr,
        )
    print(f"  TOP PRIORITY: {result.get('top_priority', 'N/A')}", file=sys.stderr)


if __name__ == "__main__":
    main()
