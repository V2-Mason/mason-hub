"""
存储类型读取器 — 根据 catalog 中的 storage.type 读取数据。

支持: sqlite, json, jsonl, markdown_files, api_response
维护者：EMP_0014
"""
import json
import sqlite3
import glob
import os
from datetime import datetime, timedelta
from pathlib import Path


def _find_latest_dated_file(directory, ext='.json', date=None):
    """在目录中找到最新（或指定日期）的 YYYY-MM-DD 命名文件。

    Args:
        directory: 目录路径
        ext: 文件扩展名
        date: 指定日期字符串 "YYYY-MM-DD"，None 表示最新

    Returns:
        str: 文件路径，或 None
    """
    directory = str(directory)
    if not os.path.isdir(directory):
        return None

    if date and date != 'latest':
        # 精确匹配
        candidates = [
            os.path.join(directory, f'{date}{ext}'),
            os.path.join(directory, f'analysis_{date}{ext}'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    # 找最新: 按文件名倒排（YYYY-MM-DD 格式天然可排）
    pattern = os.path.join(directory, f'*{ext}')
    files = sorted(glob.glob(pattern), reverse=True)
    # 过滤出包含日期格式的文件
    import re
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    for f in files:
        if date_pattern.search(os.path.basename(f)):
            return f
    # 如果没有日期格式文件，返回最新修改的
    if files:
        return max(files, key=os.path.getmtime)
    return None


def read_sqlite(path, table, query=None, params=None):
    """读取 SQLite 表数据。

    Args:
        path: .db 文件路径
        table: 表名
        query: 自定义 SQL（可选，会覆盖默认的 SELECT *）
        params: SQL 参数元组

    Returns:
        list[dict]: 行数据列表
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQLite 文件不存在: {path}")

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if query:
        rows = cur.execute(query, params or ()).fetchall()
    else:
        rows = cur.execute(f'SELECT * FROM {table}').fetchall()

    result = [dict(row) for row in rows]
    conn.close()
    return result


def read_json(path_or_dir, date='latest'):
    """读取 JSON 分析文件。

    Args:
        path_or_dir: 文件路径或目录路径
            - 如果是文件: 直接读取
            - 如果是目录: 按日期查找 YYYY-MM-DD.json
        date: "latest" 或 "YYYY-MM-DD"

    Returns:
        dict: JSON 内容
    """
    path = str(path_or_dir)

    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    if os.path.isdir(path):
        target = _find_latest_dated_file(path, ext='.json', date=date)
        if not target:
            raise FileNotFoundError(f"目录 {path} 中无{'日期 ' + date if date != 'latest' else ''}匹配的 JSON 文件")
        with open(target, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 注入元信息
        if isinstance(data, dict):
            data.setdefault('_source_file', target)
        return data

    raise FileNotFoundError(f"路径不存在: {path}")


def read_jsonl(path, filter_fn=None):
    """读取 JSONL 文件（每行一个 JSON 对象）。

    Args:
        path: .jsonl 文件路径
        filter_fn: 可选过滤函数，接收 dict 返回 bool

    Returns:
        list[dict]
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"JSONL 文件不存在: {path}")

    results = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if filter_fn is None or filter_fn(item):
                    results.append(item)
            except json.JSONDecodeError:
                continue
    return results


def read_markdown_files(path):
    """读取目录下所有 markdown 文件。

    Args:
        path: 目录或单文件路径

    Returns:
        list[dict]: [{"filename": str, "content": str, "mtime": str}]
    """
    path = str(path)

    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [{
            'filename': os.path.basename(path),
            'content': content,
            'mtime': datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
        }]

    if not os.path.isdir(path):
        raise FileNotFoundError(f"路径不存在: {path}")

    results = []
    for fp in sorted(glob.glob(os.path.join(path, '*.md'))):
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        results.append({
            'filename': os.path.basename(fp),
            'content': content,
            'mtime': datetime.fromtimestamp(os.path.getmtime(fp)).isoformat(),
        })
    return results


def freshness_check(path, max_age_hours=48):
    """检查数据文件的新鲜度。

    Args:
        path: 文件路径
        max_age_hours: 最大可接受的文件年龄（小时）

    Returns:
        dict: {"fresh": bool, "age_hours": float, "mtime": str}
    """
    if not os.path.exists(path):
        return {'fresh': False, 'age_hours': -1, 'mtime': None, 'error': '文件不存在'}

    mtime = os.path.getmtime(path)
    age_hours = (datetime.now().timestamp() - mtime) / 3600
    return {
        'fresh': age_hours <= max_age_hours,
        'age_hours': round(age_hours, 1),
        'mtime': datetime.fromtimestamp(mtime).isoformat(),
    }
