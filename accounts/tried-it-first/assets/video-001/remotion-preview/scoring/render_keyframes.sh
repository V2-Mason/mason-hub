#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$SCRIPT_DIR/rendered-frames"
mkdir -p "$OUTPUT_DIR"

cd "$PROJECT_DIR"

# 从 frame_map.json 提取帧号
FRAMES=$(python -c "import json; d=json.load(open('scoring/frame_map.json')); print(' '.join(str(p['remotion_frame']) for p in d['pairs']))")

for FRAME in $FRAMES; do
  npx remotion still src/index.jsx Anua-Promo-3Cards \
    "$OUTPUT_DIR/rendered-frame-${FRAME}.png" \
    --frame="$FRAME" \
    --log=error 2>/dev/null
done

echo "Rendered $(echo $FRAMES | wc -w | tr -d ' ') keyframes to $OUTPUT_DIR"
