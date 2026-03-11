"""
_xhs_analyze_compare.py — Viral vs Control 对比分析

用法: python _xhs_analyze_compare.py [--json-out /path/to/output.json]

对比维度:
- 互动分分布（viral vs control 的均值、中位数）
- 内容格式差异（视频占比）
- 藏赞比差异（干货信号）
- 评赞比差异（话题讨论度）
- 标题模式差异
- 标签差异

输出: 终端报告 + 可选 JSON
退出码: 0=有对比数据, 3=数据不足
"""
import argparse
import json
import re
import sqlite3
import time
from collections import Counter
from datetime import datetime

DB_PATH = '/opt/mediacrawler/database/sqlite_tables.db'


def parse_count(s) -> int:
    if s is None:
        return 0
    s = str(s).strip().replace('+', '')
    if '万' in s:
        return int(float(s.replace('万', '')) * 10000)
    if '亿' in s:
        return int(float(s.replace('亿', '')) * 100000000)
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def median(values):
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def load_tiered_notes():
    """Load notes grouped by content_tier."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check if content_tier column exists
    columns = [r[1] for r in conn.execute('PRAGMA table_info(xhs_note)').fetchall()]
    if 'content_tier' not in columns:
        conn.close()
        return {}, {}

    rows = conn.execute('''
        SELECT note_id, title, "desc", type, liked_count, collected_count,
               comment_count, share_count, tag_list, source_keyword,
               content_tier, time, nickname
        FROM xhs_note
        WHERE content_tier IN ('viral', 'control')
    ''').fetchall()
    conn.close()

    tiers = {'viral': [], 'control': []}
    for r in rows:
        liked = parse_count(r['liked_count'])
        collected = parse_count(r['collected_count'])
        comment = parse_count(r['comment_count'])
        shared = parse_count(r['share_count'])
        score = liked + collected * 3 + comment * 5 + shared * 8

        engage_rate = (comment / liked * 100) if liked > 0 else 0
        save_rate = (collected / liked * 100) if liked > 0 else 0

        ts = r['time']
        post_age_days = -1
        if ts and int(ts) > 0:
            ts_val = int(ts)
            ts_s = ts_val / 1000 if ts_val > 1e12 else ts_val
            post_age_days = round((time.time() - ts_s) / 86400)

        note = {
            'note_id': r['note_id'],
            'title': r['title'] or '',
            'desc': r['desc'] or '',
            'type': r['type'] or 'normal',
            'liked': liked, 'collected': collected,
            'comment': comment, 'shared': shared,
            'score': score,
            'engage_rate': round(engage_rate, 2),
            'save_rate': round(save_rate, 1),
            'tags': r['tag_list'] or '',
            'keyword': r['source_keyword'] or '',
            'tier': r['content_tier'],
            'post_age_days': post_age_days,
            'nickname': r['nickname'] or '',
            'has_number_title': bool(re.search(r'\d', r['title'] or '')),
            'has_exclaim_title': bool(re.search(r'[！!‼️]', r['title'] or '')),
        }
        tiers[r['content_tier']].append(note)

    return tiers


def analyze_tier(notes):
    """Compute aggregate stats for a tier."""
    if not notes:
        return None

    scores = [n['score'] for n in notes]
    likes = [n['liked'] for n in notes]
    save_rates = [n['save_rate'] for n in notes if n['liked'] > 0]
    engage_rates = [n['engage_rate'] for n in notes if n['liked'] > 0]
    ages = [n['post_age_days'] for n in notes if n['post_age_days'] >= 0]

    video_notes = [n for n in notes if n['type'] == 'video']
    with_number = [n for n in notes if n['has_number_title']]
    with_exclaim = [n for n in notes if n['has_exclaim_title']]

    # Tag frequency
    all_tags = []
    for n in notes:
        if n['tags']:
            all_tags.extend(n['tags'].split(','))
    tag_freq = Counter(t.strip() for t in all_tags if t.strip())

    return {
        'count': len(notes),
        'score_avg': round(sum(scores) / len(scores)),
        'score_median': round(median(scores)),
        'score_min': min(scores),
        'score_max': max(scores),
        'liked_avg': round(sum(likes) / len(likes)),
        'liked_median': round(median(likes)),
        'save_rate_avg': round(sum(save_rates) / max(len(save_rates), 1), 1),
        'save_rate_median': round(median(save_rates), 1),
        'engage_rate_avg': round(sum(engage_rates) / max(len(engage_rates), 1), 2),
        'engage_rate_median': round(median(engage_rates), 2),
        'video_ratio': round(len(video_notes) / len(notes) * 100),
        'video_avg_score': round(sum(n['score'] for n in video_notes) / max(len(video_notes), 1)),
        'normal_avg_score': round(sum(n['score'] for n in notes if n['type'] == 'normal') / max(len(notes) - len(video_notes), 1)),
        'number_title_ratio': round(len(with_number) / len(notes) * 100),
        'exclaim_title_ratio': round(len(with_exclaim) / len(notes) * 100),
        'age_median': round(median(ages)) if ages else -1,
        'top_tags': tag_freq.most_common(10),
    }


def build_comparison(viral_stats, control_stats):
    """Build comparison insights between viral and control."""
    if not viral_stats or not control_stats:
        return []

    comparisons = []

    # Score difference
    score_ratio = viral_stats['score_avg'] / max(control_stats['score_avg'], 1)
    comparisons.append({
        'dimension': '互动分',
        'viral': f"{viral_stats['score_avg']:,} (中位{viral_stats['score_median']:,})",
        'control': f"{control_stats['score_avg']:,} (中位{control_stats['score_median']:,})",
        'observation': f'爆款互动分是中位数帖子的 {score_ratio:.1f} 倍',
        'caveat': '互动分公式本身包含权重假设 (赞1+藏3+评5+转8)',
    })

    # Save rate
    save_diff = viral_stats['save_rate_avg'] - control_stats['save_rate_avg']
    comparisons.append({
        'dimension': '藏赞比 (干货信号)',
        'viral': f"{viral_stats['save_rate_avg']}%",
        'control': f"{control_stats['save_rate_avg']}%",
        'observation': f'爆款藏赞比{"高" if save_diff > 0 else "低"} {abs(save_diff):.1f} 个百分点',
        'caveat': '藏赞比高可能是内容有收藏价值，也可能是赞数虚高导致分母偏大',
    })

    # Engage rate
    engage_diff = viral_stats['engage_rate_avg'] - control_stats['engage_rate_avg']
    comparisons.append({
        'dimension': '评赞比 (讨论度)',
        'viral': f"{viral_stats['engage_rate_avg']}%",
        'control': f"{control_stats['engage_rate_avg']}%",
        'observation': f'爆款评赞比{"高" if engage_diff > 0 else "低"} {abs(engage_diff):.2f} 个百分点',
        'caveat': '评论数也受作者互动习惯影响（作者回复也计入评论）',
    })

    # Video ratio
    v_diff = viral_stats['video_ratio'] - control_stats['video_ratio']
    comparisons.append({
        'dimension': '视频占比',
        'viral': f"{viral_stats['video_ratio']}%",
        'control': f"{control_stats['video_ratio']}%",
        'observation': f'爆款视频占比{"高" if v_diff > 0 else "低"} {abs(v_diff)} 个百分点',
        'caveat': '可能是平台推荐算法偏好视频，而非用户偏好',
    })

    # Title patterns
    num_diff = viral_stats['number_title_ratio'] - control_stats['number_title_ratio']
    comparisons.append({
        'dimension': '标题含数字',
        'viral': f"{viral_stats['number_title_ratio']}%",
        'control': f"{control_stats['number_title_ratio']}%",
        'observation': f'爆款标题含数字比例{"高" if num_diff > 0 else "低"} {abs(num_diff)} 个百分点',
        'caveat': '含数字可能只是某些品类（测评、排行）的固有特征',
    })

    return comparisons


def analyze():
    tiers = load_tiered_notes()
    viral = tiers.get('viral', [])
    control = tiers.get('control', [])

    if not viral:
        print('No viral-tier notes found (need to run crawl with --control-group first)')
        return None
    if not control:
        print(f'No control-tier notes found ({len(viral)} viral notes exist)')
        print('Run: xhs-crawl.sh --task 1 --control-group to collect control data')
        return None

    print(f'Data: {len(viral)} viral, {len(control)} control')
    print()

    viral_stats = analyze_tier(viral)
    control_stats = analyze_tier(control)
    comparisons = build_comparison(viral_stats, control_stats)

    return {
        'meta': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'viral_count': len(viral),
            'control_count': len(control),
        },
        'viral_stats': viral_stats,
        'control_stats': control_stats,
        'comparisons': comparisons,
        'known_limitations': [
            f'控制组仅 {len(control)} 条样本，统计显著性不足',
            '爆款和控制组可能来自不同关键词/时间段',
            '互动分定义本身包含权重假设',
            '无法区分"好内容"和"好推荐"（算法推流 vs 内容质量）',
        ],
    }


def print_report(report):
    if not report:
        return

    m = report['meta']
    print('=' * 70)
    print('XHS Viral vs Control 对比分析')
    print(f'日期: {m["date"]}')
    print(f'数据: {m["viral_count"]} 爆款 vs {m["control_count"]} 对照')
    print('=' * 70)

    vs = report['viral_stats']
    cs = report['control_stats']

    print(f'\n{"维度":<20} {"爆款 (Viral)":<25} {"对照 (Control)":<25}')
    print('-' * 70)
    print(f'{"数量":<20} {vs["count"]:<25} {cs["count"]:<25}')
    print(f'{"互动分均值":<17} {vs["score_avg"]:>10,}{"":14} {cs["score_avg"]:>10,}')
    print(f'{"互动分中位":<17} {vs["score_median"]:>10,}{"":14} {cs["score_median"]:>10,}')
    print(f'{"赞均值":<19} {vs["liked_avg"]:>10,}{"":14} {cs["liked_avg"]:>10,}')
    print(f'{"藏赞比":<19} {vs["save_rate_avg"]:>9.1f}%{"":14} {cs["save_rate_avg"]:>9.1f}%')
    print(f'{"评赞比":<19} {vs["engage_rate_avg"]:>9.2f}%{"":14} {cs["engage_rate_avg"]:>9.2f}%')
    print(f'{"视频占比":<18} {vs["video_ratio"]:>9}%{"":14} {cs["video_ratio"]:>9}%')
    print(f'{"标题含数字":<17} {vs["number_title_ratio"]:>9}%{"":14} {cs["number_title_ratio"]:>9}%')

    print('\n对比发现:')
    for c in report['comparisons']:
        print(f'  {c["dimension"]}: {c["observation"]}')
        print(f'    ⚠️ {c["caveat"]}')

    print('\n已知局限:')
    for lim in report['known_limitations']:
        print(f'  - {lim}')

    print('\n' + '=' * 70)


def main():
    parser = argparse.ArgumentParser(description='XHS Viral vs Control 对比分析')
    parser.add_argument('--json-out', help='输出 JSON 到指定路径')
    args = parser.parse_args()

    report = analyze()
    if not report:
        return 3

    print_report(report)

    if args.json_out:
        import os
        os.makedirs(os.path.dirname(args.json_out) or '.', exist_ok=True)

        # Convert tuples to lists for JSON serialization
        for tier_key in ['viral_stats', 'control_stats']:
            stats = report.get(tier_key)
            if stats and 'top_tags' in stats:
                stats['top_tags'] = [{'tag': t, 'count': c} for t, c in stats['top_tags']]

        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f'\nJSON saved: {args.json_out}')

    return 0


if __name__ == '__main__':
    exit(main() or 0)
