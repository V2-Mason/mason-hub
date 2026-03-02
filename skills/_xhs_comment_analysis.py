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

# 疑问词
QUESTION_WORDS = ['吗', '呢', '？', '?', '怎么', '如何', '什么', '哪个', '哪里', '多少',
                  '为什么', '哪些', '是不是', '能不能', '可以吗', '有没有', '好不好',
                  '求推荐', '求链接', '求问', '想问', '请问']


def parse_count(s) -> int:
    if s is None:
        return 0
    s = str(s).strip().replace('+', '')
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def tokenize_simple(text: str) -> list:
    """Simple Chinese tokenization: extract 2-4 char n-grams + full CJK words."""
    # Remove URLs, mentions, emojis (rough)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\S+', '', text)

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
                if not all(c in STOP_WORDS for c in gram):
                    tokens.append(gram)

    return tokens


def is_question(text: str) -> bool:
    """Check if a comment is a question."""
    for qw in QUESTION_WORDS:
        if qw in text:
            return True
    return False


def analyze_comments():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all comments with note info
    comments = cur.execute('''
        SELECT c.comment_id, c.note_id, c.content, c.like_count,
               c.create_time, c.sub_comment_count, c.parent_comment_id,
               c.nickname, c.user_id,
               n.title as note_title
        FROM xhs_note_comment c
        LEFT JOIN xhs_note n ON c.note_id = n.note_id
        ORDER BY CAST(c.like_count AS INTEGER) DESC
    ''').fetchall()

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
            note_summaries[nid] = {
                'note_title': (c['note_title'] or '')[:40],
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
    args = parser.parse_args()

    report = analyze_comments()
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
