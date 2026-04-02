"""
Growth Memo — MVP Video Producer

Combines image slides + audio (narration + BGM) into a video using ffmpeg.

Usage:
    python produce.py <episode-dir>

Episode directory structure:
    episode-001/
        script.md                   # not used by script, for human reference
        assets/ai-generated/        # images: 01.png, 02.png, ...
        audio/narration.mp3         # TTS or recorded narration
        audio/bgm.mp3              # background music (optional)
        output/                    # output goes here
"""

import argparse
import subprocess
import sys
from pathlib import Path


def find_images(assets_dir: Path) -> list[Path]:
    """Find all images in ai-generated/, sorted by name."""
    ai_dir = assets_dir / "ai-generated"
    if not ai_dir.exists():
        print(f"Error: {ai_dir} does not exist")
        sys.exit(1)

    exts = {".png", ".jpg", ".jpeg", ".webp"}
    images = sorted(f for f in ai_dir.iterdir() if f.suffix.lower() in exts)

    if not images:
        print(f"Error: no images found in {ai_dir}")
        sys.exit(1)

    return images


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of an audio file in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def produce(episode_dir: Path, resolution: str = "1920x1080", fps: int = 30):
    """Produce a video from an episode directory."""
    assets_dir = episode_dir / "assets"
    audio_dir = episode_dir / "audio"
    output_dir = episode_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    images = find_images(assets_dir)
    print(f"Found {len(images)} images")

    # Find narration audio
    narration = None
    for name in ["narration.mp3", "narration.wav", "narration.m4a"]:
        candidate = audio_dir / name
        if candidate.exists():
            narration = candidate
            break

    if not narration:
        print("Error: no narration audio found (narration.mp3/wav/m4a)")
        sys.exit(1)

    # Calculate duration per image
    total_duration = get_audio_duration(narration)
    duration_per_image = total_duration / len(images)
    print(f"Narration: {total_duration:.1f}s, {duration_per_image:.1f}s per slide")

    # Build ffmpeg command
    # Create a concat file for images with durations
    concat_file = output_dir / "_concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for img in images:
            # Use forward slashes for ffmpeg compatibility
            img_path = str(img.resolve()).replace("\\", "/")
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {duration_per_image:.3f}\n")
        # Repeat last image (ffmpeg concat demuxer quirk)
        img_path = str(images[-1].resolve()).replace("\\", "/")
        f.write(f"file '{img_path}'\n")

    width, height = resolution.split("x")
    output_file = output_dir / "final.mp4"

    # Base command: images → video with narration
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(narration),
    ]

    # Add BGM if exists
    bgm = audio_dir / "bgm.mp3"
    if bgm.exists():
        cmd.extend(["-i", str(bgm)])
        # Mix narration (full volume) + BGM (20% volume)
        cmd.extend([
            "-filter_complex",
            f"[1:a]volume=1.0[narr];[2:a]volume=0.2[bg];[narr][bg]amix=inputs=2:duration=shortest[aout];"
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[vout]",
            "-map", "[vout]", "-map", "[aout]",
        ])
    else:
        cmd.extend([
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
            "-map", "0:v", "-map", "1:a",
        ])

    cmd.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(output_file),
    ])

    print(f"Rendering -> {output_file}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Clean up temp file
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ffmpeg error:\n{result.stderr[-500:]}")
        sys.exit(1)

    print(f"Done! Output: {output_file}")
    print(f"Duration: {total_duration:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Produce Growth Memo video from episode directory")
    parser.add_argument("episode_dir", type=Path, help="Path to episode directory")
    parser.add_argument("--resolution", default="1920x1080", help="Output resolution (default: 1920x1080)")
    parser.add_argument("--fps", type=int, default=30, help="Output FPS (default: 30)")
    args = parser.parse_args()

    if not args.episode_dir.exists():
        print(f"Error: {args.episode_dir} does not exist")
        sys.exit(1)

    produce(args.episode_dir, args.resolution, args.fps)
