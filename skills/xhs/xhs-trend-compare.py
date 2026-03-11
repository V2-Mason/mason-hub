"""
xhs-trend-compare.py — 周度趋势对比

用法: python xhs-trend-compare.py <current_analysis.json> [--prev <prev_analysis.json>]

自动在同目录找上一期分析 JSON。首次运行输出 baseline。
输出: analysis/trends/YYYY-MM-DD.json
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime


def find_previous_analysis(current_path: str) -> str:
    """Find the most recent analysis JSON before current one."""
    analysis_dir = os.path.dirname(current_path)
    current_name = os.path.basename(current_path)
    # Match analysis_YYYY-MM-DD.json or analysis_YYYY-MM-DD_enriched.json
    pattern = os.path.join(analysis_dir, 'analysis_*.json')
    candidates = []
    for f in sorted(glob.glob(pattern)):
        name = os.path.basename(f)
        if name == current_name:
            continue
        if '_enriched' in name:
            continue
        candidates.append(f)

    if not candidates:
        return ''

    # Return the most recent one before current (sorted alphabetically = chronologically for YYYY-MM-DD)
    candidates.sort(reverse=True)
    for c in candidates:
        if os.path.basename(c) < current_name:
            return c
    return ''


def compare_keywords(current_kw, prev_kw):
    """Compare keyword insights between two periods."""
    curr_map = {k['keyword']: k for k in current_kw}
    prev_map = {k['keyword']: k for k in prev_kw}

    all_keywords = set(list(curr_map.keys()) + list(prev_map.keys()))
    trends = []

    for kw in all_keywords:
        curr = curr_map.get(kw)
        prev = prev_map.get(kw)

        if curr and not prev:
            trends.append({
                'keyword': kw,
                'status': 'new',
                'avg_score': curr['avg_score'],
                'count': curr.get('count', 0),
                'avg_score_change_pct': None,
                'caveat': '新进关键词，无历史对比',
            })
        elif prev and not curr:
            trends.append({
                'keyword': kw,
                'status': 'dropped',
                'avg_score': 0,
                'prev_avg_score': prev['avg_score'],
                'count': 0,
                'avg_score_change_pct': -100,
                'caveat': '本期未出现，可能是采集关键词变更而非真实衰退',
            })
        elif curr and prev:
            prev_score = prev['avg_score']
            curr_score = curr['avg_score']
            if prev_score > 0:
                change_pct = round((curr_score - prev_score) / prev_score * 100)
            else:
                change_pct = 100 if curr_score > 0 else 0

            if change_pct > 15:
                status = 'rising'
            elif change_pct < -15:
                status = 'declining'
            else:
                status = 'stable'

            sample = curr.get('count', 0)
            caveat = ''
            if sample < 10:
                caveat = f'仅 {sample} 条样本，波动可能是噪音'
            elif abs(change_pct) > 50:
                caveat = f'变化幅度大（{change_pct:+d}%），建议等下一期确认趋势'

            trends.append({
                'keyword': kw,
                'status': status,
                'avg_score': curr_score,
                'prev_avg_score': prev_score,
                'count': sample,
                'prev_count': prev.get('count', 0),
                'avg_score_change_pct': change_pct,
                'caveat': caveat,
            })

    # Sort: rising first, then new, stable, declining, dropped
    order = {'rising': 0, 'new': 1, 'stable': 2, 'declining': 3, 'dropped': 4}
    trends.sort(key=lambda x: (order.get(x['status'], 9), -abs(x.get('avg_score_change_pct') or 0)))
    return trends


def compare_formats(current, prev):
    """Compare content format distribution changes."""
    curr_ct = current.get('content_type', {})
    prev_ct = prev.get('content_type', {})

    curr_video_ratio = curr_ct.get('video_ratio', 0)
    prev_video_ratio = prev_ct.get('video_ratio', 0)
    ratio_change = curr_video_ratio - prev_video_ratio

    curr_video_avg = curr_ct.get('video_avg_score', 0)
    prev_video_avg = prev_ct.get('video_avg_score', 0)
    curr_normal_avg = curr_ct.get('normal_avg_score', 0)
    prev_normal_avg = prev_ct.get('normal_avg_score', 0)

    # Current gap
    curr_gap = curr_video_avg / max(curr_normal_avg, 1)
    prev_gap = prev_video_avg / max(prev_normal_avg, 1)

    return {
        'video_ratio': {
            'current': curr_video_ratio,
            'previous': prev_video_ratio,
            'change': ratio_change,
        },
        'video_vs_normal_gap': {
            'current_ratio': round(curr_gap, 2),
            'previous_ratio': round(prev_gap, 2),
            'change': round(curr_gap - prev_gap, 2),
            'caveat': '互动分差距受平台算法影响，不一定反映用户偏好',
        },
    }


def compare_volume(current, prev):
    """Compare data volume changes."""
    curr_total = current.get('meta', {}).get('total_notes', 0)
    prev_total = prev.get('meta', {}).get('total_notes', 0)
    return {
        'current_notes': curr_total,
        'previous_notes': prev_total,
        'change': curr_total - prev_total,
        'caveat': '数量变化可能反映采集范围变化，而非市场变化' if abs(curr_total - prev_total) > prev_total * 0.3 else '',
    }


def generate_trend_report(current_path: str, prev_path: str) -> dict:
    with open(current_path, encoding='utf-8') as f:
        current = json.load(f)

    today = datetime.now().strftime('%Y-%m-%d')

    if not prev_path:
        return {
            'date': today,
            'type': 'baseline',
            'message': '首次分析，无历史对比。本报告作为基准线。',
            'current_file': os.path.basename(current_path),
            'meta': current.get('meta', {}),
            'keyword_baseline': current.get('keyword_insights', []),
            'format_baseline': current.get('content_type', {}),
        }

    with open(prev_path, encoding='utf-8') as f:
        prev = json.load(f)

    keyword_trends = compare_keywords(
        current.get('keyword_insights', []),
        prev.get('keyword_insights', []),
    )

    format_changes = compare_formats(current, prev)
    volume_changes = compare_volume(current, prev)

    return {
        'date': today,
        'type': 'comparison',
        'current_file': os.path.basename(current_path),
        'previous_file': os.path.basename(prev_path),
        'keyword_trends': keyword_trends,
        'format_changes': format_changes,
        'volume_changes': volume_changes,
        'known_limitations': [
            '趋势基于两期数据对比，至少需要 3 期才能确认趋势方向',
            '采集关键词变更会导致假性趋势（关键词新增/消失）',
            '样本量小的关键词波动大，不一定反映真实市场变化',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description='XHS trend comparison')
    parser.add_argument('current_json', help='Path to current analysis JSON')
    parser.add_argument('--prev', help='Path to previous analysis JSON (auto-detect if omitted)')
    args = parser.parse_args()

    if not os.path.exists(args.current_json):
        print(f'ERROR: {args.current_json} not found')
        return 1

    prev_path = args.prev or find_previous_analysis(args.current_json)
    if prev_path and not os.path.exists(prev_path):
        print(f'WARNING: {prev_path} not found, generating baseline')
        prev_path = ''

    if prev_path:
        print(f'Comparing: {os.path.basename(args.current_json)} vs {os.path.basename(prev_path)}')
    else:
        print('No previous analysis found, generating baseline report')

    report = generate_trend_report(args.current_json, prev_path)

    # Output
    analysis_dir = os.path.dirname(args.current_json)
    trends_dir = os.path.join(analysis_dir, 'trends')
    os.makedirs(trends_dir, exist_ok=True)
    out_path = os.path.join(trends_dir, f'{report["date"]}.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Terminal summary
    print(f'\n=== 趋势报告 {report["date"]} ===')
    if report['type'] == 'baseline':
        print(report['message'])
    else:
        kw_trends = report.get('keyword_trends', [])
        rising = [t for t in kw_trends if t['status'] == 'rising']
        declining = [t for t in kw_trends if t['status'] == 'declining']
        new = [t for t in kw_trends if t['status'] == 'new']
        dropped = [t for t in kw_trends if t['status'] == 'dropped']

        if rising:
            print(f'\n上升 ({len(rising)}):')
            for t in rising:
                print(f'  ↑ {t["keyword"]}: {t["avg_score_change_pct"]:+d}% (样本 {t["count"]})')
        if declining:
            print(f'\n下降 ({len(declining)}):')
            for t in declining:
                print(f'  ↓ {t["keyword"]}: {t["avg_score_change_pct"]:+d}% (样本 {t["count"]})')
        if new:
            print(f'\n新进 ({len(new)}):')
            for t in new:
                print(f'  ★ {t["keyword"]}: 均分 {t["avg_score"]:,}')
        if dropped:
            print(f'\n退出 ({len(dropped)}):')
            for t in dropped:
                print(f'  ✕ {t["keyword"]}')

        vol = report.get('volume_changes', {})
        print(f'\n数据量: {vol.get("previous_notes", 0)} → {vol.get("current_notes", 0)} ({vol.get("change", 0):+d})')

    print(f'\n输出: {out_path}')
    return 0


if __name__ == '__main__':
    exit(main() or 0)
