"""
_xhs_publish_log.py — 发布记录管理

子命令:
  log     记录一次发布
  check   回查已发布帖子的实际表现（72h+ 后）
  list    列出所有发布记录
  review  复盘：对比预期 vs 实际

用法:
  python _xhs_publish_log.py log --title "标题" --keywords "k1,k2" [--type video] [--expect high] [--reason "理由"]
  python _xhs_publish_log.py check [--id 1] [--all]
  python _xhs_publish_log.py list
  python _xhs_publish_log.py review [--json-out /path/to/output.json]
"""
import argparse
import json
import sqlite3
import time
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


def interaction_score(liked, collected, comment, shared) -> int:
    return liked + collected * 3 + comment * 5 + shared * 8


def get_latest_signal_date():
    """Find the latest market signal briefing date."""
    import os
    import glob
    briefing_dir = '/opt/mediacrawler/analysis/briefings'
    if not os.path.isdir(briefing_dir):
        return None
    files = sorted(glob.glob(os.path.join(briefing_dir, '*.json')), reverse=True)
    if files:
        basename = os.path.basename(files[0])
        return basename.replace('.json', '')
    return None


def cmd_log(args):
    """Record a new publish event."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_s = int(time.time())
    now_ms = now_s * 1000
    today = datetime.now().strftime('%Y-%m-%d')

    signal_date = get_latest_signal_date()

    # Try to load a signal snapshot if available
    signal_snapshot = ''
    if signal_date:
        import os
        briefing_path = f'/opt/mediacrawler/analysis/briefings/{signal_date}.json'
        if os.path.exists(briefing_path):
            with open(briefing_path) as f:
                briefing = json.load(f)
            # Extract relevant signals for the target keywords
            keywords = [k.strip() for k in (args.keywords or '').split(',') if k.strip()]
            relevant = []
            for sig in briefing.get('market_signals', []):
                obs = sig.get('observation', '')
                if any(kw in obs for kw in keywords) or not keywords:
                    relevant.append({
                        'observation': obs,
                        'confidence': sig.get('confidence', ''),
                    })
            signal_snapshot = json.dumps(relevant[:5], ensure_ascii=False)

    cur.execute('''
        INSERT INTO xhs_publish_log (
            title, publish_date, publish_ts, content_type,
            target_keywords, account,
            market_signal_date, signal_snapshot,
            expected_tier, expected_reason,
            add_ts, last_modify_ts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        args.title, today, now_s,
        args.type or 'normal',
        args.keywords or '',
        args.account or 'MAIN',
        signal_date or '',
        signal_snapshot,
        args.expect or '',
        args.reason or '',
        now_ms, now_ms,
    ))

    log_id = cur.lastrowid
    conn.commit()
    conn.close()

    print(f'Logged publish #{log_id}:')
    print(f'  Title: {args.title}')
    print(f'  Date: {today}')
    print(f'  Keywords: {args.keywords or "(none)"}')
    print(f'  Expected: {args.expect or "(not set)"}')
    if signal_date:
        print(f'  Signal ref: {signal_date}')
    print(f'\nAfter 72h, run: python _xhs_publish_log.py check --id {log_id}')
    return 0


def cmd_check(args):
    """Check actual performance of published posts by looking them up in xhs_note."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    now_s = int(time.time())
    today = datetime.now().strftime('%Y-%m-%d')

    if args.id:
        rows = cur.execute('SELECT * FROM xhs_publish_log WHERE id = ?', (args.id,)).fetchall()
    elif args.all:
        # Check all posts older than 72h that haven't been checked
        rows = cur.execute('''
            SELECT * FROM xhs_publish_log
            WHERE check_date IS NULL OR check_date = ''
            ORDER BY publish_ts ASC
        ''').fetchall()
    else:
        # Default: check posts between 3-14 days old without check
        rows = cur.execute('''
            SELECT * FROM xhs_publish_log
            WHERE (check_date IS NULL OR check_date = '')
              AND publish_ts < ?
              AND publish_ts > ?
            ORDER BY publish_ts ASC
        ''', (now_s - 3 * 86400, now_s - 14 * 86400)).fetchall()

    if not rows:
        print('No posts to check')
        conn.close()
        return 3

    checked = 0
    for row in rows:
        log_id = row['id']
        title = row['title']
        note_id = row['note_id']

        print(f'\n--- #{log_id}: {title} ---')

        # Try to find the note in xhs_note by note_id or title match
        note = None
        if note_id:
            note = cur.execute(
                'SELECT * FROM xhs_note WHERE note_id = ?', (note_id,)
            ).fetchone()

        if not note:
            # Fuzzy match by title
            candidates = cur.execute(
                'SELECT * FROM xhs_note WHERE title LIKE ?',
                (f'%{title[:20]}%',)
            ).fetchall()
            if len(candidates) == 1:
                note = candidates[0]
                # Save note_id for future lookups
                cur.execute('UPDATE xhs_publish_log SET note_id = ? WHERE id = ?',
                            (note['note_id'], log_id))
                print(f'  Matched note_id: {note["note_id"]}')
            elif len(candidates) > 1:
                print(f'  Multiple matches ({len(candidates)}), need note_id')
                print(f'  Hint: set note_id with: UPDATE xhs_publish_log SET note_id="xxx" WHERE id={log_id}')
                continue
            else:
                print(f'  Not found in xhs_note (may not have been crawled yet)')
                print(f'  If you have the note_id, set it manually')
                continue

        # Extract actual performance
        liked = parse_count(note['liked_count'])
        collected = parse_count(note['collected_count'])
        comment = parse_count(note['comment_count'])
        shared = parse_count(note['share_count'])
        score = interaction_score(liked, collected, comment, shared)

        # Determine outcome based on expected_tier
        expected = row['expected_tier'] or ''
        outcome = ''
        if expected:
            # Get score distribution for context
            all_scores = cur.execute(
                'SELECT liked_count, collected_count, comment_count, share_count FROM xhs_note'
            ).fetchall()
            scores_list = sorted([
                interaction_score(
                    parse_count(s[0]), parse_count(s[1]),
                    parse_count(s[2]), parse_count(s[3])
                ) for s in all_scores
            ])
            p75 = scores_list[int(len(scores_list) * 0.75)] if scores_list else 0
            p50 = scores_list[int(len(scores_list) * 0.50)] if scores_list else 0
            p25 = scores_list[int(len(scores_list) * 0.25)] if scores_list else 0

            if expected == 'high':
                outcome = 'hit' if score >= p75 else ('partial' if score >= p50 else 'miss')
            elif expected == 'medium':
                outcome = 'hit' if p25 <= score <= p75 else 'miss'
            elif expected == 'low':
                outcome = 'hit' if score <= p50 else 'miss'

        # Update record
        cur.execute('''
            UPDATE xhs_publish_log SET
                actual_liked = ?, actual_collected = ?, actual_comment = ?, actual_shared = ?,
                actual_score = ?, check_date = ?, check_ts = ?,
                outcome = ?, last_modify_ts = ?
            WHERE id = ?
        ''', (liked, collected, comment, shared, score,
              today, now_s, outcome, int(time.time() * 1000), log_id))

        age_days = round((now_s - row['publish_ts']) / 86400) if row['publish_ts'] else '?'
        print(f'  Performance ({age_days}d after publish):')
        print(f'    Liked: {liked:,}  Collected: {collected:,}  Comment: {comment:,}  Shared: {shared:,}')
        print(f'    Score: {score:,}')
        if expected:
            print(f'  Expected: {expected} → Outcome: {outcome}')
        checked += 1

    conn.commit()
    conn.close()
    print(f'\nChecked {checked}/{len(rows)} posts')
    return 0


def cmd_list(args):
    """List all publish log entries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT * FROM xhs_publish_log ORDER BY publish_ts DESC
    ''').fetchall()
    conn.close()

    if not rows:
        print('No publish records yet')
        print('Log one with: python _xhs_publish_log.py log --title "标题" --keywords "k1,k2"')
        return 3

    print(f'{"#":<4} {"日期":<12} {"标题":<35} {"预期":<8} {"实际分":<10} {"结果":<8}')
    print('-' * 80)
    for r in rows:
        score_str = f'{r["actual_score"]:,}' if r['actual_score'] else '-'
        outcome = r['outcome'] or '-'
        print(f'{r["id"]:<4} {r["publish_date"]:<12} {r["title"][:33]:<35} '
              f'{r["expected_tier"] or "-":<8} {score_str:<10} {outcome:<8}')

    total = len(rows)
    checked = sum(1 for r in rows if r['outcome'])
    hits = sum(1 for r in rows if r['outcome'] == 'hit')
    print(f'\nTotal: {total}, Checked: {checked}, Hits: {hits}')
    if checked > 0:
        print(f'Accuracy: {hits}/{checked} = {hits/checked*100:.0f}%')
    return 0


def cmd_review(args):
    """Generate prediction accuracy review."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT * FROM xhs_publish_log
        WHERE outcome IS NOT NULL AND outcome != ''
        ORDER BY publish_ts DESC
    ''').fetchall()
    conn.close()

    if not rows:
        print('No reviewed posts yet (run "check" first)')
        return 3

    total = len(rows)
    hits = sum(1 for r in rows if r['outcome'] == 'hit')
    misses = sum(1 for r in rows if r['outcome'] == 'miss')
    partials = sum(1 for r in rows if r['outcome'] == 'partial')

    # By expected tier
    by_tier = {}
    for r in rows:
        tier = r['expected_tier'] or 'unset'
        if tier not in by_tier:
            by_tier[tier] = {'total': 0, 'hit': 0, 'miss': 0, 'partial': 0}
        by_tier[tier]['total'] += 1
        by_tier[tier][r['outcome']] = by_tier[tier].get(r['outcome'], 0) + 1

    # By content type
    by_type = {}
    for r in rows:
        ct = r['content_type'] or 'normal'
        if ct not in by_type:
            by_type[ct] = {'total': 0, 'hit': 0, 'miss': 0, 'partial': 0}
        by_type[ct]['total'] += 1
        by_type[ct][r['outcome']] = by_type[ct].get(r['outcome'], 0) + 1

    report = {
        'meta': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_reviewed': total,
        },
        'accuracy': {
            'hit': hits,
            'miss': misses,
            'partial': partials,
            'hit_rate': round(hits / total * 100, 1) if total else 0,
        },
        'by_expected_tier': {
            tier: {
                'total': s['total'],
                'hit_rate': round(s['hit'] / s['total'] * 100, 1) if s['total'] else 0,
            }
            for tier, s in by_tier.items()
        },
        'by_content_type': {
            ct: {
                'total': s['total'],
                'hit_rate': round(s['hit'] / s['total'] * 100, 1) if s['total'] else 0,
            }
            for ct, s in by_type.items()
        },
        'posts': [{
            'id': r['id'],
            'title': r['title'],
            'publish_date': r['publish_date'],
            'expected_tier': r['expected_tier'] or '',
            'actual_score': r['actual_score'],
            'outcome': r['outcome'],
            'keywords': r['target_keywords'] or '',
        } for r in rows],
        'known_limitations': [
            '预期分级 (high/medium/low) 是主观判断，不同人标准不同',
            'outcome 基于当前 DB 数据分位数，DB 数据本身有偏差',
            '72h 表现不代表长期表现，病毒式传播可能更晚',
            '样本太少时准确率无统计意义',
        ],
    }

    # Print report
    print('=' * 60)
    print('XHS 发布预测准确度复盘')
    print(f'日期: {report["meta"]["date"]}')
    print(f'已复盘: {total} 条')
    print('=' * 60)

    acc = report['accuracy']
    print(f'\n总体准确率: {acc["hit"]}/{total} = {acc["hit_rate"]}%')
    print(f'  Hit: {acc["hit"]}  Partial: {acc["partial"]}  Miss: {acc["miss"]}')

    if by_tier:
        print('\n按预期分级:')
        for tier, s in report['by_expected_tier'].items():
            print(f'  {tier}: {s["hit_rate"]}% ({s["total"]} 条)')

    if by_type:
        print('\n按内容类型:')
        for ct, s in report['by_content_type'].items():
            print(f'  {ct}: {s["hit_rate"]}% ({s["total"]} 条)')

    print('\n详细记录:')
    print(f'{"#":<4} {"日期":<12} {"预期":<8} {"得分":<10} {"结果":<8} {"标题"}')
    print('-' * 70)
    for p in report['posts']:
        print(f'{p["id"]:<4} {p["publish_date"]:<12} {p["expected_tier"] or "-":<8} '
              f'{p["actual_score"]:>8,}  {p["outcome"]:<8} {p["title"][:30]}')

    print('\n已知局限:')
    for lim in report['known_limitations']:
        print(f'  - {lim}')
    print('\n' + '=' * 60)

    if args.json_out:
        import os
        os.makedirs(os.path.dirname(args.json_out) or '.', exist_ok=True)
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f'\nJSON saved: {args.json_out}')

    return 0


def main():
    parser = argparse.ArgumentParser(description='XHS 发布记录管理')
    sub = parser.add_subparsers(dest='cmd')

    # log
    log_p = sub.add_parser('log', help='记录一次发布')
    log_p.add_argument('--title', required=True, help='帖子标题')
    log_p.add_argument('--keywords', help='目标关键词（逗号分隔）')
    log_p.add_argument('--type', choices=['normal', 'video'], default='normal')
    log_p.add_argument('--account', default='MAIN')
    log_p.add_argument('--expect', choices=['high', 'medium', 'low'], help='预期表现')
    log_p.add_argument('--reason', help='预期理由')

    # check
    check_p = sub.add_parser('check', help='回查实际表现')
    check_p.add_argument('--id', type=int, help='指定记录 ID')
    check_p.add_argument('--all', action='store_true', help='检查所有未回查的记录')

    # list
    sub.add_parser('list', help='列出所有发布记录')

    # review
    review_p = sub.add_parser('review', help='预测准确度复盘')
    review_p.add_argument('--json-out', help='输出 JSON')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 1

    if args.cmd == 'log':
        return cmd_log(args)
    elif args.cmd == 'check':
        return cmd_check(args)
    elif args.cmd == 'list':
        return cmd_list(args)
    elif args.cmd == 'review':
        return cmd_review(args)


if __name__ == '__main__':
    exit(main() or 0)
