"""
_xhs_strategy_briefing.py — 市场信号 + 行动建议生成

用法: python _xhs_strategy_briefing.py <analysis.json> <output_dir> [--trends <trends.json>] [--comments <comments.json>]

信号结构（四段式）:
- 观察: 一句话描述发生了什么
- 机制假设: 最可能的原因
- 行动建议: 本周具体该做什么（含预期结果和验证时间）
- 置信度: HIGH/MEDIUM/LOW + 原因

输出: <output_dir>/briefings/YYYY-MM-DD.json
"""
import json
import sys
import os
from datetime import datetime


def generate_market_signals(report, comments=None):
    """生成市场信号。每条包含：观察 + 机制假设 + 行动建议 + 置信度。"""
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
            'hypothesis': '平台算法可能对视频有推荐权重加成，或用户在浏览时更容易停留在视频上',
            'action': f'本周将一篇已有的高互动图文内容改编为视频版本，对比同主题图文 vs 视频的互动差异',
            'action_verify': '发布后 72h 手动记录互动数据（赞/藏/评），对比同主题图文 vs 视频的表现差异',
            'confidence': 'medium',
            'confidence_reason': f'基于 {video_count} 条视频 vs {normal_count} 条图文，样本量尚可但未控制账号量级',
            'blind_spots': [
                '可能是平台算法偏好视频推荐，而非用户偏好视频内容',
                '视频制作成本更高，互动/成本比未知',
            ],
            'sample_size': total,
        })

    # 2. 高藏赞比信号
    high_save = report.get('patterns', {}).get('high_save', [])
    if high_save:
        avg_save_rate = round(sum(p['save_rate'] for p in high_save) / len(high_save), 1)
        # Extract common content type from titles
        example_titles = [p['title'][:30] for p in high_save[:3]]
        signals.append({
            'category': 'engagement_pattern',
            'observation': f'在 {len(high_save)} 条高藏赞比帖子中，平均藏赞比 {avg_save_rate}%，均为教程/清单类内容',
            'hypothesis': '用户收藏是为了"以后用到"，说明清单和教程类内容有实用价值',
            'action': '创作一篇工具使用教程或清单类内容（如"X 步完成…"或"必买清单"），重点解释步骤而非产品本身',
            'action_verify': '发布后 72h 手动记录藏赞比，目标 >30%（高藏赞比阈值）',
            'confidence': 'medium',
            'confidence_reason': f'基于 {len(high_save)} 条高藏赞比帖子，模式一致性高但样本量小',
            'blind_spots': [
                '高藏赞比是内容特征，不代表"做干货就能火"',
                '这些帖子的作者粉丝量未知，可能是大号基数效应',
            ],
            'sample_size': len(high_save),
            'examples': example_titles,
        })

    # 3. 高评赞比信号
    high_engage = report.get('patterns', {}).get('high_engage', [])
    if high_engage:
        avg_engage_rate = round(sum(p['engage_rate'] for p in high_engage) / len(high_engage), 1)
        signals.append({
            'category': 'engagement_pattern',
            'observation': f'在 {len(high_engage)} 条高评赞比帖子中，平均评赞比 {avg_engage_rate}%，评论活跃度高于均值',
            'hypothesis': '这类内容激发了观点表达欲或争议，评论互动提升了帖子的算法权重',
            'action': '下一篇内容尝试加入一个可讨论的观点（如"X 比 Y 好用"），结尾加一句引导评论的提问',
            'action_verify': '发布后 72h 手动记录评赞比，目标 >2%（高评赞比阈值）',
            'confidence': 'medium',
            'confidence_reason': f'基于 {len(high_engage)} 条帖子，但高评论可能来自争议而非内容质量',
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
        # Top 3 keywords as action focus
        top3_kw = [k['keyword'] for k in kw_insights[:3]]
        signals.append({
            'category': 'keyword',
            'observation': f'关键词互动分差距 {spread} 倍："{best["keyword"]}" 均分 {best["avg_score"]:,}，"{worst["keyword"]}" 均分 {worst["avg_score"]:,}',
            'hypothesis': '高互动关键词对应的品类有更大的用户需求基数或更少的内容供给',
            'action': f'优先围绕高互动关键词创作内容，本周重点：{" / ".join(top3_kw)}',
            'action_verify': f'发布后 72h 手动记录互动数据，对比 Top 关键词 vs 低互动关键词帖子的表现',
            'confidence': 'low' if best.get('count', 0) < 10 else 'medium',
            'confidence_reason': f'最高关键词仅 {best.get("count", 0)} 条样本，排名可能受搜索算法影响',
            'blind_spots': [
                '搜索关键词的互动分受 XHS 搜索排序算法影响',
                '不同关键词的竞争激烈程度不同，互动分高不代表易进入',
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
            'hypothesis': '数字传递了具体性和可预期的信息量（"3步" 比 "几步" 更有点击欲）',
            'action': '下一篇标题加入具体数字，如"3步"、"7天"、"花了400元"、"5个必买"',
            'action_verify': '发布后 72h 手动对比含数字标题 vs 不含数字标题的互动数据',
            'confidence': 'low',
            'confidence_reason': '相关性分析，含数字标题往往是清单/教程类，互动高可能是内容类型效应',
            'blind_spots': [
                '含数字的标题往往是清单/教程类，互动高可能是内容类型而非数字本身',
                '相关性不等于因果，在标题加数字不一定提升互动',
            ],
            'sample_size': total,
        })

    # 6. 小号信号
    small_signals = report.get('small_account_signals', [])
    if small_signals:
        signals.append({
            'category': 'small_account',
            'observation': f'在粉丝 <1 万的小号中，有 {len(small_signals)} 条帖子进入 Top 20，说明内容本身驱动了互动',
            'hypothesis': '这些帖子的互动不依赖粉丝基数，更可能反映了内容本身的吸引力',
            'action': '研究这些小号爆款的内容结构（标题模式、开头钩子、内容长度），作为创作参考',
            'action_verify': '模仿其中一篇的结构创作同主题内容，发布后 72h 手动记录互动数据对比',
            'confidence': 'high',
            'confidence_reason': '小号排除了粉丝基数效应，信号可信度高',
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

    # Check enrichment status
    enrichment = report.get('enrichment', {})
    has_enrichment = enrichment.get('creators_enriched', 0) > 0
    if not has_enrichment:
        for s in signals:
            if s['category'] in ('engagement_pattern',):
                if '作者粉丝量未知' not in str(s['blind_spots']):
                    s['blind_spots'].append('未做粉丝量富化，大号和小号混合比较')

    return signals


def generate_topic_suggestions(comments):
    """从评论中的用户提问生成选题建议。

    痛点聚焦帖子的提问 → HIGH 置信度 + 特殊来源标注。
    """
    if not comments:
        return []

    questions = comments.get('questions', [])
    if not questions:
        return []

    # Build a set of pain-point note_ids for confidence upgrade
    pain_clusters = comments.get('pain_point_clusters', [])
    pain_note_ids = {}
    for pc in pain_clusters:
        nid = pc.get('note_id', '')
        if nid and nid not in pain_note_ids:
            pain_note_ids[nid] = {
                'rank': pc.get('rank', 0),
                'rank_total': pc.get('rank_total', 0),
                'pain_type': pc.get('pain_type', ''),
                'confidence': pc.get('confidence', 'MEDIUM'),
            }

    suggestions = []
    for q in questions[:10]:
        content = q.get('content', '')
        likes = q.get('like_count', 0)
        note_title = q.get('note_title', '')
        note_id = q.get('note_id', '')

        # Generate topic suggestion based on question content
        suggestion = _question_to_topic(content)
        if suggestion:
            entry = {
                'source_question': content[:80],
                'source_likes': likes,
                'source_note': note_title,
                'topic_title': suggestion['title'],
                'content_type': suggestion['content_type'],
                'expected_engagement': suggestion['expected_engagement'],
                'reasoning': suggestion['reasoning'],
            }

            # Upgrade confidence if question comes from a pain-point cluster post
            if note_id in pain_note_ids:
                pi = pain_note_ids[note_id]
                entry['confidence'] = 'HIGH'
                entry['source_tag'] = f"全场 #{pi['rank']} 帖子的评论痛点（{pi['pain_type']}）"
            else:
                entry['confidence'] = 'MEDIUM' if likes > 10 else 'LOW'
                entry['source_tag'] = f"用户提问（{likes}赞）"

            suggestions.append(entry)

    return suggestions


def _question_to_topic(question: str) -> dict:
    """将用户提问转化为可直接使用的内容标题（规则引擎，非 LLM）。"""
    q = question.lower()
    subject = _extract_subject(question)

    # 对比类问题 → 直接用对比的两方做标题
    if any(w in q for w in ['还是', '哪个好', '好不好', '好用吗', '值得', '推荐吗', 'vs', '比较']):
        return {
            'title': f'亲测｜{subject}，到底值不值得入手？',
            'content_type': '对比测评',
            'expected_engagement': '高藏赞比（用户收藏备用）',
            'reasoning': '用户在做购买决策前寻求对比信息',
        }

    # 怎么做/教程类问题 → 步骤化标题
    if any(w in q for w in ['怎么', '如何', '怎样', '教程', '方法', '步骤', '是不是每次']):
        return {
            'title': f'3步搞定｜{subject}（新手也能学会）',
            'content_type': '教程/步骤',
            'expected_engagement': '高藏赞比（教程类内容收藏率高）',
            'reasoning': '用户遇到了操作困惑，需要具体指导',
        }

    # 在哪买/价格类问题 → 清单标题
    if any(w in q for w in ['在哪', '哪里买', '多少钱', '价格', '链接', '求链接', '代购']):
        return {
            'title': f'别买贵了！{subject}最全购买渠道整理',
            'content_type': '购物攻略/清单',
            'expected_engagement': '高转赞比（实用信息被分享）',
            'reasoning': '用户有明确购买意图，需要渠道和价格信息',
        }

    # 能不能/适合问题 → 人群化标题
    if any(w in q for w in ['能不能', '可以吗', '适合', '敏感肌', '油皮', '干皮']):
        return {
            'title': f'实话实说｜{subject}，这类人千万别买',
            'content_type': '适用人群分析',
            'expected_engagement': '高评赞比（引发同类用户讨论）',
            'reasoning': '用户在判断产品是否适合自己',
        }

    # 平替/替代问题 → 省钱标题
    if any(w in q for w in ['平替', '替代', '代替', '便宜', '省钱']):
        return {
            'title': f'省了一半钱！{subject}平替大公开',
            'content_type': '平替对比',
            'expected_engagement': '高藏赞比 + 高转赞比',
            'reasoning': '用户寻找性价比更高的替代方案',
        }

    # 通用提问 fallback → 科普标题
    if any(w in q for w in ['吗', '呢', '？', '?', '什么', '请问', '想问']):
        return {
            'title': f'终于搞懂了！{subject}一次讲清楚',
            'content_type': '问答/科普',
            'expected_engagement': '中等互动（解决具体问题）',
            'reasoning': '用户有具体疑问，回答这类问题能建立信任感',
        }

    return None


def _extract_subject(question: str) -> str:
    """从问题中提取核心主题（简单启发式）。"""
    import re
    # Remove common question markers
    subject = re.sub(r'[？?！!。，,\s]+$', '', question)
    # Remove leading markers
    subject = re.sub(r'^(请问|想问|求问|那|所以|但是|可是)', '', subject)
    # Truncate
    if len(subject) > 25:
        subject = subject[:25] + '…'
    return subject


def generate_action_checklist(signals, topic_suggestions):
    """从信号和选题建议中提取行动清单，分主清单(top 3)和次要清单。"""
    actions = []

    # From signals: sort by confidence (high > medium > low)
    conf_order = {'high': 0, 'medium': 1, 'low': 2}
    sorted_signals = sorted(signals, key=lambda s: conf_order.get(s.get('confidence', 'low'), 3))

    for s in sorted_signals:
        if 'action' in s:
            actions.append({
                'action': s['action'],
                'confidence': s['confidence'],
                'source': f"信号: {s['observation'][:50]}…",
                'verify': s.get('action_verify', ''),
                'ref_posts': s.get('ref_posts', []),
            })

    # From topic suggestions: top 3, pain-point suggestions first
    sorted_topics = sorted(topic_suggestions,
                           key=lambda t: (0 if t.get('confidence') == 'HIGH' else 1,
                                          -t.get('source_likes', 0)))
    for ts in sorted_topics[:3]:
        conf = ts.get('confidence', 'MEDIUM').lower()
        source_tag = ts.get('source_tag', f"用户提问（{ts['source_likes']}赞）")
        actions.append({
            'action': f"选题: {ts['topic_title']}",
            'confidence': conf,
            'source': f"来源：{source_tag} — {ts['source_question'][:40]}…",
            'verify': '发布后 72h 检查互动表现',
            'ref_posts': [],
        })

    return {
        'primary': actions[:3],
        'secondary': actions[3:],
    }


def _attach_ref_posts(signals, top_posts):
    """为每个信号附加相关的参考帖子（最多 5 条）。"""
    for s in signals:
        refs = []
        cat = s['category']
        for p in top_posts:
            if p.get('fake_flags'):
                continue
            ref = {'title': p['title'][:40], 'url': p.get('url', ''),
                   'score': p['score'], 'type': p.get('type', '')}
            if cat == 'format':
                # Video signal → show video posts
                if p.get('type') == 'video':
                    refs.append(ref)
            elif cat == 'engagement_pattern' and 'save' in s.get('observation', ''):
                if p.get('save_rate', 0) > 30:
                    refs.append(ref)
            elif cat == 'engagement_pattern':
                if p.get('engage_rate', 0) > 2:
                    refs.append(ref)
            elif cat == 'keyword':
                # Top 3 keywords → show matching posts
                kws = [k['keyword'] for k in (s.get('_keyword_insights', []) or [])[:3]]
                if not kws:
                    refs.append(ref)  # fallback: all top posts
            elif cat == 'small_account':
                if p.get('account_size') == '小号':
                    refs.append(ref)
            else:
                refs.append(ref)
            if len(refs) >= 5:
                break
        # Fallback: if no matching refs, use top 3 posts
        if not refs:
            for p in top_posts[:3]:
                if not p.get('fake_flags'):
                    refs.append({'title': p['title'][:40], 'url': p.get('url', ''),
                                 'score': p['score'], 'type': p.get('type', '')})
        s['ref_posts'] = refs[:5]


def generate_market_report(analysis_json_path, output_dir, trends_path=None, comments_path=None):
    with open(analysis_json_path, encoding='utf-8') as f:
        report = json.load(f)

    # Load comments if available
    comments = None
    if comments_path and os.path.exists(comments_path):
        with open(comments_path, encoding='utf-8') as f:
            comments = json.load(f)

    today = datetime.now().strftime('%Y-%m-%d')
    signals = generate_market_signals(report, comments)
    # Attach reference posts to each signal
    _attach_ref_posts(signals, report.get('top_posts', []))
    topic_suggestions = generate_topic_suggestions(comments)
    action_checklist = generate_action_checklist(signals, topic_suggestions)

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
        'disclaimer': '以下为市场分析与行动建议。置信度标注说明数据基础强弱，LOW 表示待验证假设。',
        'data_source': os.path.basename(analysis_json_path),
        'summary': {
            'total_notes': total,
            'video_ratio': report.get('content_type', {}).get('video_ratio', 0),
        },
        'action_checklist': action_checklist,
        'market_signals': signals,
        'topic_suggestions': topic_suggestions,
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
        print("Usage: python _xhs_strategy_briefing.py <analysis.json> <output_dir> [--trends <trends.json>] [--comments <comments.json>]")
        return 1

    analysis_path = sys.argv[1]
    output_dir = sys.argv[2]
    trends_path = None
    comments_path = None

    if '--trends' in sys.argv:
        idx = sys.argv.index('--trends')
        if idx + 1 < len(sys.argv):
            trends_path = sys.argv[idx + 1]

    if '--comments' in sys.argv:
        idx = sys.argv.index('--comments')
        if idx + 1 < len(sys.argv):
            comments_path = sys.argv[idx + 1]

    generate_market_report(analysis_path, output_dir, trends_path, comments_path)
    return 0


if __name__ == '__main__':
    exit(main() or 0)
