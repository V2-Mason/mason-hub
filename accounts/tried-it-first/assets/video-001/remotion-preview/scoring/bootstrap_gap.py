#!/usr/bin/env python3
"""One-time gap analysis: describe differences between rendered and reference frames.

Usage:
    python scoring/bootstrap_gap.py
    # Outputs detailed gap analysis to scoring/bootstrap_gap.md
"""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FRAME_MAP = SCRIPT_DIR / "frame_map.json"
RENDERED_DIR = SCRIPT_DIR / "rendered-frames"

GAP_PROMPT = """You are an expert motion designer analyzing how a code-based recreation differs from an original After Effects video.

The RENDERED frames are from Remotion (React/CSS). The REFERENCE frames are from a professional AE template.
The CONTENT is intentionally different (skincare products vs sneakers) — focus on STYLE, MOTION, and DESIGN differences.

For each frame pair, describe:
1. **Layout gaps**: Card sizes, positions, spacing, aspect ratios
2. **Color gaps**: Background color, card colors, accent elements, overall mood
3. **Typography gaps**: Font choices, sizes, weights, text layout
4. **Decoration gaps**: Stripes, dots, patterns, borders, circles behind products
5. **Effect gaps**: Shadows, glows, gradients, overlays
6. **Animation state gaps**: What stage should the animation be at? Is it correct?

Then provide:
- **Overall gap severity** (1-10, where 10 = completely different)
- **Top 3 parameters to change** in the Remotion code (be specific: "increase card width from 320 to 360px")

Output as markdown, organized by phase.
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


def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: No GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("ERROR: pip install google-genai", file=sys.stderr)
        sys.exit(1)

    frame_map = json.loads(FRAME_MAP.read_text())
    ref_dir = (SCRIPT_DIR / frame_map["reference_dir"]).resolve()

    contents = []
    for pair in frame_map["pairs"]:
        rendered = RENDERED_DIR / f"rendered-frame-{pair['remotion_frame']}.png"
        reference = ref_dir / pair["reference"]
        if not rendered.exists() or not reference.exists():
            continue
        contents.append(f"\n--- Phase: {pair['phase']} (frame {pair['remotion_frame']}) ---\nRENDERED:")
        contents.append(types.Part.from_bytes(data=rendered.read_bytes(), mime_type="image/png"))
        contents.append("REFERENCE:")
        contents.append(types.Part.from_bytes(data=reference.read_bytes(), mime_type="image/jpeg"))

    contents.append(GAP_PROMPT)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
    )

    output = SCRIPT_DIR / "bootstrap_gap.md"
    output.write_text(response.text, encoding="utf-8")
    print(f"Gap analysis saved to {output}")


if __name__ == "__main__":
    main()
