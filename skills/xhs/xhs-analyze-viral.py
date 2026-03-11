"""
xhs-analyze-viral.py — XHS 爆款帖子分析

用法: python xhs-analyze-viral.py [--json-out /path/to/output.json]

功能:
- 数字归一化（"1.2万" → 12000）
- 互动评分（赞 + 藏×3 + 评×5 + 转×8）
- 假流量检测（评赞比<0.2% 或 藏赞比<5%）
- 爆款模式识别（干货型/话题型/社交货币型）
- 关键词维度分析
- 标题模式分析

输出: 终端文本报告 + 可选 JSON 文件（供策略简报脚本消费）
"""
import argparse
import sqlite3
import json
import re
import sys
import time
from datetime import datetime

DB = '/opt/mediacrawler/database/sqlite_tables.db'


def parse_count(s):
    if s is None: return 0
    s = str(s).strip().replace('+', '')
    if '万' in s: return int(float(s.replace('万', '')) * 10000)
    if '亿' in s: return int(float(s.replace('亿', '')) * 100000000)
    try: return int(s)
    except: return 0


def interaction_score(liked, collected, comment, shared):
    return liked + collected * 3 + comment * 5 + shared * 8


def analyze_from_clean(clean_json_path, keywords=None):
    """从 clean 层 JSON 读取已清洗的笔记数据（Layer 2 → Layer 3）。

    clean JSON 已完成: parse_count 归一化、指标计算、假流量标记、去重。
    此函数只做关键词过滤和排序。
    """
    import os
    if not os.path.exists(clean_json_path):
        print(f'ERROR: clean JSON 不存在: {clean_json_path}', file=sys.stderr)
        return []

    with open(clean_json_path, 'r', encoding='utf-8') as f:
        notes = json.load(f)

    print(f'[INFO] 从 clean JSON 读取: {len(notes)} 条笔记')

    # 关键词过滤
    if keywords:
        kw_set = set(keywords)
        notes = [n for n in notes if n.get('keyword', '') in kw_set]
        print(f'[INFO] 关键词过滤后: {len(notes)} 条')

    # 补全 clean JSON 中可能缺少的字段（向后兼容）
    for n in notes:
        n.setdefault('content_tier', 'unknown')
        n.setdefault('crawl_timestamp', 0)

    notes.sort(key=lambda x: x.get('score', 0), reverse=True)
    return notes


def analyze(keywords=None):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check which optional columns exist (added by P1/P3 upgrades)
    columns = [row[1] for row in cur.execute('PRAGMA table_info(xhs_note)').fetchall()]
    has_crawl_ts = 'crawl_timestamp' in columns
    has_content_tier = 'content_tier' in columns

    extra_cols = ''
    if has_crawl_ts:
        extra_cols += ', crawl_timestamp'
    if has_content_tier:
        extra_cols += ', content_tier'

    where_clause = ''
    params = ()
    if keywords:
        placeholders = ','.join('?' for _ in keywords)
        where_clause = f'WHERE source_keyword IN ({placeholders})'
        params = tuple(keywords)

    rows = cur.execute(f'''
        SELECT note_id, title, "desc", type, liked_count, collected_count,
               comment_count, share_count, tag_list, source_keyword, note_url, nickname, time, user_id
               {extra_cols}
        FROM xhs_note
        {where_clause}
    ''', params).fetchall()

    notes = []
    for r in rows:
        liked = parse_count(r['liked_count'])
        collected = parse_count(r['collected_count'])
        comment = parse_count(r['comment_count'])
        shared = parse_count(r['share_count'])
        score = interaction_score(liked, collected, comment, shared)

        engage_rate = (comment / liked * 100) if liked > 0 else 0
        save_rate = (collected / liked * 100) if liked > 0 else 0
        share_rate = (shared / liked * 100) if liked > 0 else 0

        fake_flags = []
        if liked > 1000 and engage_rate < 0.2:
            fake_flags.append('评赞比过低')
        if liked > 1000 and save_rate < 5:
            fake_flags.append('藏赞比过低')

        # 时间戳转日期 + 计算帖子年龄
        ts = r['time']
        pub_date = ''
        post_age_days = -1  # -1 = unknown
        if ts and int(ts) > 0:
            ts_val = int(ts)
            # Normalize: if > 1e12, it's milliseconds
            ts_s = ts_val / 1000 if ts_val > 1e12 else ts_val
            pub_date = datetime.fromtimestamp(ts_s).strftime('%Y-%m-%d')
            post_age_days = round((time.time() - ts_s) / 86400)

        # crawl_timestamp (seconds since epoch)
        crawl_ts = r['crawl_timestamp'] if has_crawl_ts and r['crawl_timestamp'] else 0
        content_tier = r['content_tier'] if has_content_tier else 'unknown'

        notes.append({
            'note_id': r['note_id'],
            'title': r['title'] or '',
            'desc': r['desc'] or '',
            'type': r['type'] or 'normal',
            'liked': liked, 'collected': collected, 'comment': comment, 'shared': shared,
            'score': score,
            'engage_rate': round(engage_rate, 2),
            'save_rate': round(save_rate, 1),
            'share_rate': round(share_rate, 1),
            'tags': r['tag_list'] or '',
            'keyword': r['source_keyword'] or '',
            'url': r['note_url'] or '',
            'nickname': r['nickname'] or '',
            'user_id': r['user_id'] or '',
            'pub_date': pub_date,
            'post_age_days': post_age_days,
            'crawl_timestamp': crawl_ts,
            'content_tier': content_tier,
            'fake_flags': fake_flags,
        })

    conn.close()
    notes.sort(key=lambda x: x['score'], reverse=True)
    return notes


def build_report(notes):
    """构建结构化分析结果，同时用于文本输出和 JSON 输出"""

    # --- 关键词统计 ---
    kw_stats = {}
    for n in notes:
        kw = n['keyword']
        if kw not in kw_stats:
            kw_stats[kw] = {'count': 0, 'scores': [], 'video': 0, 'normal': 0,
                            'top_title': '', 'top_score': 0, 'top_url': ''}
        kw_stats[kw]['count'] += 1
        kw_stats[kw]['scores'].append(n['score'])
        if n['type'] == 'video': kw_stats[kw]['video'] += 1
        else: kw_stats[kw]['normal'] += 1
        if n['score'] > kw_stats[kw]['top_score']:
            kw_stats[kw]['top_score'] = n['score']
            kw_stats[kw]['top_title'] = n['title'][:40]
            kw_stats[kw]['top_url'] = n['url']

    # Compute global median score for competition density
    all_scores = [n['score'] for n in notes]
    global_median = sorted(all_scores)[len(all_scores) // 2] if all_scores else 0

    keyword_insights = []
    for kw, stats in sorted(kw_stats.items(), key=lambda x: sum(x[1]['scores'])/len(x[1]['scores']), reverse=True):
        avg = sum(stats['scores']) / len(stats['scores'])
        count = stats['count']
        scores = stats['scores']

        # Competition density: 蓝海/红海/待观察
        # 蓝海: count < 5 AND avg_score > global_median (few posts, high engagement)
        # 红海: count > 15 AND score spread dispersed (many posts, competitive)
        # 待观察: everything else
        if count < 5 and avg > global_median:
            competition = '蓝海'
        elif count > 15:
            competition = '红海'
        elif count >= 5 and avg < global_median * 0.5:
            competition = '红海'
        else:
            competition = '待观察'

        keyword_insights.append({
            'keyword': kw, 'count': count,
            'avg_score': round(avg), 'top_score': stats['top_score'],
            'video_ratio': round(stats['video'] / count * 100),
            'top_title': stats['top_title'], 'top_url': stats['top_url'],
            'competition': competition,
        })

    # --- 爆款模式 ---
    high_save = sorted([n for n in notes if n['save_rate'] > 30 and n['liked'] > 1000],
                       key=lambda x: x['save_rate'], reverse=True)[:5]
    high_engage = sorted([n for n in notes if n['engage_rate'] > 2 and n['liked'] > 1000],
                         key=lambda x: x['engage_rate'], reverse=True)[:5]
    high_share = sorted([n for n in notes if n['share_rate'] > 3 and n['liked'] > 1000],
                        key=lambda x: x['share_rate'], reverse=True)[:5]

    # --- 内容类型 ---
    video_notes = [n for n in notes if n['type'] == 'video']
    normal_notes = [n for n in notes if n['type'] == 'normal']
    avg_video = sum(n['score'] for n in video_notes) / max(len(video_notes), 1)
    avg_normal = sum(n['score'] for n in normal_notes) / max(len(normal_notes), 1)

    # --- 标题模式 ---
    has_num = [n for n in notes if re.search(r'\d', n['title'])]
    no_num = [n for n in notes if not re.search(r'\d', n['title'])]
    has_exclaim = [n for n in notes if re.search(r'[！!‼️]', n['title'])]

    # --- 假流量 ---
    fakes = [n for n in notes if n['fake_flags']]

    # Age distribution
    known_ages = [n['post_age_days'] for n in notes if n['post_age_days'] >= 0]
    age_stats = {}
    if known_ages:
        age_stats = {
            'min_age_days': min(known_ages),
            'max_age_days': max(known_ages),
            'median_age_days': sorted(known_ages)[len(known_ages) // 2],
            'within_30d': sum(1 for a in known_ages if a <= 30),
            'within_7d': sum(1 for a in known_ages if a <= 7),
            'older_than_90d': sum(1 for a in known_ages if a > 90),
            'age_known_count': len(known_ages),
        }

    return {
        'meta': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_notes': len(notes),
            'video_count': len(video_notes),
            'normal_count': len(normal_notes),
            'age_distribution': age_stats,
        },
        'top_posts': [{
            'title': n['title'], 'score': n['score'], 'type': n['type'],
            'liked': n['liked'], 'collected': n['collected'],
            'comment': n['comment'], 'shared': n['shared'],
            'save_rate': n['save_rate'], 'engage_rate': n['engage_rate'],
            'share_rate': n['share_rate'],
            'url': n['url'], 'nickname': n['nickname'],
            'user_id': n['user_id'],
            'pub_date': n['pub_date'],
            'post_age_days': n['post_age_days'],
            'content_tier': n['content_tier'],
            'fake_flags': n['fake_flags'],
        } for n in notes[:20]],
        'keyword_insights': keyword_insights,
        'patterns': {
            'high_save': [{'title': n['title'], 'save_rate': n['save_rate'],
                           'type': n['type'], 'nickname': n['nickname'], 'url': n['url'],
                           'pub_date': n['pub_date']} for n in high_save],
            'high_engage': [{'title': n['title'], 'engage_rate': n['engage_rate'],
                             'type': n['type'], 'nickname': n['nickname'], 'url': n['url'],
                             'pub_date': n['pub_date']} for n in high_engage],
            'high_share': [{'title': n['title'], 'share_rate': n['share_rate'],
                            'type': n['type'], 'nickname': n['nickname'], 'url': n['url'],
                            'pub_date': n['pub_date']} for n in high_share],
        },
        'content_type': {
            'video_avg_score': round(avg_video),
            'normal_avg_score': round(avg_normal),
            'video_ratio': round(len(video_notes) / max(len(notes), 1) * 100),
        },
        'title_patterns': {
            'with_number_avg': round(sum(n['score'] for n in has_num) / max(len(has_num), 1)),
            'without_number_avg': round(sum(n['score'] for n in no_num) / max(len(no_num), 1)),
            'with_exclaim_avg': round(sum(n['score'] for n in has_exclaim) / max(len(has_exclaim), 1)),
        },
        'fake_traffic': {
            'count': len(fakes),
            'posts': [{'title': n['title'], 'liked': n['liked'],
                        'save_rate': n['save_rate'], 'engage_rate': n['engage_rate'],
                        'flags': n['fake_flags']} for n in fakes[:10]],
        },
    }


def print_report(notes, report):
    """输出文本报告到终端"""
    print("=" * 60)
    print(f"XHS 爆款帖子分析报告")
    print(f"日期: {report['meta']['date']}")
    print(f"数据量: {report['meta']['total_notes']} 条笔记")
    print("=" * 60)

    # Top 15
    print(f"\nTop 15 高互动帖子:")
    print(f"{'#':<3} {'互动分':>10} {'赞':>8} {'藏':>8} {'评':>6} {'转':>6} {'类型':<6} {'藏赞比':>6} {'标题'}")
    print("-" * 100)
    for i, n in enumerate(report['top_posts'][:15]):
        flag = ' [!]' if n['fake_flags'] else ''
        print(f"{i+1:<3} {n['score']:>10,} {n['liked']:>8,} {n['collected']:>8,} "
              f"{n['comment']:>6,} {n['shared']:>6,} {n['type']:<6} {n['save_rate']:>5.1f}% "
              f"{n['title'][:40]}{flag}")

    # 内容类型
    ct = report['content_type']
    print(f"\n内容类型:")
    print(f"  视频: {report['meta']['video_count']} 条 ({ct['video_ratio']}%), 平均互动分 {ct['video_avg_score']:,}")
    print(f"  图文: {report['meta']['normal_count']} 条 ({100 - ct['video_ratio']}%), 平均互动分 {ct['normal_avg_score']:,}")

    # 关键词
    print(f"\n关键词维度:")
    print(f"{'关键词':<20} {'数量':>4} {'平均分':>10} {'视频占比':>8} {'最佳标题'}")
    print("-" * 90)
    for kw in report['keyword_insights']:
        print(f"{kw['keyword']:<20} {kw['count']:>4} {kw['avg_score']:>10,} {kw['video_ratio']:>6}%  {kw['top_title']}")

    # 爆款模式
    print(f"\n爆款模式:")
    print(f"  高藏赞比 (干货/教程):")
    for n in report['patterns']['high_save']:
        print(f"    [{n['save_rate']:.0f}%] {n['title'][:45]}")
    print(f"  高评赞比 (话题/争议):")
    for n in report['patterns']['high_engage']:
        print(f"    [{n['engage_rate']:.1f}%] {n['title'][:45]}")
    print(f"  高转赞比 (社交货币):")
    for n in report['patterns']['high_share']:
        print(f"    [{n['share_rate']:.1f}%] {n['title'][:45]}")

    # 标题
    tp = report['title_patterns']
    print(f"\n标题模式:")
    print(f"  含数字: 平均 {tp['with_number_avg']:,} vs 无数字: {tp['without_number_avg']:,} (+{round((tp['with_number_avg']/max(tp['without_number_avg'],1)-1)*100)}%)")
    print(f"  含感叹号: 平均 {tp['with_exclaim_avg']:,}")

    # 假流量
    ft = report['fake_traffic']
    print(f"\n假流量预警: {ft['count']} 条可疑")
    for n in ft['posts'][:5]:
        print(f"  {n['title'][:40]} — {', '.join(n['flags'])}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description='XHS 爆款帖子分析')
    parser.add_argument('--json-out', help='输出 JSON 分析结果到指定路径')
    parser.add_argument('--keywords', help='逗号分隔的关键词过滤（仅分析这些 source_keyword）')
    parser.add_argument('--clean-json', help='从 clean 层 JSON 读取（跳过 SQLite + 归一化）')
    args = parser.parse_args()

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]

    if args.clean_json:
        notes = analyze_from_clean(args.clean_json, keywords=keywords)
    else:
        notes = analyze(keywords=keywords)
    if not notes:
        print('ERROR: 无数据（数据库为空或 clean JSON 无匹配）')
        return 1

    report = build_report(notes)
    print_report(notes, report)

    if args.json_out:
        import os
        os.makedirs(os.path.dirname(args.json_out) or '.', exist_ok=True)
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nJSON saved: {args.json_out}")

    return 0


if __name__ == '__main__':
    exit(main() or 0)
