"""
数据中台 SDK — 业务 agent 一行代码获取干净数据。

用法示例:
    from data.tools.sdk import get_xhs_analysis, get_xhs_notes, get_scout_intel

    # XHS 互动分析（最新）
    report = get_xhs_analysis()
    print(report['meta']['total_notes'])

    # XHS 原始笔记（从本地镜像 SQLite）
    notes = get_xhs_notes(keywords=["韩国护肤"])
    for n in notes[:5]:
        print(n['title'], n['score'])

    # Scout 情报（仅红色优先级）
    red_intel = get_scout_intel(priority="red")

    # 通用：按 dataset_id 读取
    data = get_dataset("analysis_xhs_trends", date="latest")

维护者：EMP_0014
"""
from . import catalog
from . import readers
from .metrics import (
    parse_count,
    interaction_score,
    engage_rate,
    save_rate,
    share_rate,
    fake_traffic_flags,
)


class DataError(Exception):
    """数据读取错误基类。"""
    pass


class DatasetNotFoundError(DataError):
    """数据集在 catalog 中未注册。"""
    pass


class DataStaleError(DataError):
    """数据超过新鲜度阈值。"""
    pass


# =============================================================================
# 通用接口
# =============================================================================

def get_dataset(dataset_id, date='latest', **kwargs):
    """通用数据集读取器。

    根据 data_catalog.yaml 中注册的存储类型，自动选择读取方式。

    Args:
        dataset_id: catalog 中的数据集 ID
        date: "latest" 或 "YYYY-MM-DD"
        **kwargs: 传递给底层读取器的额外参数

    Returns:
        dict | list: 数据内容（格式取决于存储类型）

    Raises:
        DatasetNotFoundError: catalog 中无此数据集
        FileNotFoundError: 物理文件不存在
    """
    loc = catalog.resolve_location(dataset_id)
    if not loc:
        raise DatasetNotFoundError(f"数据集 '{dataset_id}' 未在 data_catalog.yaml 中注册")

    stype = loc['type']
    path = loc['path']
    table = loc['table']

    if stype == 'sqlite':
        query = kwargs.get('query')
        params = kwargs.get('params')
        return readers.read_sqlite(path, table, query=query, params=params)
    elif stype == 'json':
        return readers.read_json(path, date=date)
    elif stype == 'jsonl':
        filter_fn = kwargs.get('filter_fn')
        return readers.read_jsonl(path, filter_fn=filter_fn)
    elif stype == 'markdown_files':
        return readers.read_markdown_files(path)
    elif stype == 'api_response':
        raise DataError(
            f"数据集 '{dataset_id}' 是 API 类型，请使用专用函数（如 get_srx_sales）"
        )
    elif stype == 'stdout':
        raise DataError(
            f"数据集 '{dataset_id}' 无持久化存储（stdout），无法离线读取"
        )
    else:
        raise DataError(f"不支持的存储类型: {stype}")


def check_freshness(dataset_id, max_age_hours=None):
    """检查数据集新鲜度。

    Args:
        dataset_id: catalog 中的数据集 ID
        max_age_hours: 最大可接受年龄（小时），None 则用 catalog 中的预期频率推算

    Returns:
        dict: {"fresh": bool, "age_hours": float, "mtime": str}
    """
    loc = catalog.resolve_location(dataset_id)
    if not loc:
        raise DatasetNotFoundError(f"数据集 '{dataset_id}' 未在 data_catalog.yaml 中注册")

    # 默认 48 小时
    if max_age_hours is None:
        max_age_hours = 48

    path = loc['path']
    return readers.freshness_check(path, max_age_hours=max_age_hours)


# =============================================================================
# XHS 专用接口
# =============================================================================

def get_xhs_notes(keywords=None, min_score=0):
    """获取 XHS 笔记数据（从本地镜像 SQLite）。

    自动计算互动分、标记假流量。

    Args:
        keywords: 关键词列表过滤 source_keyword，None 返回全部
        min_score: 最低互动分过滤

    Returns:
        list[dict]: 按互动分降序排列的笔记列表，每条包含:
            note_id, title, desc, type, liked, collected, comment, shared,
            score, engage_rate, save_rate, share_rate, keyword, url,
            nickname, user_id, pub_date, fake_flags
    """
    loc = catalog.resolve_location('raw_xhs_notes')
    if not loc:
        raise DatasetNotFoundError("raw_xhs_notes 未在 catalog 中注册")

    # 构建 SQL
    where = ''
    params = ()
    if keywords:
        placeholders = ','.join('?' for _ in keywords)
        where = f'WHERE source_keyword IN ({placeholders})'
        params = tuple(keywords)

    rows = readers.read_sqlite(
        loc['path'], loc['table'],
        query=f'SELECT * FROM {loc["table"]} {where}',
        params=params,
    )

    import time
    from datetime import datetime

    notes = []
    for r in rows:
        liked = parse_count(r.get('liked_count'))
        collected = parse_count(r.get('collected_count'))
        comment = parse_count(r.get('comment_count'))
        shared = parse_count(r.get('share_count'))
        score = interaction_score(liked, collected, comment, shared)

        if score < min_score:
            continue

        # 时间戳处理
        ts = r.get('time')
        pub_date = ''
        post_age_days = -1
        if ts:
            try:
                ts_val = int(ts)
                if ts_val > 0:
                    ts_s = ts_val / 1000 if ts_val > 1e12 else ts_val
                    pub_date = datetime.fromtimestamp(ts_s).strftime('%Y-%m-%d')
                    post_age_days = round((time.time() - ts_s) / 86400)
            except (ValueError, TypeError):
                pass

        notes.append({
            'note_id': r.get('note_id', ''),
            'title': r.get('title', '') or '',
            'desc': r.get('desc', '') or '',
            'type': r.get('type', 'normal') or 'normal',
            'liked': liked,
            'collected': collected,
            'comment': comment,
            'shared': shared,
            'score': score,
            'engage_rate': engage_rate(comment, liked),
            'save_rate': save_rate(collected, liked),
            'share_rate': share_rate(shared, liked),
            'tags': r.get('tag_list', '') or '',
            'keyword': r.get('source_keyword', '') or '',
            'url': r.get('note_url', '') or '',
            'nickname': r.get('nickname', '') or '',
            'user_id': r.get('user_id', '') or '',
            'pub_date': pub_date,
            'post_age_days': post_age_days,
            'fake_flags': fake_traffic_flags(liked, collected, comment, shared),
        })

    notes.sort(key=lambda x: x['score'], reverse=True)
    return notes


def get_xhs_analysis(date='latest'):
    """获取 XHS 互动分析报告（爆帖排行 + 关键词洞察）。

    Args:
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        dict: 包含 meta, top_posts, keyword_insights, patterns, content_type,
              title_patterns, fake_traffic 等字段
    """
    return get_dataset('analysis_xhs_viral', date=date)


def get_xhs_trends(date='latest'):
    """获取 XHS 周度趋势对比。

    Args:
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        dict: 趋势对比数据
    """
    return get_dataset('analysis_xhs_trends', date=date)


def get_xhs_comments(date='latest'):
    """获取 XHS 评论洞察。

    Args:
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        dict: 评论分析数据（高频词、情绪信号等）
    """
    return get_dataset('analysis_xhs_comments', date=date)


def get_xhs_briefing(date='latest'):
    """获取 XHS 策略简报。

    Args:
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        dict: 策略建议（观察 + 假设 + 行动 + 置信度）
    """
    return get_dataset('report_strategy_briefing', date=date)


# =============================================================================
# Scout 情报接口
# =============================================================================

def get_scout_intel(priority=None, source=None):
    """获取 Scout 标准化情报。

    Args:
        priority: 过滤优先级（"red", "yellow", "green"），None 返回全部
        source: 过滤来源，None 返回全部

    Returns:
        list[dict]: 情报条目列表，每条包含:
            id, date, source, priority, title, summary, url,
            relevance, suggested_action, suggested_owner, digest_file
    """
    def filter_fn(item):
        if priority and item.get('priority') != priority:
            return False
        if source and item.get('source') != source:
            return False
        return True

    return get_dataset('clean_scout_intel', filter_fn=filter_fn)


# =============================================================================
# 素仁轩销售历史接口
# =============================================================================

def get_srx_history(days=30, metric='revenue'):
    """获取素仁轩销售历史时序数据（用于趋势分析）。

    Args:
        days: 最近 N 天，默认 30
        metric: 'revenue' | 'orders' | 'inventory' | 'risk' | 'all'

    Returns:
        list[dict]: 按日期升序排列的时序数据
            metric='revenue': [{"date": "2026-03-11", "revenue": 1234.5, "orders": 10}, ...]
            metric='inventory': [{"date": ..., "inventory": 100, "products": 50}, ...]
            metric='risk': [{"date": ..., "alert_count": 3, "expiring": 1, ...}, ...]
            metric='all': 包含所有字段的合并视图

    Raises:
        DataError: 数据库不存在或查询失败
    """
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent.parent / 'srx_history.db'
    if not db_path.exists():
        raise DataError("素仁轩历史数据库不存在，请先运行 data/pipelines/srx-snapshot.py")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    queries = {
        'revenue': (
            "SELECT snapshot_date AS date, total_revenue AS revenue, total_orders AS orders "
            "FROM sales_snapshots ORDER BY snapshot_date DESC LIMIT ?",
        ),
        'orders': (
            "SELECT snapshot_date AS date, total_revenue AS revenue, total_orders AS orders "
            "FROM sales_snapshots ORDER BY snapshot_date DESC LIMIT ?",
        ),
        'inventory': (
            "SELECT snapshot_date AS date, total_inventory AS inventory, total_products AS products "
            "FROM dashboard_snapshots ORDER BY snapshot_date DESC LIMIT ?",
        ),
        'risk': (
            "SELECT snapshot_date AS date, alert_count, expiring_count AS expiring, "
            "low_stock_count AS low_stock, slow_moving_count AS slow_moving "
            "FROM risk_snapshots ORDER BY snapshot_date DESC LIMIT ?",
        ),
        'all': (
            "SELECT s.snapshot_date AS date, s.total_revenue AS revenue, s.total_orders AS orders, "
            "d.total_inventory AS inventory, d.total_products AS products, "
            "r.alert_count, r.expiring_count AS expiring, r.low_stock_count AS low_stock, "
            "r.slow_moving_count AS slow_moving "
            "FROM sales_snapshots s "
            "LEFT JOIN dashboard_snapshots d ON s.snapshot_date = d.snapshot_date "
            "LEFT JOIN risk_snapshots r ON s.snapshot_date = r.snapshot_date "
            "ORDER BY s.snapshot_date DESC LIMIT ?",
        ),
    }

    if metric not in queries:
        conn.close()
        raise DataError(f"不支持的 metric: {metric}，可选: {', '.join(queries.keys())}")

    rows = conn.execute(queries[metric][0], (days,)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_srx_snapshot(date='latest'):
    """获取素仁轩某日的完整快照。

    Args:
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        dict: {
            "date": "2026-03-11",
            "sales": {"revenue": ..., "orders": ...},
            "dashboard": {"inventory": ..., "products": ...},
            "risk": {"alert_count": ..., "expiring": ..., ...},
            "raw": {"sales": {...}, "dashboard": {...}, "risk": {...}}
        }
    """
    import sqlite3
    import json as _json
    from pathlib import Path

    db_path = Path(__file__).parent.parent / 'srx_history.db'
    if not db_path.exists():
        raise DataError("素仁轩历史数据库不存在，请先运行 data/pipelines/srx-snapshot.py")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    if date == 'latest':
        row = conn.execute(
            "SELECT snapshot_date FROM sales_snapshots ORDER BY snapshot_date DESC LIMIT 1"
        ).fetchone()
        if not row:
            conn.close()
            raise DataError("无快照数据")
        date = row['snapshot_date']

    sales = conn.execute(
        "SELECT * FROM sales_snapshots WHERE snapshot_date = ?", (date,)
    ).fetchone()
    dash = conn.execute(
        "SELECT * FROM dashboard_snapshots WHERE snapshot_date = ?", (date,)
    ).fetchone()
    risk = conn.execute(
        "SELECT * FROM risk_snapshots WHERE snapshot_date = ?", (date,)
    ).fetchone()
    conn.close()

    if not sales and not dash and not risk:
        raise DataError(f"日期 {date} 无快照数据")

    result = {"date": date, "sales": {}, "dashboard": {}, "risk": {}, "raw": {}}
    if sales:
        result["sales"] = {"revenue": sales["total_revenue"], "orders": sales["total_orders"]}
        try:
            result["raw"]["sales"] = _json.loads(sales["raw_response"])
        except (ValueError, TypeError):
            pass
    if dash:
        result["dashboard"] = {"inventory": dash["total_inventory"], "products": dash["total_products"]}
        try:
            result["raw"]["dashboard"] = _json.loads(dash["raw_response"])
        except (ValueError, TypeError):
            pass
    if risk:
        result["risk"] = {
            "alert_count": risk["alert_count"],
            "expiring": risk["expiring_count"],
            "low_stock": risk["low_stock_count"],
            "slow_moving": risk["slow_moving_count"],
        }
        try:
            result["raw"]["risk"] = _json.loads(risk["raw_response"])
        except (ValueError, TypeError):
            pass

    return result


# =============================================================================
# TrendRadar 接口
# =============================================================================

def get_trendradar_news(date='latest'):
    """获取 TrendRadar 热榜新闻。

    Args:
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        list[dict]: 新闻条目（从 SQLite 读取）
    """
    loc = catalog.resolve_location('raw_trendradar_news')
    if not loc:
        raise DatasetNotFoundError("raw_trendradar_news 未在 catalog 中注册")

    path = loc['path']
    # TrendRadar 按日期分文件: output/news/YYYY-MM-DD.db
    if 'YYYY-MM-DD' in path:
        if date == 'latest':
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')
        path = path.replace('YYYY-MM-DD', date)

    return readers.read_sqlite(path, 'news_items')


# =============================================================================
# 数据目录查询
# =============================================================================

def list_datasets(status=None, owner=None):
    """列出已注册数据集。

    Args:
        status: "active", "planned", "stale", "deprecated"
        owner: 负责人 ID

    Returns:
        list[dict]: 数据集元信息列表
    """
    return catalog.list_datasets(status=status, owner=owner)


def dataset_info(dataset_id):
    """获取单个数据集的元信息。

    Returns:
        dict: catalog 中的完整定义
    """
    ds = catalog.get(dataset_id)
    if not ds:
        raise DatasetNotFoundError(f"数据集 '{dataset_id}' 未在 data_catalog.yaml 中注册")
    return ds
