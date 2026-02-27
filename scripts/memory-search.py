#!/usr/bin/env python3
"""memory-search.py — 从 ChromaDB 语义搜索相关经验

用法:
  python3 memory-search.py "搜索查询"                    # 搜索所有
  python3 memory-search.py "搜索查询" --agent EMP_0005   # 只搜特定 agent
  python3 memory-search.py "搜索查询" --top 3            # 返回 top 3
  python3 memory-search.py "搜索查询" --format inject    # 输出 prompt 注入格式

依赖: chromadb (在 ~/mason-hub/.venv 中)

退出码:
  0 — 找到结果
  1 — 未找到 / 数据库不存在 / 错误
"""

import sys
import argparse
from pathlib import Path

HUB_DIR = Path.home() / "mason-hub"
CHROMA_DIR = HUB_DIR / "memory" / "chroma_db"

try:
    import chromadb
except ImportError:
    print("Error: chromadb not installed", file=sys.stderr)
    sys.exit(1)


def search(query: str, agent: str = None, top_k: int = 5, fmt: str = "text") -> bool:
    """Search ChromaDB for relevant memories."""
    if not CHROMA_DIR.exists():
        print("ChromaDB not initialized. Run memory-store.py first.", file=sys.stderr)
        return False

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        collection = client.get_collection("agent_memory")
    except Exception:
        print("Collection 'agent_memory' not found. Run memory-store.py first.", file=sys.stderr)
        return False

    # Build where filter
    where = None
    if agent:
        where = {"agent": agent}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    if not docs:
        if fmt == "text":
            print("No relevant memories found.")
        return False

    if fmt == "inject":
        # Output format suitable for prompt injection
        print("## 相关历史经验（语义搜索结果）\n")
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            relevance = max(0, 1 - dist)  # cosine distance to similarity
            if relevance < 0.3:  # skip low-relevance results
                continue
            agent_name = meta.get("agent", "?")
            date = meta.get("date", "?")
            print(f"### [{agent_name}] {date} (相关度: {relevance:.0%})")
            print(doc.strip())
            print()
    else:
        # Human-readable format
        print(f"Query: {query}")
        print(f"Results: {len(docs)}")
        print()
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            relevance = max(0, 1 - dist)
            agent_name = meta.get("agent", "?")
            date = meta.get("date", "?")
            topic = meta.get("topic", "?")
            doc_type = meta.get("type", "?")
            print(f"  [{i+1}] {agent_name} | {date} | {topic} | {doc_type} | relevance: {relevance:.0%}")
            # Show first 2 lines of content
            lines = doc.strip().split("\n")
            for line in lines[:2]:
                print(f"      {line}")
            if len(lines) > 2:
                print(f"      ...")
            print()

    return True


def main():
    parser = argparse.ArgumentParser(description="Search agent memory via ChromaDB")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--agent", help="Filter by agent ID (e.g., EMP_0005)")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--format", choices=["text", "inject"], default="text",
                        help="Output format: text (human readable) or inject (for prompt)")
    args = parser.parse_args()

    found = search(args.query, agent=args.agent, top_k=args.top, fmt=args.format)
    sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()
