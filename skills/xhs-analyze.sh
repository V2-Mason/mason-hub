#!/bin/bash
# xhs-analyze.sh — XHS 采集数据分析
# 用法: xhs-analyze.sh [--days <N>]
#   --days N  分析最近 N 天的数据（默认 7）
# 输出: /opt/mediacrawler/analysis/weekly_analysis.json + Slack 摘要

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh
DAYS=7

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days) DAYS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== XHS Data Analysis ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"
echo "Analysis period: last $DAYS days"

log_event "xhs-analyzer" "weekly-analysis" "start" "Analyzing last $DAYS days"

# --- Run analysis on Aliyun ---
ANALYSIS_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" bash -s << REMOTE_SCRIPT
mkdir -p $MC_DIR/analysis

python3 << 'PYEOF'
import json
import sqlite3
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = "$MC_DIR/database/sqlite_tables.db"
OUTPUT_PATH = "$MC_DIR/analysis/weekly_analysis.json"
DAYS = $DAYS

def normalize_count(val):
    """数字归一化: '1.2万' -> 12000, '3456' -> 3456"""
    if val is None:
        return 0
    val = str(val).strip()
    if not val:
        return 0
    # 万
    m = re.match(r'^([\d.]+)\s*万$', val)
    if m:
        return int(float(m.group(1)) * 10000)
    # 亿
    m = re.match(r'^([\d.]+)\s*亿$', val)
    if m:
        return int(float(m.group(1)) * 100000000)
    # plain number
    try:
        return int(float(re.sub(r'[^\d.]', '', val)))
    except (ValueError, TypeError):
        return 0

def calc_score(liked, collected, comment, share):
    """互动评分: 赞 + 藏×3 + 评×5 + 转×8"""
    return liked + collected * 3 + comment * 5 + share * 8

def check_fake_traffic(liked, collected, comment):
    """假流量检测"""
    flags = []
    if liked > 1000 and comment > 0:
        comment_like_ratio = comment / liked
        if comment_like_ratio < 0.002:
            flags.append(f"评赞比过低({comment_like_ratio:.4f})")
    if liked > 0:
        collect_like_ratio = collected / liked
        if collect_like_ratio < 0.05:
            flags.append(f"藏赞比过低({collect_like_ratio:.3f})")
    return flags

# Connect to DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get notes from last N days (by add_ts or time)
cutoff_ts = int((datetime.now() - timedelta(days=DAYS)).timestamp() * 1000)
cur.execute("""
    SELECT note_id, title, desc, liked_count, collected_count,
           comment_count, share_count, type, tag_list, source_keyword,
           note_url, time, add_ts
    FROM xhs_note
    WHERE add_ts > ?
    ORDER BY add_ts DESC
""", (cutoff_ts,))

rows = cur.fetchall()
conn.close()

if not rows:
    print(json.dumps({"error": "no_data", "message": f"No notes in last {DAYS} days"}))
    exit(0)

# Process each note
notes = []
for row in rows:
    liked = normalize_count(row['liked_count'])
    collected = normalize_count(row['collected_count'])
    comment = normalize_count(row['comment_count'])
    share = normalize_count(row['share_count'])
    score = calc_score(liked, collected, comment, share)
    fake_flags = check_fake_traffic(liked, collected, comment)

    engagement_ratio = 0
    if liked > 0:
        engagement_ratio = round((collected + comment + share) / liked, 3)

    notes.append({
        'note_id': row['note_id'],
        'title': row['title'] or '',
        'score': score,
        'liked': liked,
        'collected': collected,
        'comment': comment,
        'share': share,
        'engagement_ratio': engagement_ratio,
        'type': row['type'] or 'normal',
        'source_keyword': row['source_keyword'] or '',
        'note_url': row['note_url'] or '',
        'fake_traffic_flags': fake_flags,
        'tag_list': row['tag_list'] or '',
    })

# Sort by score descending
notes.sort(key=lambda x: x['score'], reverse=True)

# Top 20 hot posts
hot_posts = notes[:20]

# Keyword statistics
kw_stats = defaultdict(lambda: {
    'scores': [], 'titles': [], 'video_count': 0, 'total_count': 0
})
for n in notes:
    kw = n['source_keyword']
    if not kw:
        continue
    kw_stats[kw]['scores'].append(n['score'])
    kw_stats[kw]['titles'].append((n['score'], n['title']))
    kw_stats[kw]['total_count'] += 1
    if n['type'] == 'video':
        kw_stats[kw]['video_count'] += 1

keyword_insights = []
for kw, stats in kw_stats.items():
    avg_score = round(sum(stats['scores']) / len(stats['scores']), 1) if stats['scores'] else 0
    top3 = sorted(stats['titles'], key=lambda x: x[0], reverse=True)[:3]
    video_ratio = round(stats['video_count'] / stats['total_count'], 3) if stats['total_count'] > 0 else 0

    keyword_insights.append({
        'keyword': kw,
        'note_count': stats['total_count'],
        'avg_score': avg_score,
        'top3_titles': [t[1] for t in top3],
        'video_ratio': video_ratio,
        'trend_direction': 'new',  # 首次分析，全部标 new
    })

keyword_insights.sort(key=lambda x: x['avg_score'], reverse=True)

# Fake traffic summary
total_checked = len(notes)
flagged = [n for n in notes if n['fake_traffic_flags']]
flagged_count = len(flagged)
flag_rate = round(flagged_count / total_checked, 3) if total_checked > 0 else 0

# Collect common patterns
pattern_counts = defaultdict(int)
for n in flagged:
    for f in n['fake_traffic_flags']:
        key = f.split('(')[0]
        pattern_counts[key] += 1
common_patterns = [f"{k} ({v}条)" for k, v in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)]

# Build result
now = datetime.now()
result = {
    'generated_at': now.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
    'period': {
        'start': (now - timedelta(days=DAYS)).strftime('%Y-%m-%d'),
        'end': now.strftime('%Y-%m-%d'),
    },
    'total_notes_analyzed': total_checked,
    'hot_posts': [{k: v for k, v in n.items() if k != 'tag_list'} for n in hot_posts],
    'keyword_insights': keyword_insights,
    'fake_traffic_report': {
        'total_checked': total_checked,
        'flagged_count': flagged_count,
        'flag_rate': flag_rate,
        'common_patterns': common_patterns,
    },
}

# Write JSON
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Print summary for Slack
print(f"TOTAL_NOTES={total_checked}")
print(f"TOP1_TITLE={hot_posts[0]['title'] if hot_posts else 'N/A'}")
print(f"TOP1_SCORE={hot_posts[0]['score'] if hot_posts else 0}")
print(f"KEYWORDS_COUNT={len(keyword_insights)}")
print(f"FLAGGED_COUNT={flagged_count}")
print(f"FLAG_RATE={flag_rate}")
if keyword_insights:
    best_kw = keyword_insights[0]
    print(f"BEST_KEYWORD={best_kw['keyword']}")
    print(f"BEST_KW_AVG={best_kw['avg_score']}")
print("ANALYSIS_OK=1")
PYEOF
REMOTE_SCRIPT
)

SSH_EXIT=$?
echo "$ANALYSIS_OUTPUT"

if [ $SSH_EXIT -ne 0 ]; then
  echo "ERROR: SSH connection failed"
  log_event "xhs-analyzer" "weekly-analysis" "error" "SSH failed (exit $SSH_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 分析失败*: SSH 连接失败" "XHS Analyzer" ":x:"
  exit 1
fi

# Check for errors
if echo "$ANALYSIS_OUTPUT" | grep -q '"error"'; then
  echo "WARNING: No data to analyze"
  log_event "xhs-analyzer" "weekly-analysis" "info" "No data in period"
  notify_slack "$SLACK_CHANNEL" "⚠️ *XHS 分析*: 最近 ${DAYS} 天没有采集数据" "XHS Analyzer" ":warning:"
  exit 0
fi

# Parse output for Slack
TOTAL=$(echo "$ANALYSIS_OUTPUT" | grep "^TOTAL_NOTES=" | cut -d= -f2)
TOP1_TITLE=$(echo "$ANALYSIS_OUTPUT" | grep "^TOP1_TITLE=" | cut -d= -f2-)
TOP1_SCORE=$(echo "$ANALYSIS_OUTPUT" | grep "^TOP1_SCORE=" | cut -d= -f2)
KW_COUNT=$(echo "$ANALYSIS_OUTPUT" | grep "^KEYWORDS_COUNT=" | cut -d= -f2)
FLAGGED=$(echo "$ANALYSIS_OUTPUT" | grep "^FLAGGED_COUNT=" | cut -d= -f2)
FLAG_RATE=$(echo "$ANALYSIS_OUTPUT" | grep "^FLAG_RATE=" | cut -d= -f2)
BEST_KW=$(echo "$ANALYSIS_OUTPUT" | grep "^BEST_KEYWORD=" | cut -d= -f2-)
BEST_AVG=$(echo "$ANALYSIS_OUTPUT" | grep "^BEST_KW_AVG=" | cut -d= -f2)
ANALYSIS_OK=$(echo "$ANALYSIS_OUTPUT" | grep "^ANALYSIS_OK=" | cut -d= -f2)

if [ "${ANALYSIS_OK:-0}" != "1" ]; then
  echo "ERROR: Analysis failed"
  log_event "xhs-analyzer" "weekly-analysis" "error" "Analysis script failed"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 分析失败*: Python 脚本异常" "XHS Analyzer" ":x:"
  exit 1
fi

log_event "xhs-analyzer" "weekly-analysis" "end" "Analyzed $TOTAL notes, $KW_COUNT keywords, $FLAGGED flagged"

# --- Slack summary ---
MSG="📊 *XHS 周度分析完成*
• 分析笔记: ${TOTAL:-0} 条 (近 ${DAYS} 天)
• 涉及关键词: ${KW_COUNT:-0} 个
• 🏆 Top 1: ${TOP1_TITLE:-N/A} (评分 ${TOP1_SCORE:-0})
• 📈 最佳关键词: ${BEST_KW:-N/A} (平均 ${BEST_AVG:-0})
• 🚩 假流量标记: ${FLAGGED:-0} 条 (${FLAG_RATE:-0})
• 完整数据: 阿里云 $MC_DIR/analysis/weekly_analysis.json"

notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Analyzer" ":bar_chart:"

echo ""
echo "=== XHS Analysis Complete ==="
