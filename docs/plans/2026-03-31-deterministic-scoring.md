# Deterministic Scoring System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Gemini subjective scoring with OpenCV property extraction + numerical comparison for zero-variance scoring.

**Architecture:** Gemini does one-time element detection on reference frames → OpenCV precisely measures 5 properties per frame → Python compares rendered vs reference numerically → outputs deterministic 0-100 score.

**Tech Stack:** Python, opencv-python, numpy, google-genai (existing), Remotion CLI

**Spec:** `docs/superpowers/specs/2026-03-31-deterministic-scoring-design.md`

---

### Task 1: Install Dependencies

**Step 1: Install opencv-python and scikit-learn**

Run:
```bash
pip install opencv-python scikit-learn
```
Expected: Both packages install successfully.

**Step 2: Verify installation**

Run:
```bash
python -c "import cv2; print(cv2.__version__); import sklearn; print(sklearn.__version__)"
```
Expected: Version numbers printed, no errors.

**Step 3: Commit**

No commit needed — pip packages are not tracked in git.

---

### Task 2: Create extract_properties.py — OpenCV Property Extractor

**Files:**
- Create: `accounts/tried-it-first/assets/video-001/remotion-preview/scoring/extract_properties.py`

This is the core module. Given an image, it detects cards and extracts 5 properties.

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Extract visual properties from a frame using OpenCV.

Given an image, detects card-like rectangles and measures:
- Card positions (bounding box center x, y)
- Card sizes (width, height)
- Card dominant colors (K-means)
- Background color (corner sampling)
- Card visibility (detected or not)

Usage:
    python extract_properties.py <image_path>
    # Outputs JSON to stdout
"""
import json
import sys
import numpy as np
import cv2
from pathlib import Path


def sample_background_color(img):
    """Sample background color from image corners (10% inset)."""
    h, w = img.shape[:2]
    margin_x, margin_y = int(w * 0.05), int(h * 0.05)
    corners = [
        img[margin_y, margin_x],                    # top-left
        img[margin_y, w - margin_x - 1],            # top-right
        img[h - margin_y - 1, margin_x],            # bottom-left
        img[h - margin_y - 1, w - margin_x - 1],    # bottom-right
    ]
    avg = np.mean(corners, axis=0).astype(int)
    # BGR to hex
    return "#{:02x}{:02x}{:02x}".format(int(avg[2]), int(avg[1]), int(avg[0]))


def dominant_color(img_region, k=1):
    """Extract dominant color from a region using K-means."""
    pixels = img_region.reshape(-1, 3).astype(np.float32)
    if len(pixels) < k:
        return "#000000"
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    # Pick the cluster with most pixels
    counts = np.bincount(labels.flatten())
    dominant = centers[np.argmax(counts)].astype(int)
    return "#{:02x}{:02x}{:02x}".format(int(dominant[2]), int(dominant[1]), int(dominant[0]))


def detect_cards(img, min_area_ratio=0.02, max_area_ratio=0.5):
    """Detect card-like rectangles in the image.

    Returns list of dicts with bounding box info, sorted left-to-right.
    """
    h, w = img.shape[:2]
    total_area = h * w
    min_area = total_area * min_area_ratio
    max_area = total_area * max_area_ratio

    # Convert to grayscale and find edges
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold to handle varying backgrounds
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3
    )

    # Also try Canny edges for better detection
    edges = cv2.Canny(blurred, 30, 100)
    combined = cv2.bitwise_or(thresh, edges)

    # Dilate to connect nearby edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(combined, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cards = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        # Get bounding rectangle
        x, y, cw, ch = cv2.boundingRect(contour)

        # Filter by aspect ratio (cards are tall rectangles, roughly 1:1.5 to 1:2.5)
        aspect = ch / cw if cw > 0 else 0
        if aspect < 1.0 or aspect > 3.5:
            continue

        # Extract the card region for color analysis
        card_region = img[y:y+ch, x:x+cw]
        # Sample interior (skip border)
        inner_margin = max(int(min(cw, ch) * 0.15), 5)
        inner = card_region[inner_margin:-inner_margin, inner_margin:-inner_margin]
        if inner.size == 0:
            inner = card_region
        color = dominant_color(inner)

        cards.append({
            "x": int(x + cw // 2),  # center x
            "y": int(y + ch // 2),  # center y
            "w": int(cw),
            "h": int(ch),
            "color": color,
        })

    # Sort left to right
    cards.sort(key=lambda c: c["x"])
    return cards


def extract_properties(image_path):
    """Extract all properties from a single frame."""
    img = cv2.imread(str(image_path))
    if img is None:
        return {"error": f"Cannot read {image_path}"}

    h, w = img.shape[:2]
    bg_color = sample_background_color(img)
    cards = detect_cards(img)

    return {
        "image_size": {"w": w, "h": h},
        "background_color": bg_color,
        "num_cards": len(cards),
        "cards": cards,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_properties.py <image_path>", file=sys.stderr)
        sys.exit(1)
    result = extract_properties(sys.argv[1])
    print(json.dumps(result, indent=2))
```

**Step 2: Test on a reference frame**

Run:
```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
python scoring/extract_properties.py "C:/Users/hangn/projects/mason-hub/accounts/surenxuan/content/anua-promo/source/original-frames/correct-frame-04.jpg"
```
Expected: JSON with `num_cards: 3`, three card entries with positions, a background color hex.

**Step 3: Test on a rendered frame**

Run:
```bash
python scoring/extract_properties.py scoring/rendered-frames/rendered-frame-30.png
```
Expected: JSON with similar structure, cards detected.

**Step 4: Debug and adjust detection if needed**

If cards aren't detected, tune `min_area_ratio`, `adaptive threshold` params, or `aspect ratio` filter. Run on multiple frames to verify consistency.

**Step 5: Commit**

```bash
git add accounts/tried-it-first/assets/video-001/remotion-preview/scoring/extract_properties.py
git commit -m "feat(scoring): add OpenCV property extractor — card detection + color + position"
```

---

### Task 3: Create build_ground_truth.py — Reference Baseline Builder

**Files:**
- Create: `accounts/tried-it-first/assets/video-001/remotion-preview/scoring/build_ground_truth.py`

Runs Gemini once for coarse element detection, then OpenCV for precise measurement. Outputs ground_truth.json.

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Build ground truth from reference frames.

Phase 1: Gemini analyzes reference frames → coarse element regions
Phase 2: OpenCV precisely measures each frame → ground_truth.json

Usage:
    python scoring/build_ground_truth.py
"""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FRAME_MAP = SCRIPT_DIR / "frame_map.json"
OUTPUT = SCRIPT_DIR / "ground_truth.json"

# Import the shared extractor
sys.path.insert(0, str(SCRIPT_DIR))
from extract_properties import extract_properties


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


GEMINI_PROMPT = """Analyze this video frame. Identify all card-like rectangular UI elements.

For each card, provide:
- approximate_region: {"x_min": int, "y_min": int, "x_max": int, "y_max": int} in pixels
- color_description: one word (e.g. "blue", "black", "white", "coral")
- content_description: what's on the card in 5 words or less

Return ONLY valid JSON:
{
  "frame_description": "<one line>",
  "num_cards": <int>,
  "cards": [
    {
      "approximate_region": {"x_min": 0, "y_min": 0, "x_max": 0, "y_max": 0},
      "color_description": "<color>",
      "content_description": "<brief>"
    }
  ]
}
"""


def gemini_coarse_detect(image_path, api_key):
    """Use Gemini to get coarse element regions (one-time)."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("WARN: google-genai not installed, skipping Gemini step", file=sys.stderr)
        return None

    client = genai.Client(api_key=api_key)
    img_bytes = Path(image_path).read_bytes()
    mime = "image/jpeg" if str(image_path).endswith(".jpg") else "image/png"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=img_bytes, mime_type=mime),
            GEMINI_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        print(f"WARN: Gemini JSON parse failed for {image_path}", file=sys.stderr)
        return None


def main():
    api_key = load_api_key()
    frame_map = json.loads(FRAME_MAP.read_text())
    ref_dir = Path(frame_map["reference_dir"])

    ground_truth = {"frames": []}

    for pair in frame_map["pairs"]:
        ref_path = ref_dir / pair["reference"]
        if not ref_path.exists():
            print(f"SKIP: {ref_path} not found", file=sys.stderr)
            continue

        print(f"Processing {pair['phase']} (frame {pair['remotion_frame']})...", file=sys.stderr)

        # Phase 1: Gemini coarse detection (optional enrichment)
        gemini_data = None
        if api_key:
            gemini_data = gemini_coarse_detect(ref_path, api_key)

        # Phase 2: OpenCV precise measurement
        opencv_data = extract_properties(str(ref_path))

        frame_entry = {
            "remotion_frame": pair["remotion_frame"],
            "reference": pair["reference"],
            "phase": pair["phase"],
            "opencv": opencv_data,
        }
        if gemini_data:
            frame_entry["gemini_hints"] = gemini_data

        ground_truth["frames"].append(frame_entry)

    OUTPUT.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print(f"Ground truth saved to {OUTPUT} ({len(ground_truth['frames'])} frames)", file=sys.stderr)


if __name__ == "__main__":
    main()
```

**Step 2: Run it**

Run:
```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
python scoring/build_ground_truth.py
```
Expected: Processes 7 frames, creates `scoring/ground_truth.json` with OpenCV measurements + Gemini hints.

**Step 3: Inspect ground_truth.json**

Run:
```bash
python -c "import json; d=json.load(open('scoring/ground_truth.json')); print(json.dumps(d['frames'][2], indent=2))"
```
Expected: Frame entry with `opencv.num_cards: 3`, card positions, colors, background color.

**Step 4: Commit**

```bash
git add scoring/build_ground_truth.py scoring/ground_truth.json
git commit -m "feat(scoring): build ground truth — Gemini coarse + OpenCV precise measurement"
```

---

### Task 4: Rewrite score_frames.py — Deterministic Scorer

**Files:**
- Rewrite: `accounts/tried-it-first/assets/video-001/remotion-preview/scoring/score_frames.py`

Replace Gemini scoring with OpenCV property comparison against ground_truth.json.

**Step 1: Rewrite the script**

```python
#!/usr/bin/env python3
"""Score rendered frames against ground truth using deterministic property comparison.

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
    """Convert #rrggbb to (r, g, b)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def color_delta_e(hex1, hex2):
    """Simple Euclidean RGB distance (0-441 range), normalized to 0-100."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    dist = math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
    # Max possible distance is sqrt(255^2 * 3) ≈ 441
    return min(dist / 441 * 100, 100)


def score_frame(gt_frame, rendered_props):
    """Score a single rendered frame against ground truth. Returns 0-100."""
    gt = gt_frame["opencv"]
    rd = rendered_props

    penalties = {}

    # --- Visibility penalty (0 or 100) ---
    gt_count = gt["num_cards"]
    rd_count = rd["num_cards"]
    if gt_count == 0 and rd_count == 0:
        visibility_penalty = 0
    elif gt_count == 0:
        visibility_penalty = 100 if rd_count > 0 else 0
    else:
        visibility_penalty = abs(gt_count - rd_count) / max(gt_count, rd_count) * 100
    penalties["visibility"] = visibility_penalty

    # --- Background color penalty ---
    bg_penalty = color_delta_e(gt["background_color"], rd["background_color"])
    penalties["background"] = bg_penalty

    # --- Card-level penalties (average across matched cards) ---
    position_penalties = []
    size_penalties = []
    color_penalties = []

    img_w = gt["image_size"]["w"]
    img_h = gt["image_size"]["h"]
    img_diag = math.sqrt(img_w ** 2 + img_h ** 2)

    # Match cards by position (left-to-right ordering)
    n_match = min(len(gt["cards"]), len(rd["cards"]))
    for i in range(n_match):
        gc = gt["cards"][i]
        rc = rd["cards"][i]

        # Position: distance as % of image diagonal
        pos_dist = math.sqrt((gc["x"] - rc["x"]) ** 2 + (gc["y"] - rc["y"]) ** 2)
        pos_penalty = min(pos_dist / img_diag * 100 * 3, 100)  # scale up, cap at 100
        position_penalties.append(pos_penalty)

        # Size: percentage difference
        gt_area = gc["w"] * gc["h"]
        rd_area = rc["w"] * rc["h"]
        if gt_area > 0:
            size_diff = abs(gt_area - rd_area) / gt_area * 100
            size_penalties.append(min(size_diff, 100))

        # Color
        color_penalties.append(color_delta_e(gc["color"], rc["color"]))

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
    frame_map = json.loads(FRAME_MAP.read_text())

    frame_scores = []
    all_penalties = []

    for gt_frame in ground_truth["frames"]:
        remotion_frame = gt_frame["remotion_frame"]
        rendered_path = RENDERED_DIR / f"rendered-frame-{remotion_frame}.png"

        if not rendered_path.exists():
            print(f"WARN: Missing rendered frame {rendered_path}", file=sys.stderr)
            continue

        rendered_props = extract_properties(str(rendered_path))
        score, penalties = score_frame(gt_frame, rendered_props)

        frame_scores.append(score)
        all_penalties.append((gt_frame["phase"], score, penalties))

        # stderr: per-frame details
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

    # Find worst penalty across all frames
    worst_phase = ""
    worst_penalty_name = ""
    worst_penalty_val = 0
    for phase, _, penalties in all_penalties:
        for name, val in penalties.items():
            if val > worst_penalty_val:
                worst_penalty_val = val
                worst_penalty_name = name
                worst_phase = phase

    print(
        f"  WORST: {worst_phase} → {worst_penalty_name}={worst_penalty_val:.0f}",
        file=sys.stderr,
    )

    # stdout: single number for autoresearch
    print(int(round(aggregate)))


if __name__ == "__main__":
    main()
```

**Step 2: Run the new scorer**

Run:
```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
python scoring/score_frames.py
```
Expected: A deterministic score 0-100 on stdout. Per-frame breakdown on stderr.

**Step 3: Run it twice to verify zero variance**

Run:
```bash
python scoring/score_frames.py 2>/dev/null && python scoring/score_frames.py 2>/dev/null
```
Expected: Same number both times. Zero variance confirmed.

**Step 4: Commit**

```bash
git add scoring/score_frames.py
git commit -m "feat(scoring): rewrite to deterministic OpenCV comparison — zero variance"
```

---

### Task 5: End-to-End Validation

**Step 1: Run full pipeline**

Run:
```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
bash scoring/render_keyframes.sh >/dev/null 2>&1 && python scoring/score_frames.py
```
Expected: Renders 7 frames → scores deterministically → single number on stdout.

**Step 2: Verify autoresearch compatibility**

The Verify command used by autoresearch is:
```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview && bash scoring/render_keyframes.sh >/dev/null 2>&1 && python scoring/score_frames.py
```

Run this exact command and verify it outputs a single integer.

**Step 3: Run 3 times to confirm zero variance**

Run the verify command 3 times. All 3 must output the same number.

**Step 4: Commit ground truth (if not already)**

```bash
git add scoring/ground_truth.json
git commit -m "data(scoring): ground truth baseline for 7 reference frames"
```

---

### Task 6: Resume Autoresearch with New Scorer

**Step 1: Record new baseline**

```bash
# Get the deterministic baseline score
cd accounts/tried-it-first/assets/video-001/remotion-preview
SCORE=$(python scoring/score_frames.py 2>/dev/null)
echo "New deterministic baseline: $SCORE"
```

**Step 2: Update autoresearch results log**

Append new baseline entry to `autoresearch-results.tsv`.

**Step 3: Resume autoresearch**

```
/autoresearch
Goal: 提升 AnuaPromo 动画与原片的视觉一致性，目标 85 分。使用确定性 OpenCV 评分。偏差报告在 stderr 中显示每帧每属性的偏差，优先修复最大偏差。
Scope: accounts/tried-it-first/assets/video-001/remotion-preview/src/AnuaPromo.jsx
Metric: OpenCV deterministic similarity score (higher is better)
Verify: cd accounts/tried-it-first/assets/video-001/remotion-preview && bash scoring/render_keyframes.sh >/dev/null 2>&1 && python scoring/score_frames.py
Guard: cd accounts/tried-it-first/assets/video-001/remotion-preview && npx remotion still src/index.jsx Anua-Promo-3Cards scoring/guard-test.png --frame=30 --log=error 2>&1
Iterations: 19
```
