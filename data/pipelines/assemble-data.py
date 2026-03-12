#!/usr/bin/env python3
"""
数据装配 CLI — 替代 optimization-cycle.sh 中的手工文件读取。

用法:
    # 输出 JSON（供 bash 脚本解析）
    python3 data/pipelines/assemble-data.py --json

    # 输出人类可读格式
    python3 data/pipelines/assemble-data.py

    # 只查管道状态
    python3 data/pipelines/assemble-data.py --status

维护者: EMP_0014
"""
import argparse
import json
import os
import sys

# 确保 mason-hub 在 sys.path
HUB_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HUB_DIR)

from data.tools.pipeline import get_pipeline_status, assemble_optimization_data


def main():
    parser = argparse.ArgumentParser(description='数据装配 CLI')
    parser.add_argument('--json', action='store_true', help='JSON 输出（供脚本解析）')
    parser.add_argument('--status', action='store_true', help='只查管道状态')
    parser.add_argument('--field', type=str, help='只输出某个字段（如 radar_report, xhs_briefing）')
    args = parser.parse_args()

    if args.status:
        status = get_pipeline_status()
        if args.json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(f"=== XHS Pipeline Status ({status['date']}) ===")
            for stage, info in status['stages'].items():
                marker = '[OK]' if info['ok'] else '[PENDING]'
                age = f"{info['age_min']}m ago" if info['ok'] else ''
                print(f"  {marker:10} {stage} {age}")
            ms = status['mirror_sync']
            print(f"\n  Mirror sync: {ms['last_sync'] or 'never'} ({ms['age_hours']}h ago)")
        return

    data = assemble_optimization_data()

    if args.field:
        value = data.get(args.field, '')
        print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
        return

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 人类可读
        print("=== 数据装配结果 ===\n")
        print(f"Gate 1: {data['gate1_result']}")
        print(f"数据源: {data['source_count']}/4 可用")
        if data['sources']:
            for s in data['sources']:
                print(f"  {s}")
        if data['issues']:
            print(f"\n问题 ({data['issue_count']}):")
            for i in data['issues']:
                print(f"  - {i}")

        if data['radar_report']:
            print(f"\n--- Radar 关注率 ---")
            print(data['radar_report'][:500])

        if data['scout_digest']:
            print(f"\n--- Scout 情报 ---")
            print(data['scout_digest'][:500])

        if data['xhs_briefing']:
            print(f"\n--- XHS 简报 ---")
            print(data['xhs_briefing'][:800])


if __name__ == '__main__':
    main()
