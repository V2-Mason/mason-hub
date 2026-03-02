"""逐镜拍摄脚本生成：localized_analysis.json → 可直接拍摄的逐镜脚本 JSON

v3: 骨架锁死 + 跨品类自动适配

核心设计原则：
  localized_analysis.json 的 timeline 是「不可更改的骨架」。
  本步骤只做「骨架 → 逐镜填充」，不允许重新编排结构。

用法：
  python shooting_script.py <localized_analysis.json> \
    [--brand surenxuan] \
    [--product-override products.json] \
    [--output shooting_script.json]

输出：
  segments[].shots[] 层级结构，每个 shot 包含完整拍摄指令
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gemini_analyze import _parse_gemini_json
from localize import _load_brand_files

CRED_DIR = os.path.expanduser('~/mason-hub/.credentials')

# ═══════════════════════════════════════════════════════════════════
# 禁用词（从 localize.py 同步）
# ═══════════════════════════════════════════════════════════════════

PROHIBITED_WORDS = [
    '美白', '祛痘', '祛斑', '抗衰老',
    '绝绝子', 'yyds', '天花板', '封神', '无敌好用',
    '宝子', '家人们', '集美',
    '一定要冲', '必入', '闭眼入',
    '治疗', '治愈', '药用',
]

# ═══════════════════════════════════════════════════════════════════
# Voice 精简摘要（避免 prompt 过长）
# ═══════════════════════════════════════════════════════════════════

VOICE_SUMMARY = """
核心人设：懂韩妆的邻家姐姐，真诚分享自己用出来的经验。
关键词：真诚、从容、有判断力、接地气、不急不躁。

语速：中速偏慢，允许停顿，每个产品 20-30 秒。
情绪：平稳中有亮点，不全程高能。温和笃定为主，效果惊喜时自然上扬。
称呼：受众用"姐妹"，自称"我"，偶尔用"咱们这个年纪"。

Hook 模式：痛点条件句前置型 —— "到了[年龄/阶段]，[具体痛点]，[解决方案预告]"
产品介绍：先说"为什么需要"（停留5秒建立共鸣），再说"这个怎么样"。
说服技巧：建议式推荐（不用命令式），同龄验证（不用"韩女人手一支"），具体化评价（不用"超级好用"）。
结尾：温和引导型 —— "感兴趣的姐妹可以先收藏"。
价格：模糊区间（"百元出头""不到两百"），不报精确数字。

绝对禁用：美白/祛痘/祛斑/抗衰老/治疗/治愈/药用
风格禁用：宝子/家人们/集美/绝绝子/yyds/天花板/封神/一定要冲/闭眼入/超级无敌好用
"""

# ═══════════════════════════════════════════════════════════════════
# 核心 Prompt
# ═══════════════════════════════════════════════════════════════════

SCRIPT_GENERATOR_PROMPT = """你是一位专业的短视频导演和脚本编剧，专注于小红书/抖音的美妆护肤类内容。

你的任务是：将一份「竞品视频本地化分析」转化为一份「可直接拍摄的逐镜脚本」。

═══════════════════════════════════════════
⚠️ 最重要的规则（违反任何一条都算失败）：
═══════════════════════════════════════════

1. 【骨架锁死】输入 JSON 的 content_structure.timeline 是不可更改的骨架。
   - 段落数量：必须和 timeline 数组长度完全一致（本次为 {segment_count} 段）
   - 段落类型：每段的 segment_type 不可更改
   - 段落顺序：不可调换
   - 时间分配：每段的秒数范围必须在原始 timestamp 的 ±3 秒以内
   - 内容逻辑流：每段要完成的「功能」（hook引注意力 → 过渡建信任 → 演示教方法 → 展示出效果）不可更改

2. 【产品替换规则 — 同品类 vs 跨品类自动适配】

   ■ 如果没有提供 product_override：
     保持原视频的产品品类，去掉竞品品牌名即可。

   ■ 如果提供了 product_override，先判断替换类型：

   A）同品类替换（原视频推化妆刷 → 换素仁轩的化妆刷）：
      - 骨架完全锁死，教程步骤不变，只换品牌和话术
      - 例：原视频"凡士林涂刷毛→纸巾打圈" → 保持一模一样的操作步骤

   B）跨品类替换（原视频推化妆刷 → 换素仁轩的精华/面霜）：
      - 此时不能锁具体操作步骤（"给精华液开刷"是荒谬的）
      - 改为锁「结构公式」层面：

        锁死的是：
        ✅ 段落数量
        ✅ 段落类型和顺序
        ✅ 每段的时长范围（±3秒）
        ✅ 每段的「叙事功能」

        自动替换的是：
        🔄 痛点场景（根据新产品的 target_concern）
        🔄 演示段的具体操作（根据新产品的 demo_action）
        🔄 效果展示的画面（根据新产品的 core_selling_point）

      - product_override JSON 中的 demo_action 字段就是新产品的操作步骤，直接填入演示段

   ■ 判断依据：比较 product_override 中的 replacement_category 与原视频 product_catalog 中的 product_type。
     如果品类词完全匹配或属于同一品类 → 同品类模式 A
     否则 → 跨品类模式 B

3. 【镜头颗粒度】每个 timeline 段落必须拆解为 1-4 个具体镜头（shot）。
   拆解依据：
   - 5秒以内的段落 → 1个镜头
   - 5-15秒的段落 → 1-2个镜头
   - 15-30秒的段落 → 2-3个镜头
   - 30秒以上的段落 → 3-4个镜头
   总镜头数建议在 8-15 之间。

4. 【口播文案必须符合品牌 voice】
   所有口播文案必须遵守品牌语言风格指南（见下方）。特别是：
   - 称呼用"姐妹"，不用"宝子/家人们/集美"
   - 语气温和笃定，不用"绝绝子/yyds/天花板/封神"
   - 说服方式用"建议式推荐"，不用"命令式安利"
   - 结尾用"感兴趣的姐妹可以先收藏"，不用"一定要冲/闭眼入"
   - 禁用词：美白→提亮、祛痘→改善痘痘、祛斑→淡化色斑、抗衰老→抗初老
   - 不报精确价格，用模糊区间（"百元出头""不到两百"）

═══════════════════════════════════════════
输出 JSON 结构
═══════════════════════════════════════════

{{
  "script_metadata": {{
    "source_video_duration": "原视频时长",
    "target_video_duration": "目标视频时长（应与原视频接近，±10秒以内）",
    "total_segments": "段落数（必须等于原始 timeline 段落数）",
    "total_shots": "总镜头数",
    "target_platform": "小红书短视频",
    "aspect_ratio": "9:16 竖版",
    "brand": "素仁轩",
    "content_type": "从原始分析继承",
    "replacement_mode": "none / same_category / cross_category"
  }},

  "segments": [
    {{
      "segment_index": 1,
      "segment_type": "从原始 timeline 继承，不可更改",
      "original_timestamp": "从原始 timeline 继承",
      "target_duration_seconds": "目标秒数（在原始范围 ±3秒内）",
      "segment_function": "这个段落要完成的功能（用一句话说清楚）",

      "shots": [
        {{
          "shot_index": "全局镜头编号（1, 2, 3...跨段落连续编号）",
          "duration_seconds": "这个镜头的秒数",
          "shot_type": "景别（特写/中景/全景/微距/肩上/俯拍）",
          "camera_movement": "镜头运动（固定/缓慢推近/跟拍手部/无）",
          "frame_description": "画面内容的详细描述（导演视角：谁在哪里做什么，构图怎样）",
          "voiceover": "这个镜头对应的口播文案原文（如无口播写'无口播'）",
          "text_overlay": "字幕或贴纸文字（如无写'无'）",
          "props": "这个镜头需要的道具清单",
          "lighting_note": "打光注意事项（同全局则写'同全局'）",
          "audio_note": "音效/BGM 注意事项",
          "acting_direction": "表演指导（表情、情绪、动作要点）"
        }}
      ]
    }}
  ],

  "global_production_notes": {{
    "location": "拍摄场景建议",
    "wardrobe": "服装建议",
    "lighting_setup": "整体打光方案",
    "bgm_suggestion": "BGM 风格建议",
    "editing_notes": "后期剪辑注意事项",
    "props_checklist": "所有道具汇总清单（去重后）",
    "estimated_raw_footage": "预估原始素材时长"
  }},

  "voiceover_full_script": "所有口播文案拼接成完整口播稿（方便博主提前练习）"
}}

═══════════════════════════════════════════
品牌资料
═══════════════════════════════════════════

=== 品牌 Brief ===
{brief_content}

=== 品牌语言风格指南（关键摘要）===
{voice_summary}

═══════════════════════════════════════════
产品替换指令
═══════════════════════════════════════════

{product_override_instruction}

═══════════════════════════════════════════
输入：竞品视频本地化分析 JSON
═══════════════════════════════════════════

{localized_analysis_json}

═══════════════════════════════════════════
执行检查清单（生成前自查）
═══════════════════════════════════════════

□ 段落数量是否等于 {segment_count}？
□ 每个段落的 segment_type 是否和原始 timeline 完全一致？
□ 每个段落的 target_duration_seconds 是否在原始 timestamp 的 ±3秒范围内？
□ 总视频时长是否和原视频接近（±10秒）？
□ 口播文案是否符合品牌 voice（无禁用词、无夸张表达、称呼用"姐妹"）？
□ 每个镜头是否有足够的拍摄指导（景别、构图、表情、道具）？
□ voiceover_full_script 是否完整拼接了所有口播？

只输出 JSON，不要其他文字。确保 JSON 格式正确。"""


# ═══════════════════════════════════════════════════════════════════
# 验证
# ═══════════════════════════════════════════════════════════════════

def _validate_script(script, original_timeline):
    """验证生成的脚本是否遵守骨架约束。"""
    errors = []
    warnings = []

    segments = script.get('segments', [])
    orig_count = len(original_timeline)

    # 1. 段落数量
    if len(segments) != orig_count:
        errors.append(
            f"段落数量不匹配：原始 {orig_count} 段，生成 {len(segments)} 段"
        )

    # 2. 段落类型匹配
    for i, (seg, orig) in enumerate(zip(segments, original_timeline)):
        orig_type = orig.get('segment_type', '')
        gen_type = seg.get('segment_type', '')
        if orig_type != gen_type:
            errors.append(
                f"段落 {i+1} 类型不匹配：原始'{orig_type}'，生成'{gen_type}'"
            )

        # 3. 时长范围检查（±3秒）
        orig_ts = orig.get('timestamp', '')
        if ' - ' in orig_ts:
            parts = orig_ts.split(' - ')
            try:
                start_parts = parts[0].strip().split(':')
                end_parts = parts[1].strip().split(':')
                orig_duration = (
                    (int(end_parts[0]) * 60 + int(end_parts[1]))
                    - (int(start_parts[0]) * 60 + int(start_parts[1]))
                )
                gen_duration = seg.get('target_duration_seconds', 0)
                if isinstance(gen_duration, str):
                    gen_duration = int(gen_duration)
                if abs(gen_duration - orig_duration) > 3:
                    warnings.append(
                        f"段落 {i+1} 时长偏差：原始 {orig_duration}s，"
                        f"生成 {gen_duration}s（允许 ±3s）"
                    )
            except (ValueError, IndexError):
                pass

    # 4. 禁用词扫描
    def _scan_text(data, path=''):
        found = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in ('voiceover', 'voiceover_full_script', 'text_overlay'):
                    if isinstance(v, str):
                        for word in PROHIBITED_WORDS:
                            if word in v:
                                found.append(f"{path}.{k}: 包含禁用词'{word}'")
                else:
                    found.extend(_scan_text(v, f"{path}.{k}"))
        elif isinstance(data, list):
            for i, v in enumerate(data):
                found.extend(_scan_text(v, f"{path}[{i}]"))
        return found

    prohibited = _scan_text(script)
    for p in prohibited:
        errors.append(f"禁用词违规：{p}")

    # 5. 镜头数量合理性
    total_shots = sum(len(seg.get('shots', [])) for seg in segments)
    if total_shots < 5:
        warnings.append(f"总镜头数过少：{total_shots}（建议 8-15）")
    elif total_shots > 20:
        warnings.append(f"总镜头数过多：{total_shots}（建议 8-15）")

    return errors, warnings


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def flatten_shots(script):
    """将 segments[].shots[] 层级结构展平为 flat shot 列表。

    给下游（storyboard / videogen / pencil）使用。
    每个 shot 会被注入 segment_index 和 segment_type。
    """
    flat = []
    for seg in script.get('segments', []):
        seg_idx = seg.get('segment_index', 0)
        seg_type = seg.get('segment_type', '')
        for shot in seg.get('shots', []):
            shot_with_ctx = dict(shot)
            shot_with_ctx['segment_index'] = seg_idx
            shot_with_ctx['segment_type'] = seg_type
            flat.append(shot_with_ctx)
    return flat


# ═══════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════

def generate_script(analysis_path, brand='surenxuan',
                    product_override_path=None, model='gemini-2.5-flash'):
    """主流程：localized_analysis.json → shooting_script.json"""
    from google import genai

    api_key = open(os.path.join(CRED_DIR, 'gemini-api-key.txt')).read().strip()
    client = genai.Client(api_key=api_key)

    # 加载输入
    with open(analysis_path, encoding='utf-8') as f:
        analysis = json.load(f)

    timeline = analysis.get('content_structure', {}).get('timeline', [])
    if not timeline:
        raise ValueError("输入 JSON 中没有 content_structure.timeline")

    segment_count = len(timeline)

    # 加载品牌资料
    brief, _ = _load_brand_files(brand)

    # 产品替换指令（自动检测同品类/跨品类）
    product_instruction = "未提供产品替换列表。请保持原视频的产品品类，但去掉竞品品牌名。"
    if product_override_path and os.path.exists(product_override_path):
        with open(product_override_path, encoding='utf-8') as f:
            products = json.load(f)

        # 检测同品类 vs 跨品类
        original_categories = set()
        for p in analysis.get('product_catalog', []):
            original_categories.add(p.get('product_type', '').lower())

        replacement_categories = set()
        for p in products:
            replacement_categories.add(p.get('replacement_category', '').lower())

        is_cross_category = True
        for rc in replacement_categories:
            for oc in original_categories:
                if rc in oc or oc in rc:
                    is_cross_category = False
                    break

        if is_cross_category:
            mode_label = "⚠️ 检测到跨品类替换（模式B）"
            mode_instruction = (
                "原视频产品品类和素仁轩产品品类不同，请使用模式B：\n"
                "- 锁定「结构公式」（段落数/类型/顺序/时长/叙事功能），不锁具体操作步骤\n"
                "- 用新产品的 demo_action 替换原视频演示段的具体操作\n"
                "- 用新产品的 target_concern 替换 hook 段的痛点场景\n"
                "- 用新产品的 core_selling_point 替换效果展示段的画面描述\n"
            )
        else:
            mode_label = "✅ 检测到同品类替换（模式A）"
            mode_instruction = (
                "原视频产品品类和素仁轩产品品类相同，请使用模式A：\n"
                "- 完全锁死骨架，包括具体操作步骤\n"
                "- 只替换品牌名和话术调性\n"
            )

        product_instruction = (
            f"{mode_label}\n\n"
            f"{mode_instruction}\n"
            f"素仁轩替换产品列表：\n"
            + json.dumps(products, indent=2, ensure_ascii=False)
        )

    # 组装 prompt
    prompt = SCRIPT_GENERATOR_PROMPT.format(
        segment_count=segment_count,
        brief_content=brief,
        voice_summary=VOICE_SUMMARY,
        product_override_instruction=product_instruction,
        localized_analysis_json=json.dumps(analysis, indent=2, ensure_ascii=False),
    )

    print(f"Generating shooting script with {model} for brand '{brand}'...")
    print(f"  骨架: {segment_count} 段 timeline")

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
    )

    script = _parse_gemini_json(response.text)

    # 验证
    errors, warnings = _validate_script(script, timeline)

    if errors:
        print(f"\n❌ 验证错误 ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

        # 重试一次
        print("重试中（附带错误反馈）...", file=sys.stderr)
        retry_prompt = (
            prompt
            + "\n\n⚠️ 上次生成有以下严重错误，请务必修正：\n"
            + "\n".join(f"- {e}" for e in errors)
        )

        response = client.models.generate_content(
            model=model,
            contents=[retry_prompt],
        )
        script = _parse_gemini_json(response.text)

        errors2, warnings2 = _validate_script(script, timeline)
        if errors2:
            print(f"\n❌ 重试后仍有错误 ({len(errors2)}):", file=sys.stderr)
            for e in errors2:
                print(f"  - {e}", file=sys.stderr)
        warnings = warnings2

    if warnings:
        print(f"\n⚠️ 警告 ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    total_shots = sum(len(s.get('shots', [])) for s in script.get('segments', []))
    print(f"  Generated {total_shots} shots across {segment_count} segments")

    return script


def main():
    parser = argparse.ArgumentParser(description='从本地化分析生成逐镜拍摄脚本')
    parser.add_argument('analysis', help='localized_analysis.json 路径')
    parser.add_argument('--brand', default='surenxuan', help='品牌名（默认 surenxuan）')
    parser.add_argument('--product-override', default=None,
                        help='产品替换 JSON 文件路径')
    parser.add_argument('--model', default='gemini-2.5-flash', help='Gemini 模型')
    parser.add_argument('--output', help='输出路径（默认 {input_dir}/shooting_script.json）')
    args = parser.parse_args()

    if not os.path.exists(args.analysis):
        print(f"ERROR: 文件不存在: {args.analysis}", file=sys.stderr)
        return 1

    try:
        result = generate_script(
            args.analysis, brand=args.brand,
            product_override_path=args.product_override,
            model=args.model,
        )
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON 解析失败: {e}", file=sys.stderr)
        return 1

    output_path = args.output or os.path.join(
        os.path.dirname(args.analysis) or '.', 'shooting_script.json'
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 摘要
    segments = result.get('segments', [])
    total_shots = sum(len(s.get('shots', [])) for s in segments)
    meta = result.get('script_metadata', {})

    print(f"\n✅ 脚本已生成: {output_path}")
    print(f"   段落数: {len(segments)}")
    print(f"   总镜头数: {total_shots}")
    print(f"   目标时长: {meta.get('target_video_duration', 'N/A')}")

    # 简表
    print(f"\n{'Shot':>4} | {'段落类型':<10} | {'秒数':>4} | {'内容':<30} | {'道具':<15}")
    print("-" * 80)
    for seg in segments:
        for shot in seg.get('shots', []):
            desc = shot.get('frame_description', '')[:28]
            props = shot.get('props', '')
            if isinstance(props, list):
                props = ', '.join(str(p) for p in props)
            props = str(props)[:13] if props else '无'
            print(
                f"{shot.get('shot_index', '?'):>4} | "
                f"{seg.get('segment_type', '?'):<10} | "
                f"{shot.get('duration_seconds', '?'):>4} | "
                f"{desc:<30} | "
                f"{props:<15}"
            )

    return 0


if __name__ == '__main__':
    exit(main())
