"""Nano Banana 2 分镜图生成

v2 路径（推荐）：shooting_script.json → 每个 shot 一张图
v1 路径（向后兼容）：localized_analysis.json → 每个 timeline segment 一张图

用法：
  # v2: 从拍摄脚本生成（推荐）
  python storyboard.py <shooting_script.json> [--from-script] [--output-dir ./storyboard/]

  # v1: 从本地化分析生成（旧路径）
  python storyboard.py <localized_analysis.json> [--output-dir ./storyboard/]

v2 流程：
  1. 读取 shooting_script.json 的 shots[]
  2. 从 shot.camera/action/visual_focus + script.visual_style/character 构造 prompt
  3. 第一张图建立角色形象，后续传入第一张作为 reference
  4. 输出 shot_NNN_{type}.png + prompts.json
"""
import argparse
import base64
import json
import os
import sys
import time

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

# --- v2: 从拍摄脚本生成 ---

SHOT_PROMPT_TEMPLATE = """为以下短视频镜头生成一张高质量的预览图。

【镜头信息】
- 镜头类型：{shot_type}
- 时长：{duration}
- 动作：{action_description}
- 关键手势/动作：{key_gesture}
- 视觉焦点：{visual_focus}

【构图与镜头】
- 取景：{framing}
- 角度：{angle}
- 运动：{movement}

【视觉风格】
- 色温：{color_temperature}
- 光线：{lighting}
- 滤镜/调色：{filter_style}
- 画面比例：{aspect_ratio}
- 字幕区域：画面底部 15% 预留字幕空间
{text_overlay_section}

【角色】
- {character_description}
- 着装：{wardrobe}
- 发型：{hair}
- 妆容：{makeup}
- 本镜表情：{expression_arc}

【画面中的道具】
{props_list}

请生成一张写实风格的分镜预览图。"""


def _extract_shots(script):
    """从脚本中提取 flat shot 列表，兼容 v2(shots[]) 和 v3(segments[].shots[]) 格式。"""
    # v3: segments[].shots[]
    if 'segments' in script:
        flat = []
        for seg in script['segments']:
            for shot in seg.get('shots', []):
                shot_with_ctx = dict(shot)
                shot_with_ctx['_segment_type'] = seg.get('segment_type', '')
                flat.append(shot_with_ctx)
        return flat
    # v2: flat shots[]
    return script.get('shots', [])


def _build_shot_prompt(shot, script):
    """从拍摄脚本的 shot + 全局设定构造图像生成 prompt。

    兼容 v2 (nested camera/action/voiceover) 和 v3 (flat fields) 格式。
    """
    vs = script.get('visual_style', {})
    gpn = script.get('global_production_notes', {})
    char = script.get('character', {})

    # v2 nested fields
    cam = shot.get('camera', {})
    act = shot.get('action', {})
    overlay = shot.get('text_overlay', {})

    # v3 flat fields — 如果存在则优先使用
    frame_desc = shot.get('frame_description', '') or act.get('description', '')
    key_gesture = act.get('key_gesture', '')
    expression_arc = shot.get('acting_direction', '') or act.get('expression_arc', '自然从容')
    framing = cam.get('framing', shot.get('shot_type', '半身'))
    angle = cam.get('angle', '正面平视')
    movement = cam.get('movement', '') or shot.get('camera_movement', '固定机位')

    # Props: v3 uses flat 'props', v2 uses action.props_in_frame
    props_raw = shot.get('props', act.get('props_in_frame', []))
    if isinstance(props_raw, str):
        props_list = f'- {props_raw}' if props_raw and props_raw != '无' else '- 无特殊道具'
    elif isinstance(props_raw, list) and props_raw:
        props_list = '\n'.join(f'- {p}' for p in props_raw)
    else:
        props_list = '- 无特殊道具'

    # Text overlay: v3 is string, v2 is dict
    if isinstance(overlay, dict):
        main_text = overlay.get('main_text')
    else:
        main_text = overlay if overlay and overlay != '无' else None
    text_overlay_section = ''
    if main_text:
        text_overlay_section = f"\n【画面文字】\n- 贴片文字：{main_text}"

    # Lighting: v3 global_production_notes.lighting_setup, v2 visual_style.lighting
    lighting = vs.get('lighting', '') or gpn.get('lighting_setup', '自然光 + 环形补光灯')

    return SHOT_PROMPT_TEMPLATE.format(
        shot_type=shot.get('shot_type', shot.get('_segment_type', '')),
        duration=shot.get('duration_seconds', ''),
        action_description=frame_desc,
        key_gesture=key_gesture,
        visual_focus=shot.get('visual_focus', ''),
        framing=framing,
        angle=angle,
        movement=movement,
        color_temperature=vs.get('color_temperature', '暖色调'),
        lighting=lighting,
        filter_style=vs.get('filter', '轻微暖调，保持真实质感'),
        aspect_ratio=vs.get('aspect_ratio', '9:16'),
        text_overlay_section=text_overlay_section,
        character_description=char.get('description', gpn.get('wardrobe', '35岁左右中国女性')),
        wardrobe=char.get('wardrobe', '简洁舒适的家居服'),
        hair=char.get('hair', '自然披肩'),
        makeup=char.get('makeup_base', '淡妆'),
        expression_arc=expression_arc,
        props_list=props_list,
    )


def generate_storyboard_from_script(script_path, output_dir,
                                     model='gemini-3.1-flash-image-preview', delay=2):
    """v2: 从拍摄脚本生成分镜图。每个 shot 一张图。"""
    from google import genai
    from google.genai import types

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    with open(script_path, encoding='utf-8') as f:
        script = json.load(f)

    shots = _extract_shots(script)
    if not shots:
        raise ValueError("No shots found in shooting script JSON")

    os.makedirs(output_dir, exist_ok=True)

    prompts_log = []
    first_image_path = None

    print(f"Generating {len(shots)} storyboard frames from script with {model}...")

    for i, shot in enumerate(shots):
        shot_type = shot.get('shot_type', 'unknown')
        shot_num = f"{i + 1:03d}"
        filename = f"shot_{shot_num}_{shot_type}.png"
        filepath = os.path.join(output_dir, filename)

        prompt_text = _build_shot_prompt(shot, script)

        # Build content list: text prompt + optional character reference
        contents = [prompt_text]
        if first_image_path and os.path.exists(first_image_path):
            with open(first_image_path, 'rb') as img_f:
                img_bytes = img_f.read()
            contents = [
                "请参照以下图片中的角色形象，保持角色外观一致：",
                types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                prompt_text,
            ]

        duration = shot.get('duration_seconds', '')
        print(f"  [{shot_num}/{len(shots)}] {shot_type} ({duration})...", end='', flush=True)

        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                ),
            )

            image_saved = False
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open(filepath, 'wb') as out_f:
                        out_f.write(part.inline_data.data)
                    image_saved = True
                    break

            if image_saved:
                print(f" OK ({os.path.getsize(filepath) // 1024}KB)")
                if first_image_path is None:
                    first_image_path = filepath
            else:
                print(f" WARN: no image in response")

        except Exception as e:
            print(f" ERROR: {e}")

        prompts_log.append({
            'shot_num': i + 1,
            'shot_type': shot_type,
            'duration': duration,
            'prompt': prompt_text[:500],
            'output_file': filename,
            'has_character_ref': first_image_path is not None and i > 0,
        })

        if i < len(shots) - 1:
            time.sleep(delay)

    # Save prompts log
    prompts_path = os.path.join(output_dir, 'prompts.json')
    with open(prompts_path, 'w', encoding='utf-8') as f:
        json.dump(prompts_log, f, indent=2, ensure_ascii=False)

    generated = sum(1 for p in prompts_log if os.path.exists(os.path.join(output_dir, p['output_file'])))
    print(f"\nStoryboard complete: {generated}/{len(shots)} images generated")
    print(f"Prompts log: {prompts_path}")

    # 自动生成 Pencil 画布预览
    try:
        from pencil_storyboard import generate_pen_from_script
        pen_path = os.path.join(output_dir, 'storyboard.pen')
        generate_pen_from_script(script_path, output_dir, pen_path)
    except Exception as e:
        print(f"  Pencil preview skipped: {e}", file=sys.stderr)

    return prompts_log


# --- v1: 旧路径（向后兼容，deprecated） ---

SEGMENT_PROMPT_TEMPLATE = """为以下短视频分镜生成一张高质量的预览图。

【场景信息】
- 片段类型：{segment_type}
- 时间戳：{timestamp}
- 内容描述：{description}
- 关键技巧：{key_technique}
{product_context}

【视觉风格要求】
- 色调：温暖自然，柔和的暖色调
- 光线：{lighting}
- 画面风格：干净明亮，写实风格，不过度修图
- 字幕区域：画面底部 15% 预留字幕空间
- 画面比例：竖版 9:16（小红书/抖音短视频）
- 整体色彩：{color_palette}

【角色要求】
- 主角是一位 35 岁左右的中国女性
- 面容自然温和，皮肤真实质感
- 穿着简洁舒适的家居服或休闲装
- 表情从容、自然，不夸张
- 动作自然放松

请生成一张写实风格的分镜预览图。"""


def _build_segment_prompt(segment, analysis):
    """Construct image generation prompt for a timeline segment."""
    visual = analysis.get('visual_analysis', {})
    lighting = visual.get('lighting', '自然光，柔和')
    color_palette = visual.get('filter_tone', '暖色调')

    # Find matching product context if segment mentions a product
    product_context = ''
    products = analysis.get('product_catalog', [])
    seg_ts = segment.get('timestamp', '')
    for prod in products:
        prod_ts = prod.get('timestamp', '')
        # Check if timestamps overlap
        if prod_ts and seg_ts and prod_ts.split(' - ')[0] in seg_ts:
            product_context = (
                f"\n【关联产品】\n"
                f"- 品类：{prod.get('product_type', '')}\n"
                f"- 功效：{prod.get('core_function', '')}\n"
                f"- 展示方式：{prod.get('demo_method', '')}"
            )
            break

    return SEGMENT_PROMPT_TEMPLATE.format(
        segment_type=segment.get('segment_type', ''),
        timestamp=segment.get('timestamp', ''),
        description=segment.get('description', ''),
        key_technique=segment.get('key_technique', ''),
        product_context=product_context,
        lighting=lighting,
        color_palette=color_palette,
    )


def generate_storyboard(analysis_path, output_dir, model='gemini-3.1-flash-image-preview', delay=2):
    """Generate storyboard images from localized analysis JSON."""
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

    prompts_log = []
    first_image_path = None

    print(f"Generating {len(timeline)} storyboard frames with {model}...")

    for i, segment in enumerate(timeline):
        seg_type = segment.get('segment_type', 'unknown')
        seg_num = f"{i + 1:03d}"
        filename = f"segment_{seg_num}_{seg_type}.png"
        filepath = os.path.join(output_dir, filename)

        prompt_text = _build_segment_prompt(segment, analysis)

        # Build content list: text prompt + optional character reference
        contents = [prompt_text]
        if first_image_path and os.path.exists(first_image_path):
            # Pass first image as character reference for consistency
            with open(first_image_path, 'rb') as img_f:
                img_bytes = img_f.read()
            contents = [
                "请参照以下图片中的角色形象，保持角色外观一致：",
                types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                prompt_text,
            ]

        print(f"  [{seg_num}/{len(timeline)}] {seg_type}: {segment.get('timestamp', '')}...", end='', flush=True)

        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                ),
            )

            # Extract image from response
            image_saved = False
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open(filepath, 'wb') as out_f:
                        out_f.write(part.inline_data.data)
                    image_saved = True
                    break

            if image_saved:
                print(f" OK ({os.path.getsize(filepath) // 1024}KB)")
                if first_image_path is None:
                    first_image_path = filepath
            else:
                print(f" WARN: no image in response")

        except Exception as e:
            print(f" ERROR: {e}")

        prompts_log.append({
            'segment_num': i + 1,
            'segment_type': seg_type,
            'timestamp': segment.get('timestamp', ''),
            'prompt': prompt_text[:500],
            'output_file': filename,
            'has_character_ref': first_image_path is not None and i > 0,
        })

        if i < len(timeline) - 1:
            time.sleep(delay)

    # Save prompts log
    prompts_path = os.path.join(output_dir, 'prompts.json')
    with open(prompts_path, 'w', encoding='utf-8') as f:
        json.dump(prompts_log, f, indent=2, ensure_ascii=False)

    generated = sum(1 for p in prompts_log if os.path.exists(os.path.join(output_dir, p['output_file'])))
    print(f"\nStoryboard complete: {generated}/{len(timeline)} images generated")
    print(f"Prompts log: {prompts_path}")

    return prompts_log


def main():
    parser = argparse.ArgumentParser(description='Generate storyboard with Nano Banana 2')
    parser.add_argument('input', help='Path to shooting_script.json (v2) or localized_analysis.json (v1)')
    parser.add_argument('--from-script', action='store_true',
                        help='Use v2 path: read from shooting_script.json (auto-detected if input has "shots" key)')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: {input_dir}/storyboard/)')
    parser.add_argument('--model', default='gemini-3.1-flash-image-preview',
                        help='Image generation model (default: gemini-3.1-flash-image-preview / Nano Banana 2)')
    parser.add_argument('--delay', type=int, default=2,
                        help='Seconds between API calls (default: 2)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.input) or '.', 'storyboard'
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
            generate_storyboard_from_script(args.input, output_dir,
                                             model=args.model, delay=args.delay)
        else:
            print("Using v1 path (deprecated): reading from analysis JSON")
            generate_storyboard(args.input, output_dir, model=args.model, delay=args.delay)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
