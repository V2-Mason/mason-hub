#!/usr/bin/env python3
"""
Radar Tracker -- TrendRadar 点击追踪 MVP
为 TrendRadar HTML 报告注入"无用"按钮，记录 Mason 的标记，
生成每周关注率统计，建议淘汰低关注关键词组。
"""

import hashlib
import html as html_mod
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, request

app = Flask(__name__)


@app.after_request
def _add_cors(response):
    """Allow cross-origin requests (file:// or different port)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# --- 配置 ---
TRENDRADAR_HTML = os.environ.get(
    "TRENDRADAR_HTML",
    os.path.expanduser(
        "~/mason-hub/tools/trendradar/output/html/latest/current.html"
    ),
)
TRENDRADAR_HTML_DIR = os.environ.get(
    "TRENDRADAR_HTML_DIR",
    os.path.expanduser("~/mason-hub/tools/trendradar/output/html"),
)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")
RETIRE_THRESHOLD = float(os.environ.get("RETIRE_THRESHOLD", "0.3"))


# --- 数据库 ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_title TEXT NOT NULL,
            keyword_group TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            dismissed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_title TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            first_seen_date TEXT NOT NULL DEFAULT (date('now')),
            UNIQUE(news_title)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS read_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_title TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            read_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(news_title)
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


# --- HTML 注入辅助 ---
def _make_news_id(title):
    """用标题 hash 作为稳定 ID"""
    return hashlib.md5(title.encode("utf-8")).hexdigest()[:12]


def _js_escape(s):
    """转义字符串用于 JS 单引号字面量"""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


def _make_dismiss_btn(title, source):
    """生成 dismiss 按钮 HTML"""
    news_id = _make_news_id(title)
    esc_title = html_mod.escape(_js_escape(title), quote=True)
    esc_source = html_mod.escape(_js_escape(source), quote=True)
    return (
        '<button class="dismiss-btn" title="标记无用" '
        "onclick=\"dismissItem(this, "
        "'" + news_id + "', "
        "'" + esc_title + "', "
        "this.closest('[data-kwgroup]') ? this.closest('[data-kwgroup]').dataset.kwgroup : '', "
        "'" + esc_source + "')\">"
        "\u00d7</button>"
    )


def _make_read_btn(title, source):
    """生成已读标记按钮 HTML"""
    esc_title = html_mod.escape(_js_escape(title), quote=True)
    esc_source = html_mod.escape(_js_escape(source), quote=True)
    return (
        '<button class="read-btn" title="标记已读" '
        "onclick=\"markRead(this, "
        "'" + esc_title + "', "
        "'" + esc_source + "')\">"
        "\u2713</button>"
    )


def _load_read_titles():
    """加载所有已标记已读的标题。"""
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT news_title FROM read_items").fetchall()
    conn.close()
    return {r["news_title"] for r in rows}


# CSS + JS 注入到 </head> 前
INJECT_HEAD = """
<style>
.dismiss-btn {
    background: none;
    border: 1px solid #e5e7eb;
    color: #9ca3af;
    font-size: 16px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s ease;
    padding: 0;
    line-height: 1;
}
.dismiss-btn:hover {
    background: #fef2f2;
    border-color: #fca5a5;
    color: #ef4444;
}
.dismiss-btn.dismissed {
    background: #fee2e2;
    border-color: #fca5a5;
    color: #ef4444;
    opacity: 0.6;
    cursor: default;
}
.news-item.is-dismissed, .rss-item.is-dismissed {
    opacity: 0.35;
}
.news-item { position: relative; }
.read-btn {
    background: none;
    border: 1px solid #e5e7eb;
    color: #9ca3af;
    font-size: 14px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s ease;
    padding: 0;
    line-height: 1;
}
.read-btn:hover {
    background: #f0fdf4;
    border-color: #86efac;
    color: #22c55e;
}
.read-btn.is-read {
    background: #f0fdf4;
    border-color: #86efac;
    color: #22c55e;
    cursor: default;
}
.news-item.is-read .news-link, .rss-item.is-read .rss-link,
.news-item.is-read .news-title, .rss-item.is-read .rss-title {
    text-decoration: line-through;
    color: #9ca3af;
}
.news-item.is-read, .rss-item.is-read {
    opacity: 0.5;
}
</style>
<script>
function dismissItem(btn, newsId, title, keywordGroup, source) {
    if (btn.classList.contains('dismissed')) return;
    fetch('/api/dismiss', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            news_id: newsId,
            title: title,
            keyword_group: keywordGroup,
            source: source
        })
    }).then(function(r) { return r.json(); }).then(function(data) {
        if (data.ok) {
            btn.classList.add('dismissed');
            btn.textContent = '\\u2713';
            var item = btn.closest('.news-item') || btn.closest('.rss-item');
            if (item) item.classList.add('is-dismissed');
        }
    }).catch(function(err) { console.error('dismiss failed', err); });
}
function markRead(btn, title, source) {
    if (btn.classList.contains('is-read')) return;
    fetch('/api/mark-read', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: title, source: source})
    }).then(function(r) { return r.json(); }).then(function(data) {
        if (data.ok) {
            btn.classList.add('is-read');
            var item = btn.closest('.news-item') || btn.closest('.rss-item');
            if (item) item.classList.add('is-read');
        }
    }).catch(function(err) { console.error('mark-read failed', err); });
}
</script>
"""


def _load_dismissed_titles():
    """加载所有已标记无用的标题，用于自动隐藏。"""
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT news_title FROM dismissals").fetchall()
    conn.close()
    return {r["news_title"] for r in rows}


def _is_dismissed(title, dismissed_set):
    """检查标题是否匹配已 dismiss 的内容（精确匹配 + 子串包含）。"""
    if not title:
        return False
    title_clean = title.strip()
    # 精确匹配
    if title_clean in dismissed_set:
        return True
    # 子串匹配：dismissed 标题包含在新标题中，或反过来（处理标题微调）
    for d in dismissed_set:
        if len(d) >= 8 and (d in title_clean or title_clean in d):
            return True
    return False


def _load_seen_before_today():
    """加载今日之前已看过的标题，用于每日去重。"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT news_title FROM seen_items WHERE first_seen_date < ?",
        (today,),
    ).fetchall()
    conn.close()
    return {r["news_title"] for r in rows}


def _record_seen_batch(items):
    """批量记录今日看到的新闻标题。items = [(title, source), ...]"""
    if not items:
        return
    conn = get_db()
    conn.executemany(
        "INSERT OR IGNORE INTO seen_items (news_title, source) VALUES (?, ?)",
        items,
    )
    conn.commit()
    conn.close()


def inject_dismiss_buttons(raw_html):
    """在每条新闻/RSS 条目旁注入 dismiss 按钮，自动隐藏已标记无用和往日已读的条目。"""

    dismissed_set = _load_dismissed_titles()
    seen_before = _load_seen_before_today()
    newly_seen = []  # collect (title, source) for batch insert

    # 1) 注入 CSS + JS 到 </head>
    raw_html = raw_html.replace("</head>", INJECT_HEAD + "\n</head>", 1)

    # 2) Add data-kwgroup attribute to word-group divs
    def _add_kwgroup_attr(m):
        block = m.group(0)
        name_m = re.search(r'class="word-name"[^>]*>([^<]+)</div>', block)
        name = name_m.group(1).strip() if name_m else ""
        return block.replace(
            '<div class="word-group">',
            '<div class="word-group" data-kwgroup="' + html_mod.escape(name) + '">',
            1,
        )

    # word-group 包含多个 news-item，匹配到 word-group 结尾
    raw_html = re.sub(
        r'<div class="word-group">(?=\s*<div class="word-header">)',
        lambda m: m.group(0),  # placeholder, handled below
        raw_html,
    )
    # Simpler: just replace the opening tag with data attribute
    # Find each word-group opening and the word-name inside its header
    parts = raw_html.split('<div class="word-group">')
    if len(parts) > 1:
        rebuilt = [parts[0]]
        for part in parts[1:]:
            name_m = re.search(r'class="word-name"[^>]*>([^<]+)</div>', part)
            name = name_m.group(1).strip() if name_m else ""
            rebuilt.append(
                '<div class="word-group" data-kwgroup="'
                + html_mod.escape(name)
                + '">'
                + part
            )
        raw_html = "".join(rebuilt)

    # 3) Add data-kwgroup to feed-group divs (RSS)
    parts = raw_html.split('<div class="feed-group">')
    if len(parts) > 1:
        rebuilt = [parts[0]]
        for part in parts[1:]:
            name_m = re.search(r'class="feed-name"[^>]*>([^<]+)</div>', part)
            name = name_m.group(1).strip() if name_m else ""
            rebuilt.append(
                '<div class="feed-group" data-kwgroup="'
                + html_mod.escape(name)
                + '">'
                + part
            )
        raw_html = "".join(rebuilt)

    # 4) Add data-kwgroup to standalone-group divs
    parts = raw_html.split('<div class="standalone-group">')
    if len(parts) > 1:
        rebuilt = [parts[0]]
        for part in parts[1:]:
            name_m = re.search(r'class="standalone-name"[^>]*>([^<]+)</div>', part)
            name = name_m.group(1).strip() if name_m else ""
            rebuilt.append(
                '<div class="standalone-group" data-kwgroup="'
                + html_mod.escape(name)
                + '">'
                + part
            )
        raw_html = "".join(rebuilt)

    # 5) Inject dismiss + read buttons into news-items, hide already-dismissed and already-seen
    dedup_hidden = [0]  # mutable counter for closure
    read_set = _load_read_titles()

    def _inject_news_btn(m):
        block = m.group(0)
        title_m = re.search(r'class="news-link"[^>]*>([^<]+)</a>', block)
        title = title_m.group(1).strip() if title_m else ""
        src_m = re.search(r'class="source-name"[^>]*>([^<]+)</span>', block)
        source = src_m.group(1).strip() if src_m else ""
        # 已 dismiss 的条目直接隐藏
        if _is_dismissed(title, dismissed_set):
            return ""
        # 往日已读的条目隐藏（每日去重）
        if title and _is_dismissed(title, seen_before):
            dedup_hidden[0] += 1
            return ""
        # 记录为今日已见
        if title:
            newly_seen.append((title, source))
        read_btn = _make_read_btn(title, source)
        dismiss_btn = _make_dismiss_btn(title, source)
        # 如果已标记已读，给 item 加 is-read class，按钮加 is-read
        is_already_read = title in read_set
        if is_already_read:
            block = block.replace('class="news-item"', 'class="news-item is-read"', 1)
            read_btn = read_btn.replace('class="read-btn"', 'class="read-btn is-read"', 1)
        idx = block.rfind("</div>")
        return block[:idx] + read_btn + dismiss_btn + block[idx:]

    raw_html = re.sub(
        r'<div class="news-item[^"]*">\s*<div class="news-number">'
        r'.*?</div>\s*<div class="news-content">.*?</div>\s*</div>',
        _inject_news_btn,
        raw_html,
        flags=re.DOTALL,
    )

    # 6) Inject dismiss buttons into RSS items, hide already-dismissed and already-seen
    def _inject_rss_btn(m):
        block = m.group(0)
        title_m = re.search(r'class="rss-link"[^>]*>([^<]+)</a>', block)
        title = title_m.group(1).strip() if title_m else ""
        author_m = re.search(r'class="rss-author"[^>]*>([^<]+)</span>', block)
        source = author_m.group(1).strip() if author_m else ""
        if _is_dismissed(title, dismissed_set):
            return ""
        if title and _is_dismissed(title, seen_before):
            dedup_hidden[0] += 1
            return ""
        if title:
            newly_seen.append((title, source))
        read_btn = _make_read_btn(title, source)
        dismiss_btn = _make_dismiss_btn(title, source)
        is_already_read = title in read_set
        if is_already_read:
            block = block.replace('class="rss-item"', 'class="rss-item is-read"', 1)
            read_btn = read_btn.replace('class="read-btn"', 'class="read-btn is-read"', 1)
        idx = block.rfind("</div>")
        return block[:idx] + read_btn + dismiss_btn + block[idx:]

    raw_html = re.sub(
        r'<div class="rss-item">\s*<div class="rss-meta">.*?</div>\s*'
        r'<div class="rss-title">.*?</div>\s*</div>',
        _inject_rss_btn,
        raw_html,
        flags=re.DOTALL,
    )

    # 7) 批量记录今日已见
    _record_seen_batch(newly_seen)

    # 8) 注入已过滤条数提示
    hidden_count = len(dismissed_set)
    dedup_count = dedup_hidden[0]
    if hidden_count > 0 or dedup_count > 0:
        parts = []
        if hidden_count > 0:
            parts.append(str(hidden_count) + ' 个标记无用')
        if dedup_count > 0:
            parts.append(str(dedup_count) + ' 个往日已读')
        badge = (
            '<div style="background:#1e293b;padding:8px 20px;font-family:system-ui,sans-serif;'
            'font-size:13px;color:#94a3b8;">'
            '已过滤 ' + ' + '.join(parts) + ' · '
            '<a href="/api/stats" style="color:#60a5fa;text-decoration:none;">查看统计</a>'
            '</div>'
        )
        raw_html = raw_html.replace("<body>", "<body>" + badge, 1)

    return raw_html


# --- 历史报告辅助 ---
def _list_available_reports():
    """扫描 HTML 目录，返回可用的日期和时间列表。"""
    html_dir = Path(TRENDRADAR_HTML_DIR)
    reports = []
    if not html_dir.exists():
        return reports
    for date_dir in sorted(html_dir.iterdir()):
        if date_dir.name == "latest" or not date_dir.is_dir():
            continue
        for html_file in sorted(date_dir.glob("*.html")):
            reports.append({
                "date": date_dir.name,
                "time": html_file.stem,
                "path": str(html_file),
            })
    return reports


def _build_date_nav(reports, current_date=None, current_time=None):
    """生成日期/时间导航栏 HTML。"""
    if not reports:
        return ""

    # Group by date
    dates = {}
    for r in reports:
        dates.setdefault(r["date"], []).append(r)

    nav_html = """
<div style="background:#1e293b;padding:12px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;font-family:system-ui,-apple-system,sans-serif;">
  <span style="color:#94a3b8;font-size:13px;font-weight:600;">Radar 历史</span>
  <select id="date-select" onchange="loadReport()" style="background:#334155;color:#e2e8f0;border:1px solid #475569;padding:6px 12px;border-radius:6px;font-size:13px;cursor:pointer;">
"""
    for date in sorted(dates.keys(), reverse=True):
        selected = ' selected' if date == current_date else ''
        label = date + " (" + str(len(dates[date])) + "份)"
        nav_html += '    <option value="' + date + '"' + selected + '>' + label + '</option>\n'

    nav_html += """  </select>
  <select id="time-select" onchange="loadReport()" style="background:#334155;color:#e2e8f0;border:1px solid #475569;padding:6px 12px;border-radius:6px;font-size:13px;cursor:pointer;">
"""
    # Times for current date
    cur_times = dates.get(current_date, [])
    for r in reversed(cur_times):
        selected = ' selected' if r["time"] == current_time else ''
        nav_html += '    <option value="' + r["time"] + '"' + selected + '>' + r["time"].replace("-", ":") + '</option>\n'

    nav_html += """  </select>
  <a href="/" style="color:#60a5fa;font-size:13px;text-decoration:none;">← 最新</a>
  <a href="/insights" style="color:#60a5fa;font-size:13px;text-decoration:none;">📈 趋势分析</a>
  <a href="/intel" style="color:#60a5fa;font-size:13px;text-decoration:none;">🔍 情报</a>
  <script>
  var reportDates = """ + str({d: [r["time"] for r in reversed(rs)] for d, rs in dates.items()}).replace("'", '"') + """;
  document.getElementById('date-select').onchange = function() {
    var d = this.value;
    var ts = document.getElementById('time-select');
    ts.innerHTML = '';
    (reportDates[d] || []).forEach(function(t) {
      var opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t.replace('-', ':');
      ts.appendChild(opt);
    });
    loadReport();
  };
  function loadReport() {
    var d = document.getElementById('date-select').value;
    var t = document.getElementById('time-select').value;
    window.location.href = '/history/' + d + '/' + t;
  }
  </script>
</div>
"""
    return nav_html


# --- 路由 ---
@app.route("/")
def unified():
    """统一视图：分层关键词命中 + 未分类热门 + Scout 情报摘要"""
    from html import escape as h

    date_str = datetime.now().strftime('%Y-%m-%d')

    try:
        match_title = _load_matcher()
    except Exception as e:
        return Response("<h1>Error loading matcher</h1><p>" + str(e) + "</p>",
                        status=500, content_type="text/html; charset=utf-8")

    items = _get_data(date_str)
    results = _match_items(items, match_title)
    total_matched = sum(len(v) for v in results.values())
    trends = _get_frequency_trends(match_title)
    dismissed_set = _load_dismissed_titles()
    seen_before = _load_seen_before_today()
    read_set = _load_read_titles()
    newly_seen = []

    # Unmatched items (hot items not caught by keywords)
    matched_titles = set()
    for matched in results.values():
        for _, _, title, _ in matched:
            matched_titles.add(title)
    unmatched = [(st, src, title, url) for st, src, title, url in items
                 if title not in matched_titles]

    # Cross-platform detection
    cross_platform = set()
    for g, matched in results.items():
        sources = set(st for st, _, _, _ in matched)
        if len(sources) > 1:
            cross_platform.add(g)

    # Scout digest
    scout_html = ""
    if INTEL_DIGESTS_DIR.exists():
        digest_files = sorted(INTEL_DIGESTS_DIR.glob("*.md"),
                              key=lambda f: f.stat().st_mtime, reverse=True)
        if digest_files:
            md = digest_files[0].read_text(encoding='utf-8')
            scout_html = _render_markdown_to_html(md)
            scout_label = digest_files[0].stem

    # Navigation tabs
    nav = """
<div style="background:#1e293b;padding:0;font-family:system-ui,sans-serif;">
  <div style="display:flex;align-items:center;padding:10px 20px;gap:4px;">
    <a href="/" style="background:#334155;color:#e2e8f0;padding:6px 14px;border-radius:6px 6px 0 0;font-size:13px;text-decoration:none;font-weight:600;">统一视图</a>
    <a href="/hotlist" style="color:#94a3b8;padding:6px 14px;font-size:13px;text-decoration:none;">热榜原始</a>
    <a href="/insights" style="color:#94a3b8;padding:6px 14px;font-size:13px;text-decoration:none;">趋势分析</a>
    <a href="/intel" style="color:#94a3b8;padding:6px 14px;font-size:13px;text-decoration:none;">情报简报</a>
    <span style="flex:1"></span>
    <span style="color:#475569;font-size:12px;">""" + date_str + """</span>
  </div>
</div>"""

    page = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar — {date_str}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 760px; margin: 0 auto; padding: 16px; }}
  .header {{ background: #1a1a2e; color: #fff; padding: 20px 24px; border-radius: 12px; margin-bottom: 16px; }}
  .header h1 {{ font-size: 20px; font-weight: 600; }}
  .header .meta {{ font-size: 13px; color: #aaa; margin-top: 4px; }}
  .stats {{ display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }}
  .stat {{ background: rgba(255,255,255,0.1); padding: 6px 12px; border-radius: 8px; font-size: 12px; }}
  .stat b {{ font-size: 16px; display: block; }}
  .layer {{ background: #fff; border-radius: 12px; margin-bottom: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .layer-header {{ padding: 12px 18px; font-size: 15px; font-weight: 600; border-bottom: 1px solid #f0f0f0; }}
  .layer-desc {{ font-size: 12px; color: #888; font-weight: 400; margin-left: 8px; }}
  .group {{ padding: 0 18px; }}
  .group-name {{ font-size: 13px; font-weight: 600; color: #666; padding: 10px 0 4px; border-bottom: 1px solid #f5f5f5; }}
  .item {{ display: flex; align-items: center; padding: 6px 0; border-bottom: 1px solid #fafafa; gap: 8px; }}
  .item:last-child {{ border-bottom: none; }}
  .item a {{ color: #1a73e8; text-decoration: none; font-size: 13px; flex: 1; }}
  .item a:hover {{ text-decoration: underline; }}
  .item .src {{ font-size: 10px; color: #999; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }}
  .btn {{ background: none; border: 1px solid #e5e7eb; color: #9ca3af; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 13px; flex-shrink: 0; transition: all 0.2s; display:flex; align-items:center; justify-content:center; }}
  .btn-read:hover {{ background: #f0fdf4; border-color: #86efac; color: #22c55e; }}
  .btn-read.is-read {{ background: #f0fdf4; border-color: #86efac; color: #22c55e; cursor: default; }}
  .btn-dismiss:hover {{ background: #fef2f2; border-color: #fca5a5; color: #ef4444; }}
  .item.is-read a {{ text-decoration: line-through; color: #9ca3af; }}
  .item.is-read {{ opacity: 0.5; }}
  .cross {{ font-size: 10px; color: #e65100; background: #fff3e0; padding: 1px 5px; border-radius: 3px; margin-left: 4px; }}
  .scout {{ background: #fff; border-radius: 12px; margin-bottom: 12px; padding: 18px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .scout h2 {{ font-size: 15px; margin-bottom: 12px; }}
  .trend-section {{ background: #fff; border-radius: 12px; margin-bottom: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .trend-section h2 {{ font-size: 15px; margin-bottom: 12px; }}
  .trend-row {{ display: flex; align-items: center; padding: 5px 0; font-size: 13px; border-bottom: 1px solid #fafafa; }}
  .trend-row:last-child {{ border-bottom: none; }}
  .trend-name {{ flex: 1; }}
  .trend-count {{ width: 40px; text-align: right; font-weight: 600; }}
  .trend-arrow {{ width: 24px; text-align: center; font-size: 14px; }}
  .trend-arrow.up {{ color: #e53935; }}
  .trend-arrow.down {{ color: #43a047; }}
  .trend-arrow.flat {{ color: #999; }}
  .trend-bar {{ width: 60px; height: 5px; background: #eee; border-radius: 3px; overflow: hidden; margin-left: 6px; }}
  .trend-bar-fill {{ height: 100%; border-radius: 3px; }}
  .footer {{ text-align: center; font-size: 11px; color: #bbb; padding: 16px; }}
</style>
<script>
function markRead(btn, title, source) {{
    if (btn.classList.contains('is-read')) return;
    fetch('/api/mark-read', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{title: title, source: source}})
    }}).then(r => r.json()).then(data => {{
        if (data.ok) {{
            btn.classList.add('is-read');
            var item = btn.closest('.item');
            if (item) item.classList.add('is-read');
        }}
    }});
}}
function dismiss(btn, title, group, source) {{
    fetch('/api/dismiss', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{title: title, keyword_group: group, source: source}})
    }}).then(r => r.json()).then(data => {{
        if (data.ok) {{
            var item = btn.closest('.item');
            if (item) item.style.display = 'none';
        }}
    }});
}}
</script>
</head>
<body>
{nav}
<div class="container">

<div class="header">
  <h1>Radar</h1>
  <div class="meta">{date_str} · {len(items)} 条采集 · {total_matched} 条关键词命中 · {len(unmatched)} 条未分类</div>
  <div class="stats">
    <div class="stat"><b>{len(items)}</b>采集</div>
    <div class="stat"><b>{total_matched}</b>命中</div>
    <div class="stat"><b>{len(results)}</b>关键词组</div>
    <div class="stat"><b>{len(unmatched)}</b>未分类</div>
  </div>
</div>
"""

    def _render_item(title, url, src_label, group_name=""):
        """Render a single item with read + dismiss buttons."""
        if _is_dismissed(title, dismissed_set):
            return ""
        if _is_dismissed(title, seen_before):
            return ""
        newly_seen.append((title, src_label))
        is_read = title in read_set
        read_cls = " is-read" if is_read else ""
        btn_cls = " is-read" if is_read else ""
        esc_t = h(title.replace("'", "\\'"))
        esc_g = h(group_name.replace("'", "\\'"))
        esc_s = h(src_label.replace("'", "\\'"))
        link = f'<a href="{h(url)}" target="_blank">{h(title)}</a>' if url else f'<span style="flex:1;font-size:13px">{h(title)}</span>'
        return (
            f'<div class="item{read_cls}">'
            f'{link}<span class="src">{h(src_label)}</span>'
            f"<button class=\"btn btn-read{btn_cls}\" onclick=\"markRead(this, '{esc_t}', '{esc_s}')\">✓</button>"
            f"<button class=\"btn btn-dismiss\" onclick=\"dismiss(this, '{esc_t}', '{esc_g}', '{esc_s}')\">&times;</button>"
            f'</div>\n'
        )

    # --- Layered keyword hits ---
    for layer_code, layer_emoji, layer_desc, layer_color in LAYER_DISPLAY:
        layer_groups = {g: v for g, v in results.items()
                        if LAYERS.get(g, ('?',))[0] == layer_code}
        if not layer_groups:
            continue

        count = sum(len(v) for v in layer_groups.values())
        page += f"""
<div class="layer">
  <div class="layer-header" style="background: {layer_color};">
    {layer_emoji} {layer_desc}
    <span class="layer-desc">({count} 条)</span>
  </div>
"""
        for g, matched in sorted(layer_groups.items(), key=lambda x: -len(x[1])):
            cross_tag = ' <span class="cross">跨平台</span>' if g in cross_platform else ''
            page += f'  <div class="group"><div class="group-name">{h(g)}{cross_tag}</div>\n'
            for src_type, src, title, url in matched:
                src_label = SOURCE_LABELS.get(src, src)
                page += "    " + _render_item(title, url, src_label, g)
            page += '  </div>\n'
        page += '</div>\n'

    if not results:
        page += '<div class="layer" style="padding:18px;text-align:center;color:#999;">今日无关键词命中</div>\n'

    # --- Unmatched hot items ---
    if unmatched:
        # Deduplicate and limit
        seen_unmatched = set()
        filtered = []
        for st, src, title, url in unmatched:
            if title not in seen_unmatched and not _is_dismissed(title, dismissed_set) and not _is_dismissed(title, seen_before):
                seen_unmatched.add(title)
                filtered.append((st, src, title, url))
        if filtered:
            page += f"""
<div class="layer">
  <div class="layer-header" style="background: #f3f4f6;">
    📰 未分类热榜 <span class="layer-desc">({len(filtered)} 条，关键词未命中)</span>
  </div>
  <div class="group">
"""
            for st, src, title, url in filtered[:50]:  # cap at 50
                src_label = SOURCE_LABELS.get(src, src)
                page += "    " + _render_item(title, url, src_label)
            page += '  </div>\n</div>\n'

    # --- 7-day trends ---
    if trends:
        max_total = max(t['total'] for t in trends.values()) or 1
        bar_colors = {'C': '#43a047', 'C+': '#009688', 'D': '#ff9800', 'B': '#1e88e5', 'A': '#e53935'}
        page += '<div class="trend-section"><h2>📈 关键词热度（近 7 天）</h2>\n'
        for g, t in sorted(trends.items(), key=lambda x: -x[1]['total']):
            layer_code = LAYERS.get(g, ('?',))[0]
            arrow_class = {'↑': 'up', '↓': 'down', '→': 'flat'}.get(t['trend'], 'flat')
            bar_pct = int(t['total'] / max_total * 100)
            bar_color = bar_colors.get(layer_code, '#999')
            page += f"""  <div class="trend-row">
    <span class="trend-name">{h(g)}</span>
    <span class="trend-count">{t['total']}</span>
    <span class="trend-arrow {arrow_class}">{t['trend']}</span>
    <div class="trend-bar"><div class="trend-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div></div>
  </div>\n"""
        page += '</div>\n'

    # --- Scout digest ---
    if scout_html:
        page += f"""
<div class="scout">
  <h2>🔍 Scout 情报摘要 — {h(scout_label)}</h2>
  <div style="font-size:13px;">
    {scout_html}
  </div>
</div>
"""

    _record_seen_batch(newly_seen)

    page += f"""
<div class="footer">
  Radar · Mason Hub · {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
</div>
</body>
</html>"""

    return Response(page, content_type="text/html; charset=utf-8")


@app.route("/hotlist")
def hotlist():
    """原始热榜视图（旧首页）。"""
    html_path = Path(TRENDRADAR_HTML)
    if not html_path.exists():
        return Response(
            "<h1>No TrendRadar report found</h1>"
            "<p>Expected at: " + str(html_path) + "</p>",
            status=404,
            content_type="text/html; charset=utf-8",
        )
    content = html_path.read_text(encoding="utf-8")
    injected = inject_dismiss_buttons(content)
    reports = _list_available_reports()
    nav = _build_date_nav(reports)
    if nav:
        injected = injected.replace("<body>", "<body>" + nav, 1)
    else:
        # 即使没有历史报告，也加趋势分析入口
        simple_nav = (
            '<div style="background:#1e293b;padding:12px 20px;font-family:system-ui,sans-serif;">'
            '<a href="/insights" style="color:#60a5fa;font-size:13px;text-decoration:none;">📈 趋势分析</a>'
            '</div>'
        )
        injected = injected.replace("<body>", "<body>" + simple_nav, 1)
    return Response(injected, content_type="text/html; charset=utf-8")


@app.route("/history/<date>/<time_slot>")
def history(date, time_slot):
    """查看历史报告。"""
    html_path = Path(TRENDRADAR_HTML_DIR) / date / (time_slot + ".html")
    if not html_path.exists():
        return Response(
            "<h1>Report not found</h1>"
            "<p>" + date + " " + time_slot + "</p>",
            status=404,
            content_type="text/html; charset=utf-8",
        )
    content = html_path.read_text(encoding="utf-8")
    injected = inject_dismiss_buttons(content)
    reports = _list_available_reports()
    nav = _build_date_nav(reports, current_date=date, current_time=time_slot)
    if nav:
        injected = injected.replace("<body>", "<body>" + nav, 1)
    return Response(injected, content_type="text/html; charset=utf-8")


@app.route("/api/dismiss", methods=["GET", "POST"])
def dismiss():
    """接收 dismiss 标记，写入 SQLite。
    POST: JSON body {title, keyword_group, source}
    GET:  /api/dismiss?title=xxx&keyword_group=yyy&source=zzz
    """
    if request.method == "GET":
        title = (request.args.get("title") or "").strip()
        keyword_group = (request.args.get("keyword_group") or "").strip()
        source = (request.args.get("source") or "").strip()
    else:
        data = request.get_json(force=True)
        title = (data.get("title") or "").strip()
        keyword_group = (data.get("keyword_group") or "").strip()
        source = (data.get("source") or "").strip()

    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO dismissals (news_title, keyword_group, source) VALUES (?, ?, ?)",
        (title, keyword_group, source),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/mark-read", methods=["POST"])
def mark_read():
    """标记一条新闻为已读。"""
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400
    source = (data.get("source") or "").strip()
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO read_items (news_title, source) VALUES (?, ?)",
        (title, source),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/stats")
def stats():
    """返回每组关键词的命中数 vs 无用标记数统计。"""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT keyword_group,
               COUNT(*) as dismiss_count,
               MIN(dismissed_at) as first_dismissed,
               MAX(dismissed_at) as last_dismissed
        FROM dismissals
        WHERE keyword_group != ''
        GROUP BY keyword_group
        ORDER BY dismiss_count DESC
        """
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "keyword_group": r["keyword_group"],
            "dismiss_count": r["dismiss_count"],
            "first_dismissed": r["first_dismissed"],
            "last_dismissed": r["last_dismissed"],
        })
    return jsonify({"stats": result})


def _count_weekly_hits(weeks=2):
    """从 TrendRadar 数据统计每组关键词每周的总命中数。"""
    try:
        match_title = _load_matcher()
    except Exception:
        return None

    now = datetime.now()
    weekly_hits = []
    for w in range(weeks):
        week_end = now - timedelta(weeks=w)
        week_start = week_end - timedelta(weeks=1)
        group_counts = {}
        for i in range(7):
            d = week_start + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            day_items = _get_data(ds)
            day_results = _match_items(day_items, match_title)
            for g, matched in day_results.items():
                group_counts[g] = group_counts.get(g, 0) + len(matched)
        weekly_hits.append({
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "hits_by_group": group_counts,
        })
    return weekly_hits


@app.route("/api/weekly-report")
def weekly_report():
    """
    返回关注率报告。
    关注率 = 1 - (dismissed / total_hits)。
    连续两周关注率低于阈值的关键词组建议淘汰。
    ?weeks=N 可指定回看周数（默认 2）。
    """
    weeks = int(request.args.get("weeks", 2))
    conn = get_db()

    # 每周 dismiss 数
    report_weeks = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for w in range(weeks):
        week_end = now - timedelta(weeks=w)
        week_start = week_end - timedelta(weeks=1)
        rows = conn.execute(
            """
            SELECT keyword_group,
                   COUNT(*) as dismissed
            FROM dismissals
            WHERE keyword_group != ''
              AND dismissed_at >= ?
              AND dismissed_at < ?
            GROUP BY keyword_group
            """,
            (week_start.isoformat(), week_end.isoformat()),
        ).fetchall()
        week_data = {r["keyword_group"]: r["dismissed"] for r in rows}
        report_weeks.append({
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "dismissals_by_group": week_data,
        })

    all_groups = conn.execute(
        """
        SELECT keyword_group, COUNT(*) as total_dismissed
        FROM dismissals
        WHERE keyword_group != ''
        GROUP BY keyword_group
        """
    ).fetchall()
    conn.close()

    # 每周总命中数（从 TrendRadar 数据）
    weekly_hits = _count_weekly_hits(weeks) or []

    # 计算每组每周的关注率
    for i, rw in enumerate(report_weeks):
        hits = weekly_hits[i]["hits_by_group"] if i < len(weekly_hits) else {}
        rw["hits_by_group"] = hits
        relevance = {}
        all_kw = set(list(rw["dismissals_by_group"].keys()) + list(hits.keys()))
        for kw in all_kw:
            total = hits.get(kw, 0)
            dismissed = rw["dismissals_by_group"].get(kw, 0)
            if total > 0:
                relevance[kw] = round(1.0 - dismissed / total, 2)
            elif dismissed > 0:
                relevance[kw] = 0.0
            # 无数据的不算
        rw["relevance_by_group"] = relevance

    # 淘汰建议：连续两周关注率低于阈值
    suggest_retire = []
    if len(report_weeks) >= 2:
        r0 = report_weeks[0].get("relevance_by_group", {})
        r1 = report_weeks[1].get("relevance_by_group", {})
        all_kw = set(list(r0.keys()) + list(r1.keys()))
        for kw in sorted(all_kw):
            rel0 = r0.get(kw)
            rel1 = r1.get(kw)
            if rel0 is not None and rel1 is not None:
                if rel0 < RETIRE_THRESHOLD and rel1 < RETIRE_THRESHOLD:
                    suggest_retire.append({
                        "keyword_group": kw,
                        "recent_week_relevance": rel0,
                        "prev_week_relevance": rel1,
                        "recent_week_hits": report_weeks[0].get("hits_by_group", {}).get(kw, 0),
                        "recent_week_dismissed": report_weeks[0]["dismissals_by_group"].get(kw, 0),
                        "reason": f"连续两周关注率低于 {RETIRE_THRESHOLD:.0%}（本周 {rel0:.0%}，上周 {rel1:.0%}）",
                    })

    return jsonify({
        "threshold": RETIRE_THRESHOLD,
        "weeks": report_weeks,
        "all_time": {
            r["keyword_group"]: r["total_dismissed"] for r in all_groups
        },
        "suggest_retire": suggest_retire,
    })


# --- 趋势分析（合并自 trend_report.py）---
TRENDRADAR_DIR = Path(os.path.expanduser("~/mason-hub/tools/trendradar"))

LAYERS = {
    '韩妆/护肤': ('A', '现有业务'), '跨境电商': ('A', '现有业务'), '小红书': ('A', '现有业务'),
    'AI视频': ('B', '技术动态'), 'Vibe Coding': ('B', '技术动态'), 'AI Agent': ('B', '技术动态'),
    '出海': ('C', '赛道扫描'), 'AI工具/SaaS': ('C', '赛道扫描'), '内容电商': ('C', '赛道扫描'),
    '抖音/TikTok': ('C', '赛道扫描'), '个人IP': ('C', '赛道扫描'), '新消费': ('C', '赛道扫描'),
    '基础设施/硬科技': ('C+', '硬件基建'),
    '独立开发': ('D', '同类人'), '趋势观察': ('D', '同类人'),
}

LAYER_DISPLAY = [
    ('C', '📡 赛道扫描', '你正在探索的新方向', '#e8f5e9'),
    ('C+', '🔩 硬件基建', '内存/存储/电力/储能', '#e0f2f1'),
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
    'theverge': 'The Verge', 'arstechnica': 'Ars', 'mit-tech-review': 'MIT TR',
    'mckinsey': 'McKinsey', 'cbinsights': 'CB Insights',
    'tomshardware': "Tom's HW", 'utilitydive': 'Utility Dive',
}


def _load_matcher():
    """加载 TrendRadar 的关键词匹配器"""
    import sys as _sys
    _sys.path.insert(0, str(TRENDRADAR_DIR))
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


def _get_data(date_str):
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


def _match_items(items, match_title):
    results = {}
    for src_type, src, title, url in items:
        group = match_title(title)
        if group:
            results.setdefault(group, []).append((src_type, src, title, url))
    return results


def _get_frequency_trends(match_title, days=7):
    today = datetime.now()
    daily_counts = {}
    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.strftime('%Y-%m-%d')
        items = _get_data(ds)
        results = _match_items(items, match_title)
        daily_counts[ds] = {g: len(v) for g, v in results.items()}

    all_groups = set()
    for dc in daily_counts.values():
        all_groups.update(dc.keys())

    trends = {}
    for g in all_groups:
        counts = [daily_counts.get(ds, {}).get(g, 0) for ds in sorted(daily_counts.keys())]
        total = sum(counts)
        if total > 0:
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


@app.route("/insights")
@app.route("/insights/<date_str>")
def insights(date_str=None):
    """趋势分析页面：分层展示 + 7 天热度趋势"""
    from html import escape as h

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    try:
        match_title = _load_matcher()
    except Exception as e:
        return Response("<h1>Error loading matcher</h1><p>" + str(e) + "</p>",
                        status=500, content_type="text/html; charset=utf-8")

    items = _get_data(date_str)
    results = _match_items(items, match_title)
    total_matched = sum(len(v) for v in results.values())
    trends = _get_frequency_trends(match_title)
    dismissed_set = _load_dismissed_titles()
    seen_before = _load_seen_before_today()
    read_set = _load_read_titles()
    insights_newly_seen = []

    # 跨平台检测
    cross_platform = set()
    for g, matched in results.items():
        sources = set(st for st, _, _, _ in matched)
        if len(sources) > 1:
            cross_platform.add(g)

    html_out = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar 趋势分析 {date_str}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 16px; }}
  .nav {{ background: #1e293b; padding: 12px 20px; display: flex; align-items: center; gap: 16px; font-family: system-ui, sans-serif; }}
  .nav a {{ color: #60a5fa; text-decoration: none; font-size: 13px; }}
  .nav a:hover {{ text-decoration: underline; }}
  .nav span {{ color: #94a3b8; font-size: 13px; }}
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
  .item {{ display: flex; align-items: baseline; padding: 8px 0; border-bottom: 1px solid #fafafa; gap: 8px; }}
  .item:last-child {{ border-bottom: none; }}
  .item a {{ color: #1a73e8; text-decoration: none; font-size: 14px; flex: 1; }}
  .item a:hover {{ text-decoration: underline; }}
  .item .src {{ font-size: 11px; color: #999; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }}
  .item .dismiss {{ background: none; border: 1px solid #e5e7eb; color: #9ca3af; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 14px; flex-shrink: 0; transition: all 0.2s; }}
  .item .dismiss:hover {{ background: #fef2f2; border-color: #fca5a5; color: #ef4444; }}
  .item .read-mark {{ background: none; border: 1px solid #e5e7eb; color: #9ca3af; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 14px; flex-shrink: 0; transition: all 0.2s; }}
  .item .read-mark:hover {{ background: #f0fdf4; border-color: #86efac; color: #22c55e; }}
  .item .read-mark.is-read {{ background: #f0fdf4; border-color: #86efac; color: #22c55e; cursor: default; }}
  .item.is-read a {{ text-decoration: line-through; color: #9ca3af; }}
  .item.is-read {{ opacity: 0.5; }}
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
  .cross {{ font-size: 10px; color: #e65100; background: #fff3e0; padding: 1px 5px; border-radius: 3px; margin-left: 4px; }}
  .footer {{ text-align: center; font-size: 11px; color: #bbb; padding: 16px; }}
  .hidden {{ display: none; }}
</style>
<script>
function dismissInsight(btn, title, group, source) {{
    fetch('/api/dismiss', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{title: title, keyword_group: group, source: source}})
    }}).then(r => r.json()).then(data => {{
        if (data.ok) {{
            var item = btn.closest('.item');
            if (item) item.style.display = 'none';
        }}
    }});
}}
function markReadInsight(btn, title, source) {{
    if (btn.classList.contains('is-read')) return;
    fetch('/api/mark-read', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{title: title, source: source}})
    }}).then(r => r.json()).then(data => {{
        if (data.ok) {{
            btn.classList.add('is-read');
            var item = btn.closest('.item');
            if (item) item.classList.add('is-read');
        }}
    }});
}}
</script>
</head>
<body>
<div class="nav">
  <a href="/">统一视图</a>
  <span>·</span>
  <a href="/hotlist">热榜原始</a>
  <span>·</span>
  <span style="color:#e2e8f0;font-weight:600;">趋势分析</span>
  <span>·</span>
  <a href="/intel">情报简报</a>
  <span>·</span>
  <span style="color:#94a3b8;">{date_str}</span>
</div>
<div class="container">

<div class="header">
  <h1>Radar 趋势分析</h1>
  <div class="meta">{date_str} · {len(items)} 条采集 · {total_matched} 条命中 · {len(results)} 个关键词组</div>
  <div class="stats">
    <div class="stat"><b>{len(items)}</b>采集</div>
    <div class="stat"><b>{total_matched}</b>命中</div>
    <div class="stat"><b>{len(results)}</b>关键词组</div>
  </div>
</div>
"""

    # 分层展示
    for layer_code, layer_emoji, layer_desc, layer_color in LAYER_DISPLAY:
        layer_groups = {g: v for g, v in results.items()
                        if LAYERS.get(g, ('?',))[0] == layer_code}
        if not layer_groups:
            continue

        count = sum(len(v) for v in layer_groups.values())
        html_out += f"""
<div class="layer">
  <div class="layer-header" style="background: {layer_color};">
    {layer_emoji} {layer_desc}
    <span class="layer-desc">({count} 条)</span>
  </div>
"""
        for g, matched in sorted(layer_groups.items(), key=lambda x: -len(x[1])):
            cross_tag = ' <span class="cross">跨平台</span>' if g in cross_platform else ''
            html_out += f'  <div class="group"><div class="group-name">{h(g)}{cross_tag}</div>\n'

            for src_type, src, title, url in matched:
                if _is_dismissed(title, dismissed_set):
                    continue
                if _is_dismissed(title, seen_before):
                    continue
                insights_newly_seen.append((title, src))
                src_label = SOURCE_LABELS.get(src, src)
                esc_title = h(title.replace("'", "\\'"))
                esc_g = h(g.replace("'", "\\'"))
                esc_src = h(src_label.replace("'", "\\'"))
                link = f'<a href="{h(url)}" target="_blank">{h(title)}</a>' if url else f'<span style="flex:1;font-size:14px">{h(title)}</span>'
                is_read = title in read_set
                read_cls = ' is-read' if is_read else ''
                read_btn_cls = ' is-read' if is_read else ''
                html_out += f'    <div class="item{read_cls}">{link}<span class="src">{h(src_label)}</span>'
                html_out += f"<button class=\"read-mark{read_btn_cls}\" onclick=\"markReadInsight(this, '{esc_title}', '{esc_src}')\">\u2713</button>"
                html_out += f"<button class=\"dismiss\" onclick=\"dismissInsight(this, '{esc_title}', '{esc_g}', '{esc_src}')\">&times;</button></div>\n"

            html_out += '  </div>\n'
        html_out += '</div>\n'

    _record_seen_batch(insights_newly_seen)

    if not results:
        html_out += '<div class="layer" style="padding:18px;text-align:center;color:#999;">今日无关键词命中</div>\n'

    # 7 天热度趋势
    if trends:
        max_total = max(t['total'] for t in trends.values()) or 1
        html_out += """
<div class="insight">
  <h2>📈 关键词热度（近 7 天）</h2>
"""
        bar_colors = {'C': '#43a047', 'C+': '#009688', 'D': '#ff9800', 'B': '#1e88e5', 'A': '#e53935'}
        for g, t in sorted(trends.items(), key=lambda x: -x[1]['total']):
            layer_code = LAYERS.get(g, ('?',))[0]
            arrow_class = {'↑': 'up', '↓': 'down', '→': 'flat'}.get(t['trend'], 'flat')
            bar_pct = int(t['total'] / max_total * 100)
            bar_color = bar_colors.get(layer_code, '#999')
            html_out += f"""  <div class="trend-row">
    <span class="trend-name">{h(g)}</span>
    <span class="trend-count">{t['total']}</span>
    <span class="trend-arrow {arrow_class}">{t['trend']}</span>
    <div class="trend-bar"><div class="trend-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div></div>
  </div>
"""
        html_out += '</div>\n'

    html_out += f"""
<div class="footer">
  Radar · Mason Hub · 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
</div>
</body>
</html>"""

    return Response(html_out, content_type="text/html; charset=utf-8")


# --- Scout 情报简报 ---
INTEL_DIGESTS_DIR = Path(os.path.expanduser("~/mason-hub/intel/digests"))


def _render_markdown_to_html(md_text):
    """简易 Markdown → HTML 转换（标题/列表/粗体/链接/表格/分隔线）"""
    from html import escape as h
    lines = md_text.split('\n')
    html_lines = []
    in_table = False
    in_ul = False

    for line in lines:
        stripped = line.strip()

        # 表格
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            # 分隔行
            if all(set(c) <= set('-: ') for c in cells):
                continue
            if not in_table:
                html_lines.append('<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px;">')
                tag = 'th'
                in_table = True
            else:
                tag = 'td'
            row = ''.join(f'<{tag} style="border:1px solid #e5e7eb;padding:6px 10px;text-align:left;">{_inline_fmt(h(c))}</{tag}>' for c in cells)
            html_lines.append(f'<tr>{row}</tr>')
            continue
        elif in_table:
            html_lines.append('</table>')
            in_table = False

        # 空行结束列表
        if not stripped and in_ul:
            html_lines.append('</ul>')
            in_ul = False

        # 标题
        if stripped.startswith('# '):
            html_lines.append(f'<h1 style="font-size:22px;margin:20px 0 8px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">{_inline_fmt(h(stripped[2:]))}</h1>')
        elif stripped.startswith('## '):
            html_lines.append(f'<h2 style="font-size:17px;margin:18px 0 6px;color:#1a1a2e;">{_inline_fmt(h(stripped[3:]))}</h2>')
        elif stripped.startswith('### '):
            html_lines.append(f'<h3 style="font-size:14px;margin:14px 0 4px;color:#374151;">{_inline_fmt(h(stripped[4:]))}</h3>')
        elif stripped.startswith('- '):
            if not in_ul:
                html_lines.append('<ul style="margin:4px 0;padding-left:20px;">')
                in_ul = True
            html_lines.append(f'<li style="margin:3px 0;font-size:14px;line-height:1.6;">{_inline_fmt(h(stripped[2:]))}</li>')
        elif stripped == '':
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p style="margin:4px 0;font-size:14px;line-height:1.6;">{_inline_fmt(h(stripped))}</p>')

    if in_ul:
        html_lines.append('</ul>')
    if in_table:
        html_lines.append('</table>')

    return '\n'.join(html_lines)


def _inline_fmt(text):
    """处理行内格式：**粗体**、[链接](url)、`代码`"""
    import re as _re
    # 链接
    text = _re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" style="color:#1a73e8;">\1</a>', text)
    # 粗体
    text = _re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # 行内代码
    text = _re.sub(r'`([^`]+)`', r'<code style="background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:12px;">\1</code>', text)
    return text


@app.route("/intel")
@app.route("/intel/<date_str>")
def intel(date_str=None):
    """Scout 情报简报页面"""
    from html import escape as h

    if not INTEL_DIGESTS_DIR.exists():
        return Response("<h1>intel/digests/ 目录不存在</h1>", status=404,
                        content_type="text/html; charset=utf-8")

    # 列出所有简报文件（按修改时间倒序，确保最新生成的排第一）
    digest_files = sorted(INTEL_DIGESTS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not digest_files:
        return Response("<h1>暂无情报简报</h1>", status=404,
                        content_type="text/html; charset=utf-8")

    # 选择要显示的文件
    selected_file = None
    if date_str:
        for f in digest_files:
            if date_str in f.stem:
                selected_file = f
                break
    if not selected_file:
        selected_file = digest_files[0]

    md_content = selected_file.read_text(encoding='utf-8')
    body_html = _render_markdown_to_html(md_content)

    # 构建日期选择器
    file_options = ''
    for f in digest_files:
        label = f.stem
        sel = ' selected' if f == selected_file else ''
        file_options += f'<option value="{h(label)}"{sel}>{label}</option>\n'

    page = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar 情报 — {h(selected_file.stem)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .nav {{ background: #1e293b; padding: 12px 20px; display: flex; align-items: center; gap: 16px; font-family: system-ui, sans-serif; flex-wrap: wrap; }}
  .nav a {{ color: #60a5fa; text-decoration: none; font-size: 13px; }}
  .nav a:hover {{ text-decoration: underline; }}
  .nav span {{ color: #94a3b8; font-size: 13px; }}
  .nav select {{ background: #334155; color: #e2e8f0; border: 1px solid #475569; border-radius: 4px; padding: 4px 8px; font-size: 13px; }}
  .container {{ max-width: 760px; margin: 0 auto; padding: 16px; }}
  .content {{ background: #fff; border-radius: 12px; padding: 24px 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .footer {{ text-align: center; font-size: 11px; color: #bbb; padding: 16px; }}
</style>
</head>
<body>
<div class="nav">
  <a href="/">统一视图</a>
  <span>·</span>
  <a href="/hotlist">热榜原始</a>
  <span>·</span>
  <a href="/insights">趋势分析</a>
  <span>·</span>
  <span style="color:#e2e8f0;font-weight:600;">情报简报</span>
  <span>·</span>
  <select onchange="window.location='/intel/'+this.value">
    {file_options}
  </select>
</div>
<div class="container">
  <div class="content">
    {body_html}
  </div>
  <div class="footer">
    Radar · Mason Hub · Scout 情报系统
  </div>
</div>
</body>
</html>"""

    return Response(page, content_type="text/html; charset=utf-8")


if __name__ == "__main__":
    print("Radar Tracker starting on port 8081...")
    print("HTML source: " + TRENDRADAR_HTML)
    print("Database: " + DB_PATH)
    app.run(host="0.0.0.0", port=8081, debug=False)
