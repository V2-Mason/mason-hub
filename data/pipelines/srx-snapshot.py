#!/usr/bin/env python3
"""
素仁轩销售数据快照管道 — 定期快照 API 到时序 SQLite 表。

用法:
    python3 srx-snapshot.py                    # 正常快照
    python3 srx-snapshot.py --dry-run          # 只调 API 不写库
    python3 srx-snapshot.py --stats            # 显示历史统计
    python3 srx-snapshot.py --export-csv       # 导出 CSV

设计:
    - 调用 3 个 API 端点（sales/summary, dashboard/overview, risk-alerts）
    - 按日期存入 SQLite 时序表（每天最多 1 条，幂等）
    - 保留原始 JSON 响应（raw_response 字段），防信息丢失
    - 与 data-coo-daily.sh 共用认证逻辑但独立运行

维护者: EMP_0014
Schema: data/schemas/srx_sales_snapshot.yaml
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# =============================================================================
# 配置
# =============================================================================

# 数据库位置（GCP 本地，不依赖阿里云）
HUB_DIR = Path(os.environ.get('HUB_DIR', Path.home() / 'mason-hub'))
DB_PATH = HUB_DIR / 'data' / 'srx_history.db'

# API 配置
SRX_API = os.environ.get('SRX_API', 'http://106.14.44.68:8000')
TIMEOUT = 15  # 秒

# 时区
ET = timezone(timedelta(hours=-4))  # EDT


def log(msg):
    ts = datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')
    print(f"[{ts}] {msg}")


# =============================================================================
# 数据库初始化
# =============================================================================

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sales_snapshots (
    snapshot_id   TEXT PRIMARY KEY,
    snapshot_date TEXT NOT NULL,
    snapshot_ts   TEXT NOT NULL,
    total_revenue REAL,
    total_orders  INTEGER,
    raw_response  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_snapshots(snapshot_date);

CREATE TABLE IF NOT EXISTS dashboard_snapshots (
    snapshot_id     TEXT PRIMARY KEY,
    snapshot_date   TEXT NOT NULL,
    snapshot_ts     TEXT NOT NULL,
    total_inventory INTEGER,
    total_products  INTEGER,
    raw_response    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dash_date ON dashboard_snapshots(snapshot_date);

CREATE TABLE IF NOT EXISTS risk_snapshots (
    snapshot_id      TEXT PRIMARY KEY,
    snapshot_date    TEXT NOT NULL,
    snapshot_ts      TEXT NOT NULL,
    alert_count      INTEGER NOT NULL,
    expiring_count   INTEGER,
    low_stock_count  INTEGER,
    slow_moving_count INTEGER,
    raw_response     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_risk_date ON risk_snapshots(snapshot_date);

CREATE TABLE IF NOT EXISTS snapshot_meta (
    snapshot_date TEXT PRIMARY KEY,
    snapshot_ts   TEXT NOT NULL,
    status        TEXT NOT NULL,
    sales_ok      INTEGER DEFAULT 0,
    dashboard_ok  INTEGER DEFAULT 0,
    risk_ok       INTEGER DEFAULT 0,
    error_detail  TEXT
);
"""


def init_db():
    """创建数据库和表。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(CREATE_TABLES_SQL)
    conn.commit()
    return conn


# =============================================================================
# API 调用
# =============================================================================

def load_credentials():
    """从 .env 加载 API 凭证。"""
    env_file = HUB_DIR / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, _, val = line.partition('=')
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key in ('SRX_API_EMAIL', 'SRX_API_PASSWORD'):
                        os.environ.setdefault(key, val)

    email = os.environ.get('SRX_API_EMAIL')
    password = os.environ.get('SRX_API_PASSWORD')
    return email, password


def api_login(email, password):
    """JWT 登录，返回 token 或 None。"""
    try:
        payload = json.dumps({"email": email, "password": password}).encode()
        req = urllib.request.Request(
            f"{SRX_API}/api/auth/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read())
            return data.get("access_token", "")
    except Exception as e:
        log(f"Login failed: {e}")
        return None


def api_get(endpoint, token=None):
    """GET 请求，返回 (data_dict, raw_json_str) 或 (None, error_str)。"""
    url = f"{SRX_API}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode('utf-8')
            data = json.loads(raw)
            return data, raw
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, str(e)


# =============================================================================
# 快照逻辑
# =============================================================================

def snapshot_sales(conn, date_str, ts_str, token, dry_run=False):
    """快照 /api/sales/summary。"""
    sid = f"sales_{date_str}"

    # 幂等检查
    existing = conn.execute(
        "SELECT 1 FROM sales_snapshots WHERE snapshot_id = ?", (sid,)
    ).fetchone()
    if existing:
        log(f"  sales: 已存在 {sid}，跳过")
        return True

    data, raw = api_get("/api/sales/summary", token)
    if data is None:
        log(f"  sales: API 失败 — {raw}")
        return False

    # API 返回 {"data": {"revenue": ..., "order_count": ...}}
    inner = data.get('data', data) if isinstance(data, dict) else data
    revenue = inner.get('revenue', inner.get('total_revenue', inner.get('total')))
    orders = inner.get('order_count', inner.get('total_orders', inner.get('count')))

    if dry_run:
        log(f"  sales: [DRY RUN] revenue={revenue}, orders={orders}")
        return True

    conn.execute(
        "INSERT INTO sales_snapshots VALUES (?, ?, ?, ?, ?, ?)",
        (sid, date_str, ts_str, revenue, orders, raw),
    )
    log(f"  sales: revenue={revenue}, orders={orders}")
    return True


def snapshot_dashboard(conn, date_str, ts_str, token, dry_run=False):
    """快照 /api/dashboard/overview。"""
    sid = f"dash_{date_str}"

    existing = conn.execute(
        "SELECT 1 FROM dashboard_snapshots WHERE snapshot_id = ?", (sid,)
    ).fetchone()
    if existing:
        log(f"  dashboard: 已存在 {sid}，跳过")
        return True

    data, raw = api_get("/api/dashboard/overview", token)
    if data is None:
        log(f"  dashboard: API 失败 — {raw}")
        return False

    # API 返回 {"data": {"inventory": {...}, "inventory_value": {...}, ...}}
    inner = data.get('data', data) if isinstance(data, dict) else data
    # 计算总库存量：从 inventory 子对象汇总
    inv_obj = inner.get('inventory', {}) if isinstance(inner, dict) else {}
    if isinstance(inv_obj, dict):
        inventory = sum(v for v in inv_obj.values() if isinstance(v, (int, float)))
    else:
        inventory = inner.get('total_inventory', inner.get('inventory_count'))
    # 产品数：从 inventory_by_category 汇总或直接取
    cats = inner.get('inventory_by_category', [])
    if cats:
        products = sum(c.get('product_count', 0) for c in cats)
    else:
        products = inner.get('total_products', inner.get('product_count'))

    if dry_run:
        log(f"  dashboard: [DRY RUN] inventory={inventory}, products={products}")
        return True

    conn.execute(
        "INSERT INTO dashboard_snapshots VALUES (?, ?, ?, ?, ?, ?)",
        (sid, date_str, ts_str, inventory, products, raw),
    )
    log(f"  dashboard: inventory={inventory}, products={products}")
    return True


def snapshot_risk(conn, date_str, ts_str, token, dry_run=False):
    """快照 /api/intelligence/risk-alerts。"""
    sid = f"risk_{date_str}"

    existing = conn.execute(
        "SELECT 1 FROM risk_snapshots WHERE snapshot_id = ?", (sid,)
    ).fetchone()
    if existing:
        log(f"  risk: 已存在 {sid}，跳过")
        return True

    data, raw = api_get("/api/intelligence/risk-alerts", token)
    if data is None:
        log(f"  risk: API 失败 — {raw}")
        return False

    alerts = data if isinstance(data, list) else data.get('alerts', data.get('data', []))
    if not isinstance(alerts, list):
        alerts = [alerts] if alerts else []

    # 按 type 分类计数
    by_type = {}
    for a in alerts:
        t = a.get('type', a.get('alert_type', 'unknown'))
        by_type[t] = by_type.get(t, 0) + 1

    total = len(alerts)
    expiring = by_type.get('expiring', by_type.get('expiry_warning', 0))
    low_stock = by_type.get('low_stock', by_type.get('inventory_low', 0))
    slow_moving = by_type.get('slow_moving', 0)

    if dry_run:
        log(f"  risk: [DRY RUN] total={total}, expiring={expiring}, low_stock={low_stock}, slow_moving={slow_moving}")
        return True

    conn.execute(
        "INSERT INTO risk_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, date_str, ts_str, total, expiring, low_stock, slow_moving,
         json.dumps(alerts, ensure_ascii=False) if isinstance(data, list) else raw),
    )
    log(f"  risk: total={total}, expiring={expiring}, low_stock={low_stock}, slow_moving={slow_moving}")
    return True


def run_snapshot(dry_run=False):
    """执行完整快照。"""
    now = datetime.now(ET)
    date_str = now.strftime('%Y-%m-%d')
    ts_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    log(f"开始快照 — {date_str}")
    log(f"  DB: {DB_PATH}")

    # 加载凭证 & 登录
    email, password = load_credentials()
    if not email or not password:
        log("ERROR: SRX_API_EMAIL 或 SRX_API_PASSWORD 未配置")
        return False

    token = api_login(email, password)
    if not token:
        log("ERROR: JWT 登录失败，中止快照")
        return False

    log("  认证: OK")

    # 初始化数据库
    conn = init_db()

    # 执行 3 个端点快照
    sales_ok = snapshot_sales(conn, date_str, ts_str, token, dry_run)
    dash_ok = snapshot_dashboard(conn, date_str, ts_str, token, dry_run)
    risk_ok = snapshot_risk(conn, date_str, ts_str, token, dry_run)

    # 写元信息
    status = 'ok' if all([sales_ok, dash_ok, risk_ok]) else 'partial'
    errors = []
    if not sales_ok: errors.append('sales')
    if not dash_ok: errors.append('dashboard')
    if not risk_ok: errors.append('risk')

    if not dry_run:
        conn.execute(
            """INSERT OR REPLACE INTO snapshot_meta VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (date_str, ts_str, status,
             int(sales_ok), int(dash_ok), int(risk_ok),
             ','.join(errors) if errors else None),
        )
        conn.commit()

    conn.close()

    log(f"快照完成 — status={status}, sales={sales_ok}, dash={dash_ok}, risk={risk_ok}")
    return status == 'ok'


# =============================================================================
# 统计 & 导出
# =============================================================================

def show_stats():
    """显示快照历史统计。"""
    if not DB_PATH.exists():
        print("数据库不存在，尚无快照数据")
        return

    conn = sqlite3.connect(str(DB_PATH))

    for table, label in [
        ('sales_snapshots', '销售快照'),
        ('dashboard_snapshots', '仪表盘快照'),
        ('risk_snapshots', '风险快照'),
    ]:
        row = conn.execute(f"SELECT COUNT(*), MIN(snapshot_date), MAX(snapshot_date) FROM {table}").fetchone()
        count, first, last = row
        print(f"{label}: {count} 条, 范围 {first or 'N/A'} → {last or 'N/A'}")

    # 最近 7 天汇总
    print("\n最近 7 天销售趋势:")
    rows = conn.execute(
        "SELECT snapshot_date, total_revenue, total_orders FROM sales_snapshots ORDER BY snapshot_date DESC LIMIT 7"
    ).fetchall()
    if rows:
        for date, rev, orders in reversed(rows):
            rev_str = f"¥{rev:,.0f}" if rev else "N/A"
            ord_str = str(orders) if orders else "N/A"
            print(f"  {date}: {rev_str} ({ord_str} 单)")
    else:
        print("  (暂无数据)")

    conn.close()


def export_csv():
    """导出 CSV 格式。"""
    if not DB_PATH.exists():
        print("数据库不存在")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    print("date,revenue,orders,inventory,products,risk_total,risk_expiring,risk_low_stock,risk_slow_moving")
    rows = conn.execute("""
        SELECT
            s.snapshot_date,
            s.total_revenue,
            s.total_orders,
            d.total_inventory,
            d.total_products,
            r.alert_count,
            r.expiring_count,
            r.low_stock_count,
            r.slow_moving_count
        FROM sales_snapshots s
        LEFT JOIN dashboard_snapshots d ON s.snapshot_date = d.snapshot_date
        LEFT JOIN risk_snapshots r ON s.snapshot_date = r.snapshot_date
        ORDER BY s.snapshot_date
    """).fetchall()

    for r in rows:
        vals = [str(r[k] if r[k] is not None else '') for k in r.keys()]
        print(','.join(vals))

    conn.close()


# =============================================================================
# 入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='素仁轩销售数据快照')
    parser.add_argument('--dry-run', action='store_true', help='只调 API 不写库')
    parser.add_argument('--stats', action='store_true', help='显示历史统计')
    parser.add_argument('--export-csv', action='store_true', help='导出 CSV')
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.export_csv:
        export_csv()
    else:
        success = run_snapshot(dry_run=args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
