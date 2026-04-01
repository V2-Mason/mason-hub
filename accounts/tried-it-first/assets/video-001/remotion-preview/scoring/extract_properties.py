#!/usr/bin/env python3
"""Extract visual properties from a frame using OpenCV.

Given an image, detects card-like rectangles and measures:
- Card positions (bounding box center x, y)
- Card sizes (width, height)
- Card dominant colors (K-means via cv2)
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
    """Sample background color from image corners (5% inset)."""
    h, w = img.shape[:2]
    mx, my = int(w * 0.05), int(h * 0.05)
    corners = [
        img[my, mx],
        img[my, w - mx - 1],
        img[h - my - 1, mx],
        img[h - my - 1, w - mx - 1],
    ]
    avg = np.mean(corners, axis=0).astype(int)
    return "#{:02x}{:02x}{:02x}".format(int(avg[2]), int(avg[1]), int(avg[0]))


def dominant_color(img_region, k=2):
    """Extract dominant color from a region using cv2.kmeans."""
    pixels = img_region.reshape(-1, 3).astype(np.float32)
    if len(pixels) < k:
        return "#000000"
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
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

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold + Canny edges
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3
    )
    edges = cv2.Canny(blurred, 30, 100)
    combined = cv2.bitwise_or(thresh, edges)

    # Dilate to connect nearby edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(combined, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cards = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        x, y, cw, ch = cv2.boundingRect(contour)

        # Cards are tall rectangles (aspect ratio 1.0 ~ 3.5)
        aspect = ch / cw if cw > 0 else 0
        if aspect < 1.0 or aspect > 3.5:
            continue

        # Extract card region for color analysis (skip border)
        card_region = img[y:y+ch, x:x+cw]
        inner_margin = max(int(min(cw, ch) * 0.15), 5)
        inner = card_region[inner_margin:-inner_margin, inner_margin:-inner_margin]
        if inner.size == 0:
            inner = card_region
        color = dominant_color(inner)

        cards.append({
            "x": int(x + cw // 2),
            "y": int(y + ch // 2),
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
