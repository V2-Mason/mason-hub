"""
xhs_strategy_briefing.py — 基于分析 JSON 生成策略简报

用法: python xhs_strategy_briefing.py <analysis.json> <output_dir>

输出: <output_dir>/briefings/YYYY-MM-DD.json + 终端文字摘要
"""
import json
import sys
import os
from datetime import datetime


def generate_content_recommendations(report):
    """基于分析数据生成内容建议（规则引擎，不依赖 LLM）"""
    recs = []

    # 1. 内容形式建议
    ct = report.get('content_type', {})
    if ct.get('video_avg_score', 0) > ct.get('normal_avg_score', 0) * 1.5:
        recs.append({
            'type': 'format',
            'priority': 'high',
            'recommendation': '以视频为主',
            'reason': f"视频平均互动分 {ct['video_avg_score']:,} 是图文 {ct['normal_avg_score']:,} 的 {ct['video_avg_score']/max(ct['normal_avg_score'],1):.1f} 倍",
        })

    # 2. 从高藏赞比帖子提取教程选题
    high_save = report.get('patterns', {}).get('high_save', [])
    if high_save:
        titles = [p['title'][:30] for p in high_save[:3]]
        recs.append({
            'type': 'topic',
            'priority': 'high',
            'recommendation': '做干货清单/教程类内容',
            'reason': f"高藏赞比帖子用户收藏意愿强，参考: {', '.join(titles)}",
        })

    # 3. 从高评赞比帖子提取话题选题
    high_engage = report.get('patterns', {}).get('high_engage', [])
    if high_engage:
        titles = [p['title'][:30] for p in high_engage[:3]]
        recs.append({
            'type': 'topic',
            'priority': 'medium',
            'recommendation': '尝试争议/反常识类标题引发讨论',
            'reason': f"高评赞比帖子评论活跃，参考: {', '.join(titles)}",
        })

    # 4. 从高转赞比帖子提取社交货币选题
    high_share = report.get('patterns', {}).get('high_share', [])
    if high_share:
        titles = [p['title'][:30] for p in high_share[:3]]
        recs.append({
            'type': 'topic',
            'priority': 'medium',
            'recommendation': '做实用攻略类内容（用户愿意转发给朋友）',
            'reason': f"高转赞比帖子社交传播强，参考: {', '.join(titles)}",
        })

    # 5. 标题公式建议
    tp = report.get('title_patterns', {})
    if tp.get('with_number_avg', 0) > tp.get('without_number_avg', 0) * 1.1:
        boost = round((tp['with_number_avg'] / max(tp['without_number_avg'], 1) - 1) * 100)
        recs.append({
            'type': 'title',
            'priority': 'medium',
            'recommendation': f'标题带数字，互动提升 {boost}%',
            'reason': f"含数字标题均分 {tp['with_number_avg']:,} vs 无数字 {tp['without_number_avg']:,}",
        })

    # 6. 关键词建议
    kw_insights = report.get('keyword_insights', [])
    if kw_insights:
        best = kw_insights[0]
        worst = kw_insights[-1] if len(kw_insights) > 1 else None
        recs.append({
            'type': 'keyword',
            'priority': 'high',
            'recommendation': f"重点选题方向: {best['keyword']}",
            'reason': f"平均互动分最高 ({best['avg_score']:,})，视频占比 {best.get('video_ratio', 0)}%",
        })
        if worst and worst['avg_score'] < best['avg_score'] * 0.3:
            recs.append({
                'type': 'keyword',
                'priority': 'low',
                'recommendation': f"减少投入: {worst['keyword']}",
                'reason': f"平均互动分仅 {worst['avg_score']:,}，性价比低",
            })

    return recs


def generate_briefing(analysis_json_path, output_dir):
    with open(analysis_json_path, encoding='utf-8') as f:
        report = json.load(f)

    today = datetime.now().strftime('%Y-%m-%d')
    recs = generate_content_recommendations(report)

    # 构建简报
    briefing = {
        'date': today,
        'data_source': analysis_json_path,
        'summary': {
            'total_notes': report['meta']['total_notes'],
            'video_ratio': report['content_type']['video_ratio'],
            'video_advantage': round(report['content_type']['video_avg_score'] /
                                     max(report['content_type']['normal_avg_score'], 1), 1),
        },
        'hot_posts': [{
            'title': p['title'],
            'url': p['url'],
            'score': p['score'],
            'liked': p['liked'],
            'collected': p['collected'],
            'save_rate': p['save_rate'],
            'type': p['type'],
            'why_hot': (
                '干货型(高收藏)' if p['save_rate'] > 50
                else '话题型(高评论)' if p['engage_rate'] > 3
                else '传播型(高转发)' if p['share_rate'] > 10
                else '综合热门'
            ),
        } for p in report['top_posts'][:10]],
        'keyword_insights': report.get('keyword_insights', []),
        'content_recommendations': recs,
        'fake_traffic': report.get('fake_traffic', {}),
    }

    # 保存
    briefing_dir = os.path.join(output_dir, 'briefings')
    os.makedirs(briefing_dir, exist_ok=True)
    out_path = os.path.join(briefing_dir, f'{today}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)

    # 终端输出
    print(f"=== XHS 策略简报 {today} ===")
    print(f"数据: {report['meta']['total_notes']} 条笔记")
    print()

    print("内容建议:")
    for r in recs:
        icon = {'high': '!!!', 'medium': '!!', 'low': '!'}[r['priority']]
        print(f"  [{icon}] {r['recommendation']}")
        print(f"       {r['reason']}")
    print()

    print("Top 5 值得学习的帖子:")
    for i, p in enumerate(briefing['hot_posts'][:5]):
        print(f"  {i+1}. [{p['why_hot']}] {p['title'][:40]}")
        print(f"     赞{p['liked']:,} 藏{p['collected']:,} 藏赞比{p['save_rate']}%")
    print()

    ft = briefing['fake_traffic']
    print(f"假流量: {ft.get('count', 0)} 条可疑")
    print()
    print(f"简报已保存: {out_path}")

    return out_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python xhs_strategy_briefing.py <analysis.json> <output_dir>")
        return 1

    out_path = generate_briefing(sys.argv[1], sys.argv[2])
    return 0


if __name__ == '__main__':
    exit(main() or 0)
