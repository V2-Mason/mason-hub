"""生成 Pencil 画布文件（.pen）用于分镜/素材预览

将 shooting_script.json + 生成的分镜图排列在 Pencil 无限画布上，
Mason 在 VSCode 里打开 .pen 文件即可看到完整分镜全貌。

用法：
  python pencil_storyboard.py <shooting_script.json> --images-dir ./storyboard/ [--output storyboard.pen]

.pen 格式参考：https://docs.pencil.dev/for-developers/the-pen-format
"""
import argparse
import json
import os
import sys
from datetime import datetime


# 布局常量
CARD_W = 280
CARD_GAP = 40
IMG_H = 400          # 9:16 比例显示高度
LABEL_H = 28
TS_H = 16
VOICEOVER_H = 56
CARD_PADDING = 12
CARD_H = CARD_PADDING * 2 + LABEL_H + TS_H + IMG_H + VOICEOVER_H + 24  # 内部间距
START_X = 80
START_Y = 180
COLS = 5


def _make_text(id, x, y, content, font_size=14, font_weight="400",
               fill="#333333", width=None, height=None, text_growth=None):
    """构造一个 text 节点。"""
    node = {
        "id": id,
        "type": "text",
        "x": x,
        "y": y,
        "content": content,
        "fontSize": font_size,
        "fontFamily": "Inter",
        "fontWeight": font_weight,
        "fill": fill,
    }
    if width is not None:
        node["width"] = width
    if height is not None:
        node["height"] = height
    if text_growth:
        node["textGrowth"] = text_growth
    return node


def _make_card(shot_id, idx, shot, images_dir, pen_dir):
    """构造一张 shot 卡片（frame 节点 + children）。"""
    col = idx % COLS
    row = idx // COLS
    card_x = START_X + col * (CARD_W + CARD_GAP)
    card_y = START_Y + row * (CARD_H + CARD_GAP)

    inner_w = CARD_W - CARD_PADDING * 2

    children = []
    cy = CARD_PADDING  # 当前 y 偏移

    # 标签
    label = shot.get('label', f'Shot {idx + 1}')
    children.append(_make_text(
        f"label-{shot_id}", CARD_PADDING, cy,
        label, font_size=14, font_weight="600", fill="#1a1a1a",
    ))
    cy += LABEL_H

    # 时间戳
    ts = shot.get('timestamp', '')
    if ts:
        children.append(_make_text(
            f"ts-{shot_id}", CARD_PADDING, cy,
            ts, font_size=11, fill="#999999",
        ))
    cy += TS_H + 4

    # 图片区域
    img_file = shot.get('image_file', '')
    img_abs = os.path.join(images_dir, img_file) if img_file else ''
    img_exists = img_abs and os.path.isfile(img_abs)

    if img_exists:
        # 计算相对路径：从 .pen 文件所在目录到图片
        rel_path = os.path.relpath(img_abs, pen_dir)
        children.append({
            "id": f"img-{shot_id}",
            "type": "rectangle",
            "x": CARD_PADDING,
            "y": cy,
            "width": inner_w,
            "height": IMG_H,
            "cornerRadius": 8,
            "fill": {
                "type": "image",
                "url": rel_path,
                "mode": "fit",
            },
        })
    else:
        # 占位符
        children.append({
            "id": f"img-{shot_id}",
            "type": "rectangle",
            "x": CARD_PADDING,
            "y": cy,
            "width": inner_w,
            "height": IMG_H,
            "cornerRadius": 8,
            "fill": "#F0F0F0",
        })
        children.append(_make_text(
            f"ph-{shot_id}", CARD_PADDING + 80, cy + IMG_H // 2 - 8,
            "pending...", font_size=13, fill="#BBBBBB",
        ))
    cy += IMG_H + 8

    # 口播文案
    vo = shot.get('voiceover', '')
    if vo:
        display = vo[:80] + ('...' if len(vo) > 80 else '')
        children.append(_make_text(
            f"vo-{shot_id}", CARD_PADDING, cy,
            display, font_size=11, fill="#666666",
            width=inner_w, height=VOICEOVER_H,
            text_growth="fixed-width",
        ))

    card = {
        "id": f"card-{shot_id}",
        "type": "frame",
        "x": card_x,
        "y": card_y,
        "width": CARD_W,
        "height": CARD_H,
        "cornerRadius": 12,
        "fill": "#FFFFFF",
        "stroke": {"fill": "#E0E0E0", "thickness": 1},
        "effect": {
            "type": "shadow",
            "shadowType": "outer",
            "offset": {"x": 0, "y": 2},
            "blur": 8,
            "color": "#00000015",
        },
        "clip": True,
        "children": children,
    }
    return card


def generate_pen_from_script(script_path, images_dir, output_path):
    """从 shooting_script.json + 分镜图目录生成 .pen 画布文件。

    Args:
        script_path: shooting_script.json 路径
        images_dir: 分镜图 PNG 所在目录（绝对路径）
        output_path: 输出 .pen 文件路径

    Returns:
        output_path
    """
    with open(script_path, encoding='utf-8') as f:
        script = json.load(f)

    meta = script.get('script_metadata', {})
    brief = script.get('creative_brief', {})

    # 提取 flat shot 列表，兼容 v2(shots[]) 和 v3(segments[].shots[])
    if 'segments' in script:
        shots_data = []
        for seg in script['segments']:
            for shot in seg.get('shots', []):
                shot_with_ctx = dict(shot)
                shot_with_ctx['_segment_type'] = seg.get('segment_type', '')
                shots_data.append(shot_with_ctx)
    else:
        shots_data = script.get('shots', [])

    # 组装 shot 列表（统一格式给 card 构造器）
    shots = []
    for i, s in enumerate(shots_data):
        # shot_type: v3 uses shot_type as framing, _segment_type as content type
        seg_type = s.get('_segment_type', '')
        shot_type = seg_type or s.get('shot_type', 'unknown')
        shot_num = f"{i + 1:03d}"

        # voiceover: v3 is string, v2 is dict
        vo = s.get('voiceover', '')
        if isinstance(vo, dict):
            vo_text = vo.get('text', '')
        else:
            vo_text = str(vo)

        # Duration: v3 is integer seconds, v2 is "0-6" range
        dur = str(s.get('duration_seconds', ''))
        if '-' in dur:
            try:
                parts = dur.split('-')
                start_s, end_s = int(parts[0].strip()), int(parts[1].strip())
                dur = f"{start_s // 60}:{start_s % 60:02d} - {end_s // 60}:{end_s % 60:02d}"
            except (ValueError, IndexError):
                pass
        elif dur.isdigit():
            dur = f"{dur}s"

        shots.append({
            'id': f"shot_{shot_num}",
            'label': f"Shot {i + 1} · {shot_type}",
            'timestamp': dur,
            'voiceover': vo_text,
            'image_file': f"shot_{shot_num}_{shot_type}.png",
        })

    pen_dir = os.path.dirname(os.path.abspath(output_path))
    images_dir_abs = os.path.abspath(images_dir)

    children = []

    # 标题
    title = (meta.get('content_topic', '')
             or meta.get('content_type', '')
             or brief.get('one_line_concept', '')
             or '分镜预览')
    children.append(_make_text(
        "title", START_X, 40, title,
        font_size=32, font_weight="bold", fill="#1a1a1a",
    ))

    # 副标题（元数据）
    brand = meta.get('brand', '')
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    subtitle = f"{brand} | {len(shots)} 个镜头 | {now_str}"
    children.append(_make_text(
        "subtitle", START_X, 90, subtitle,
        font_size=14, fill="#888888",
    ))

    # Hook 概要
    hook = brief.get('hook_strategy', '')
    if hook:
        children.append(_make_text(
            "hook-summary", START_X, 120, f"Hook: {hook[:100]}",
            font_size=12, fill="#AA6600",
        ))

    # Shot 卡片
    for i, shot in enumerate(shots):
        card = _make_card(shot['id'], i, shot, images_dir_abs, pen_dir)
        children.append(card)

    # 底部合规检查（如果有）
    checklist = script.get('brand_compliance_checklist', {})
    if checklist:
        bottom_y = START_Y + ((len(shots) - 1) // COLS + 1) * (CARD_H + CARD_GAP) + 20
        items = []
        for k, v in checklist.items():
            mark = 'pass' if v in (True, 'pass', 'ok') else str(v)
            items.append(f"{k}: {mark}")
        checklist_text = "Brand Compliance: " + " | ".join(items)
        children.append(_make_text(
            "compliance", START_X, bottom_y, checklist_text,
            font_size=12, fill="#558855",
        ))

    pen_doc = {
        "version": "1.0.0",
        "children": children,
    }

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pen_doc, f, indent=2, ensure_ascii=False)

    print(f"Pencil storyboard: {output_path} ({len(shots)} cards)")
    return output_path


def generate_pen_from_images(images_dir, output_path, title="素材预览",
                              labels=None):
    """简化版：只从图片目录生成 .pen（不需要 shooting_script）。

    用于电商素材等不依赖拍摄脚本的场景。

    Args:
        images_dir: 图片目录
        output_path: 输出 .pen 文件路径
        title: 画布标题
        labels: 可选 dict {filename: label}
    """
    pen_dir = os.path.dirname(os.path.abspath(output_path))
    images_dir_abs = os.path.abspath(images_dir)

    # 收集图片
    image_files = sorted(
        f for f in os.listdir(images_dir_abs)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    )

    if not image_files:
        print(f"No images found in {images_dir}", file=sys.stderr)
        return None

    shots = []
    for i, fname in enumerate(image_files):
        label = (labels or {}).get(fname, fname.rsplit('.', 1)[0])
        shots.append({
            'id': f"img_{i + 1:03d}",
            'label': label,
            'timestamp': '',
            'voiceover': '',
            'image_file': fname,
        })

    children = []

    children.append(_make_text(
        "title", START_X, 40, title,
        font_size=32, font_weight="bold", fill="#1a1a1a",
    ))
    children.append(_make_text(
        "subtitle", START_X, 90,
        f"{len(shots)} images | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        font_size=14, fill="#888888",
    ))

    for i, shot in enumerate(shots):
        card = _make_card(shot['id'], i, shot, images_dir_abs, pen_dir)
        children.append(card)

    pen_doc = {"version": "1.0.0", "children": children}

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pen_doc, f, indent=2, ensure_ascii=False)

    print(f"Pencil board: {output_path} ({len(shots)} cards)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Generate Pencil storyboard canvas')
    parser.add_argument('input', help='Path to shooting_script.json or image directory')
    parser.add_argument('--images-dir', help='Directory with storyboard PNGs')
    parser.add_argument('--output', help='Output .pen file path')
    parser.add_argument('--title', default=None, help='Canvas title')
    args = parser.parse_args()

    if os.path.isdir(args.input):
        # 纯图片模式
        images_dir = args.input
        output = args.output or os.path.join(images_dir, 'preview.pen')
        generate_pen_from_images(images_dir, output, title=args.title or '素材预览')
    elif os.path.isfile(args.input):
        # 从 shooting_script.json
        images_dir = args.images_dir
        if not images_dir:
            images_dir = os.path.join(os.path.dirname(args.input) or '.', 'storyboard')
        output = args.output or args.input.replace('.json', '.pen')
        generate_pen_from_script(args.input, images_dir, output)
    else:
        print(f"ERROR: Not found: {args.input}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
