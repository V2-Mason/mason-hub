#!/usr/bin/env python3
"""从视频中提取帧到目录。

Usage: python extract-frames.py <video.mp4> --out <dir> [--fps 29.97]

依赖: ffmpeg (系统 PATH 中)
"""
import subprocess
import sys
import os
import argparse

def extract(video_path, out_dir, fps=29.97):
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps={fps}',
        '-q:v', '2',
        os.path.join(out_dir, 'frame_%04d.png')
    ]
    print(f"Extracting frames from {video_path} → {out_dir} at {fps}fps")
    subprocess.run(cmd, check=True)
    count = len([f for f in os.listdir(out_dir) if f.endswith('.png')])
    print(f"Extracted {count} frames")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract video frames')
    parser.add_argument('video', help='Input video file')
    parser.add_argument('--out', required=True, help='Output directory')
    parser.add_argument('--fps', type=float, default=29.97, help='Frame rate (default: 29.97)')
    args = parser.parse_args()
    extract(args.video, args.out, args.fps)
