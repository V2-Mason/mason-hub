#!/bin/bash
# xhs-strategy-briefing.sh — XHS 策略简报生成
# 用法: xhs-strategy-briefing.sh
# 读取 xhs-analyze.sh 产出的 weekly_analysis.json，生成策略简报
# 输出: /opt/mediacrawler/analysis/briefings/YYYY-MM-DD.json + Slack 摘要

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh

echo "=== XHS Strategy Briefing ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

log_event "xhs-strategy" "briefing" "start" "Generating strategy briefing"

# --- Generate briefing on Aliyun ---
BRIEFING_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" bash -s << 'REMOTE_SCRIPT'
MC_DIR="/opt/mediacrawler"
ANALYSIS_FILE="$MC_DIR/analysis/weekly_analysis.json"
TODAY=$(date '+%Y-%m-%d')
BRIEFING_DIR="$MC_DIR/analysis/briefings"
BRIEFING_FILE="$BRIEFING_DIR/$TODAY.json"

mkdir -p "$BRIEFING_DIR"

if [ ! -f "$ANALYSIS_FILE" ]; then
  echo "ERROR: Analysis file not found at $ANALYSIS_FILE"
  exit 1
fi

python3 << 'PYEOF'
import json
from datetime import datetime

ANALYSIS_FILE = "/opt/mediacrawler/analysis/weekly_analysis.json"
TODAY = datetime.now().strftime('%Y-%m-%d')
BRIEFING_FILE = f"/opt/mediacrawler/analysis/briefings/{TODAY}.json"

with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

hot_posts = data.get('hot_posts', [])
keyword_insights = data.get('keyword_insights', [])
fake_report = data.get('fake_traffic_report', {})

# --- Hot posts with learn_reason ---
enriched_posts = []
for p in hot_posts[:20]:
    reasons = []
    er = p.get('engagement_ratio', 0)
    collected = p.get('collected', 0)
    liked = p.get('liked', 0)
    comment = p.get('comment', 0)

    # 高藏赞比 → 教程/干货类
    if liked > 0 and collected / liked > 0.5:
        reasons.append("高藏赞比，适合教程/干货类内容参考")
    # 高评赞比 → 话题/争议类
    if liked > 0 and comment / liked > 0.1:
        reasons.append("高评赞比，话题互动性强")
    # 高互动比
    if er > 1.5:
        reasons.append("互动比极高，内容引发深度参与")
    # 视频类高赞
    if p.get('type') == 'video' and liked > 500:
        reasons.append("视频爆款，可学习拍摄/剪辑手法")
    # 图文类高赞
    if p.get('type') == 'normal' and liked > 500:
        reasons.append("图文爆款，可学习排版/文案")

    if not reasons:
        reasons.append("综合互动评分高")

    post_entry = {k: v for k, v in p.items()}
    post_entry['learn_reason'] = '；'.join(reasons)
    enriched_posts.append(post_entry)

# --- Content recommendations (rule-based) ---
# 分析关键词数据，为 3 个号生成建议
recommendations = []

# 找出各类型最佳内容
tutorial_posts = [p for p in hot_posts if p.get('liked', 0) > 0 and p.get('collected', 0) / max(p.get('liked', 0), 1) > 0.3]
topic_posts = [p for p in hot_posts if p.get('liked', 0) > 0 and p.get('comment', 0) / max(p.get('liked', 0), 1) > 0.05]
video_posts = [p for p in hot_posts if p.get('type') == 'video']
image_posts = [p for p in hot_posts if p.get('type') == 'normal']

# 号 1 品牌号: 产品介绍/教程/开箱
brand_suggestions = []
if tutorial_posts:
    brand_suggestions.append({
        'topic': f"参考爆款教程做产品教程 — 如「{tutorial_posts[0].get('title', '')[:20]}」",
        'format': 'image_text' if image_posts else 'video',
        'reason': '高藏赞比内容适合品牌号做产品教程',
        'reference_notes': [p['note_id'] for p in tutorial_posts[:3]]
    })
# 找韩国护肤/好物关键词
korea_kws = [k for k in keyword_insights if '韩国' in k.get('keyword', '')]
if korea_kws:
    best_korea = korea_kws[0]
    brand_suggestions.append({
        'topic': f"「{best_korea['keyword']}」热门话题跟进",
        'format': 'video' if best_korea.get('video_ratio', 0) > 0.5 else 'image_text',
        'reason': f"该关键词平均互动 {best_korea['avg_score']}，{'视频' if best_korea.get('video_ratio', 0) > 0.5 else '图文'}更受欢迎",
        'reference_notes': []
    })
recommendations.append({
    'account': '号 1 素仁轩品牌号',
    'suggestions': brand_suggestions[:3]
})

# 号 2 种草号: 护肤+零食+家居种草
seed_suggestions = []
product_kws = [k for k in keyword_insights if '推荐' in k.get('keyword', '')]
if product_kws:
    for kw in product_kws[:2]:
        seed_suggestions.append({
            'topic': f"「{kw['keyword']}」种草合集",
            'format': 'image_text',
            'reason': f"推荐类内容适合种草号，平均互动 {kw['avg_score']}",
            'reference_notes': []
        })
if topic_posts:
    seed_suggestions.append({
        'topic': f"参考话题帖做互动种草 — 如「{topic_posts[0].get('title', '')[:20]}」",
        'format': 'video' if video_posts else 'image_text',
        'reason': '高评赞比内容可引发讨论，适合种草号引流',
        'reference_notes': [p['note_id'] for p in topic_posts[:3]]
    })
recommendations.append({
    'account': '号 2 韩国好物种草号',
    'suggestions': seed_suggestions[:3]
})

# 号 3 人设号: 代购日常/信任建设
persona_suggestions = []
trend_kws = [k for k in keyword_insights if '趋势' in k.get('keyword', '') or '爆款' in k.get('keyword', '') or '新品' in k.get('keyword', '')]
if trend_kws:
    for kw in trend_kws[:1]:
        persona_suggestions.append({
            'topic': f"「{kw['keyword']}」代购视角解读",
            'format': 'video',
            'reason': '趋势话题适合人设号做代购日常分享',
            'reference_notes': []
        })
persona_suggestions.append({
    'topic': '韩国代购日常 vlog / 买手笔记',
    'format': 'video',
    'reason': '人设号核心是建立信任，日常内容是基石',
    'reference_notes': []
})
recommendations.append({
    'account': '号 3 韩国生活人设号',
    'suggestions': persona_suggestions[:3]
})

# --- Build briefing ---
briefing = {
    'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00'),
    'period': data.get('period', {}),
    'hot_posts': enriched_posts,
    'keyword_insights': keyword_insights,
    'content_recommendations': recommendations,
    'fake_traffic_report': fake_report,
}

with open(BRIEFING_FILE, 'w', encoding='utf-8') as f:
    json.dump(briefing, f, ensure_ascii=False, indent=2)

# Print summary
print(f"BRIEFING_OK=1")
print(f"BRIEFING_FILE={BRIEFING_FILE}")
print(f"HOT_COUNT={len(enriched_posts)}")
print(f"KW_COUNT={len(keyword_insights)}")
print(f"REC_COUNT={sum(len(r['suggestions']) for r in recommendations)}")

# Top 3 recommendations summary
for rec in recommendations:
    acct = rec['account']
    if rec['suggestions']:
        top_topic = rec['suggestions'][0]['topic'][:30]
        print(f"REC_{acct}={top_topic}")
PYEOF
REMOTE_SCRIPT
)

SSH_EXIT=$?
echo "$BRIEFING_OUTPUT"

if [ $SSH_EXIT -ne 0 ]; then
  echo "ERROR: SSH connection failed"
  log_event "xhs-strategy" "briefing" "error" "SSH failed (exit $SSH_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 策略简报失败*: SSH 连接失败" "XHS Strategy" ":x:"
  exit 1
fi

if echo "$BRIEFING_OUTPUT" | grep -q "^ERROR:"; then
  ERROR_MSG=$(echo "$BRIEFING_OUTPUT" | grep "^ERROR:" | head -1)
  echo "FAIL: $ERROR_MSG"
  log_event "xhs-strategy" "briefing" "error" "$ERROR_MSG"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 策略简报失败*: $ERROR_MSG" "XHS Strategy" ":x:"
  exit 1
fi

BRIEFING_OK=$(echo "$BRIEFING_OUTPUT" | grep "^BRIEFING_OK=" | cut -d= -f2)
if [ "${BRIEFING_OK:-0}" != "1" ]; then
  echo "ERROR: Briefing generation failed"
  log_event "xhs-strategy" "briefing" "error" "Python script failed"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 策略简报失败*: 生成脚本异常" "XHS Strategy" ":x:"
  exit 1
fi

HOT_COUNT=$(echo "$BRIEFING_OUTPUT" | grep "^HOT_COUNT=" | cut -d= -f2)
KW_COUNT=$(echo "$BRIEFING_OUTPUT" | grep "^KW_COUNT=" | cut -d= -f2)
REC_COUNT=$(echo "$BRIEFING_OUTPUT" | grep "^REC_COUNT=" | cut -d= -f2)

# Extract per-account recommendations for Slack
REC_BRAND=$(echo "$BRIEFING_OUTPUT" | grep "^REC_号 1" | cut -d= -f2-)
REC_SEED=$(echo "$BRIEFING_OUTPUT" | grep "^REC_号 2" | cut -d= -f2-)
REC_PERSONA=$(echo "$BRIEFING_OUTPUT" | grep "^REC_号 3" | cut -d= -f2-)

log_event "xhs-strategy" "briefing" "end" "Briefing generated: $HOT_COUNT hot posts, $KW_COUNT keywords, $REC_COUNT recommendations"

# --- Slack summary ---
MSG="📋 *XHS 策略简报* ($(TZ=Asia/Shanghai date '+%Y-%m-%d'))

*爆帖分析*: ${HOT_COUNT:-0} 篇 Top 内容
*关键词洞察*: ${KW_COUNT:-0} 个关键词趋势

*内容建议*:
• 品牌号: ${REC_BRAND:-待补充}
• 种草号: ${REC_SEED:-待补充}
• 人设号: ${REC_PERSONA:-待补充}

*假流量*: 详见完整报告
完整简报: 阿里云 $MC_DIR/analysis/briefings/$(TZ=Asia/Shanghai date '+%Y-%m-%d').json"

notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Strategy" ":memo:"

echo ""
echo "=== XHS Strategy Briefing Complete ==="
