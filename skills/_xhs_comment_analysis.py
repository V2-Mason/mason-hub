"""
_xhs_comment_analysis.py — 评论分析

用法: python _xhs_comment_analysis.py [--json-out /path/to/output.json] [--top-n 10]

分析维度:
1. 高频词提取（简单分词，无需 jieba）
2. 提问识别（含问号或疑问词的评论）
3. 热门评论（按 like_count 排序）
4. 每个帖子的评论情绪概览

输出: 终端报告 + 可选 JSON
"""
import argparse
import json
import re
import sqlite3
import time
from collections import Counter
from datetime import datetime

DB_PATH = '/opt/mediacrawler/database/sqlite_tables.db'

# 常见停用词（中文）
STOP_WORDS = set('的了是在不我有也就都和人这个你一大很到说那要会可以没什么吗呢吧啊哦嗯好多还'
                 '上下中就是可以不是没有这个那个一个什么怎么为什么已经如果因为但是所以而且或者'
                 '他她它们我们你们他们自己最比被把给让从跟向对于以及之后之前')

# emoji 描述性文字（小红书评论里 [笑哭R] 类的文字化表达）+ 无意义高频词
EMOJI_STOP_WORDS = set('笑哭 害羞 捂脸 哭惹 飞吻 偷笑 呲牙 抓狂 可怜 '
                       '吃惊 撇嘴 调皮 得意 色色 大哭 鼓掌 强强 弱弱 '
                       '感觉 有点 一下 真的 好像 觉得 还是 可能 应该 '
                       '哈哈 嘻嘻 嘿嘿 呜呜 啊啊 嗯嗯 哇哇 '
                       '姐妹 宝宝 集美 亲亲 这个 那个'.split())

# 疑问词
QUESTION_WORDS = ['吗', '呢', '？', '?', '怎么', '如何', '什么', '哪个', '哪里', '多少',
                  '为什么', '哪些', '是不是', '能不能', '可以吗', '有没有', '好不好',
                  '求推荐', '求链接', '求问', '想问', '请问']


def parse_count(s) -> int:
    """Parse count strings like '10万+', '1.5万', '3037', etc."""
    if s is None:
        return 0
    s = str(s).strip().replace('+', '').replace(',', '')
    # Handle 万 (10k) suffix
    if '万' in s:
        try:
            return int(float(s.replace('万', '')) * 10000)
        except (ValueError, TypeError):
            return 0
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def tokenize_simple(text: str) -> list:
    """Simple Chinese tokenization: extract 2-4 char n-grams + full CJK words."""
    # Remove URLs, mentions
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    # Remove emoji text markers like [笑哭R] [捂脸R]
    text = re.sub(r'\[[^\]]{1,6}R?\]', '', text)

    # Extract CJK character sequences
    cjk_seqs = re.findall(r'[\u4e00-\u9fff]+', text)

    tokens = []
    for seq in cjk_seqs:
        if len(seq) <= 1:
            continue
        # 2-gram and 3-gram
        for n in [2, 3]:
            for i in range(len(seq) - n + 1):
                gram = seq[i:i+n]
                if gram in EMOJI_STOP_WORDS:
                    continue
                if not all(c in STOP_WORDS for c in gram):
                    tokens.append(gram)

    return tokens


def is_question(text: str) -> bool:
    """Check if a comment is a question."""
    for qw in QUESTION_WORDS:
        if qw in text:
            return True
    return False


def _extract_user_persona(comments, questions):
    """从评论中提取用户画像速写（规则引擎）。"""
    all_text = ' '.join((c['content'] or '') for c in comments)
    total = len(comments)
    if total == 0:
        return None

    # 1. Usage scenarios — what are they doing with the product?
    scenario_patterns = {
        '日常护肤': ['日常', '每天', '早晚', '睡前', '护肤'],
        '换季/敏感期': ['换季', '过敏', '泛红', '敏感', '刺痛'],
        '旅行/出行': ['旅行', '出门', '出差', '随身', '便携'],
        '送礼': ['送人', '送给', '礼物', '男朋友', '女朋友', '闺蜜'],
        '尝鲜/种草': ['种草', '试试', '想买', '入手', '拔草'],
        '省钱/平替': ['平替', '便宜', '省钱', '划算', '性价比'],
    }
    scenarios = []
    for label, keywords in scenario_patterns.items():
        count = sum(1 for c in comments if any(kw in (c['content'] or '') for kw in keywords))
        if count >= 2:
            scenarios.append({'label': label, 'mention_count': count})
    scenarios.sort(key=lambda x: x['mention_count'], reverse=True)

    # 2. Concerns / pain points
    concern_patterns = {
        '效果疑虑': ['有用吗', '有效吗', '真的假的', '管用', '没效果', '没用'],
        '价格顾虑': ['太贵', '好贵', '值得吗', '便宜', '价格', '打折'],
        '成分安全': ['成分', '刺激', '过敏', '安全', '孕妇'],
        '使用方法': ['怎么用', '怎么涂', '用量', '步骤', '顺序'],
        '适合肤质': ['油皮', '干皮', '混油', '混干', '敏感肌'],
        '购买渠道': ['在哪买', '链接', '旗舰店', '代购', '正品'],
    }
    concerns = []
    for label, keywords in concern_patterns.items():
        count = sum(1 for c in comments if any(kw in (c['content'] or '') for kw in keywords))
        if count >= 2:
            concerns.append({'label': label, 'mention_count': count})
    concerns.sort(key=lambda x: x['mention_count'], reverse=True)

    # 3. Decision barriers — from questions specifically
    barriers = []
    barrier_patterns = {
        '不确定是否适合自己': ['适合', '可以吗', '能不能', '能用吗'],
        '担心买到假货': ['正品', '假货', '真假', '鉴别'],
        '不知道怎么选': ['哪个好', '哪款', '推荐', '选择'],
        '价格犹豫': ['多少钱', '价格', '贵', '值得'],
    }
    for label, keywords in barrier_patterns.items():
        count = sum(1 for q in questions if any(kw in q.get('content', '') for kw in keywords))
        if count >= 1:
            barriers.append({'label': label, 'mention_count': count})
    barriers.sort(key=lambda x: x['mention_count'], reverse=True)

    # 4. Emotional tone — simple keyword matching
    tone_counts = {
        '积极/认可': 0, '犹豫/观望': 0, '求助/提问': 0, '吐槽/不满': 0,
    }
    positive_kw = ['好用', '推荐', '回购', '爱了', '绝了', '神器', '好看', '喜欢', '赞']
    hesitant_kw = ['观望', '犹豫', '纠结', '要不要', '值不值', '再看看']
    negative_kw = ['踩雷', '难用', '不好', '后悔', '退了', '差评', '失望', '鸡肋']
    for c in comments:
        text = c['content'] or ''
        if any(kw in text for kw in positive_kw):
            tone_counts['积极/认可'] += 1
        if any(kw in text for kw in hesitant_kw):
            tone_counts['犹豫/观望'] += 1
        if is_question(text):
            tone_counts['求助/提问'] += 1
        if any(kw in text for kw in negative_kw):
            tone_counts['吐槽/不满'] += 1

    tones = [{'label': k, 'count': v} for k, v in tone_counts.items() if v > 0]
    tones.sort(key=lambda x: x['count'], reverse=True)

    return {
        'scenarios': scenarios[:5],
        'concerns': concerns[:5],
        'barriers': barriers[:4],
        'emotional_tone': tones,
        'sample_size': total,
    }


def _detect_pain_point_clusters(comments, note_meta=None):
    """热帖痛点聚焦：检测同一帖子评论中围绕同一痛点的聚集。

    逻辑：当一篇 Top 20 帖子的评论中有 3+ 条指向同一痛点类型时，
    说明帖子触达了需求但没满足需求 → 内容机会。
    包含互动排名、帖子链接、市场判断。
    """
    note_meta = note_meta or {}

    # Pain point categories with detection keywords
    pain_categories = {
        '执行门槛高': ['麻烦', '复杂', '太难', '步骤', '费时', '难用', '怎么办', '不方便',
                       '买来干嘛', '这么多步骤', '找这么多借口'],
        '材料难获取': ['在哪买', '没有', '怎么办', '替代', '平替', '用什么代替', '链接', '求链接'],
        '适用范围存疑': ['适合', '油皮', '干皮', '敏感', '可以吗', '能用吗', '能不能',
                         '什么肤质', '不适合'],
        '效果存疑': ['有用吗', '真的假的', '有效', '没效果', '智商税', '翻车', '踩雷'],
        '价格质疑': ['太贵', '好贵', '值不值', '多少钱', '价格', '性价比'],
    }

    # Opportunity text templates per pain type
    opportunity_map = {
        '执行门槛高': '做同一效果的低门槛版本，解决"太复杂"的痛点',
        '材料难获取': '做替代方案/购买渠道指南，解决"买不到"的痛点',
        '适用范围存疑': '做特定人群适用性测评，解决"不确定适不适合自己"的痛点',
        '效果存疑': '做真实效果对比/长期使用报告，解决"到底有没有用"的疑虑',
        '价格质疑': '做不同价位替代方案对比，解决"太贵了"的阻力',
    }

    # Group comments by note_id
    note_comments = {}
    for c in comments:
        nid = c['note_id']
        if nid not in note_comments:
            note_comments[nid] = {
                'note_title': (c['note_title'] or '')[:40],
                'comments': [],
            }
        note_comments[nid]['comments'].append(c)

    clusters = []
    for nid, data in note_comments.items():
        note_title = data['note_title']
        cms = data['comments']
        total_comments = len(cms)
        meta = note_meta.get(nid, {})

        # Question density for this note
        q_count = sum(1 for c in cms if is_question(c['content'] or ''))
        q_density = round(q_count / max(total_comments, 1) * 100)

        for pain_label, keywords in pain_categories.items():
            matching = []
            for c in cms:
                text = c['content'] or ''
                if any(kw in text for kw in keywords):
                    matching.append({
                        'content': text[:80],
                        'like_count': parse_count(c['like_count']),
                    })

            if len(matching) >= 3:
                matching.sort(key=lambda x: x['like_count'], reverse=True)
                total_likes = sum(m['like_count'] for m in matching)
                pain_ratio = round(len(matching) / max(total_comments, 1) * 100)
                interaction_score = meta.get('interaction_score', 0)
                rank = meta.get('rank', 0)
                rank_total = meta.get('rank_total', 0)

                # Confidence: HIGH if top 5 + high question density, else MEDIUM
                confidence = 'HIGH' if (rank <= 5 and q_density >= 30) else 'MEDIUM'

                # Generate market judgment
                rank_text = f'全场 #{rank}' if rank else ''
                market_judgment = f'需求已被 {interaction_score:,} 互动分验证（{rank_text}），但评论揭示了"{pain_label}"障碍'
                opportunity = opportunity_map.get(pain_label, '可以做解决此障碍的简化版/替代版内容')

                clusters.append({
                    'note_id': nid,
                    'note_title': note_title,
                    'note_url': meta.get('note_url', ''),
                    'interaction_score': interaction_score,
                    'rank': rank,
                    'rank_total': rank_total,
                    'pain_type': pain_label,
                    'comment_count': len(matching),
                    'total_comments': total_comments,
                    'question_density': q_density,
                    'pain_ratio': pain_ratio,
                    'total_likes': total_likes,
                    'confidence': confidence,
                    'market_judgment': market_judgment,
                    'opportunity': opportunity,
                    'representative_comments': matching[:3],
                })

    # Sort by interaction_score desc (highest traffic posts first)
    clusters.sort(key=lambda x: x['interaction_score'], reverse=True)
    return clusters[:10]


def _compute_comment_quality(comments, note_meta=None):
    """为有评论的帖子计算评论质量分。

    三个维度:
    - question_ratio: 评论中提问比例（高=用户有执行困惑）
    - controversy_ratio: 争议性评论比例（高=话题有对立面）
    - product_alt_ratio: 产品替代/对比评论比例（高=有选品需求）
    """
    note_meta = note_meta or {}
    controversy_kw = ['难用', '不好', '踩雷', '后悔', '找借口', '智商税',
                      '不同意', '才不是', '并不', '无语', '服了']
    product_alt_kw = ['平替', '替代', '代替', '哪个好', '还是', '推荐',
                      '用什么', '什么牌子', '品牌', '产品']

    # Group by note_id
    note_comments = {}
    for c in comments:
        nid = c['note_id']
        if nid not in note_comments:
            note_comments[nid] = {
                'note_title': (c['note_title'] or '')[:40],
                'note_id': nid,
                'comments': [],
            }
        note_comments[nid]['comments'].append(c)

    results = []
    for nid, data in note_comments.items():
        cms = data['comments']
        total = len(cms)
        if total < 3:
            continue

        q_count = sum(1 for c in cms if is_question(c['content'] or ''))
        controv = sum(1 for c in cms if any(kw in (c['content'] or '') for kw in controversy_kw))
        prod_alt = sum(1 for c in cms if any(kw in (c['content'] or '') for kw in product_alt_kw))

        q_ratio = round(q_count / total * 100)
        c_ratio = round(controv / total * 100)
        p_ratio = round(prod_alt / total * 100)

        # Composite score: weighted combination (0-100)
        # High question ratio + controversy = discussion-type content
        score = min(100, q_ratio * 2 + c_ratio * 3 + p_ratio * 2)

        meta = note_meta.get(nid, {})
        results.append({
            'note_id': nid,
            'note_title': data['note_title'],
            'note_url': meta.get('note_url', ''),
            'interaction_score': meta.get('interaction_score', 0),
            'rank': meta.get('rank', 0),
            'total_comments': total,
            'question_ratio': q_ratio,
            'controversy_ratio': c_ratio,
            'product_alt_ratio': p_ratio,
            'quality_score': score,
            'insights': [],
        })

        # Generate insights
        r = results[-1]
        if q_ratio > 30:
            r['insights'].append('提问密集：用户有执行困惑，内容机会存在')
        if c_ratio > 20:
            r['insights'].append('争议性高：话题有对立面，做"另一个视角"也能有流量')
        if p_ratio > 20:
            r['insights'].append('选品需求强：用户在比较产品，可以做对比/选购内容')

    results.sort(key=lambda x: x['quality_score'], reverse=True)
    return results[:15]


def analyze_comments(keywords=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all comments with note info (including URL and interaction data)
    where_clause = ''
    params = ()
    if keywords:
        placeholders = ','.join('?' for _ in keywords)
        where_clause = f'WHERE n.source_keyword IN ({placeholders})'
        params = tuple(keywords)

    comments = cur.execute(f'''
        SELECT c.comment_id, c.note_id, c.content, c.like_count,
               c.create_time, c.sub_comment_count, c.parent_comment_id,
               c.nickname, c.user_id,
               n.title as note_title,
               n.note_url,
               n.liked_count as note_liked,
               n.collected_count as note_collected,
               n.comment_count as note_comment_count,
               n.share_count as note_shared
        FROM xhs_note_comment c
        LEFT JOIN xhs_note n ON c.note_id = n.note_id
        {where_clause}
        ORDER BY CAST(c.like_count AS INTEGER) DESC
    ''', params).fetchall()

    # Build note metadata (interaction score + rank + URL) for enriching analyses
    note_meta = {}
    for c in comments:
        nid = c['note_id']
        if nid not in note_meta:
            liked = parse_count(c['note_liked'])
            collected = parse_count(c['note_collected'])
            cmt = parse_count(c['note_comment_count'])
            shared = parse_count(c['note_shared'])
            score = liked + collected * 3 + cmt * 5 + shared * 8
            note_meta[nid] = {
                'note_url': c['note_url'] or '',
                'interaction_score': score,
                'note_title': (c['note_title'] or '')[:40],
            }
    # Compute rank
    ranked = sorted(note_meta.items(), key=lambda x: x[1]['interaction_score'], reverse=True)
    for rank, (nid, meta) in enumerate(ranked, 1):
        meta['rank'] = rank
        meta['rank_total'] = len(ranked)

    conn.close()

    if not comments:
        print('No comments in database')
        return None

    print(f'Total comments: {len(comments)}')
    note_ids = set(c['note_id'] for c in comments)
    print(f'Across {len(note_ids)} notes')
    print()

    # --- 1. High-frequency words ---
    all_tokens = []
    for c in comments:
        content = c['content'] or ''
        if content:
            all_tokens.extend(tokenize_simple(content))

    word_freq = Counter(all_tokens)
    # Filter: at least 3 occurrences
    top_words = [(w, cnt) for w, cnt in word_freq.most_common(50) if cnt >= 2]

    # --- 2. Questions ---
    questions = []
    for c in comments:
        content = c['content'] or ''
        if content and is_question(content):
            questions.append({
                'content': content[:100],
                'like_count': parse_count(c['like_count']),
                'nickname': c['nickname'] or '',
                'note_title': (c['note_title'] or '')[:30],
                'note_id': c['note_id'],
            })
    questions.sort(key=lambda x: x['like_count'], reverse=True)

    # --- 3. Top liked comments ---
    top_liked = []
    for c in comments[:30]:  # already sorted by like_count DESC
        likes = parse_count(c['like_count'])
        if likes > 0:
            top_liked.append({
                'content': (c['content'] or '')[:100],
                'like_count': likes,
                'nickname': c['nickname'] or '',
                'note_title': (c['note_title'] or '')[:30],
                'note_id': c['note_id'],
                'sub_comment_count': c['sub_comment_count'] or 0,
            })

    # --- 4. Per-note summary ---
    note_summaries = {}
    for c in comments:
        nid = c['note_id']
        if nid not in note_summaries:
            meta = note_meta.get(nid, {})
            note_summaries[nid] = {
                'note_title': (c['note_title'] or '')[:40],
                'note_url': meta.get('note_url', ''),
                'interaction_score': meta.get('interaction_score', 0),
                'comment_count': 0,
                'question_count': 0,
                'total_likes': 0,
                'top_comment': '',
                'top_comment_likes': 0,
            }
        ns = note_summaries[nid]
        ns['comment_count'] += 1
        likes = parse_count(c['like_count'])
        ns['total_likes'] += likes
        if c['content'] and is_question(c['content']):
            ns['question_count'] += 1
        if likes > ns['top_comment_likes']:
            ns['top_comment_likes'] = likes
            ns['top_comment'] = (c['content'] or '')[:60]

    # --- 5. User persona extraction ---
    persona = _extract_user_persona(comments, questions)

    # --- 6. Pain point clusters (热帖痛点聚焦) ---
    pain_clusters = _detect_pain_point_clusters(comments, note_meta)

    # --- 7. Comment quality scores ---
    comment_quality = _compute_comment_quality(comments, note_meta)

    report = {
        'meta': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_comments': len(comments),
            'notes_with_comments': len(note_ids),
            'total_questions': len(questions),
        },
        'high_frequency_words': [{'word': w, 'count': cnt} for w, cnt in top_words[:20]],
        'questions': questions[:15],
        'top_liked_comments': top_liked[:15],
        'user_persona': persona,
        'pain_point_clusters': pain_clusters,
        'comment_quality': comment_quality,
        'note_summaries': [
            {**{'note_id': nid}, **ns}
            for nid, ns in sorted(note_summaries.items(),
                                  key=lambda x: x[1]['comment_count'], reverse=True)
        ],
    }

    return report


def print_report(report):
    if not report:
        return

    m = report['meta']
    print('=' * 60)
    print('XHS 评论分析报告')
    print(f'日期: {m["date"]}')
    print(f'数据量: {m["total_comments"]} 条评论, {m["notes_with_comments"]} 个帖子')
    print('=' * 60)

    # High-frequency words
    print('\n高频词 (Top 20):')
    for w in report['high_frequency_words']:
        print(f'  {w["word"]}: {w["count"]}')

    # Questions
    print(f'\n用户提问 ({m["total_questions"]} 条):')
    for i, q in enumerate(report['questions'][:10]):
        like_tag = f' ({q["like_count"]}赞)' if q['like_count'] > 0 else ''
        print(f'  {i+1}. {q["content"][:60]}{like_tag}')
        print(f'     ← {q["note_title"]}')

    # Top liked
    print('\n热门评论 (按赞数排序):')
    for i, c in enumerate(report['top_liked_comments'][:10]):
        print(f'  {i+1}. [{c["like_count"]}赞] {c["content"][:60]}')
        print(f'     ← {c["note_title"]}')

    # Per-note summary
    print('\n帖子评论概览:')
    print(f'{"帖子标题":<40} {"评论":>4} {"提问":>4} {"总赞":>6} {"热评"}')
    print('-' * 100)
    for ns in report['note_summaries'][:15]:
        print(f'{ns["note_title"]:<40} {ns["comment_count"]:>4} '
              f'{ns["question_count"]:>4} {ns["total_likes"]:>6} '
              f'{ns["top_comment"][:30]}')

    print('\n' + '=' * 60)


def main():
    parser = argparse.ArgumentParser(description='XHS 评论分析')
    parser.add_argument('--json-out', help='输出 JSON 到指定路径')
    parser.add_argument('--keywords', help='逗号分隔的关键词过滤（仅分析这些 source_keyword 对应笔记的评论）')
    args = parser.parse_args()

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]

    report = analyze_comments(keywords=keywords)
    if not report:
        return 3

    print_report(report)

    if args.json_out:
        import os
        os.makedirs(os.path.dirname(args.json_out) or '.', exist_ok=True)
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f'\nJSON saved: {args.json_out}')

    return 0


if __name__ == '__main__':
    exit(main() or 0)
