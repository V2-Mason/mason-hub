"""用 Gemini 分析竞品视频，输出结构化拆解 JSON

用法：
  python gemini_analyze.py <video_file> [--model gemini-2.5-flash] [--output analysis.json]

输出 JSON 结构：
{
  "hook": { "type": "...", "text": "...", "duration_sec": 5 },
  "products": [{ "name": "...", "intro_method": "...", "duration_sec": 20 }],
  "persuasion_techniques": ["从众效应", ...],
  "visual_style": { "lighting": "...", "editing_pace": "...", "text_overlay": "..." },
  "cta": { "type": "...", "text": "..." },
  "target_audience": { "age_range": "...", "gender": "...", "concerns": [...] },
  "overall_tone": "...",
  "reusable_patterns": ["...", ...],
  "estimated_duration_sec": 90
}
"""
import argparse
import json
import os
import sys
import time

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

ANALYSIS_PROMPT = """你是一个专业的社交媒体内容分析师。请仔细观看这个视频，然后用 JSON 格式输出以下拆解：

1. **hook**（开头钩子）：类型（痛点共鸣/震撼展示/经验权威/悬念提问）、原文、时长
2. **products**：提到的每个产品，包括名称、介绍方式（亲测分享/成分科普/效果对比/场景植入）、分配时长
3. **persuasion_techniques**：使用的说服技巧（从众效应/稀缺感/权威背书/效果对比/情绪渲染/真实体验）
4. **visual_style**：灯光风格、剪辑节奏（快/中/慢）、字幕/贴纸风格、画面构图
5. **cta**（行动号召）：类型（收藏/关注/评论/私信/购买链接）、原文
6. **target_audience**：目标受众年龄范围、性别、核心关注点
7. **overall_tone**：整体调性（闺蜜安利/专业测评/日常分享/激情带货）
8. **reusable_patterns**：可以复用的内容模式或话术结构（列出 3-5 个）
9. **estimated_duration_sec**：视频总时长估计（秒）
10. **口播文字**：尽可能还原视频中的口播完整文字

只输出 JSON，不要其他文字。确保 JSON 格式正确。"""


def analyze_video(video_path, model='gemini-2.5-flash'):
    """上传视频到 Gemini 并分析"""
    from google import genai

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    file_size = os.path.getsize(video_path) / (1024 * 1024)
    print(f"Uploading {os.path.basename(video_path)} ({file_size:.1f}MB) to Gemini...")

    # Upload file
    uploaded = client.files.upload(file=video_path)
    print(f"Uploaded: {uploaded.name}, state={uploaded.state}")

    # Wait for processing
    while uploaded.state.name == 'PROCESSING':
        print("  Processing...")
        time.sleep(5)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != 'ACTIVE':
        raise RuntimeError(f"File processing failed: state={uploaded.state.name}")

    print(f"File ready. Analyzing with {model}...")

    # Generate analysis
    response = client.models.generate_content(
        model=model,
        contents=[
            uploaded,
            ANALYSIS_PROMPT,
        ],
    )

    # Parse JSON from response
    text = response.text.strip()
    # Remove markdown code fences if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

    result = json.loads(text)

    # Clean up uploaded file
    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description='Analyze video with Gemini')
    parser.add_argument('video', help='Local video file path')
    parser.add_argument('--model', default='gemini-3-flash-preview',
                        help='Gemini model (default: gemini-3-flash-preview)')
    parser.add_argument('--output', help='Output JSON path (default: {video}_analysis.json)')
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"ERROR: File not found: {args.video}", file=sys.stderr)
        return 1

    try:
        result = analyze_video(args.video, model=args.model)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Gemini response as JSON: {e}", file=sys.stderr)
        return 1

    output_path = args.output or args.video.rsplit('.', 1)[0] + '_analysis.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis saved to {output_path}")
    print(f"Products found: {len(result.get('products', []))}")
    print(f"Tone: {result.get('overall_tone', 'N/A')}")
    print(f"Reusable patterns: {len(result.get('reusable_patterns', []))}")

    return 0


if __name__ == '__main__':
    exit(main())
