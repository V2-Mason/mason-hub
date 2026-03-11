#!/usr/bin/env python3
"""memory-store.py — 将 agent 记忆内容存入 ChromaDB 向量数据库

用法:
  python3 memory-store.py [agent_id]        # 存储单个 agent
  python3 memory-store.py --all             # 存储所有 agent
  python3 memory-store.py --rebuild         # 重建整个数据库
  python3 memory-store.py --incremental     # 只索引有变更的文件

数据源:
  1. memory/*_lessons.md           — agent lessons (existing)
  2. domains/ecommerce/.../decisions.md — project decisions (existing)
  3. agents/EMP_*/memory/long_term.md  — agent long-term memory (new)
  4. ~/.claude/projects/-home-hangn-mason-hub/memory/*.md — global memory (new)

依赖: chromadb, sentence-transformers (在 ~/mason-hub/.venv 中)
"""

import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

HUB_DIR = Path.home() / "mason-hub"
MEMORY_DIR = HUB_DIR / "memory"
CHROMA_DIR = MEMORY_DIR / "chroma_db"
DECISIONS_DIR = HUB_DIR / "domains" / "ecommerce" / "projects" / "srx"
LONG_TERM_DIR = HUB_DIR / "agents"
GLOBAL_MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-hangn-mason-hub" / "memory"
LAST_INDEXED_FILE = CHROMA_DIR / ".last_indexed"

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("Error: chromadb not installed. Run: source ~/mason-hub/.venv/bin/activate && pip install chromadb sentence-transformers")
    sys.exit(1)


def load_last_indexed() -> dict:
    """Load {filepath: mtime} mapping from last indexing run."""
    if not LAST_INDEXED_FILE.exists():
        return {}
    try:
        return json.loads(LAST_INDEXED_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_last_indexed(indexed: dict):
    """Save {filepath: mtime} mapping."""
    LAST_INDEXED_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_INDEXED_FILE.write_text(json.dumps(indexed, indent=2))


def file_needs_reindex(filepath: Path, last_indexed: dict) -> bool:
    """Check if file has been modified since last indexing."""
    if not filepath.exists():
        return False
    current_mtime = filepath.stat().st_mtime
    prev_mtime = last_indexed.get(str(filepath), 0)
    return current_mtime > prev_mtime


def parse_lessons(filepath: Path) -> list[dict]:
    """Parse a lessons.md file into sections."""
    if not filepath.exists() or filepath.stat().st_size == 0:
        return []

    content = filepath.read_text()
    sections = []
    current = None

    for line in content.split("\n"):
        # Match: ## 2026-02-27: module_name or ## [COMPACTED] ... or ## [FAILED] ...
        m = re.match(r"^## (?:\[(\w+)\] )?(\d{4}-\d{2}-\d{2})?:?\s*(.*)", line)
        if m:
            if current and current["body"].strip():
                sections.append(current)
            tag = m.group(1) or "lesson"
            date_str = m.group(2) or ""
            topic = m.group(3) or "general"
            current = {
                "tag": tag,
                "date": date_str,
                "topic": topic.strip(),
                "body": "",
                "source": str(filepath),
            }
        elif current is not None:
            current["body"] += line + "\n"

    if current and current["body"].strip():
        sections.append(current)

    return sections


def parse_decisions(filepath: Path) -> list[dict]:
    """Parse a decisions.md file into entries."""
    if not filepath.exists():
        return []

    content = filepath.read_text()
    sections = []
    current = None

    for line in content.split("\n"):
        m = re.match(r"^\[(\d{4}-\d{2}-\d{2})\]", line)
        if m:
            if current and current["body"].strip():
                sections.append(current)
            current = {
                "tag": "decision",
                "date": m.group(1),
                "topic": "decision",
                "body": "",
                "source": str(filepath),
            }
        elif current is not None:
            current["body"] += line + "\n"
        # Lines before first [date] are ignored (headers)

    if current and current["body"].strip():
        sections.append(current)

    return sections


def parse_long_term(filepath: Path) -> list[dict]:
    """Parse an agent long_term.md file into sections using ## headers as chunk boundaries."""
    if not filepath.exists() or filepath.stat().st_size == 0:
        return []

    content = filepath.read_text()
    sections = []
    current = None

    for line in content.split("\n"):
        # Match ## headers (but not # top-level header)
        m = re.match(r"^## (.+)", line)
        if m:
            if current and current["body"].strip():
                sections.append(current)
            header = m.group(1).strip()
            # Try to extract date from header like "## Topic (2026-02-28, ...)"
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", header)
            date_str = date_match.group(1) if date_match else ""
            # Clean topic: remove date parenthetical
            topic = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}[^)]*\)", "", header).strip()
            current = {
                "tag": "long_term",
                "date": date_str,
                "topic": topic,
                "body": "",
                "source": str(filepath),
            }
        elif current is not None:
            current["body"] += line + "\n"

    if current and current["body"].strip():
        sections.append(current)

    return sections


def parse_global_memory(filepath: Path) -> list[dict]:
    """Parse a global memory .md file into sections using ## headers as chunk boundaries."""
    if not filepath.exists() or filepath.stat().st_size == 0:
        return []

    content = filepath.read_text()
    sections = []
    current = None

    for line in content.split("\n"):
        m = re.match(r"^## (.+)", line)
        if m:
            if current and current["body"].strip():
                sections.append(current)
            header = m.group(1).strip()
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", header)
            date_str = date_match.group(1) if date_match else ""
            topic = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}[^)]*\)", "", header).strip()
            current = {
                "tag": "global",
                "date": date_str,
                "topic": topic,
                "body": "",
                "source": str(filepath),
            }
        elif current is not None:
            current["body"] += line + "\n"

    if current and current["body"].strip():
        sections.append(current)

    return sections


def collect_all_sources(agent_id: str = None) -> list[tuple[Path, str]]:
    """Return list of (filepath, source_type) for all indexable files."""
    sources = []

    # 1. Lessons files
    if agent_id and agent_id not in ("--all", "--rebuild", "--incremental"):
        lesson_files = [MEMORY_DIR / f"{agent_id}_lessons.md"]
    else:
        lesson_files = list(MEMORY_DIR.glob("*_lessons.md"))
    for f in lesson_files:
        if f.exists():
            sources.append((f, "lesson"))

    # 2. Decisions file
    decisions_file = DECISIONS_DIR / "decisions.md"
    if decisions_file.exists():
        sources.append((decisions_file, "decision"))

    # 3. Agent long-term memory files
    if LONG_TERM_DIR.exists():
        for lt_file in sorted(LONG_TERM_DIR.glob("EMP_*/memory/long_term.md")):
            sources.append((lt_file, "long_term"))

    # 4. Global memory files
    if GLOBAL_MEMORY_DIR.exists():
        for gm_file in sorted(GLOBAL_MEMORY_DIR.glob("*.md")):
            sources.append((gm_file, "global"))

    return sources


def parse_file(filepath: Path, source_type: str) -> tuple[list[str], list[str], list[dict]]:
    """Parse a file and return (docs, ids, metas) tuples."""
    docs, ids, metas = [], [], []

    if source_type == "lesson":
        agent = filepath.stem.replace("_lessons", "")
        sections = parse_lessons(filepath)
        for i, s in enumerate(sections):
            doc_id = f"{agent}_lesson_{s['date']}_{i}"
            text = f"[{s['tag']}] {s['date']} {s['topic']}\n{s['body'].strip()}"
            docs.append(text)
            ids.append(doc_id)
            metas.append({
                "agent": agent,
                "type": s["tag"],
                "date": s["date"],
                "topic": s["topic"],
                "source": s["source"],
            })

    elif source_type == "decision":
        sections = parse_decisions(filepath)
        for i, s in enumerate(sections):
            doc_id = f"decision_{s['date']}_{i}"
            docs.append(s["body"].strip())
            ids.append(doc_id)
            metas.append({
                "agent": "shared",
                "type": "decision",
                "date": s["date"],
                "topic": "project_decision",
                "source": str(filepath),
            })

    elif source_type == "long_term":
        # Extract agent ID from path: agents/EMP_XXXX/memory/long_term.md
        agent = filepath.parent.parent.name  # e.g., EMP_0005
        sections = parse_long_term(filepath)
        for i, s in enumerate(sections):
            doc_id = f"{agent}_longterm_{s['topic'][:30]}_{i}"
            # Sanitize id (ChromaDB requires no special chars issues)
            doc_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", doc_id)
            text = f"[long_term] {agent} {s['topic']}\n{s['body'].strip()}"
            docs.append(text)
            ids.append(doc_id)
            metas.append({
                "agent": agent,
                "type": "long_term",
                "date": s["date"],
                "topic": s["topic"],
                "source": s["source"],
            })

    elif source_type == "global":
        sections = parse_global_memory(filepath)
        for i, s in enumerate(sections):
            fname = filepath.stem  # e.g., MEMORY, trendradar
            doc_id = f"global_{fname}_{s['topic'][:30]}_{i}"
            doc_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", doc_id)
            text = f"[global] {s['topic']}\n{s['body'].strip()}"
            docs.append(text)
            ids.append(doc_id)
            metas.append({
                "agent": "global",
                "type": "global",
                "date": s["date"],
                "topic": s["topic"],
                "source": s["source"],
            })

    return docs, ids, metas


def store_to_chroma(agent_id: str = None, rebuild: bool = False, incremental: bool = False):
    """Store memory entries into ChromaDB."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if rebuild:
        # Delete and recreate collection
        try:
            client.delete_collection("agent_memory")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name="agent_memory",
        metadata={"hnsw:space": "cosine"},
    )

    last_indexed = load_last_indexed() if incremental else {}
    new_indexed = {}

    all_docs = []
    all_ids = []
    all_metas = []

    sources = collect_all_sources(agent_id)
    skipped = 0

    for filepath, source_type in sources:
        if not filepath.exists():
            continue

        # Incremental: skip files that haven't changed
        if incremental and not file_needs_reindex(filepath, last_indexed):
            skipped += 1
            new_indexed[str(filepath)] = last_indexed.get(str(filepath), 0)
            continue

        docs, ids, metas = parse_file(filepath, source_type)
        all_docs.extend(docs)
        all_ids.extend(ids)
        all_metas.extend(metas)

        # Record mtime for incremental tracking
        new_indexed[str(filepath)] = filepath.stat().st_mtime

    if not all_docs:
        if incremental and skipped > 0:
            print(f"No changes detected ({skipped} files up-to-date)")
            # Preserve existing indexed timestamps
            save_last_indexed({**last_indexed, **new_indexed})
        else:
            print("No documents to store")
        return

    # Upsert in batches (ChromaDB limit is ~5000 per batch)
    batch_size = 100
    for i in range(0, len(all_docs), batch_size):
        batch_docs = all_docs[i:i + batch_size]
        batch_ids = all_ids[i:i + batch_size]
        batch_metas = all_metas[i:i + batch_size]
        collection.upsert(
            documents=batch_docs,
            ids=batch_ids,
            metadatas=batch_metas,
        )

    # Count by type
    type_counts = {}
    for m in all_metas:
        t = m["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"Stored {len(all_docs)} documents in ChromaDB")
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")
    if incremental and skipped > 0:
        print(f"  Skipped (unchanged): {skipped} files")
    print(f"  Total in collection: {collection.count()}")
    print(f"  DB path: {CHROMA_DIR}")

    # Save indexed timestamps (merge with previous for incremental)
    if incremental:
        save_last_indexed({**last_indexed, **new_indexed})
    else:
        save_last_indexed(new_indexed)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Store agent memory into ChromaDB")
    parser.add_argument("agent_id", nargs="?", default=None,
                        help="Agent ID (e.g., EMP_0005) or omit for all")
    parser.add_argument("--all", action="store_true", help="Index all agents")
    parser.add_argument("--rebuild", action="store_true", help="Full re-index (delete + recreate)")
    parser.add_argument("--incremental", action="store_true",
                        help="Only re-index files changed since last run")
    args = parser.parse_args()

    if args.rebuild:
        store_to_chroma(rebuild=True)
    elif args.incremental:
        store_to_chroma(incremental=True)
    elif args.all or args.agent_id is None:
        store_to_chroma()
    else:
        store_to_chroma(agent_id=args.agent_id)
