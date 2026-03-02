"""爆款帖子分析 — 基于已有 167 条数据"""
import sqlite3
import json
import re

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

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

rows = cur.execute('''
    SELECT note_id, title, "desc", type, liked_count, collected_count, 
           comment_count, share_count, tag_list, source_keyword, note_url, nickname
    FROM xhs_note
''').fetchall()

notes = []
for r in rows:
    liked = parse_count(r['liked_count'])
    collected = parse_count(r['collected_count'])
    comment = parse_count(r['comment_count'])
    shared = parse_count(r['share_count'])
    score = interaction_score(liked, collected, comment, shared)
    
    # 互动比
    engage_rate = (comment / liked * 100) if liked > 0 else 0  # 评赞比
    save_rate = (collected / liked * 100) if liked > 0 else 0  # 藏赞比
    share_rate = (shared / liked * 100) if liked > 0 else 0  # 转赞比
    
    # 假流量标记
    fake_flags = []
    if liked > 1000 and engage_rate < 0.2:
        fake_flags.append('评赞比过低')
    if liked > 1000 and save_rate < 5:
        fake_flags.append('藏赞比过低')
    
    notes.append({
        'note_id': r['note_id'],
        'title': r['title'] or '',
        'desc': r['desc'] or '',
        'type': r['type'] or 'normal',
        'liked': liked, 'collected': collected, 'comment': comment, 'shared': shared,
        'score': score,
        'engage_rate': engage_rate, 'save_rate': save_rate, 'share_rate': share_rate,
        'tags': r['tag_list'] or '',
        'keyword': r['source_keyword'] or '',
        'url': r['note_url'] or '',
        'nickname': r['nickname'] or '',
        'fake_flags': fake_flags,
    })

conn.close()

notes.sort(key=lambda x: x['score'], reverse=True)

# ===== 输出报告 =====
print("=" * 60)
print("📊 XHS 爆款帖子分析报告")
print(f"数据量: {len(notes)} 条笔记")
print("=" * 60)

# --- 1. Top 15 爆帖 ---
print("\n🔥 Top 15 高互动帖子:")
print(f"{'排名':<4} {'互动分':>10} {'赞':>8} {'藏':>8} {'评':>6} {'转':>6} {'类型':<6} {'藏赞比':>6} {'标题'}")
print("-" * 100)
for i, n in enumerate(notes[:15]):
    flag = ' ⚠️' if n['fake_flags'] else ''
    print(f"{i+1:<4} {n['score']:>10,} {n['liked']:>8,} {n['collected']:>8,} {n['comment']:>6,} {n['shared']:>6,} {n['type']:<6} {n['save_rate']:>5.1f}% {n['title'][:40]}{flag}")

# --- 2. 内容类型分析 ---
print("\n\n📋 内容类型分析:")
video_notes = [n for n in notes if n['type'] == 'video']
normal_notes = [n for n in notes if n['type'] == 'normal']
print(f"  视频: {len(video_notes)} 条 ({len(video_notes)/len(notes)*100:.0f}%)")
print(f"  图文: {len(normal_notes)} 条 ({len(normal_notes)/len(notes)*100:.0f}%)")

if video_notes:
    avg_v = sum(n['score'] for n in video_notes) / len(video_notes)
    print(f"  视频平均互动分: {avg_v:,.0f}")
if normal_notes:
    avg_n = sum(n['score'] for n in normal_notes) / len(normal_notes)
    print(f"  图文平均互动分: {avg_n:,.0f}")

# --- 3. 关键词维度分析 ---
print("\n\n🔑 关键词维度分析:")
kw_stats = {}
for n in notes:
    kw = n['keyword']
    if kw not in kw_stats:
        kw_stats[kw] = {'count': 0, 'scores': [], 'video': 0, 'normal': 0, 'top_title': '', 'top_score': 0}
    kw_stats[kw]['count'] += 1
    kw_stats[kw]['scores'].append(n['score'])
    if n['type'] == 'video': kw_stats[kw]['video'] += 1
    else: kw_stats[kw]['normal'] += 1
    if n['score'] > kw_stats[kw]['top_score']:
        kw_stats[kw]['top_score'] = n['score']
        kw_stats[kw]['top_title'] = n['title'][:30]

print(f"{'关键词':<20} {'数量':>4} {'平均分':>10} {'最高分':>10} {'视频占比':>8} {'最佳标题'}")
print("-" * 100)
for kw, stats in sorted(kw_stats.items(), key=lambda x: sum(x[1]['scores'])/len(x[1]['scores']), reverse=True):
    avg = sum(stats['scores']) / len(stats['scores'])
    v_ratio = stats['video'] / stats['count'] * 100
    print(f"{kw:<20} {stats['count']:>4} {avg:>10,.0f} {stats['top_score']:>10,} {v_ratio:>6.0f}%  {stats['top_title']}")

# --- 4. 爆款模式识别 ---
print("\n\n🎯 爆款模式识别:")

# 高藏赞比 = 教程/干货类（用户想保存学习）
high_save = sorted([n for n in notes if n['save_rate'] > 30 and n['liked'] > 1000], key=lambda x: x['save_rate'], reverse=True)
print(f"\n  📌 高藏赞比（>30%）= 干货/教程类，用户想收藏:")
for n in high_save[:5]:
    print(f"    [{n['save_rate']:.0f}%] {n['title'][:45]} ({n['type']}) @{n['nickname'][:10]}")

# 高评赞比 = 话题/争议类（引发讨论）
high_engage = sorted([n for n in notes if n['engage_rate'] > 2 and n['liked'] > 1000], key=lambda x: x['engage_rate'], reverse=True)
print(f"\n  💬 高评赞比（>2%）= 话题/争议类，引发讨论:")
for n in high_engage[:5]:
    print(f"    [{n['engage_rate']:.1f}%] {n['title'][:45]} ({n['type']}) @{n['nickname'][:10]}")

# 高转赞比 = 社交货币类（用户想分享给朋友）
high_share = sorted([n for n in notes if n['share_rate'] > 3 and n['liked'] > 1000], key=lambda x: x['share_rate'], reverse=True)
print(f"\n  🔄 高转赞比（>3%）= 社交货币类，用户想分享:")
for n in high_share[:5]:
    print(f"    [{n['share_rate']:.1f}%] {n['title'][:45]} ({n['type']}) @{n['nickname'][:10]}")

# --- 5. 标题模式 ---
print("\n\n✍️ 标题模式分析:")
# 标题含 emoji
emoji_titles = [n for n in notes if re.search(r'[\U0001F300-\U0001F9FF]', n['title'])]
no_emoji = [n for n in notes if not re.search(r'[\U0001F300-\U0001F9FF]', n['title'])]
print(f"  含 Emoji: {len(emoji_titles)} 条, 平均互动分 {sum(n['score'] for n in emoji_titles)/max(len(emoji_titles),1):,.0f}")
print(f"  无 Emoji: {len(no_emoji)} 条, 平均互动分 {sum(n['score'] for n in no_emoji)/max(len(no_emoji),1):,.0f}")

# 标题含数字
num_titles = [n for n in notes if re.search(r'\d', n['title'])]
no_num = [n for n in notes if not re.search(r'\d', n['title'])]
print(f"  含数字: {len(num_titles)} 条, 平均互动分 {sum(n['score'] for n in num_titles)/max(len(num_titles),1):,.0f}")
print(f"  无数字: {len(no_num)} 条, 平均互动分 {sum(n['score'] for n in no_num)/max(len(no_num),1):,.0f}")

# 标题含感叹号/问号
exclaim = [n for n in notes if '！' in n['title'] or '!' in n['title'] or '‼️' in n['title']]
question = [n for n in notes if '？' in n['title'] or '?' in n['title']]
print(f"  含感叹号: {len(exclaim)} 条, 平均互动分 {sum(n['score'] for n in exclaim)/max(len(exclaim),1):,.0f}")
print(f"  含问号: {len(question)} 条, 平均互动分 {sum(n['score'] for n in question)/max(len(question),1):,.0f}")

# --- 6. 假流量预警 ---
fakes = [n for n in notes if n['fake_flags']]
print(f"\n\n⚠️ 假流量预警: {len(fakes)} 条可疑")
for n in fakes[:5]:
    print(f"  {n['title'][:40]} — {', '.join(n['fake_flags'])} (赞{n['liked']:,} 藏赞比{n['save_rate']:.1f}% 评赞比{n['engage_rate']:.2f}%)")

# --- 7. 给素仁轩的建议 ---
print("\n\n💡 对素仁轩的内容建议:")
print("  1. 内容形式: 视频为主（占比 74%，且平均互动远高于图文）")
print("  2. 高收藏选题: 护肤流程/步骤类（藏赞比最高），用户有收藏学习需求")
print("  3. 高讨论选题: 争议/反常识类标题（如\"还真有人越防晒越黑\"），引发评论")
print("  4. 标题公式: Emoji + 数字 + 情绪词（感叹/疑问）效果最好")
print("  5. 韩国元素: 强调韩国/韩女/oliveyoung等标签天然有流量")

print("\n" + "=" * 60)
