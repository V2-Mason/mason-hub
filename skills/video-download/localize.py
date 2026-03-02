"""品牌本地化：Gemini 拆解 JSON → 同 schema 的本地化 JSON

用法：
  python localize.py <analysis.json> [--brand surenxuan] [--output localized.json]

核心约束：
  - 输出 JSON 格式与输入完全一致（key/层级/数组长度不变）
  - 只改文案内容（描述语气、话术、调性词），不改时间/数据/产品信息
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gemini_analyze import _parse_gemini_json

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')
BRANDS_DIR = os.path.expanduser('~/mason-hub/shared/brands')

# Fields that must NOT be modified during localization
IMMUTABLE_KEYS = [
    'basic_info',
    'product_catalog',
    'visual_analysis',
    'engagement_triggers',
]

# Prohibited words from voice.md (hard-coded subset for automated scanning)
PROHIBITED_WORDS = [
    '美白', '祛痘', '祛斑', '抗衰老',
    '绝绝子', 'yyds', '天花板', '封神', '无敌好用',
    '宝子', '家人们', '集美',
    '一定要冲', '必入', '闭眼入',
    '治疗', '治愈', '药用',
]

LOCALIZATION_PROMPT_TEMPLATE = """你是一位品牌内容本地化专家。你的任务是将竞品视频拆解结果适配到目标品牌的风格和语境中。

⚠️ 核心规则（绝对不可违反）：
1. 输出 JSON 的结构（所有 key、嵌套层级、数组长度）必须与输入 JSON 完全一致
2. 不要新增任何 key，不要删除任何 key，不要改变数组元素数量
3. 只修改以下字段中的文本值：
   - content_structure.timeline[].description — 调整描述语气，适配品牌调性
   - content_structure.timeline[].key_technique — 如果技巧不适用于品牌，替换为品牌 voice 里的对应技巧
   - audio_analysis.voiceover_style — 替换为品牌的口播风格标签
   - audio_analysis.tone_keywords — 替换为品牌的调性关键词
   - audio_analysis.signature_phrases[].phrase — 用品牌的话术模板替换原文话术
   - copywriting_analysis.selling_point_expression_patterns[].example — 用品牌风格重写示例
   - copywriting_analysis.call_to_action.text — 用品牌的结尾引导话术替换
   - replicable_template.content_formula — 适配品牌调性重述
   - replicable_template.formula_breakdown — 开头/主体/结尾公式用品牌风格重述
   - replicable_template.adaptation_for_small_creator — 用品牌实际资源重述
4. 以下字段绝对不要改动：
   - basic_info（整个模块）
   - hook_analysis.first_3_seconds, hook_analysis.hook_visual（原始视频描述）
   - product_catalog（整个模块 — 这是原始视频的产品信息）
   - visual_analysis（整个模块 — 这是原始视频的视觉描述）
   - engagement_triggers（整个模块 — 这是互动机制分析）
   - 所有 timestamp 字段
   - 所有 duration_seconds 字段
5. 修改时参照以下品牌资料：

=== 品牌 Brief ===
{brief_content}

=== 品牌语言风格指南 ===
{voice_content}

=== 关键适配规则 ===
- 称呼受众用"姐妹"，不用"宝子""家人们""集美"
- 语气温和笃定，不用"绝绝子""yyds""天花板""封神"
- 说服技巧从"命令式安利"改为"建议式推荐"
- 从众效应从"韩女人手一支"改为"群里好几个姐妹都在用"的同龄验证
- 结尾引导用"感兴趣的姐妹可以先收藏"而不是"一定要冲"
- 价格表达用模糊区间（"百元出头""不到两百"），不报精确价格
- 禁用词：美白→提亮、祛痘→改善痘痘、祛斑→淡化色斑、抗衰老→抗初老

只输出 JSON，不要其他文字。确保 JSON 格式正确。

=== 输入 JSON ===
{analysis_json}"""


def _load_brand_files(brand):
    """Load brief.md and voice.md for the given brand."""
    brand_dir = os.path.join(BRANDS_DIR, brand)
    brief_path = os.path.join(brand_dir, 'brief.md')
    voice_path = os.path.join(brand_dir, 'voice.md')

    brief = ''
    voice = ''
    if os.path.exists(brief_path):
        brief = open(brief_path, encoding='utf-8').read()
    else:
        print(f"WARNING: brief.md not found at {brief_path}", file=sys.stderr)

    if os.path.exists(voice_path):
        voice = open(voice_path, encoding='utf-8').read()
    else:
        print(f"WARNING: voice.md not found at {voice_path}", file=sys.stderr)

    return brief, voice


def _validate_schema(original, localized, path=''):
    """Recursively validate that localized JSON has identical key structure."""
    errors = []

    if type(original) != type(localized):
        errors.append(f"{path}: type mismatch ({type(original).__name__} vs {type(localized).__name__})")
        return errors

    if isinstance(original, dict):
        orig_keys = set(original.keys())
        loc_keys = set(localized.keys())
        if orig_keys != loc_keys:
            missing = orig_keys - loc_keys
            extra = loc_keys - orig_keys
            if missing:
                errors.append(f"{path}: missing keys {missing}")
            if extra:
                errors.append(f"{path}: extra keys {extra}")
        for key in orig_keys & loc_keys:
            errors.extend(_validate_schema(original[key], localized[key], f"{path}.{key}"))

    elif isinstance(original, list):
        if len(original) != len(localized):
            errors.append(f"{path}: array length mismatch ({len(original)} vs {len(localized)})")
        else:
            for i in range(len(original)):
                errors.extend(_validate_schema(original[i], localized[i], f"{path}[{i}]"))

    return errors


def _validate_immutable(original, localized):
    """Ensure immutable fields are unchanged."""
    errors = []
    for key in IMMUTABLE_KEYS:
        if key in original and key in localized:
            if json.dumps(original[key], sort_keys=True, ensure_ascii=False) != \
               json.dumps(localized[key], sort_keys=True, ensure_ascii=False):
                errors.append(f"Immutable field '{key}' was modified")
    return errors


def _scan_prohibited_words(data, path=''):
    """Scan all string values for prohibited words."""
    found = []
    if isinstance(data, dict):
        for k, v in data.items():
            found.extend(_scan_prohibited_words(v, f"{path}.{k}"))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            found.extend(_scan_prohibited_words(v, f"{path}[{i}]"))
    elif isinstance(data, str):
        for word in PROHIBITED_WORDS:
            if word in data:
                found.append(f"{path}: contains '{word}'")
    return found


def localize(analysis_path, brand='surenxuan', model='gemini-3-flash-preview'):
    """Run localization: analysis JSON → localized JSON (same schema)."""
    from google import genai

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    # Load inputs
    with open(analysis_path, encoding='utf-8') as f:
        original = json.load(f)

    brief, voice = _load_brand_files(brand)
    analysis_text = json.dumps(original, indent=2, ensure_ascii=False)

    prompt = LOCALIZATION_PROMPT_TEMPLATE.format(
        brief_content=brief,
        voice_content=voice,
        analysis_json=analysis_text,
    )

    print(f"Localizing with {model} for brand '{brand}'...")

    # Generate localized version
    response = client.models.generate_content(
        model=model,
        contents=[prompt],
    )

    localized = _parse_gemini_json(response.text)

    # Validate
    schema_errors = _validate_schema(original, localized)
    immutable_errors = _validate_immutable(original, localized)
    prohibited = _scan_prohibited_words(localized)

    all_errors = schema_errors + immutable_errors
    if all_errors:
        print(f"Validation errors ({len(all_errors)}):", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)

        # Retry once with error feedback
        print("Retrying with error feedback...", file=sys.stderr)
        retry_prompt = prompt + f"\n\n⚠️ 上次输出有以下问题，请修正：\n" + \
            "\n".join(f"- {e}" for e in all_errors)

        response = client.models.generate_content(
            model=model,
            contents=[retry_prompt],
        )
        localized = _parse_gemini_json(response.text)

        # Re-validate
        schema_errors = _validate_schema(original, localized)
        immutable_errors = _validate_immutable(original, localized)
        if schema_errors or immutable_errors:
            print(f"Retry still has errors:", file=sys.stderr)
            for e in schema_errors + immutable_errors:
                print(f"  - {e}", file=sys.stderr)
            # Force-fix immutable fields
            for key in IMMUTABLE_KEYS:
                if key in original:
                    localized[key] = original[key]
            print("Force-restored immutable fields.", file=sys.stderr)

    if prohibited:
        print(f"Prohibited word warnings ({len(prohibited)}):", file=sys.stderr)
        for w in prohibited[:10]:
            print(f"  - {w}", file=sys.stderr)

    return localized


def main():
    parser = argparse.ArgumentParser(description='Localize Gemini analysis with brand voice')
    parser.add_argument('analysis', help='Path to Gemini analysis JSON')
    parser.add_argument('--brand', default='surenxuan', help='Brand name (default: surenxuan)')
    parser.add_argument('--model', default='gemini-3-flash-preview', help='Gemini model')
    parser.add_argument('--output', help='Output path (default: {input}_localized.json)')
    args = parser.parse_args()

    if not os.path.exists(args.analysis):
        print(f"ERROR: File not found: {args.analysis}", file=sys.stderr)
        return 1

    try:
        result = localize(args.analysis, brand=args.brand, model=args.model)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Gemini response: {e}", file=sys.stderr)
        return 1

    output_path = args.output or args.analysis.replace('.json', '_localized.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nLocalized analysis saved to {output_path}")
    return 0


if __name__ == '__main__':
    exit(main())
