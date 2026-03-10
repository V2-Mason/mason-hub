"""
Scout v2 — SQLite 数据库 schema 和操作函数

数据库文件: intel/scout.db
表结构参考 BettaFish daily_news/daily_topics/topic_news_relation，适配 Scout 情报管线。
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scout.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    domain TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    search_source TEXT DEFAULT 'github',
    reason TEXT,
    source TEXT DEFAULT 'auto',
    week TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(keyword, week)
);

CREATE TABLE IF NOT EXISTS intel_items (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    source TEXT,
    priority TEXT DEFAULT 'yellow',
    domain TEXT,
    digest_file TEXT,

    -- InsightEngine 附加
    relevance TEXT,
    internal_context TEXT,
    sentiment TEXT,
    sentiment_score REAL,

    -- ForumEngine 附加
    confidence TEXT,
    consensus TEXT,
    dissent TEXT,

    -- MediaEngine 附加
    image_analysis TEXT,

    -- 元数据
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS topic_intel_relation (
    topic_id INTEGER REFERENCES topics(id),
    intel_id TEXT REFERENCES intel_items(id),
    relevance_score REAL DEFAULT 0.5,
    PRIMARY KEY (topic_id, intel_id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    engines_completed TEXT,
    total_items INTEGER DEFAULT 0,
    report_path TEXT,
    error TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def init_db(db_path: str = None) -> sqlite3.Connection:
    """创建表并返回连接。db_path 默认 intel/scout.db。"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

def upsert_topics(conn: sqlite3.Connection, topics: list[dict]):
    """批量写入话题。冲突时更新 priority / reason / search_source。"""
    sql = """
        INSERT INTO topics (keyword, domain, priority, search_source, reason, source, week, created_at)
        VALUES (:keyword, :domain, :priority, :search_source, :reason, :source, :week, :created_at)
        ON CONFLICT(keyword, week) DO UPDATE SET
            priority = excluded.priority,
            reason = excluded.reason,
            search_source = excluded.search_source
    """
    now = _now_iso()
    rows = []
    for t in topics:
        rows.append({
            "keyword": t["keyword"],
            "domain": t.get("domain", "tech"),
            "priority": t.get("priority", "medium"),
            "search_source": t.get("search_source", "github"),
            "reason": t.get("reason"),
            "source": t.get("source", "auto"),
            "week": t["week"],
            "created_at": now,
        })
    conn.executemany(sql, rows)
    conn.commit()


# ---------------------------------------------------------------------------
# Intel Items
# ---------------------------------------------------------------------------

_INTEL_COLS = [
    "id", "date", "title", "summary", "url", "source", "priority", "domain",
    "digest_file", "relevance", "internal_context", "sentiment",
    "sentiment_score", "confidence", "consensus", "dissent", "image_analysis",
]


def upsert_intel_items(conn: sqlite3.Connection, items: list[dict]):
    """批量写入/更新情报条目。冲突时更新所有非主键字段。"""
    placeholders = ", ".join(f":{c}" for c in _INTEL_COLS)
    col_names = ", ".join(_INTEL_COLS)
    update_set = ", ".join(
        f"{c} = excluded.{c}" for c in _INTEL_COLS if c != "id"
    )

    sql = f"""
        INSERT INTO intel_items ({col_names}, created_at, updated_at)
        VALUES ({placeholders}, :created_at, :updated_at)
        ON CONFLICT(id) DO UPDATE SET
            {update_set},
            updated_at = excluded.updated_at
    """
    now = _now_iso()
    rows = []
    for item in items:
        row = {c: item.get(c) for c in _INTEL_COLS}
        row["created_at"] = now
        row["updated_at"] = now
        rows.append(row)
    conn.executemany(sql, rows)
    conn.commit()


# ---------------------------------------------------------------------------
# Topic ↔ Intel relation
# ---------------------------------------------------------------------------

def link_topic_intel(conn: sqlite3.Connection, topic_id: int, intel_id: str, score: float = 0.5):
    """关联话题与情报条目。冲突时更新 relevance_score。"""
    conn.execute(
        """
        INSERT INTO topic_intel_relation (topic_id, intel_id, relevance_score)
        VALUES (?, ?, ?)
        ON CONFLICT(topic_id, intel_id) DO UPDATE SET relevance_score = excluded.relevance_score
        """,
        (topic_id, intel_id, score),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_topics_for_week(conn: sqlite3.Connection, week: str) -> list[dict]:
    """获取指定周的所有话题。week 格式 '2026-W11'。"""
    rows = conn.execute(
        "SELECT * FROM topics WHERE week = ? ORDER BY priority DESC, id",
        (week,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_intel_items_for_date(conn: sqlite3.Connection, date: str) -> list[dict]:
    """获取指定日期的所有情报条目。date 格式 '2026-03-10'。"""
    rows = conn.execute(
        "SELECT * FROM intel_items WHERE date = ? ORDER BY priority DESC, id",
        (date,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Enrichment (InsightEngine / ForumEngine / MediaEngine)
# ---------------------------------------------------------------------------

_ENRICHMENT_FIELDS = {
    "relevance", "internal_context", "sentiment", "sentiment_score",
    "confidence", "consensus", "dissent", "image_analysis",
}


def update_intel_enrichment(conn: sqlite3.Connection, intel_id: str, **fields):
    """更新情报条目的 insight/forum/media 附加字段。"""
    valid = {k: v for k, v in fields.items() if k in _ENRICHMENT_FIELDS}
    if not valid:
        return
    set_clause = ", ".join(f"{k} = ?" for k in valid)
    values = list(valid.values()) + [_now_iso(), intel_id]
    conn.execute(
        f"UPDATE intel_items SET {set_clause}, updated_at = ? WHERE id = ?",
        values,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Migration from JSONL
# ---------------------------------------------------------------------------

def migrate_from_jsonl(conn: sqlite3.Connection, jsonl_path: str) -> int:
    """从 scout_normalized.jsonl 迁移数据到 intel_items 表。返回导入条数。"""
    path = Path(jsonl_path)
    if not path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            items.append({
                "id": raw["id"],
                "date": raw.get("date", ""),
                "title": raw.get("title", ""),
                "summary": raw.get("summary"),
                "url": raw.get("url"),
                "source": raw.get("source"),
                "priority": raw.get("priority", "yellow"),
                "domain": raw.get("domain"),
                "digest_file": raw.get("digest_file"),
                "relevance": raw.get("relevance"),
            })

    upsert_intel_items(conn, items)
    return len(items)


# ---------------------------------------------------------------------------
# Pipeline Runs
# ---------------------------------------------------------------------------

def log_pipeline_run(conn: sqlite3.Connection, run_id: str, **fields):
    """记录或更新管道执行。首次调用插入，后续调用按 run_id 更新。"""
    existing = conn.execute(
        "SELECT id FROM pipeline_runs WHERE run_id = ?", (run_id,)
    ).fetchone()

    if existing is None:
        conn.execute(
            """
            INSERT INTO pipeline_runs (run_id, date, status, started_at, finished_at,
                                       engines_completed, total_items, report_path, error)
            VALUES (:run_id, :date, :status, :started_at, :finished_at,
                    :engines_completed, :total_items, :report_path, :error)
            """,
            {
                "run_id": run_id,
                "date": fields.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "status": fields.get("status", "running"),
                "started_at": fields.get("started_at", _now_iso()),
                "finished_at": fields.get("finished_at"),
                "engines_completed": json.dumps(fields.get("engines_completed", [])),
                "total_items": fields.get("total_items", 0),
                "report_path": fields.get("report_path"),
                "error": fields.get("error"),
            },
        )
    else:
        update_parts = []
        values = []
        for k in ("date", "status", "finished_at", "total_items", "report_path", "error"):
            if k in fields:
                update_parts.append(f"{k} = ?")
                values.append(fields[k])
        if "engines_completed" in fields:
            update_parts.append("engines_completed = ?")
            values.append(json.dumps(fields["engines_completed"]))
        if update_parts:
            values.append(run_id)
            conn.execute(
                f"UPDATE pipeline_runs SET {', '.join(update_parts)} WHERE run_id = ?",
                values,
            )
    conn.commit()
