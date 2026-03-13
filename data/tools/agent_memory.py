"""
agent_memory.py — v1.1 Agent 记忆 SDK

统一封装 session 读写、warm memory 读取、cold 语义搜索。
防止各组件各自实现内存读写导致不一致。

用法:
    from data.tools.agent_memory import write_session, read_warm, read_cold, list_sessions
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
AGENTS_DIR = HUB_DIR / "agents"
VENV_PYTHON = HUB_DIR / ".venv" / "bin" / "python3"

SCHEMA_VERSION = 1


def _agent_memory_dir(role_id: str) -> Path:
    return AGENTS_DIR / role_id / "memory"


def write_session(
    role_id: str,
    instance_id: str,
    task_id: str,
    status: str,
    content: str,
    started_at: str = "",
    ended_at: str = "",
    duration: int = 0,
    rounds: int = 0,
    account: str = "surenxuan",
    workflow_id: str = "",
    step_id: str = "",
) -> Path:
    """原子写入一个 session 文件。

    Returns:
        写入的文件路径
    """
    sessions_dir = _agent_memory_dir(role_id) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{instance_id}.md"

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter_lines = [
        "---",
        f"instance_id: {instance_id}",
        f"role_id: {role_id}",
        f"task_id: {task_id}",
        f"status: {status}",
        f"started_at: {started_at or now}",
        f"ended_at: {ended_at or now}",
        f"schema_version: {SCHEMA_VERSION}",
    ]
    if duration:
        frontmatter_lines.append(f"duration: {duration}")
    if rounds:
        frontmatter_lines.append(f"rounds: {rounds}")
    if account:
        frontmatter_lines.append(f"account: {account}")
    if workflow_id:
        frontmatter_lines.append(f"workflow_id: {workflow_id}")
    if step_id:
        frontmatter_lines.append(f"step_id: {step_id}")
    frontmatter_lines.append("---")

    full_content = "\n".join(frontmatter_lines) + "\n\n" + content + "\n"
    session_file.write_text(full_content, encoding="utf-8")
    return session_file


def list_sessions(
    role_id: str, limit: int = 10, days: int = 7
) -> list[dict]:
    """列出最近的 session 文件元数据。"""
    sessions_dir = _agent_memory_dir(role_id) / "sessions"
    if not sessions_dir.exists():
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)
    results = []

    files = sorted(sessions_dir.glob("session-*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[:limit]:
        meta = _parse_frontmatter(f)
        if meta:
            meta["file"] = str(f)
            results.append(meta)

    return results


def read_warm(role_id: str) -> str:
    """读取 warm.md 内容。"""
    warm_file = _agent_memory_dir(role_id) / "warm.md"
    if warm_file.exists():
        return warm_file.read_text(encoding="utf-8")
    return ""


def read_cold(role_id: str, query: str, top: int = 5) -> str:
    """语义搜索 cold 层（ChromaDB）。"""
    if not VENV_PYTHON.exists():
        # 回退：直接读 long_term.md 末尾
        lt_file = _agent_memory_dir(role_id) / "long_term.md"
        if lt_file.exists():
            lines = lt_file.read_text(encoding="utf-8").splitlines()
            return "\n".join(lines[-50:])
        return ""

    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(HUB_DIR / "scripts" / "memory-search.py"),
             query, "--scope", "all", "--top", str(top), "--format", "text"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, Exception):
        return ""


def archive_old_sessions(role_id: str, days: int = 30) -> int:
    """归档超过 N 天的 session 文件。

    Returns:
        归档的文件数
    """
    sessions_dir = _agent_memory_dir(role_id) / "sessions"
    if not sessions_dir.exists():
        return 0

    cutoff = datetime.utcnow() - timedelta(days=days)
    archived = 0

    for f in sessions_dir.glob("session-*.md"):
        # 从文件名提取日期
        parts = f.stem.split("-")
        if len(parts) >= 2:
            try:
                file_date = datetime.strptime(parts[1], "%Y%m%d")
                if file_date < cutoff:
                    archive_dir = _agent_memory_dir(role_id) / "archive" / file_date.strftime("%Y-%m")
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    f.rename(archive_dir / f.name)
                    archived += 1
            except ValueError:
                pass

    return archived


def _parse_frontmatter(filepath: Path) -> dict | None:
    """解析 session 文件的 YAML frontmatter。"""
    try:
        text = filepath.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return None
        end = text.index("---", 3)
        fm_text = text[3:end].strip()
        meta = {}
        for line in fm_text.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
        return meta
    except (ValueError, Exception):
        return None
