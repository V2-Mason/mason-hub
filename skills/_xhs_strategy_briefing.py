"""
_xhs_strategy_briefing.py — 市场信号生成（原策略简报，已重构）

用法: python _xhs_strategy_briefing.py <analysis.json> <output_dir> [--trends <trends.json>]

核心变化:
- 删除 generate_content_recommendations() — 不做虚假因果推断
- 新增 generate_market_signals() — 每个信号只描述观察事实
- 语言规范: 禁止 "应该/建议/推荐"，只用 "数据显示/观察到/在 N 条样本中"

输出: <output_dir>/briefings/YYYY-MM-DD.json
"""
import json
import sys
import os
from datetime import datetime


def generate_market_signals(report):
    """生成市场观察信号。每个信号只描述事实，不做因果推断。"""
    signals = []
    total = report.get('meta', {}).get('total_notes', 0)

    # 1. 内容格式信号
    ct = report.get('content_type', {})
    video_avg = ct.get('video_avg_score', 0)
    normal_avg = ct.get('normal_avg_score', 0)
    video_count = report.get('meta', {}).get('video_count', 0)
    normal_count = report.get('meta', {}).get('normal_count', 0)

    if video_avg > 0 and normal_avg > 0:
        ratio = round(video_avg / max(normal_avg, 1), 1)
        signals.append({
            'category': 'format',
            'observation': f'视频平均互动分是图文的 {ratio} 倍（视频 {video_avg:,} vs 图文 {normal_avg:,}）',
            'confidence': 'medium',
            'blind_spots': [
                '可能是平台算法偏好视频推荐，而非用户偏好视频内容',
                '视频制作成本更高，互动/成本比未知',
                f'视频 {video_count} 条 vs 图文 {normal_count} 条，样本量不对等可能影响均值',
            ],
            'sample_size': total,
        })

    # 2. 高藏赞比信号（干货/教程类内容受关注）
    high_save = report.get('patterns', {}).get('high_save', [])
    if high_save:
        avg_save_rate = round(sum(p['save_rate'] for p in high_save) / len(high_save), 1)
        signals.append({
            'category': 'engagement_pattern',
            'observation': f'在 {len(high_save)} 条高藏赞比帖子中，平均藏赞比 {avg_save_rate}%，均为教程/清单类内容',
            'confidence': 'medium',
            'blind_spots': [
                '高藏赞比是内容特征，不代表"做干货就能火"',
                '这些帖子的作者粉丝量未知，可能是大号基数效应',
            ],
            'sample_size': len(high_save),
        })

    # 3. 高评赞比信号（话题/争议性内容）
    high_engage = report.get('patterns', {}).get('high_engage', [])
    if high_engage:
        avg_engage_rate = round(sum(p['engage_rate'] for p in high_engage) / len(high_engage), 1)
        signals.append({
            'category': 'engagement_pattern',
            'observation': f'在 {len(high_engage)} 条高评赞比帖子中，平均评赞比 {avg_engage_rate}%，评论活跃度高于均值',
            'confidence': 'medium',
            'blind_spots': [
                '高评论可能来自争议而非认可',
                '部分高评论帖子可能是刷评',
            ],
            'sample_size': len(high_engage),
        })

    # 4. 关键词热度信号
    kw_insights = report.get('keyword_insights', [])
    if len(kw_insights) >= 2:
        best = kw_insights[0]
        worst = kw_insights[-1]
        spread = round(best['avg_score'] / max(worst['avg_score'], 1), 1)
        signals.append({
            'category': 'keyword',
            'observation': f'关键词互动分差距 {spread} 倍："{best["keyword"]}" 均分 {best["avg_score"]:,}，"{worst["keyword"]}" 均分 {worst["avg_score"]:,}',
            'confidence': 'low' if best.get('count', 0) < 10 else 'medium',
            'blind_spots': [
                '搜索关键词的互动分受 XHS 搜索排序算法影响',
                '不同关键词的竞争激烈程度不同，互动分高不代表易进入',
                f'最高关键词仅 {best.get("count", 0)} 条样本',
            ],
            'sample_size': sum(k.get('count', 0) for k in kw_insights),
        })

    # 5. 标题模式信号
    tp = report.get('title_patterns', {})
    num_avg = tp.get('with_number_avg', 0)
    no_num_avg = tp.get('without_number_avg', 0)
    if num_avg > 0 and no_num_avg > 0:
        diff_pct = round((num_avg / max(no_num_avg, 1) - 1) * 100)
        signals.append({
            'category': 'title_pattern',
            'observation': f'含数字标题平均互动分 {num_avg:,}，无数字标题 {no_num_avg:,}（差 {diff_pct:+d}%）',
            'confidence': 'low',
            'blind_spots': [
                '含数字的标题往往是清单/教程类，互动高可能是内容类型而非数字本身',
                '相关性不等于因果，在标题加数字不一定提升互动',
            ],
            'sample_size': total,
        })

    # 6. 小号信号（如果有 enriched 数据）
    small_signals = report.get('small_account_signals', [])
    if small_signals:
        signals.append({
            'category': 'small_account',
            'observation': f'在粉丝 <1 万的小号中，有 {len(small_signals)} 条帖子进入 Top 20，说明内容本身驱动了互动',
            'confidence': 'high',
            'blind_spots': [
                '小号可能是大号的小号（矩阵账号），粉丝量不完全反映账号实力',
            ],
            'sample_size': len(small_signals),
            'examples': [{
                'title': p['title'][:40],
                'score': p['score'],
                'follower_count': p.get('follower_count', 0),
                'nickname': p.get('nickname', ''),
            } for p in small_signals[:5]],
        })

    # Check enrichment status for blind_spots
    enrichment = report.get('enrichment', {})
    has_enrichment = enrichment.get('creators_enriched', 0) > 0
    if not has_enrichment:
        for s in signals:
            if s['category'] in ('engagement_pattern',):
                if '作者粉丝量未知' not in str(s['blind_spots']):
                    s['blind_spots'].append('未做粉丝量富化，大号和小号混合比较')

    return signals


def generate_market_report(analysis_json_path, output_dir, trends_path=None):
    with open(analysis_json_path, encoding='utf-8') as f:
        report = json.load(f)

    today = datetime.now().strftime('%Y-%m-%d')
    signals = generate_market_signals(report)

    total = report.get('meta', {}).get('total_notes', 0)

    # Known limitations
    limitations = [
        f'仅 {total} 条笔记，统计显著性不足',
        '数据来自搜索 API，受平台排序算法影响',
    ]
    enrichment = report.get('enrichment', {})
    if not enrichment.get('creators_enriched', 0):
        limitations.append('大号和小号混合（未做粉丝量富化）')
    if enrichment.get('rate_limited'):
        limitations.append('粉丝量富化被限流，部分作者数据缺失')

    # Hot posts with account_size tags (if enriched)
    hot_posts = []
    for p in report.get('top_posts', [])[:20]:
        if p.get('fake_flags'):
            continue
        hp = {
            'title': p['title'],
            'url': p.get('url', ''),
            'score': p['score'],
            'liked': p['liked'],
            'collected': p['collected'],
            'comment': p.get('comment', 0),
            'shared': p.get('shared', 0),
            'save_rate': p['save_rate'],
            'engage_rate': p.get('engage_rate', 0),
            'pub_date': p.get('pub_date', ''),
            'type': p['type'],
            'nickname': p.get('nickname', ''),
        }
        if 'follower_count' in p:
            hp['follower_count'] = p['follower_count']
            hp['account_size'] = p.get('account_size', '')
        hot_posts.append(hp)

    # Load trends if available
    trends = None
    if trends_path and os.path.exists(trends_path):
        with open(trends_path, encoding='utf-8') as f:
            trends = json.load(f)

    # Build output
    output = {
        'type': 'market_signals',
        'date': today,
        'disclaimer': '以下为市场观察，非内容建议。描述的是"发生了什么"，不是"应该做什么"。',
        'data_source': os.path.basename(analysis_json_path),
        'summary': {
            'total_notes': total,
            'video_ratio': report.get('content_type', {}).get('video_ratio', 0),
        },
        'market_signals': signals,
        'hot_posts': hot_posts,
        'keyword_insights': report.get('keyword_insights', []),
        'fake_traffic': report.get('fake_traffic', {}),
        'known_limitations': limitations,
    }

    if trends:
        output['trends'] = trends

    # Small account signals section (top level for dashboard)
    if report.get('small_account_signals'):
        output['small_account_signals'] = report['small_account_signals']

    # Save
    briefing_dir = os.path.join(output_dir, 'briefings')
    os.makedirs(briefing_dir, exist_ok=True)
    out_path = os.path.join(briefing_dir, f'{today}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Terminal output
    print(f"=== XHS 市场信号 {today} ===")
    print(f"数据: {total} 条笔记")
    print(f"声明: {output['disclaimer']}")
    print()

    print(f"市场信号 ({len(signals)}):")
    for s in signals:
        conf_icon = {'high': '●', 'medium': '◐', 'low': '○'}[s['confidence']]
        print(f"  [{conf_icon} {s['confidence']}] {s['observation']}")
        for bs in s['blind_spots'][:2]:
            print(f"      盲区: {bs}")
    print()

    print(f"Top 5 热帖:")
    for i, p in enumerate(hot_posts[:5]):
        size_tag = f" [{p['account_size']}]" if 'account_size' in p else ''
        print(f"  {i+1}. {p['title'][:40]}{size_tag}")
        print(f"     互动分 {p['score']:,} | 赞 {p['liked']:,} 藏 {p['collected']:,}")
    print()

    ft = output['fake_traffic']
    print(f"假流量: {ft.get('count', 0)} 条可疑")
    print()
    print(f"局限性:")
    for lim in limitations:
        print(f"  - {lim}")
    print()
    print(f"输出: {out_path}")

    return out_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python _xhs_strategy_briefing.py <analysis.json> <output_dir> [--trends <trends.json>]")
        return 1

    analysis_path = sys.argv[1]
    output_dir = sys.argv[2]
    trends_path = None

    if '--trends' in sys.argv:
        idx = sys.argv.index('--trends')
        if idx + 1 < len(sys.argv):
            trends_path = sys.argv[idx + 1]

    generate_market_report(analysis_path, output_dir, trends_path)
    return 0


if __name__ == '__main__':
    exit(main() or 0)
