#!/usr/bin/env python3
"""
初始化视频复盘 SQLite 数据库

用法:
  python scripts/video_review/db_init.py
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/data/video-reviews/reviews.db")
SCHEMA_PATH = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/data/video-reviews/schema.sql")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn.executescript(schema)
    conn.commit()

    # 验证
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' OR type='view' ORDER BY name"
    ).fetchall()

    print(f"Database initialized at: {DB_PATH}")
    print(f"\nTables and views created:")
    for (name,) in tables:
        print(f"  - {name}")

    conn.close()


if __name__ == "__main__":
    init_db()
