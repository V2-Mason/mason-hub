#!/usr/bin/env python3
"""memory-store.py — 将 lessons.md 内容存入 ChromaDB 向量数据库

用法:
  python3 memory-store.py [agent_id]        # 存储单个 agent
  python3 memory-store.py --all             # 存储所有 agent
  python3 memory-store.py --rebuild         # 重建整个数据库

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

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("Error: chromadb not installed. Run: source ~/mason-hub/.venv/bin/activate && pip install chromadb sentence-transformers")
    sys.exit(1)


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


def store_to_chroma(agent_id: str = None, rebuild: bool = False):
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

    all_docs = []
    all_ids = []
    all_metas = []

    # Collect lessons
    if agent_id and agent_id != "--all":
        files = [MEMORY_DIR / f"{agent_id}_lessons.md"]
    else:
        files = list(MEMORY_DIR.glob("*_lessons.md"))

    for f in files:
        if not f.exists():
            continue
        agent = f.stem.replace("_lessons", "")
        sections = parse_lessons(f)
        for i, s in enumerate(sections):
            doc_id = f"{agent}_lesson_{s['date']}_{i}"
            text = f"[{s['tag']}] {s['date']} {s['topic']}\n{s['body'].strip()}"
            all_docs.append(text)
            all_ids.append(doc_id)
            all_metas.append({
                "agent": agent,
                "type": s["tag"],
                "date": s["date"],
                "topic": s["topic"],
                "source": s["source"],
            })

    # Collect decisions
    decisions_file = DECISIONS_DIR / "decisions.md"
    if decisions_file.exists():
        sections = parse_decisions(decisions_file)
        for i, s in enumerate(sections):
            doc_id = f"decision_{s['date']}_{i}"
            all_docs.append(s["body"].strip())
            all_ids.append(doc_id)
            all_metas.append({
                "agent": "shared",
                "type": "decision",
                "date": s["date"],
                "topic": "project_decision",
                "source": str(decisions_file),
            })

    if not all_docs:
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

    print(f"Stored {len(all_docs)} documents in ChromaDB")
    print(f"  Lessons: {sum(1 for m in all_metas if m['type'] != 'decision')}")
    print(f"  Decisions: {sum(1 for m in all_metas if m['type'] == 'decision')}")
    print(f"  DB path: {CHROMA_DIR}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--all"

    if arg == "--rebuild":
        store_to_chroma(rebuild=True)
    elif arg == "--all":
        store_to_chroma()
    else:
        store_to_chroma(agent_id=arg)
