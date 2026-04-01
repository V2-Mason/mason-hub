#!/usr/bin/env python3
"""Send both videos to Gemini for granular parameter-level comparison."""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REF_VIDEO = Path("C:/Users/hangn/projects/mason-hub/accounts/surenxuan/content/anua-promo/source/reference-video/ref-correct-10s.mp4")
OUR_VIDEO = SCRIPT_DIR.parent / "output" / "anua-promo-final.mp4"
OUTPUT = SCRIPT_DIR / "video_comparison_detailed.md"

PROMPT = """You are a motion graphics engineer reverse-engineering an After Effects template.

Video 1 = Original AE template (sneakers)
Video 2 = Code replica (skincare products) built with Remotion (React)

Ignore product content differences. Focus ONLY on motion/animation/effects.

For EVERY animation difference you find, output this EXACT format:

---
DIFFERENCE #N: [short name]
TIMESTAMP_ORIGINAL: [start_ms]-[end_ms]
TIMESTAMP_REPLICA: [start_ms]-[end_ms]
WHAT_ORIGINAL_DOES: [precise description with pixel estimates]
WHAT_REPLICA_DOES: [precise description]
PARAMETERS_TO_CHANGE:
  - property: [CSS/Remotion property name]
    current_value: [what replica uses]
    target_value: [what it should be]
    easing: [linear/ease-in/ease-out/ease-in-out/spring or cubic-bezier]
    duration_ms: [how long the animation takes]
  - property: ...
---

Be extremely specific:
- Positions in percentage of screen width/height
- Durations in milliseconds
- Easing curves with specific parameters
- Scale values with overshoot if present
- Opacity values
- Colors as hex
- Rotation in degrees
- Background pattern types and sizes

List ALL differences, minimum 10. Order by timestamp.
At the end, provide the TOP 5 fixes ranked by visual impact.
"""


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        for parent in [SCRIPT_DIR] + list(SCRIPT_DIR.parents):
            env_file = parent / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    print("Uploading videos to Gemini...", file=sys.stderr)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=REF_VIDEO.read_bytes(), mime_type="video/mp4"),
            "VIDEO 1 (original AE template)",
            types.Part.from_bytes(data=OUR_VIDEO.read_bytes(), mime_type="video/mp4"),
            "VIDEO 2 (code replica)",
            PROMPT,
        ],
    )

    OUTPUT.write_text(response.text, encoding="utf-8")
    print(response.text)
    print(f"\nSaved to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
