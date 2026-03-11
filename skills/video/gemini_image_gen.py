#!/usr/bin/env python3
"""Gemini Image Generation — equivalent to Nano Banana Pro ComfyUI workflow.

Usage:
    # Text-to-image (no reference)
    python skills/video/gemini_image_gen.py --prompt "A cat in a spacesuit" --output out.png

    # Image editing with reference images
    python skills/video/gemini_image_gen.py \
        --prompt "Change the background to a beach sunset" \
        --images ref1.png ref2.jpg \
        --output out.png

    # Full options
    python skills/video/gemini_image_gen.py \
        --prompt "Make the product glow" \
        --system-prompt "You are a professional product photographer" \
        --images product.png scene.jpg \
        --aspect-ratio 1:1 \
        --resolution 2K \
        --seed 42 \
        --output result.png
"""

import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai", file=sys.stderr)
    sys.exit(1)


def load_image_as_part(image_path: str) -> types.Part:
    """Load a local image file as a Gemini Part."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
    image_bytes = path.read_bytes()
    return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)


def generate_image(
    prompt: str,
    image_paths: list[str] | None = None,
    system_prompt: str | None = None,
    aspect_ratio: str = "1:1",
    resolution: str = "2K",
    seed: int | None = None,
    api_key: str | None = None,
) -> bytes | None:
    """Generate an image using Gemini 3 Pro Image Preview.

    Args:
        prompt: Main prompt describing what to generate/edit.
        image_paths: Up to 14 reference image file paths.
        system_prompt: System instruction defining model behavior.
        aspect_ratio: Output aspect ratio (1:1, 16:9, 9:16, etc).
        resolution: Output resolution (1K, 2K, 4K).
        seed: Random seed for reproducibility.
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var).

    Returns:
        PNG image bytes, or None if generation failed.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("No API key provided. Set GEMINI_API_KEY or pass --api-key")

    client = genai.Client(api_key=key)

    # Build contents: [image_parts..., text_prompt]
    contents = []
    if image_paths:
        if len(image_paths) > 14:
            raise ValueError(f"Max 14 reference images, got {len(image_paths)}")
        for img_path in image_paths:
            contents.append(load_image_as_part(img_path))
    contents.append(prompt)

    # Build config
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=resolution.lower(),
        ),
    )

    if system_prompt:
        config.system_instruction = system_prompt

    if seed is not None:
        config.seed = seed

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=config,
    )

    # Extract image from response
    if not response.candidates:
        print("ERROR: No candidates in response", file=sys.stderr)
        if response.prompt_feedback:
            print(f"  Prompt feedback: {response.prompt_feedback}", file=sys.stderr)
        return None

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            data = part.inline_data.data
            if isinstance(data, bytes):
                return data
            return base64.b64decode(data)

    print("ERROR: No image in response. Model returned text only:", file=sys.stderr)
    for part in response.candidates[0].content.parts:
        if part.text:
            print(f"  {part.text}", file=sys.stderr)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Image Generation (Nano Banana Pro equivalent)"
    )
    parser.add_argument("--prompt", "-p", required=True, help="Main prompt")
    parser.add_argument("--system-prompt", "-s", help="System instruction")
    parser.add_argument("--images", "-i", nargs="+", help="Reference images (max 14)")
    parser.add_argument("--aspect-ratio", "-a", default="1:1",
                        choices=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                        help="Output aspect ratio (default: 1:1)")
    parser.add_argument("--resolution", "-r", default="2K",
                        choices=["1K", "2K", "4K"],
                        help="Output resolution (default: 2K)")
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY)")
    parser.add_argument("--output", "-o", default="output.png", help="Output file path")

    args = parser.parse_args()

    image_bytes = generate_image(
        prompt=args.prompt,
        image_paths=args.images,
        system_prompt=args.system_prompt,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        seed=args.seed,
        api_key=args.api_key,
    )

    if image_bytes:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        print(f"Saved: {output_path} ({len(image_bytes)} bytes)")
    else:
        print("Image generation failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
