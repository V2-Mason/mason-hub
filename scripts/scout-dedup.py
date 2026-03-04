#!/usr/bin/env python3
"""Scout dedup — 情报去重工具

Usage:
    python3 scout-dedup.py --check "owner/repo" 1234
    python3 scout-dedup.py --update "owner/repo" 1234

check: 返回 "new" / "trending" / "known" (exit code: 0=new, 1=trending, 2=known)
update: 写入/更新 seen.jsonl
"""
import argparse
import json
import os
import sys
from datetime import date

SEEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "intel", "seen.jsonl")


def load_seen() -> dict:
    """Load seen.jsonl into {repo: record} dict."""
    records = {}
    if not os.path.exists(SEEN_FILE):
        return records
    with open(SEEN_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records[rec["repo"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    return records


def save_seen(records: dict):
    """Rewrite seen.jsonl from records dict."""
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        for rec in sorted(records.values(), key=lambda r: r.get("repo", "")):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def check(repo: str, stars: int) -> str:
    """Check if repo is new/trending/known."""
    records = load_seen()
    if repo not in records:
        return "new"
    old_stars = records[repo].get("last_stars", 0)
    if old_stars > 0 and stars > 0 and (stars - old_stars) / old_stars > 0.20:
        return "trending"
    return "known"


def update(repo: str, stars: int):
    """Update seen.jsonl with repo."""
    records = load_seen()
    today = date.today().isoformat()
    if repo in records:
        records[repo]["last_stars"] = stars
        records[repo]["last_seen"] = today
    else:
        records[repo] = {
            "repo": repo,
            "first_seen": today,
            "last_stars": stars,
            "last_seen": today,
        }
    save_seen(records)


def main():
    parser = argparse.ArgumentParser(description="Scout dedup tool")
    parser.add_argument("--check", nargs=2, metavar=("REPO", "STARS"), help="Check repo status")
    parser.add_argument("--update", nargs=2, metavar=("REPO", "STARS"), help="Update repo in seen.jsonl")
    args = parser.parse_args()

    if args.check:
        repo, stars = args.check[0], int(args.check[1])
        result = check(repo, stars)
        print(result)
        if result == "new":
            # Auto-update on first check
            update(repo, stars)
            sys.exit(0)
        elif result == "trending":
            update(repo, stars)
            sys.exit(1)
        else:
            sys.exit(2)

    elif args.update:
        repo, stars = args.update[0], int(args.update[1])
        update(repo, stars)
        print(f"updated: {repo} ({stars} stars)")

    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
