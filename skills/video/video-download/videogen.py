"""VEO 3.1 视频片段生成：分镜图 → 每段视频片段

v2 路径（推荐）：shooting_script.json + shot_*.png → shot_*.mp4
v1 路径（向后兼容）：localized_analysis.json + segment_*.png → segment_*.mp4

用法：
  # v2: 从拍摄脚本（推荐）
  python videogen.py <shooting_script.json> --storyboard-dir ./storyboard/ [--from-script]

  # v1: 从分析 JSON（旧路径）
  python videogen.py <localized_analysis.json> --storyboard-dir ./storyboard/
"""
import argparse
import json
import os
import sys
import time

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

# VEO 3.1 only supports 4, 6, 8 second durations
DURATION_MAP = {4: '4', 6: '6', 8: '8'}


def _map_duration(seconds):
    """Map timeline segment duration to VEO-supported duration (4/6/8)."""
    if seconds <= 5:
        return '4'
    elif seconds <= 7:
        return '6'
    else:
        return '8'


def _parse_shot_duration(duration_str):
    """Parse shot duration like '0-8' or '22-30' to seconds."""
    try:
        parts = str(duration_str).split('-')
        if len(parts) == 2:
            return max(int(parts[1].strip()) - int(parts[0].strip()), 1)
    except (ValueError, IndexError):
        pass
    return 6  # default


def _extract_shots_from_script(script):
    """从脚本提取 flat shot 列表，兼容 v2(shots[]) 和 v3(segments[].shots[])。"""
    if 'segments' in script:
        flat = []
        for seg in script['segments']:
            for shot in seg.get('shots', []):
                shot_with_ctx = dict(shot)
                shot_with_ctx['_segment_type'] = seg.get('segment_type', '')
                flat.append(shot_with_ctx)
        return flat
    return script.get('shots', [])


def _build_video_prompt_from_shot(shot, script):
    """Build VEO prompt that mirrors every field in the shooting script shot.

    严格按分镜脚本的每个字段生成 prompt，不遗漏任何指令。
    """
    gpn = script.get('global_production_notes', {})
    seg_ctx = shot.get('_segment_type', '')

    parts = []

    # --- 全局设定 ---
    parts.append("【格式】竖版9:16短视频片段。")

    location = gpn.get('location', '')
    if location:
        parts.append(f"【场景】{location}")

    wardrobe = gpn.get('wardrobe', '')
    if wardrobe:
        parts.append(f"【服装】{wardrobe}")

    lighting = gpn.get('lighting_setup', '')
    if lighting:
        parts.append(f"【灯光】{lighting}")

    # --- 镜头信息 ---
    shot_type = shot.get('shot_type', '')
    if shot_type:
        parts.append(f"【景别】{shot_type}")

    camera_movement = shot.get('camera_movement', '')
    if camera_movement:
        parts.append(f"【镜头运动】{camera_movement}")

    duration = shot.get('duration_seconds', '')
    if duration:
        parts.append(f"【时长】{duration}秒")

    # --- 画面内容（核心） ---
    desc = shot.get('frame_description', '')
    if desc:
        parts.append(f"【画面描述】{desc}")

    # --- 表演指导 ---
    acting = shot.get('acting_direction', '')
    if acting:
        parts.append(f"【表演指导】{acting}")

    # --- 道具 ---
    props = shot.get('props', '')
    if props and props != '无':
        parts.append(f"【道具】{props}")

    # --- 画面文字/贴片 ---
    overlay = shot.get('text_overlay', '')
    if overlay:
        parts.append(f"【画面文字】{overlay}")

    # --- 台词/旁白 ---
    voiceover = shot.get('voiceover', '')
    if voiceover:
        parts.append(f"【口播台词】{voiceover}")

    # --- 声音设计 ---
    audio = shot.get('audio_note', '')
    if audio:
        parts.append(f"【声音设计】{audio}")

    # --- 光线备注（shot 级别覆盖全局） ---
    lighting_note = shot.get('lighting_note', '')
    if lighting_note and lighting_note != '同全局':
        parts.append(f"【光线备注】{lighting_note}")

    parts.append("画面写实自然，保持真实质感。")

    return '\n'.join(parts)


def generate_video_clips_from_script(script_path, storyboard_dir, output_dir,
                                      model='veo-3.1-generate-preview',
                                      poll_interval=15, max_wait=600, retry=1,
                                      skip_existing=True):
    """v2: Generate video clips from shooting script + storyboard images.

    Args:
        script_path: Path to shooting_script.json.
        storyboard_dir: Directory containing shot_NNN_type.png storyboard images.
        output_dir: Output directory for video clips.
        model: VEO model name.
        poll_interval: Seconds between poll checks.
        max_wait: Max seconds to wait per clip.
        retry: Number of retries on failure.
        skip_existing: Skip clips that already exist in output_dir.

    Returns:
        List of result dicts with shot info and output paths.
    """
    from google import genai
    from google.genai import types

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    with open(script_path, encoding='utf-8') as f:
        script = json.load(f)

    shots = _extract_shots_from_script(script)
    if not shots:
        raise ValueError("No shots found in shooting script JSON")

    os.makedirs(output_dir, exist_ok=True)

    results = []
    print(f"Generating {len(shots)} video clips from script with {model}...")

    for i, shot in enumerate(shots):
        shot_type = shot.get('shot_type', 'unknown').replace('/', '_')
        shot_num = f"{i + 1:03d}"
        duration_str = shot.get('duration_seconds', '')
        duration_secs = _parse_shot_duration(duration_str)
        veo_duration = _map_duration(duration_secs)

        # Find matching storyboard image
        img_filename = f"shot_{shot_num}_{shot_type}.png"
        img_path = os.path.join(storyboard_dir, img_filename)

        if not os.path.exists(img_path):
            print(f"  [{shot_num}/{len(shots)}] {shot_type}: SKIP (no storyboard image)")
            results.append({
                'shot_num': i + 1,
                'shot_type': shot_type,
                'status': 'skipped',
                'reason': 'no storyboard image',
            })
            continue

        video_filename = f"shot_{shot_num}_{shot_type}.mp4"
        video_path = os.path.join(output_dir, video_filename)

        # Skip existing clips
        if skip_existing and os.path.exists(video_path) and os.path.getsize(video_path) > 1024:
            size_kb = os.path.getsize(video_path) // 1024
            print(f"  [{shot_num}/{len(shots)}] {shot_type}: SKIP (exists, {size_kb}KB)")
            results.append({
                'shot_num': i + 1,
                'shot_type': shot_type,
                'duration': veo_duration,
                'output_file': video_filename,
                'status': 'ok',
                'skipped': True,
            })
            continue

        prompt = _build_video_prompt_from_shot(shot, script)

        print(f"  [{shot_num}/{len(shots)}] {shot_type} ({duration_str}, {veo_duration}s)...",
              end='', flush=True)

        with open(img_path, 'rb') as img_f:
            img_bytes = img_f.read()

        success = False
        for attempt in range(1 + retry):
            try:
                image = types.Image(
                    image_bytes=img_bytes,
                    mime_type='image/png',
                )

                operation = client.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    image=image,
                    config=types.GenerateVideosConfig(
                        aspect_ratio='9:16',
                        duration_seconds=veo_duration,
                    ),
                )

                elapsed = 0
                while not operation.done:
                    if elapsed >= max_wait:
                        print(f" TIMEOUT ({max_wait}s)", flush=True)
                        break
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                    operation = client.operations.get(operation)

                if operation.done and operation.response:
                    generated = operation.response.generated_videos[0]
                    client.files.download(file=generated.video)
                    generated.video.save(video_path)

                    size_kb = os.path.getsize(video_path) // 1024
                    print(f" OK ({size_kb}KB, {elapsed}s)")
                    success = True
                    break
                elif operation.done:
                    print(f" ERROR: operation completed without video", flush=True)
                    if attempt < retry:
                        print(f"    Retrying ({attempt + 1}/{retry})...", end='', flush=True)

            except Exception as e:
                print(f" ERROR: {e}", flush=True)
                if attempt < retry:
                    print(f"    Retrying ({attempt + 1}/{retry})...", end='', flush=True)
                    time.sleep(5)

        results.append({
            'shot_num': i + 1,
            'shot_type': shot_type,
            'duration': veo_duration,
            'prompt': prompt[:300],
            'output_file': video_filename if success else None,
            'status': 'ok' if success else 'failed',
        })

    generated = sum(1 for r in results if r['status'] == 'ok')
    print(f"\nVideo generation complete: {generated}/{len(shots)} clips")

    log_path = os.path.join(output_dir, 'videogen_log.json')
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


# --- v1: 旧路径（向后兼容） ---


def _parse_timestamp_duration(timestamp):
    """Parse 'MM:SS - MM:SS' to duration in seconds."""
    try:
        parts = timestamp.split(' - ')
        if len(parts) != 2:
            return 6  # default

        def to_seconds(ts):
            ts = ts.strip()
            if ':' in ts:
                chunks = ts.split(':')
                if len(chunks) == 2:
                    return int(chunks[0]) * 60 + int(chunks[1])
                elif len(chunks) == 3:
                    return int(chunks[0]) * 3600 + int(chunks[1]) * 60 + int(chunks[2])
            return 0

        start = to_seconds(parts[0])
        end = to_seconds(parts[1])
        return max(end - start, 1)
    except (ValueError, IndexError):
        return 6


def _build_video_prompt(segment, analysis):
    """Build motion/action prompt for VEO from segment info."""
    seg_type = segment.get('segment_type', '')
    desc = segment.get('description', '')
    technique = segment.get('key_technique', '')

    visual = analysis.get('visual_analysis', {})
    lighting = visual.get('lighting', '')

    prompt = f"竖版9:16短视频片段。{desc}"
    if technique:
        prompt += f" 关键动作：{technique}。"
    if lighting:
        prompt += f" 光线：{lighting}。"
    prompt += " 画面自然流畅，写实风格，镜头缓慢移动。"

    return prompt


def generate_video_clips(analysis_path, storyboard_dir, output_dir,
                         model='veo-3.1-generate-preview', poll_interval=15,
                         max_wait=600, retry=1):
    """Generate video clips from storyboard images using VEO 3.1.

    Args:
        analysis_path: Path to localized analysis JSON.
        storyboard_dir: Directory containing storyboard PNGs.
        output_dir: Output directory for video clips.
        model: VEO model name.
        poll_interval: Seconds between poll checks.
        max_wait: Max seconds to wait per clip.
        retry: Number of retries on failure.

    Returns:
        List of result dicts with segment info and output paths.
    """
    from google import genai
    from google.genai import types

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    with open(analysis_path, encoding='utf-8') as f:
        analysis = json.load(f)

    timeline = analysis.get('content_structure', {}).get('timeline', [])
    if not timeline:
        raise ValueError("No timeline segments found in analysis JSON")

    os.makedirs(output_dir, exist_ok=True)

    results = []
    print(f"Generating {len(timeline)} video clips with {model}...")

    for i, segment in enumerate(timeline):
        seg_type = segment.get('segment_type', 'unknown')
        seg_num = f"{i + 1:03d}"
        timestamp = segment.get('timestamp', '')
        duration_secs = _parse_timestamp_duration(timestamp)
        veo_duration = _map_duration(duration_secs)

        # Find matching storyboard image
        img_filename = f"segment_{seg_num}_{seg_type}.png"
        img_path = os.path.join(storyboard_dir, img_filename)

        if not os.path.exists(img_path):
            print(f"  [{seg_num}/{len(timeline)}] {seg_type}: SKIP (no storyboard image)")
            results.append({
                'segment_num': i + 1,
                'segment_type': seg_type,
                'status': 'skipped',
                'reason': 'no storyboard image',
            })
            continue

        video_filename = f"segment_{seg_num}_{seg_type}.mp4"
        video_path = os.path.join(output_dir, video_filename)

        prompt = _build_video_prompt(segment, analysis)

        print(f"  [{seg_num}/{len(timeline)}] {seg_type} ({timestamp}, {veo_duration}s)...",
              end='', flush=True)

        # Read storyboard image
        with open(img_path, 'rb') as img_f:
            img_bytes = img_f.read()

        success = False
        for attempt in range(1 + retry):
            try:
                image = types.Image(
                    image_bytes=img_bytes,
                    mime_type='image/png',
                )

                operation = client.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    image=image,
                    config=types.GenerateVideosConfig(
                        aspect_ratio='9:16',
                        duration_seconds=veo_duration,
                    ),
                )

                # Poll for completion
                elapsed = 0
                while not operation.done:
                    if elapsed >= max_wait:
                        print(f" TIMEOUT ({max_wait}s)", flush=True)
                        break
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                    operation = client.operations.get(operation)

                if operation.done and operation.response:
                    generated = operation.response.generated_videos[0]
                    client.files.download(file=generated.video)
                    generated.video.save(video_path)

                    size_kb = os.path.getsize(video_path) // 1024
                    print(f" OK ({size_kb}KB, {elapsed}s)")
                    success = True
                    break
                elif operation.done:
                    print(f" ERROR: operation completed without video", flush=True)
                    if attempt < retry:
                        print(f"    Retrying ({attempt + 1}/{retry})...", end='', flush=True)

            except Exception as e:
                print(f" ERROR: {e}", flush=True)
                if attempt < retry:
                    print(f"    Retrying ({attempt + 1}/{retry})...", end='', flush=True)
                    time.sleep(5)

        results.append({
            'segment_num': i + 1,
            'segment_type': seg_type,
            'timestamp': timestamp,
            'duration': veo_duration,
            'prompt': prompt[:300],
            'output_file': video_filename if success else None,
            'status': 'ok' if success else 'failed',
        })

    # Summary
    generated = sum(1 for r in results if r['status'] == 'ok')
    print(f"\nVideo generation complete: {generated}/{len(timeline)} clips")

    # Save results log
    log_path = os.path.join(output_dir, 'videogen_log.json')
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def main():
    parser = argparse.ArgumentParser(description='Generate video clips with VEO 3.1')
    parser.add_argument('input', help='Path to shooting_script.json (v2) or localized_analysis.json (v1)')
    parser.add_argument('--storyboard-dir', required=True, help='Directory with storyboard PNGs')
    parser.add_argument('--from-script', action='store_true',
                        help='Use v2 path: read from shooting_script.json (auto-detected if input has "shots" key)')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: {input_dir}/video_clips/)')
    parser.add_argument('--model', default='veo-3.1-generate-preview',
                        help='VEO model (default: veo-3.1-generate-preview)')
    parser.add_argument('--poll-interval', type=int, default=15,
                        help='Poll interval in seconds (default: 15)')
    parser.add_argument('--max-wait', type=int, default=600,
                        help='Max wait per clip in seconds (default: 600)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.input) or '.', 'video_clips'
    )

    # Auto-detect v2 script format
    use_script = args.from_script
    if not use_script:
        with open(args.input, encoding='utf-8') as f:
            data = json.load(f)
        if 'shots' in data or 'segments' in data:
            use_script = True
            print("Auto-detected shooting script format (v2/v3 path)")

    try:
        if use_script:
            generate_video_clips_from_script(
                args.input, args.storyboard_dir, output_dir,
                model=args.model, poll_interval=args.poll_interval,
                max_wait=args.max_wait,
            )
        else:
            print("Using v1 path (deprecated): reading from analysis JSON")
            generate_video_clips(
                args.input, args.storyboard_dir, output_dir,
                model=args.model, poll_interval=args.poll_interval,
                max_wait=args.max_wait,
            )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
