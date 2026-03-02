"""用 Gemini 分析竞品视频，输出结构化拆解 JSON（v2 严格版）

用法：
  python gemini_analyze.py <video_file> [--model gemini-3-flash-preview] [--output analysis.json]

输出 JSON 结构：basic_info / hook_analysis / product_catalog / content_structure /
visual_analysis / audio_analysis / copywriting_analysis / engagement_triggers /
replicable_template — 详见 ANALYSIS_PROMPT
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

ANALYSIS_PROMPT = """你是一位资深小红书内容运营专家，专注于美妆/护肤赛道的爆款内容逆向工程。你必须按要求严格执行。

请从"内容创作者"的视角（不是观众视角）拆解这个视频，目标是提取出可复用的内容创作模板。

⚠️ 重要输出规则（必须严格遵守）：
1. 产品品牌名可以不记录，但必须记录【产品品类】和【核心功效/卖点】。例如：不需要写"XXX品牌喷雾"，但必须写"妆前定妆喷雾，主打保湿不卡粉"。
2. timeline 必须完整覆盖视频中提到的每一个产品/片段，不允许省略任何一个。如果视频推荐了19个产品，timeline 就必须有19个产品条目+开头和结尾。
3. 视频标题：如果在画面中不可见，标注为 null，不要自行推测。
4. 所有口播内容请尽量精确转录原文，不要意译或概括。
5. 时间戳精确到秒，格式为 MM:SS。
6. 不要对任何内容打码或用星号替代。
7. 在 product_catalog 的每个产品条目中，如果视频中提到了价格相关信息（直接报价、模糊区间如"百元价位"/"不到两百"、性价比判断如"比同类产品便宜"、用量换算等），如实记录在 price_signal 字段中。如果视频完全没有提及价格相关信息，标注为"未提及价格"。不要根据自己对产品的了解补充价格，只记录视频中实际出现的信息。

请按以下结构输出 JSON：

{
  "basic_info": {
    "video_duration": "视频总时长",
    "content_type": "图文轮播 / 真人出镜口播 / 产品展示 / 教程演示 / 混合（请具体描述混合方式）",
    "estimated_target_audience": "目标用户画像（年龄、肤质、消费水平、核心痛点）",
    "product_category": "涉及的产品大品类",
    "total_products_mentioned": "视频中总共推荐/提及了多少个产品"
  },

  "hook_analysis": {
    "first_3_seconds": "前3秒的具体内容描述（画面+文字+口播，分别说明）",
    "hook_type": "痛点型 / 悬念型 / 数据型 / 对比型 / 争议型 / 种草型 / 复合型（如复合请列出组合）",
    "hook_text": "口播原文转录",
    "hook_visual": "画面具体内容",
    "hook_effectiveness": "为什么这个hook能留住用户（分析心理机制）"
  },

  "product_catalog": [
    {
      "sequence": "出场顺序编号（1, 2, 3...）",
      "timestamp": "MM:SS - MM:SS",
      "product_type": "产品品类（如：定妆喷雾、面霜、唇釉、痘痘贴、卧蚕笔等）",
      "core_function": "核心功效/卖点（如：妆前保湿防卡粉、隔夜吸脓消痘、一笔成型妈生卧蚕等）",
      "target_skin_concern": "针对什么肤质/问题（如：大干皮、敏感肌、爱长痘、混油皮等）",
      "demo_method": "展示方式（如：上脸实测、手臂试色、质地特写、before/after对比等）",
      "key_claim": "博主对这个产品的核心评价原文（1句话）",
      "price_signal": "价格相关信息（直接报价/模糊区间/性价比判断/用量换算，如未提及标注'未提及价格'）",
      "persuasion_technique": "用了什么说服技巧（如：从众背书、稀缺感、痛点对号入座、视觉证言等）",
      "duration_seconds": "这个产品占了多少秒"
    }
  ],

  "content_structure": {
    "overall_framework": "总体结构（如：总-分-总、问题-方案-效果、递进式等）",
    "timeline": [
      {
        "timestamp": "MM:SS - MM:SS",
        "segment_type": "hook / 过渡 / 产品介绍 / 使用演示 / 效果展示 / 互动引导 / outro",
        "description": "这个片段具体做了什么",
        "key_technique": "用了什么内容技巧"
      }
    ],
    "transcript": [
      {
        "timestamp": "MM:SS",
        "speaker": "博主 / 旁白 / 字幕",
        "text": "逐句转录的原文（尽量精确，不意译）"
      }
    ],
    "pacing_pattern": "节奏模式描述（语速、每个产品平均时长、是否有喘息空间、信息密度评估）",
    "transition_style": "产品之间的转场方式（如：硬切、口播过渡、视觉分隔等）",
    "total_segments": "总共分几个段落"
  },

  "visual_analysis": {
    "cover_design": {
      "layout": "封面构图方式",
      "text_on_cover": "封面文字内容（原文，如不可见标注 null）",
      "font_style": "字体风格（大小、颜色、位置、是否有描边/阴影）",
      "color_palette": "主色调和整体色彩风格",
      "product_placement": "产品在封面中的展示方式"
    },
    "filming_techniques": [
      {
        "technique": "拍摄手法名称（如：怼脸特写、桌面平铺、手持探店、微距质地等）",
        "usage_context": "在什么环节使用",
        "effect": "达到了什么视觉效果"
      }
    ],
    "lighting": "打光方式及对画面质感的影响",
    "filter_tone": "滤镜/调色风格及对品牌调性的作用",
    "text_overlay_style": "字幕/贴纸的设计系统（字体、颜色、位置规律、强调方式）"
  },

  "audio_analysis": {
    "voiceover_style": "口播风格（用一个精准的标签定义，如：闺蜜激动安利型、冷静专业测评型等）",
    "speaking_pace": "语速评估（快/中/慢，以及节奏特征）",
    "emotional_arc": "情绪变化曲线（全程高能？还是有起伏？）",
    "tone_keywords": ["3-5个形容这个口播调性的关键词"],
    "bgm_style": "背景音乐风格及音量层次",
    "signature_phrases": [
      {
        "phrase": "原文话术",
        "function": "这句话的功能（如：制造紧迫感、建立信任、引导行动等）",
        "frequency": "出现频率（高频/偶尔）"
      }
    ]
  },

  "copywriting_analysis": {
    "title": "视频标题原文（如画面中不可见，标注 null）",
    "title_formula": "标题公式拆解（如可见）",
    "selling_point_expression_patterns": [
      {
        "pattern_name": "卖点表达模式名称（如：痛点前置型、效果可视化型、从众背书型）",
        "example": "视频中的具体例子（口播原文）",
        "why_effective": "为什么有效"
      }
    ],
    "persuasion_techniques_summary": ["使用的说服技巧清单及每个的具体运用方式"],
    "call_to_action": {
      "text": "结尾引导话术原文",
      "type": "引导类型（收藏/关注/评论/私信/购买链接）",
      "placement": "出现在什么位置"
    },
    "hashtags": ["使用的标签（如可见，否则标注 null）"]
  },

  "engagement_triggers": {
    "comment_bait": {
      "strategy": "引导评论的策略",
      "mechanism": "为什么能引发评论"
    },
    "save_trigger": {
      "strategy": "引导收藏的策略",
      "mechanism": "为什么能引发收藏"
    },
    "share_trigger": {
      "strategy": "引导分享的策略",
      "mechanism": "为什么能引发分享"
    },
    "primary_engagement_goal": "这个视频的核心互动目标是什么（完播率/收藏率/评论率/分享率），以及为什么"
  },

  "replicable_template": {
    "content_formula": "用一句话概括这个视频的内容公式（要具体到可以直接复用）",
    "formula_breakdown": {
      "opening": "开头公式",
      "body": "主体公式",
      "closing": "结尾公式"
    },
    "applicable_scenarios": ["这个模板适合用在哪些场景/品类"],
    "adaptation_for_small_creator": "如果是小博主/预算有限，怎么简化复制",
    "minimum_viable_version": "这个内容的最小可行版本是什么（最少需要几个产品、什么设备、什么场景）",
    "difficulty_level": "复制难度（低/中/高）及原因",
    "required_resources": ["复制这个内容需要的核心资源"]
  }
}

只输出 JSON，不要其他文字。确保 JSON 格式正确。"""


def _parse_gemini_json(text):
    """从 Gemini 响应中健壮地提取 JSON。

    处理常见问题：markdown code fences、trailing commas、
    响应前后有多余文字等。
    """
    # Strip markdown code fences
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract outermost {} block (skip any preamble/postamble text)
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                block = text[start:i + 1]
                # Try parse the extracted block
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    # Fix trailing commas before } or ]
                    fixed = re.sub(r',\s*([}\]])', r'\1', block)
                    try:
                        return json.loads(fixed)
                    except json.JSONDecodeError:
                        pass
                # Reset and keep scanning (unlikely but safe)
                start = None

    raise json.JSONDecodeError(
        "Could not extract valid JSON from Gemini response",
        text[:200], 0
    )


def analyze_video(video_path, model='gemini-2.5-flash'):
    """上传视频到 Gemini 并分析"""
    from google import genai

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    file_size = os.path.getsize(video_path) / (1024 * 1024)
    print(f"Uploading {os.path.basename(video_path)} ({file_size:.1f}MB) to Gemini...")

    # Upload file (use ASCII-safe temp path to avoid header encoding errors)
    upload_path = video_path
    temp_link = None
    if not os.path.basename(video_path).isascii():
        temp_dir = tempfile.mkdtemp()
        temp_link = os.path.join(temp_dir, 'video.mp4')
        os.symlink(os.path.abspath(video_path), temp_link)
        upload_path = temp_link

    uploaded = client.files.upload(file=upload_path)

    if temp_link:
        os.unlink(temp_link)
        os.rmdir(os.path.dirname(temp_link))
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

    # Parse JSON from response (robust: handle markdown fences, trailing commas, etc.)
    text = response.text.strip()
    result = _parse_gemini_json(text)

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
    print(f"Products found: {len(result.get('product_catalog', []))}")
    print(f"Content type: {result.get('basic_info', {}).get('content_type', 'N/A')}")
    tpl = result.get('replicable_template', {})
    print(f"Formula: {tpl.get('content_formula', 'N/A')}")
    print(f"Difficulty: {tpl.get('difficulty_level', 'N/A')}")

    return 0


if __name__ == '__main__':
    exit(main())
