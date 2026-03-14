#!/usr/bin/env python3
"""memory-router.py — Memory Entry 写入归属判定器

根据 agent_scope + account_scope 自动路由到正确的 Pipe：
- agent + account → Pipe 3 (accounts/{account}/memory/{agent}.md)
- agent only → Pipe 1 (agents/{agent}/memory/memory.md)
- account only → Pipe 2 (accounts/{account}/shared.md)
- neither → Pipe 4 (全局，写到 memory_pending.jsonl 让人判定)

用法：
  echo '{"content":"经验","agent_scope":"EMP_0002","account_scope":"surenxuan"}' | python3 scripts/memory-router.py
  python3 scripts/memory-router.py --file data/memory_pending.jsonl --process
"""

import argparse
import json
import os
import sys
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))


def route_entry(entry: dict, dry_run: bool = False) -> dict:
    agent = entry.get("agent_scope") or ""
    account = entry.get("account_scope") or ""
    content = entry.get("content", "")
    source = entry.get("source_task", "")

    if agent and account:
        pipe = 3
        target = HUB_DIR / "accounts" / account / "memory" / f"{agent}.md"
    elif agent:
        pipe = 1
        target = HUB_DIR / "agents" / agent / "memory" / "memory.md"
    elif account:
        pipe = 2
        target = HUB_DIR / "accounts" / account / "shared.md"
    else:
        pipe = 4
        target = HUB_DIR / "data" / "memory_pending.jsonl"

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix == ".jsonl":
            with open(target, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        else:
            with open(target, "a") as f:
                f.write(f"- {content}\n")

    return {
        "pipe": pipe,
        "target": str(target.relative_to(HUB_DIR)),
        "content_preview": content[:60],
        "routed": not dry_run,
    }


def process_pending(dry_run: bool = False):
    """处理 memory_pending.jsonl 中的条目（需要人工确认归属）"""
    pending_file = HUB_DIR / "data" / "memory_pending.jsonl"
    if not pending_file.exists():
        print(json.dumps({"status": "no_pending_entries"}))
        return

    entries = []
    with open(pending_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    print(json.dumps({
        "pending_count": len(entries),
        "entries": [
            {"content": e.get("content", "")[:80], "source": e.get("source_task", "")}
            for e in entries
        ]
    }, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Memory 写入路由")
    parser.add_argument("--file", help="从文件读取 JSONL 条目")
    parser.add_argument("--process", action="store_true", help="显示 pending 条目")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.process:
        process_pending(args.dry_run)
        return

    if args.file:
        with open(args.file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    result = route_entry(entry, args.dry_run)
                    print(json.dumps(result, ensure_ascii=False))
    else:
        # 从 stdin 读单条
        data = sys.stdin.read().strip()
        if data:
            entry = json.loads(data)
            result = route_entry(entry, args.dry_run)
            print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
