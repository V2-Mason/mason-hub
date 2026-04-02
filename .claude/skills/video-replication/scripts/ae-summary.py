#!/usr/bin/env python3
"""解析 AE Full Export JSON，输出 comp 树和层级摘要。

Usage: python ae-summary.py <ae_full_export.json>

输出每个 comp 的层级结构，标注：
- [MATTE] Track Matte 层
- [TM:5013] Alpha Matte / [TM:5014] Alpha Inverted
- [3D] 3D 层
- [CAM] Camera
- [ANIM] 有动画的属性
"""
import json
import sys

def summarize(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)

    for cid, comp in d['comps'].items():
        name = comp['name']
        layers = comp['layers']
        print(f"\n{'='*60}")
        print(f"  {name} ({len(layers)} layers)")
        print(f"{'='*60}")

        for i, layer in enumerate(layers):
            flags = []
            if layer.get('isTrackMatte'):
                flags.append('MATTE')
            if layer.get('trackMatteType'):
                flags.append(f"TM:{layer['trackMatteType']}")
            if layer.get('threeDLayer'):
                flags.append('3D')
            if layer.get('type') == 'camera':
                flags.append('CAM')

            # Check animated properties
            anim_props = []
            if 'transform' in layer:
                for prop_name, prop in layer['transform'].items():
                    if isinstance(prop, dict) and prop.get('animated'):
                        anim_props.append(prop_name)
            if anim_props:
                flags.append(f"ANIM:{','.join(anim_props)}")

            # Stretch
            stretch = layer.get('stretch', 100)
            if stretch != 100:
                flags.append(f"stretch={stretch}%")

            flag_str = f" [{' | '.join(flags)}]" if flags else ''
            ltype = layer.get('type', '?')
            idx = layer.get('index', '?')
            print(f"  [{i}] {layer['name']} (type={ltype}, idx={idx}){flag_str}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <ae_full_export.json>")
        sys.exit(1)
    summarize(sys.argv[1])
