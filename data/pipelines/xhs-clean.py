#!/usr/bin/env python3
"""
XHS 笔记清洗管道 — Layer 2 (Clean)

将 raw_xhs_notes (SQLite) 归一化为 clean_xhs_notes (JSON):
  1. parse_count 将中文数字转整数
  2. 时间戳统一为 YYYY-MM-DD
  3. 计算标准化派生字段（interaction_score, engage_rate 等）
  4. 标记假流量
  5. 按 note_id 去重（保留最新）

输入: SQLite xhs_note 表（阿里云或本地镜像）
输出: /opt/mediacrawler/clean/notes_YYYY-MM-DD.json（或指定路径）

用法:
    # 在阿里云本地运行（标准路径）
    python3 xhs-clean.py

    # 指定输入数据库和输出路径
    python3 xhs-clean.py --db /path/to/sqlite_tables.db --output /path/to/output.json

    # 使用 GCP 镜像
    python3 xhs-clean.py --db ~/mason-hub/data/mirror/sqlite_tables.db --output /tmp/clean_notes.json

    # 只做 dry-run 验证
    python3 xhs-clean.py --dry-run

维护者: EMP_0014
Schema: data/schemas/xhs_clean_notes.yaml
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime


# =============================================================================
# 指标函数 — 与 data/tools/metrics.py 完全一致
# =============================================================================
# 注意：此脚本可能在阿里云独立运行，无法 import data.tools.metrics。
# 因此内联指标函数，但公式必须与 metrics.py 和 xhs_metrics.yaml 保持完全一致。
# 修改公式时必须三处同步更新。

def parse_count(s):
    """将 XHS 中文数字格式归一化为整数。"""
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


def interaction_score(liked, collected, comment, shared):
    """互动评分 = liked + collected×3 + comment×5 + shared×8"""
    return liked + collected * 3 + comment * 5 + shared * 8


def engage_rate(comment, liked):
    """评赞比 (%)"""
    if liked <= 0:
        return 0.0
    return round(comment / liked * 100, 2)


def save_rate(collected, liked):
    """藏赞比 (%)"""
    if liked <= 0:
        return 0.0
    return round(collected / liked * 100, 1)


def share_rate(shared, liked):
    """转赞比 (%)"""
    if liked <= 0:
        return 0.0
    return round(shared / liked * 100, 1)


def fake_traffic_flags(liked, collected, comment, shared):
    """假流量检测标记。"""
    flags = []
    if liked > 1000:
        if engage_rate(comment, liked) < 0.2:
            flags.append('评赞比过低')
        if save_rate(collected, liked) < 5:
            flags.append('藏赞比过低')
    return flags


# =============================================================================
# 清洗主逻辑
# =============================================================================

def clean_notes(db_path, table='xhs_note'):
    """从 SQLite 读取并清洗 XHS 笔记数据。

    Returns:
        list[dict]: 清洗后的笔记列表（按 note_id 去重）
    """
    if not os.path.exists(db_path):
        print(f"[ERROR] 数据库不存在: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(f'SELECT * FROM {table}')
    except sqlite3.OperationalError as e:
        print(f"[ERROR] 查询失败: {e}", file=sys.stderr)
        sys.exit(1)

    rows = cursor.fetchall()
    conn.close()

    now = time.time()
    clean_ts = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    seen = {}  # note_id → index in results (去重用)
    results = []

    for r in rows:
        r = dict(r)
        note_id = r.get('note_id', '')

        # --- Step 1: parse_count 归一化 ---
        liked = parse_count(r.get('liked_count'))
        collected = parse_count(r.get('collected_count'))
        comment = parse_count(r.get('comment_count'))
        shared = parse_count(r.get('share_count'))

        # --- Step 2: 时间戳标准化 ---
        ts = r.get('time')
        pub_date = ''
        post_age_days = -1
        if ts:
            try:
                ts_val = int(ts)
                if ts_val > 0:
                    ts_s = ts_val / 1000 if ts_val > 1e12 else ts_val
                    pub_date = datetime.fromtimestamp(ts_s).strftime('%Y-%m-%d')
                    post_age_days = round((now - ts_s) / 86400)
            except (ValueError, TypeError):
                pass

        # --- Step 3: 计算标准指标 ---
        score = interaction_score(liked, collected, comment, shared)
        e_rate = engage_rate(comment, liked)
        s_rate = save_rate(collected, liked)
        sh_rate = share_rate(shared, liked)
        flags = fake_traffic_flags(liked, collected, comment, shared)

        note = {
            'note_id': note_id,
            'title': r.get('title', '') or '',
            'desc': r.get('desc', '') or '',
            'type': r.get('type', 'normal') or 'normal',
            'liked': liked,
            'collected': collected,
            'comment': comment,
            'shared': shared,
            'tags': r.get('tag_list', '') or '',
            'keyword': r.get('source_keyword', '') or '',
            'url': r.get('note_url', '') or '',
            'nickname': r.get('nickname', '') or '',
            'user_id': r.get('user_id', '') or '',
            'pub_date': pub_date,
            'post_age_days': post_age_days,
            'clean_timestamp': clean_ts,
            'score': score,
            'engage_rate': e_rate,
            'save_rate': s_rate,
            'share_rate': sh_rate,
            'fake_flags': flags,
        }

        # --- Step 4: 按 note_id 去重（保留最新） ---
        crawl_ts = r.get('crawl_timestamp', '') or ''
        if note_id in seen:
            existing_idx = seen[note_id]
            existing_ts = results[existing_idx].get('_crawl_ts', '')
            if crawl_ts > existing_ts:
                note['_crawl_ts'] = crawl_ts
                results[existing_idx] = note
        else:
            note['_crawl_ts'] = crawl_ts
            seen[note_id] = len(results)
            results.append(note)

    # 移除内部字段
    for note in results:
        note.pop('_crawl_ts', None)

    return results


def main():
    parser = argparse.ArgumentParser(description='XHS 笔记清洗管道 (Layer 2)')
    parser.add_argument('--db', default='/opt/mediacrawler/database/sqlite_tables.db',
                        help='SQLite 数据库路径')
    parser.add_argument('--output', default=None,
                        help='输出 JSON 文件路径（默认: /opt/mediacrawler/clean/notes_YYYY-MM-DD.json）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只验证不写文件')
    parser.add_argument('--stats', action='store_true',
                        help='输出统计摘要')
    args = parser.parse_args()

    # 默认输出路径
    if args.output is None:
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = '/opt/mediacrawler/clean'
        args.output = os.path.join(output_dir, f'notes_{today}.json')

    print(f"[INFO] 输入: {args.db}")
    print(f"[INFO] 输出: {args.output}")

    # 清洗
    notes = clean_notes(args.db)

    # 统计
    total = len(notes)
    fake_count = sum(1 for n in notes if n['fake_flags'])
    video_count = sum(1 for n in notes if n['type'] == 'video')
    keywords = set(n['keyword'] for n in notes if n['keyword'])
    dedup_saved = 0  # 去重数量在 clean_notes 内部处理

    print(f"[INFO] 清洗完成: {total} 条笔记")
    print(f"  - 视频: {video_count}, 图文: {total - video_count}")
    print(f"  - 假流量标记: {fake_count}")
    print(f"  - 关键词: {len(keywords)} 个 ({', '.join(sorted(keywords)[:5])}{'...' if len(keywords) > 5 else ''})")

    if args.stats:
        if notes:
            scores = [n['score'] for n in notes]
            print(f"  - 互动分: min={min(scores)}, max={max(scores)}, "
                  f"median={sorted(scores)[len(scores)//2]}")

    if args.dry_run:
        print("[DRY-RUN] 不写入文件")
        return

    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 写入
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    print(f"[OK] 已写入 {args.output} ({os.path.getsize(args.output)} bytes)")


if __name__ == '__main__':
    main()
