#!/usr/bin/env python3
"""Send both videos to Gemini for granular parameter-level comparison."""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REF_VIDEO = Path("C:/Users/hangn/projects/mason-hub/accounts/surenxuan/content/anua-promo/source/reference-video/ref-correct-10s.mp4")
OUR_VIDEO = Path("C:/Users/hangn/projects/mason-hub/accounts/surenxuan/content/anua-promo/output/v7-full.mp4")
OUTPUT = SCRIPT_DIR / "video_comparison_detailed.md"

PROMPT = """You are a motion graphics engineer reverse-engineering an After Effects template.

Video 1 = Original AE template (10-second clip, sneakers promo)
Video 2 = Code replica (skincare products) built with Remotion (React)

CRITICAL CONTEXT about the replica's code structure:
- The replica uses Remotion (React) at 30fps, total 300 frames (10 seconds).
- It has a SINGLE mode: three cards side by side throughout the entire video.
- Timeline: Logo(0-28) → Cards spring in(30-48, mass=0.7/damping=20/stiffness=100) → Shadow fade(48-58) → Content Set 1 spring in(60-75) → Static(75-210) → 6-frame white flash(210-216, peak=213) + card scale pulse 1→0.98→1 + old content slides out with rotate(210-213) + new content slides in with rotate(213-225) → Static(225-285) → Exit(285-300) + logo fade back
- Features: spring entry with overshoot (mass=0.7/damping=12/stiffness=170), 15-frame white flash ease-in-out (205-220, peak=213, NO card pulse), old content slides UP(-100px)+rotates(-20deg) with fast ease-in exit, new content slides DOWN(+100px→0)+rotates(+20deg→0) with decelerating ease-out entry, middle card bg instant-switch to black at flash peak, delayed price tags (15 frames after content, with spring bounce), diffused dual-layer shadows, hand-drawn SVG arrow stroke-dashoffset, NEW labels with staggered scale pop, WaveFrame border draw, right card image grid with gaps+borders + geometric grid bg, Montserrat font, borderRadius=18px, product spring entry with rotation, products static once settled

TASK:
1. First, describe the STRUCTURE of the original 10s clip scene-by-scene:
   - How many cards are visible at each moment?
   - When do cards enter/exit?
   - Does the original ever show a SINGLE card, or is it always 3 cards?
   - What is the exact timeline of scenes?

2. Then, for EVERY animation difference you find, output this format:

---
DIFFERENCE #N: [short name]
TIMESTAMP_ORIGINAL: [start_s]-[end_s]
TIMESTAMP_REPLICA: [start_s]-[end_s]
SEVERITY: [critical/major/minor]
WHAT_ORIGINAL_DOES: [precise description]
WHAT_REPLICA_DOES: [precise description]
REMOTION_FIX:
  - component: [Card3/Card1/Deco/PriceTag/etc]
    property: [CSS/Remotion property or code constant]
    current_value: [exact current value in code]
    target_value: [what it should be — give exact number]
    easing: [linear/ease-out/cubic-bezier(a,b,c,d)/spring(mass,damping,stiffness)]
    frame_range: [start_frame-end_frame at 30fps]
---

Be extremely specific — I will directly translate your output into code:
- Positions as fraction of screen (0.0 to 1.0)
- Durations in frames (at 30fps)
- Colors as hex (#RRGGBB)
- Scale as decimal (1.0 = 100%)
- Rotation in degrees
- Easing as cubic-bezier or spring parameters

3. At the end, provide:

STRUCTURAL ISSUES (things fundamentally wrong with the code architecture):
- e.g., "single-card mode should not exist" or "scene transition timing is wrong"

TOP 5 PARAMETER FIXES (ranked by visual impact, with exact values)

OVERALL SCORE (0-100):
- Layout fidelity (card count, positions, sizes): /25
- Color & visual fidelity (backgrounds, card colors, gradients): /25
- Motion & timing (easing, duration, keyframes, transitions): /25
- Effects & polish (decorations, text, overlays): /25
- Total: /100
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
    sys.stdout.buffer.write(response.text.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    print(f"\nSaved to {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
