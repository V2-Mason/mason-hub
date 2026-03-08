#!/usr/bin/env python3
"""TrendRadar 趋势报告生成器 — 文本版(/standup) + HTML简报版"""

import sqlite3
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from html import escape

TRENDRADAR_DIR = Path.home() / "mason-hub" / "tools" / "trendradar"
HTML_OUTPUT_DIR = Path.home() / "mason-hub" / "tools" / "trendradar-config" / "reports"

# 关键词组到层级的映射
LAYERS = {
    '韩妆/护肤': ('A', '现有业务'), '跨境电商': ('A', '现有业务'), '小红书': ('A', '现有业务'),
    'AI视频': ('B', '技术动态'), 'Vibe Coding': ('B', '技术动态'), 'AI Agent': ('B', '技术动态'),
    '出海': ('C', '赛道扫描'), 'AI工具/SaaS': ('C', '赛道扫描'), '内容电商': ('C', '赛道扫描'),
    '抖音/TikTok': ('C', '赛道扫描'), '个人IP': ('C', '赛道扫描'), '新消费': ('C', '赛道扫描'),
    '独立开发': ('D', '同类人'), '趋势观察': ('D', '同类人'),
    '基础设施/硬科技': ('C+', '硬件基建'),
}

LAYER_DISPLAY = [
    ('C', '📡 赛道扫描', '你正在探索的新方向', '#e8f5e9'),
    ('C+', '🔩 硬件基建', '内存/HBM/算力/储能基础设施', '#f3e5f5'),
    ('D', '🌱 同类人', '独立开发者 / 一人公司动态', '#fff3e0'),
    ('B', '🔧 技术动态', '你的技术能力圈', '#e3f2fd'),
    ('A', '📊 现有业务', '素仁轩 / 跨境电商相关', '#fce4ec'),
]

SOURCE_LABELS = {
    'baidu': '百度', 'weibo': '微博', 'douyin': '抖音', 'zhihu': '知乎',
    'bilibili-hot-search': 'B站', 'toutiao': '头条', 'wallstreetcn-hot': '华尔街见闻',
    'thepaper': '澎湃', 'cls-hot': '财联社', 'ifeng': '凤凰', 'tieba': '贴吧',
    'hacker-news': 'HN', 'producthunt': 'PH', 'techcrunch': 'TC',
    'ruanyifeng': '阮一峰', '36kr': '36氪', 'huxiu': '虎嗅', 'sspai': '少数派',
    'a16z': 'a16z', 'sequoia': 'Sequoia', 'ycombinator': 'YC',
}


def load_matcher():
    """加载 TrendRadar 的关键词匹配器"""
    sys.path.insert(0, str(TRENDRADAR_DIR))
    from trendradar.core.frequency import load_frequency_words, _word_matches

    groups, filter_words, global_filters = load_frequency_words(
        str(TRENDRADAR_DIR / "config" / "frequency_words.txt")
    )

    def match_title(title):
        title_lower = title.lower()
        for gf in global_filters:
            if gf.lower() in title_lower:
                return None
        for g in groups:
            normal = g.get('normal', [])
            required = g.get('required', [])
            if required:
                if not all(_word_matches(w, title_lower) for w in required):
                    continue
            if normal:
                if any(_word_matches(w, title_lower) for w in normal):
                    return g.get('display_name', '?')
            elif required:
                return g.get('display_name', '?')
        return None

    return match_title


def get_data(date_str):
    """读取指定日期的热榜和 RSS 数据"""
    items = []
    news_db = TRENDRADAR_DIR / f"output/news/{date_str}.db"
    rss_db = TRENDRADAR_DIR / f"output/rss/{date_str}.db"

    if news_db.exists():
        conn = sqlite3.connect(str(news_db))
        for title, url, src in conn.execute('SELECT title, url, platform_id FROM news_items'):
            items.append(('热榜', src, title, url or ''))
        conn.close()

    if rss_db.exists():
        conn = sqlite3.connect(str(rss_db))
        for title, url, src in conn.execute('SELECT title, url, feed_id FROM rss_items'):
            items.append(('RSS', src, title, url or ''))
        conn.close()

    return items


def match_items(items, match_title):
    """对所有条目做关键词匹配，返回 {group: [(src_type, src, title, url), ...]}"""
    results = {}
    for src_type, src, title, url in items:
        group = match_title(title)
        if group:
            if group not in results:
                results[group] = []
            results[group].append((src_type, src, title, url))
    return results


def get_frequency_insights(match_title, days=7):
    """计算过去 N 天每个关键词组的命中频率趋势"""
    today = datetime.now()
    daily_counts = {}  # {date_str: {group: count}}

    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.strftime('%Y-%m-%d')
        items = get_data(ds)
        results = match_items(items, match_title)
        daily_counts[ds] = {g: len(v) for g, v in results.items()}

    # 汇总趋势
    all_groups = set()
    for dc in daily_counts.values():
        all_groups.update(dc.keys())

    trends = {}
    for g in all_groups:
        counts = [daily_counts.get(ds, {}).get(g, 0) for ds in sorted(daily_counts.keys())]
        total = sum(counts)
        if total > 0:
            # 前半 vs 后半对比
            half = len(counts) // 2
            first_half = sum(counts[:half]) or 0
            second_half = sum(counts[half:]) or 0
            if second_half > first_half * 1.5:
                trend = '↑'
            elif first_half > second_half * 1.5:
                trend = '↓'
            else:
                trend = '→'
            trends[g] = {'total': total, 'trend': trend, 'daily': counts}

    return trends


# ─── 文本报告（/standup 用）───

def generate_report(date_str=None):
    """生成分层趋势报告（纯文本）"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    match_title = load_matcher()
    items = get_data(date_str)

    if not items:
        return "趋势热榜：今日无数据（TrendRadar 可能未运行）"

    results = match_items(items, match_title)
    total_matched = sum(len(v) for v in results.values())

    lines = [f"趋势热榜（{total_matched}/{len(items)} 命中）："]

    if total_matched == 0:
        lines.append("  今日无关键词命中")
        return "\n".join(lines)

    for layer_code, layer_label, _, _ in LAYER_DISPLAY:
        layer_groups = {g: v for g, v in results.items()
                        if LAYERS.get(g, ('?',))[0] == layer_code}
        if not layer_groups:
            continue

        count = sum(len(v) for v in layer_groups.values())
        lines.append(f"  {layer_label}（{count}）")

        for g, matched in sorted(layer_groups.items(), key=lambda x: -len(x[1])):
            if layer_code in ('C', 'D'):
                for _, src, t, _ in matched[:3]:
                    lines.append(f"    {g}: \"{t[:50]}\" [{SOURCE_LABELS.get(src, src)}]")
                if len(matched) > 3:
                    lines.append(f"    {g}: +{len(matched)-3} 条")
            else:
                preview = ", ".join(f"\"{t[:25]}\"" for _, _, t, _ in matched[:2])
                lines.append(f"    {g}({len(matched)}): {preview}")

    return "\n".join(lines)


# ─── HTML 简报 ───

def generate_html(date_str=None):
    """生成 HTML 趋势简报"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    match_title = load_matcher()
    items = get_data(date_str)
    results = match_items(items, match_title)
    total_matched = sum(len(v) for v in results.values())

    # 频率趋势（用已有数据）
    trends = get_frequency_insights(match_title)

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>趋势简报 {date_str}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 16px; }}
  .header {{ background: #1a1a2e; color: #fff; padding: 24px; border-radius: 12px; margin-bottom: 16px; }}
  .header h1 {{ font-size: 20px; font-weight: 600; }}
  .header .meta {{ font-size: 13px; color: #aaa; margin-top: 4px; }}
  .stats {{ display: flex; gap: 12px; margin-top: 12px; }}
  .stat {{ background: rgba(255,255,255,0.1); padding: 8px 14px; border-radius: 8px; font-size: 13px; }}
  .stat b {{ font-size: 18px; display: block; }}
  .layer {{ background: #fff; border-radius: 12px; margin-bottom: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .layer-header {{ padding: 14px 18px; font-size: 15px; font-weight: 600; border-bottom: 1px solid #f0f0f0; }}
  .layer-desc {{ font-size: 12px; color: #888; font-weight: 400; margin-left: 8px; }}
  .group {{ padding: 0 18px; }}
  .group-name {{ font-size: 13px; font-weight: 600; color: #666; padding: 10px 0 4px; border-bottom: 1px solid #f5f5f5; }}
  .item {{ display: flex; align-items: baseline; padding: 8px 0; border-bottom: 1px solid #fafafa; }}
  .item:last-child {{ border-bottom: none; }}
  .item a {{ color: #1a73e8; text-decoration: none; font-size: 14px; flex: 1; }}
  .item a:hover {{ text-decoration: underline; }}
  .item .src {{ font-size: 11px; color: #999; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; margin-left: 8px; white-space: nowrap; }}
  .insight {{ background: #fff; border-radius: 12px; margin-bottom: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .insight h2 {{ font-size: 15px; margin-bottom: 12px; }}
  .trend-row {{ display: flex; align-items: center; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #fafafa; }}
  .trend-row:last-child {{ border-bottom: none; }}
  .trend-name {{ flex: 1; }}
  .trend-count {{ width: 50px; text-align: right; font-weight: 600; }}
  .trend-arrow {{ width: 30px; text-align: center; font-size: 16px; }}
  .trend-arrow.up {{ color: #e53935; }}
  .trend-arrow.down {{ color: #43a047; }}
  .trend-arrow.flat {{ color: #999; }}
  .trend-bar {{ width: 80px; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; margin-left: 8px; }}
  .trend-bar-fill {{ height: 100%; border-radius: 3px; }}
  .footer {{ text-align: center; font-size: 11px; color: #bbb; padding: 16px; }}
  .empty {{ padding: 18px; text-align: center; color: #999; font-size: 14px; }}
  .cross {{ font-size: 10px; color: #e65100; background: #fff3e0; padding: 1px 5px; border-radius: 3px; margin-left: 4px; }}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>趋势简报</h1>
  <div class="meta">{date_str} · TrendRadar + RSSHub</div>
  <div class="stats">
    <div class="stat"><b>{len(items)}</b>采集</div>
    <div class="stat"><b>{total_matched}</b>命中</div>
    <div class="stat"><b>{len(results)}</b>关键词组</div>
  </div>
</div>
"""

    # 检测跨平台命中（同一关键词在热榜和RSS都有）
    cross_platform = set()
    for g, matched in results.items():
        sources = set(src_type for src_type, _, _, _ in matched)
        if len(sources) > 1:
            cross_platform.add(g)

    # 分层展示
    for layer_code, layer_emoji, layer_desc, layer_color in LAYER_DISPLAY:
        layer_groups = {g: v for g, v in results.items()
                        if LAYERS.get(g, ('?',))[0] == layer_code}
        if not layer_groups:
            continue

        count = sum(len(v) for v in layer_groups.values())
        html += f"""
<div class="layer">
  <div class="layer-header" style="background: {layer_color};">
    {layer_emoji} {layer_desc}
    <span class="layer-desc">({count} 条)</span>
  </div>
"""
        for g, matched in sorted(layer_groups.items(), key=lambda x: -len(x[1])):
            cross_tag = ' <span class="cross">跨平台</span>' if g in cross_platform else ''
            html += f'  <div class="group"><div class="group-name">{escape(g)}{cross_tag}</div>\n'

            for src_type, src, title, url in matched:
                src_label = SOURCE_LABELS.get(src, src)
                if url:
                    html += f'    <div class="item"><a href="{escape(url)}" target="_blank">{escape(title)}</a><span class="src">{escape(src_label)}</span></div>\n'
                else:
                    html += f'    <div class="item"><span style="flex:1;font-size:14px">{escape(title)}</span><span class="src">{escape(src_label)}</span></div>\n'

            html += '  </div>\n'
        html += '</div>\n'

    if not results:
        html += '<div class="layer"><div class="empty">今日无关键词命中</div></div>\n'

    # Insight: 频率趋势
    if trends:
        max_total = max(t['total'] for t in trends.values()) or 1
        html += """
<div class="insight">
  <h2>📈 关键词热度（近 7 天）</h2>
"""
        for g, t in sorted(trends.items(), key=lambda x: -x[1]['total']):
            layer_code = LAYERS.get(g, ('?',))[0]
            arrow_class = {'↑': 'up', '↓': 'down', '→': 'flat'}.get(t['trend'], 'flat')
            bar_pct = int(t['total'] / max_total * 100)
            bar_colors = {'C': '#43a047', 'D': '#ff9800', 'B': '#1e88e5', 'A': '#e53935'}
            bar_color = bar_colors.get(layer_code, '#999')
            html += f"""  <div class="trend-row">
    <span class="trend-name">{escape(g)}</span>
    <span class="trend-count">{t['total']}</span>
    <span class="trend-arrow {arrow_class}">{t['trend']}</span>
    <div class="trend-bar"><div class="trend-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div></div>
  </div>
"""
        html += '</div>\n'

    html += f"""
<div class="footer">
  Mason Hub · TrendRadar · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>

</div>
</body>
</html>"""

    # 保存
    HTML_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = HTML_OUTPUT_DIR / f"{date_str}.html"
    out_path.write_text(html, encoding='utf-8')

    # 同时写一份 latest.html
    latest_path = HTML_OUTPUT_DIR / "latest.html"
    latest_path.write_text(html, encoding='utf-8')

    return str(out_path)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "text"
    date = sys.argv[2] if len(sys.argv) > 2 else None

    if mode == "html":
        path = generate_html(date)
        print(f"HTML 简报已生成: {path}")
    else:
        print(generate_report(date))
