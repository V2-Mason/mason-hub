"""从分析 JSON 生成 Slack 摘要文本（市场信号版）"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python _xhs_slack_summary.py <analysis.json>")
        return 1

    with open(sys.argv[1]) as f:
        r = json.load(f)

    m = r['meta']
    ct = r['content_type']
    tp = r['top_posts'][:3]
    ft = r['fake_traffic']
    kw = r['keyword_insights'][:3]
    total = m['total_notes']

    lines = []
    lines.append(f"信号基于 {total} 条笔记，仅供参考")
    lines.append(f"视频 {ct['video_ratio']}% | 视频均分 {ct['video_avg_score']:,} vs 图文 {ct['normal_avg_score']:,}")
    lines.append("")

    # Top 3 with account size if available
    lines.append("Top 3 热帖:")
    for i, p in enumerate(tp):
        size_tag = f" [{p['account_size']}]" if p.get('account_size') else ''
        lines.append(f"  {i+1}. {p['title'][:35]}{size_tag} (互动分{p['score']:,})")
    lines.append("")

    lines.append("关键词热度:")
    for k in kw:
        lines.append(f"  - {k['keyword']}: 均分 {k['avg_score']:,} ({k.get('count', 0)} 条)")
    lines.append("")

    lines.append(f"假流量: {ft['count']} 条可疑")
    lines.append(f"看板: http://106.14.44.68/xhs/")

    print('\n'.join(lines))


if __name__ == '__main__':
    exit(main() or 0)
