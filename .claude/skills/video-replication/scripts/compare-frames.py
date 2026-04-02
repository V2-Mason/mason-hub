#!/usr/bin/env python3
"""逐帧 SSIM 对比，输出差异报告。

Usage: python compare-frames.py <ref_dir> <render_dir> [--threshold 0.95]

输出:
- 每帧 SSIM 分数
- 差异最大的 Top 10 帧
- 整体均值

依赖: pip install scikit-image pillow numpy
"""
import os
import sys
import argparse
import numpy as np
from PIL import Image

def load_image(path):
    return np.array(Image.open(path).convert('RGB'))

def ssim_simple(img1, img2):
    """简化 SSIM 计算（不依赖 skimage，精度够用）"""
    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)

    mu1 = img1.mean()
    mu2 = img2.mean()
    sigma1_sq = img1.var()
    sigma2_sq = img2.var()
    sigma12 = ((img1 - mu1) * (img2 - mu2)).mean()

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    num = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    den = (mu1 ** 2 + mu2 ** 2 + C1) * (sigma1_sq + sigma2_sq + C2)
    return num / den

def compare(ref_dir, render_dir, threshold=0.95):
    ref_files = sorted([f for f in os.listdir(ref_dir) if f.endswith('.png')])
    render_files = sorted([f for f in os.listdir(render_dir) if f.endswith('.png')])

    n = min(len(ref_files), len(render_files))
    if n == 0:
        print("ERROR: No frames found")
        sys.exit(1)

    print(f"Comparing {n} frames (ref: {len(ref_files)}, render: {len(render_files)})")
    print(f"{'Frame':<12} {'SSIM':>8} {'Status'}")
    print("-" * 35)

    scores = []
    for i in range(n):
        ref_img = load_image(os.path.join(ref_dir, ref_files[i]))
        render_img = load_image(os.path.join(render_dir, render_files[i]))

        # Resize if dimensions don't match
        if ref_img.shape != render_img.shape:
            from PIL import Image as PILImage
            render_pil = PILImage.fromarray(render_img).resize(
                (ref_img.shape[1], ref_img.shape[0]), PILImage.LANCZOS)
            render_img = np.array(render_pil)

        score = ssim_simple(ref_img, render_img)
        status = "OK" if score >= threshold else "DIFF"
        scores.append((i, ref_files[i], score, status))
        print(f"{ref_files[i]:<12} {score:>8.4f} {status}")

    print(f"\n{'='*35}")
    mean_ssim = np.mean([s[2] for s in scores])
    below = [s for s in scores if s[2] < threshold]
    print(f"Mean SSIM: {mean_ssim:.4f}")
    print(f"Frames below {threshold}: {len(below)}/{n}")

    if below:
        print(f"\nTop 10 worst frames:")
        for _, fname, score, _ in sorted(below, key=lambda x: x[2])[:10]:
            print(f"  {fname}: {score:.4f}")

    return mean_ssim

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compare frames by SSIM')
    parser.add_argument('ref_dir', help='Reference frames directory')
    parser.add_argument('render_dir', help='Rendered frames directory')
    parser.add_argument('--threshold', type=float, default=0.95, help='SSIM threshold (default: 0.95)')
    args = parser.parse_args()
    compare(args.ref_dir, args.render_dir, args.threshold)
