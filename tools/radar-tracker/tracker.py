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
RETIRE_THRESHOLD = float(os.environ.get("RETIRE_THRESHOLD", "0.5"))


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


def inject_dismiss_buttons(raw_html):
    """在每条新闻/RSS 条目旁注入 dismiss 按钮，并自动隐藏已标记无用的条目。"""

    dismissed_set = _load_dismissed_titles()

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

    # 5) Inject dismiss buttons into news-items, hide already-dismissed
    def _inject_news_btn(m):
        block = m.group(0)
        title_m = re.search(r'class="news-link"[^>]*>([^<]+)</a>', block)
        title = title_m.group(1).strip() if title_m else ""
        src_m = re.search(r'class="source-name"[^>]*>([^<]+)</span>', block)
        source = src_m.group(1).strip() if src_m else ""
        # 已 dismiss 的条目直接隐藏
        if _is_dismissed(title, dismissed_set):
            return ""
        btn = _make_dismiss_btn(title, source)
        idx = block.rfind("</div>")
        return block[:idx] + btn + block[idx:]

    raw_html = re.sub(
        r'<div class="news-item[^"]*">\s*<div class="news-number">'
        r'.*?</div>\s*<div class="news-content">.*?</div>\s*</div>',
        _inject_news_btn,
        raw_html,
        flags=re.DOTALL,
    )

    # 6) Inject dismiss buttons into RSS items, hide already-dismissed
    def _inject_rss_btn(m):
        block = m.group(0)
        title_m = re.search(r'class="rss-link"[^>]*>([^<]+)</a>', block)
        title = title_m.group(1).strip() if title_m else ""
        author_m = re.search(r'class="rss-author"[^>]*>([^<]+)</span>', block)
        source = author_m.group(1).strip() if author_m else ""
        if _is_dismissed(title, dismissed_set):
            return ""
        btn = _make_dismiss_btn(title, source)
        idx = block.rfind("</div>")
        return block[:idx] + btn + block[idx:]

    raw_html = re.sub(
        r'<div class="rss-item">\s*<div class="rss-meta">.*?</div>\s*'
        r'<div class="rss-title">.*?</div>\s*</div>',
        _inject_rss_btn,
        raw_html,
        flags=re.DOTALL,
    )

    # 7) 注入已过滤条数提示
    hidden_count = len(dismissed_set)
    if hidden_count > 0:
        badge = (
            '<div style="background:#1e293b;padding:8px 20px;font-family:system-ui,sans-serif;'
            'font-size:13px;color:#94a3b8;">'
            '已过滤 ' + str(hidden_count) + ' 个标记无用的话题 · '
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
def index():
    """代理展示最新 TrendRadar HTML 报告，注入 dismiss 按钮。"""
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


@app.route("/api/dismiss", methods=["POST"])
def dismiss():
    """接收 dismiss 标记，写入 SQLite。"""
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400
    keyword_group = (data.get("keyword_group") or "").strip()
    source = (data.get("source") or "").strip()

    conn = get_db()
    conn.execute(
        "INSERT INTO dismissals (news_title, keyword_group, source) VALUES (?, ?, ?)",
        (title, keyword_group, source),
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


@app.route("/api/weekly-report")
def weekly_report():
    """
    返回关注率报告。
    连续两周每周 dismiss >= 3 条的关键词组建议淘汰。
    ?weeks=N 可指定回看周数（默认 2）。
    """
    weeks = int(request.args.get("weeks", 2))
    conn = get_db()

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

    suggest_retire = []
    if len(report_weeks) >= 2:
        w0 = report_weeks[0]["dismissals_by_group"]
        w1 = report_weeks[1]["dismissals_by_group"]
        all_kw = set(list(w0.keys()) + list(w1.keys()))
        for kw in all_kw:
            d0 = w0.get(kw, 0)
            d1 = w1.get(kw, 0)
            if d0 >= 3 and d1 >= 3:
                suggest_retire.append({
                    "keyword_group": kw,
                    "recent_week_dismissed": d0,
                    "prev_week_dismissed": d1,
                    "reason": "连续两周每周被标记 >=3 条无用",
                })

    return jsonify({
        "threshold": RETIRE_THRESHOLD,
        "weeks": report_weeks,
        "all_time": {
            r["keyword_group"]: r["total_dismissed"] for r in all_groups
        },
        "suggest_retire": suggest_retire,
    })


if __name__ == "__main__":
    print("Radar Tracker starting on port 8081...")
    print("HTML source: " + TRENDRADAR_HTML)
    print("Database: " + DB_PATH)
    app.run(host="0.0.0.0", port=8081, debug=False)
