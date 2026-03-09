#!/usr/bin/env python3
"""memory-search.py — 从 ChromaDB 语义搜索相关经验

用法:
  python3 memory-search.py "搜索查询"                    # 搜索所有
  python3 memory-search.py "搜索查询" --agent EMP_0005   # 只搜特定 agent
  python3 memory-search.py "搜索查询" --top 3            # 返回 top 3
  python3 memory-search.py "搜索查询" --format inject    # 输出 prompt 注入格式
  python3 memory-search.py "搜索查询" --format json      # JSON 输出
  python3 memory-search.py "搜索查询" --scope cross      # 跨 agent 搜索
  python3 memory-search.py "搜索查询" --type long_term   # 按类型过滤

依赖: chromadb (在 ~/mason-hub/.venv 中)

退出码:
  0 — 找到结果
  1 — 未找到 / 数据库不存在 / 错误
"""

import sys
import json
import argparse
from pathlib import Path

HUB_DIR = Path.home() / "mason-hub"
CHROMA_DIR = HUB_DIR / "memory" / "chroma_db"

try:
    import chromadb
except ImportError:
    print("Error: chromadb not installed", file=sys.stderr)
    sys.exit(1)


def build_where_filter(agent: str = None, scope: str = None, doc_type: str = None) -> dict | None:
    """Build ChromaDB where filter from scope/agent/type parameters."""
    conditions = []

    # Scope filtering
    if scope == "own" and agent:
        conditions.append({"agent": agent})
    elif scope == "cross" and agent:
        # Others + global (exclude own agent)
        conditions.append({"agent": {"$ne": agent}})
    # scope == "all" or no scope: no agent filter

    # Agent filter (explicit --agent overrides scope)
    if agent and scope is None:
        conditions.append({"agent": agent})

    # Type filter
    if doc_type:
        conditions.append({"type": doc_type})

    if not conditions:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


def search(query: str, agent: str = None, top_k: int = 5, fmt: str = "text",
           scope: str = None, doc_type: str = None) -> bool:
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

    # Guard: empty collection
    if collection.count() == 0:
        print("Collection is empty. Run memory-store.py --rebuild first.", file=sys.stderr)
        return False

    # Build where filter
    where = build_where_filter(agent=agent, scope=scope, doc_type=doc_type)

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
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

    if fmt == "json":
        # JSON output
        items = []
        for doc, meta, dist in zip(docs, metas, distances):
            relevance = max(0, 1 - dist)
            if relevance < 0.3:
                continue
            items.append({
                "agent": meta.get("agent", "?"),
                "type": meta.get("type", "?"),
                "date": meta.get("date", "?"),
                "topic": meta.get("topic", "?"),
                "source": meta.get("source", "?"),
                "relevance": round(relevance, 3),
                "content": doc.strip(),
            })
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return len(items) > 0

    elif fmt == "inject":
        # Output format suitable for prompt injection
        print("## 相关历史经验（语义搜索结果）\n")
        found_any = False
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            relevance = max(0, 1 - dist)  # cosine distance to similarity
            if relevance < 0.3:  # skip low-relevance results
                continue
            found_any = True
            agent_name = meta.get("agent", "?")
            date = meta.get("date", "?")
            doc_type_label = meta.get("type", "?")
            source = meta.get("source", "?")
            # Extract just filename from source path
            source_short = Path(source).name if source != "?" else "?"
            print(f"### [{agent_name}] {date} ({doc_type_label}, {source_short}) (相关度: {relevance:.0%})")
            print(doc.strip())
            print()
        return found_any

    else:
        # Human-readable format
        print(f"Query: {query}")
        print(f"Results: {len(docs)}")
        if scope:
            print(f"Scope: {scope}")
        if doc_type:
            print(f"Type filter: {doc_type}")
        print()
        found_any = False
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            relevance = max(0, 1 - dist)
            agent_name = meta.get("agent", "?")
            date = meta.get("date", "?")
            topic = meta.get("topic", "?")
            doc_type_label = meta.get("type", "?")
            source = meta.get("source", "?")
            source_short = Path(source).name if source != "?" else "?"
            found_any = True
            print(f"  [{i+1}] {agent_name} | {date} | {topic} | {doc_type_label} | {source_short} | relevance: {relevance:.0%}")
            # Show first 2 lines of content
            lines = doc.strip().split("\n")
            for line in lines[:2]:
                print(f"      {line}")
            if len(lines) > 2:
                print(f"      ...")
            print()

        return found_any


def main():
    parser = argparse.ArgumentParser(description="Search agent memory via ChromaDB")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--agent", help="Filter by agent ID (e.g., EMP_0005)")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--format", choices=["text", "inject", "json"], default="text",
                        help="Output format: text (human readable), inject (for prompt), json")
    parser.add_argument("--scope", choices=["own", "all", "cross"],
                        help="Search scope: own (only requesting agent), all (everything), cross (others + global)")
    parser.add_argument("--type", dest="doc_type",
                        choices=["lesson", "long_term", "decision", "global"],
                        help="Filter by document type")
    args = parser.parse_args()

    found = search(args.query, agent=args.agent, top_k=args.top, fmt=args.format,
                   scope=args.scope, doc_type=args.doc_type)
    sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()
