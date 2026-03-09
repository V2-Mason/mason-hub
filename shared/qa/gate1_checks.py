#!/usr/bin/env python3
"""
Gate 1 — 机器验证（自动）
Layer 1 通用结构 + Layer 2 平台参数

任何 agent 都可以调用：
  python3 shared/qa/gate1_checks.py --platform xiaohongshu --release-dir /path/to/release/
  python3 shared/qa/gate1_checks.py --platform douyin --files video.mp4 thumbnail.jpg

输出 JSON 格式的验收报告，每项 PASS/FAIL + 原因。
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Layer 2: 平台参数加载
# ---------------------------------------------------------------------------

PLATFORMS_DIR = Path(__file__).parent / "platforms"


def load_platform(name: str) -> dict:
    """加载平台参数 YAML（用纯 Python 解析避免依赖）"""
    path = PLATFORMS_DIR / f"{name}.yaml"
    if not path.exists():
        return {}
    # 简易 YAML 解析（只支持 key: value 和嵌套）
    result = {}
    current_section = None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            current_section = stripped[:-1]
            result[current_section] = {}
        elif ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # 尝试转数字
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
            if current_section:
                result[current_section][key] = val
            else:
                result[key] = val
    return result


# ---------------------------------------------------------------------------
# Gate 1 检查项（Layer 1 通用结构）
# ---------------------------------------------------------------------------

def check_file_exists(filepath: str) -> dict:
    """文件是否存在且非空"""
    p = Path(filepath)
    if not p.exists():
        return {"check": "file_exists", "file": filepath, "status": "FAIL", "reason": "文件不存在"}
    if p.stat().st_size == 0:
        return {"check": "file_exists", "file": filepath, "status": "FAIL", "reason": "文件为空（0 bytes）"}
    return {"check": "file_exists", "file": filepath, "status": "PASS", "size_bytes": p.stat().st_size}


def check_video_duration(filepath: str, platform: dict) -> dict:
    """视频时长是否在平台允许范围内"""
    video_params = platform.get("video", {})
    max_duration = video_params.get("max_duration_seconds", 600)
    min_duration = video_params.get("min_duration_seconds", 1)

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True, timeout=10
        )
        duration = float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return {"check": "video_duration", "file": filepath, "status": "SKIP", "reason": "ffprobe 不可用或解析失败"}

    if duration < min_duration:
        return {"check": "video_duration", "file": filepath, "status": "FAIL",
                "reason": f"时长 {duration:.1f}s < 最小 {min_duration}s", "duration": duration}
    if duration > max_duration:
        return {"check": "video_duration", "file": filepath, "status": "FAIL",
                "reason": f"时长 {duration:.1f}s > 最大 {max_duration}s", "duration": duration}
    return {"check": "video_duration", "file": filepath, "status": "PASS", "duration": duration}


def check_video_resolution(filepath: str, platform: dict) -> dict:
    """视频分辨率是否符合平台要求"""
    video_params = platform.get("video", {})
    min_width = video_params.get("min_width", 0)
    min_height = video_params.get("min_height", 0)

    if min_width == 0 and min_height == 0:
        return {"check": "video_resolution", "file": filepath, "status": "SKIP", "reason": "平台无分辨率要求"}

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
             "-select_streams", "v:0", "-of", "csv=s=x:p=0", filepath],
            capture_output=True, text=True, timeout=10
        )
        w, h = result.stdout.strip().split("x")
        width, height = int(w), int(h)
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return {"check": "video_resolution", "file": filepath, "status": "SKIP", "reason": "ffprobe 不可用"}

    if width < min_width or height < min_height:
        return {"check": "video_resolution", "file": filepath, "status": "FAIL",
                "reason": f"分辨率 {width}x{height} < 最小 {min_width}x{min_height}"}
    return {"check": "video_resolution", "file": filepath, "status": "PASS",
            "resolution": f"{width}x{height}"}


def check_file_size(filepath: str, platform: dict) -> dict:
    """文件大小是否在平台限制内"""
    video_params = platform.get("video", {})
    max_size_mb = video_params.get("max_file_size_mb", 0)
    if max_size_mb == 0:
        return {"check": "file_size", "file": filepath, "status": "SKIP", "reason": "平台无文件大小限制"}

    if not Path(filepath).exists():
        return {"check": "file_size", "file": filepath, "status": "SKIP", "reason": "文件不存在"}

    size_mb = Path(filepath).stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        return {"check": "file_size", "file": filepath, "status": "FAIL",
                "reason": f"文件 {size_mb:.1f}MB > 最大 {max_size_mb}MB"}
    return {"check": "file_size", "file": filepath, "status": "PASS", "size_mb": round(size_mb, 1)}


def check_title_length(title: str, platform: dict) -> dict:
    """标题字数是否在平台限制内"""
    text_params = platform.get("text", {})
    max_title = text_params.get("max_title_chars", 0)
    if max_title == 0:
        return {"check": "title_length", "status": "SKIP", "reason": "平台无标题限制"}

    length = len(title)
    if length > max_title:
        return {"check": "title_length", "status": "FAIL",
                "reason": f"标题 {length} 字 > 最大 {max_title} 字", "title": title[:50]}
    if length == 0:
        return {"check": "title_length", "status": "FAIL", "reason": "标题为空"}
    return {"check": "title_length", "status": "PASS", "length": length}


def check_subtitle_encoding(filepath: str) -> dict:
    """字幕文件编码是否正确，有无乱码"""
    p = Path(filepath)
    if not p.exists():
        return {"check": "subtitle_encoding", "file": filepath, "status": "SKIP", "reason": "字幕文件不存在"}

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"check": "subtitle_encoding", "file": filepath, "status": "FAIL", "reason": "非 UTF-8 编码，可能乱码"}

    # 检查常见乱码特征
    garbled_chars = sum(1 for c in text if c == '\ufffd' or (0xFFF0 <= ord(c) <= 0xFFFF))
    if garbled_chars > 0:
        return {"check": "subtitle_encoding", "file": filepath, "status": "FAIL",
                "reason": f"检测到 {garbled_chars} 个乱码字符"}

    empty_lines = sum(1 for line in text.splitlines() if line.strip() == "")
    total_lines = len(text.splitlines())
    if total_lines > 0 and empty_lines / total_lines > 0.5:
        return {"check": "subtitle_encoding", "file": filepath, "status": "WARN",
                "reason": f"超过 50% 空行（{empty_lines}/{total_lines}）"}

    return {"check": "subtitle_encoding", "file": filepath, "status": "PASS"}


def check_forbidden_words(text: str, platform: dict) -> dict:
    """检查违禁词"""
    forbidden = platform.get("forbidden_words", {})
    words = [w.strip() for w in str(forbidden.get("list", "")).split(",") if w.strip()]
    if not words:
        return {"check": "forbidden_words", "status": "SKIP", "reason": "平台无违禁词列表"}

    found = [w for w in words if w in text]
    if found:
        return {"check": "forbidden_words", "status": "FAIL",
                "reason": f"包含违禁词: {', '.join(found)}"}
    return {"check": "forbidden_words", "status": "PASS", "words_checked": len(words)}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_gate1(platform_name: str, files: list, title: str = "", body_text: str = "") -> dict:
    """运行全部 Gate 1 检查，返回结构化报告"""
    platform = load_platform(platform_name)
    results = []
    passed = 0
    failed = 0
    skipped = 0
    warned = 0

    # 文件存在性检查
    for f in files:
        r = check_file_exists(f)
        results.append(r)

    # 视频特定检查
    video_files = [f for f in files if f.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))]
    for vf in video_files:
        results.append(check_video_duration(vf, platform))
        results.append(check_video_resolution(vf, platform))
        results.append(check_file_size(vf, platform))

    # 字幕检查
    subtitle_files = [f for f in files if f.endswith((".srt", ".vtt", ".ass"))]
    for sf in subtitle_files:
        results.append(check_subtitle_encoding(sf))

    # 文本检查
    if title:
        results.append(check_title_length(title, platform))
    all_text = f"{title} {body_text}"
    if all_text.strip():
        results.append(check_forbidden_words(all_text, platform))

    # 统计
    for r in results:
        s = r.get("status", "")
        if s == "PASS":
            passed += 1
        elif s == "FAIL":
            failed += 1
        elif s == "SKIP":
            skipped += 1
        elif s == "WARN":
            warned += 1

    verdict = "PASS" if failed == 0 else "FAIL"

    return {
        "gate": "Gate 1 — 机器验证",
        "platform": platform_name,
        "verdict": verdict,
        "summary": f"{passed} passed, {failed} failed, {warned} warnings, {skipped} skipped",
        "checks": results
    }


def main():
    parser = argparse.ArgumentParser(description="Gate 1 机器验证")
    parser.add_argument("--platform", required=True, help="平台名称 (xiaohongshu/douyin/shipinhao)")
    parser.add_argument("--files", nargs="+", default=[], help="待检查文件列表")
    parser.add_argument("--release-dir", help="发布目录（自动扫描其中所有文件）")
    parser.add_argument("--title", default="", help="内容标题")
    parser.add_argument("--body", default="", help="内容正文")
    args = parser.parse_args()

    files = list(args.files)
    if args.release_dir:
        rd = Path(args.release_dir)
        if rd.exists():
            files.extend(str(f) for f in rd.iterdir() if f.is_file())

    report = run_gate1(args.platform, files, args.title, args.body)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
