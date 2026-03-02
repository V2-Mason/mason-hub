"""Nano Banana 2 分镜图生成：本地化 JSON → 每个 timeline segment 一张图

用法：
  python storyboard.py <localized_analysis.json> [--output-dir ./storyboard/] [--model nano-banana-2]

流程：
  1. 读取 content_structure.timeline 的每个 segment
  2. 结合 visual_analysis + product_catalog 构造 prompt
  3. 第一张图建立角色形象，后续传入第一张作为 reference
  4. 输出 segment_NNN_{type}.png + prompts.json
"""
import argparse
import base64
import json
import os
import sys
import time

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

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


def generate_storyboard(analysis_path, output_dir, model='nano-banana-2', delay=2):
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
    parser.add_argument('analysis', help='Path to localized analysis JSON')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: {analysis_dir}/storyboard/)')
    parser.add_argument('--model', default='nano-banana-2',
                        help='Image generation model (default: nano-banana-2)')
    parser.add_argument('--delay', type=int, default=2,
                        help='Seconds between API calls (default: 2)')
    args = parser.parse_args()

    if not os.path.exists(args.analysis):
        print(f"ERROR: File not found: {args.analysis}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(args.analysis), 'storyboard'
    )

    try:
        generate_storyboard(args.analysis, output_dir, model=args.model, delay=args.delay)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
