"""
平台文档变更检测 — 对比两次爬取的文档内容，输出变更摘要

用法:
  python skills/_platform_doc_diff.py [--platform xhs|wechat-store] [--output json|text]

功能:
  1. 读取 index.json 和 .content_hashes.json
  2. 对比当前文件内容 vs 上次记录的 hash
  3. 检测：新增文档、内容变更、删除文档
  4. 输出结构化变更报告
  5. 重点标注规则中心 + 平台公告变更（影响运营）
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))

PLATFORMS = {
    "xhs": {
        "name": "小红书开放平台",
        "base_dir": Path("intel/raw/xhs-docs"),
        "critical_categories": ["规则中心", "平台公告", "产品发布", "技术变更", "其他公告"],
    },
    "wechat-store": {
        "name": "微信小店",
        "base_dir": Path("intel/raw/wechat-store-docs"),
        "critical_categories": ["规则中心", "平台公告", "成长中心"],
    },
    # Future: douyin, etc.
}


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def diff_platform(platform_key: str) -> dict:
    """Detect changes for a platform's docs."""
    config = PLATFORMS[platform_key]
    base_dir = config["base_dir"]
    hash_file = base_dir / ".content_hashes.json"
    index_file = base_dir / "index.json"

    # Load old hashes
    old_hashes = {}
    if hash_file.exists():
        old_hashes = json.loads(hash_file.read_text())

    # Load index
    index = {"pages": []}
    if index_file.exists():
        index = json.loads(index_file.read_text())

    # Compute current hashes for all md files
    current_hashes = {}
    current_files = {}
    for md_file in base_dir.rglob("*.md"):
        if md_file.name.startswith(".") or md_file.name == "小红书开放平台API完整文档.md":
            continue
        rel = str(md_file.relative_to(base_dir))
        text = md_file.read_text(encoding="utf-8", errors="replace")
        current_hashes[rel] = content_hash(text)
        current_files[rel] = {
            "path": str(md_file),
            "size": len(text),
            "title": md_file.stem,
        }

    # Detect changes
    new_files = []
    changed_files = []
    deleted_files = []

    for rel, h in current_hashes.items():
        if rel not in old_hashes:
            new_files.append({"path": rel, **current_files[rel]})
        elif old_hashes[rel] != h:
            changed_files.append({"path": rel, **current_files[rel]})

    for rel in old_hashes:
        if rel not in current_hashes:
            deleted_files.append({"path": rel})

    # Tag critical changes
    critical = config["critical_categories"]
    for item in new_files + changed_files:
        item["critical"] = any(cat in item["path"] for cat in critical)

    report = {
        "platform": config["name"],
        "platform_key": platform_key,
        "timestamp": datetime.now(CST).isoformat(),
        "summary": {
            "total_docs": len(current_hashes),
            "new": len(new_files),
            "changed": len(changed_files),
            "deleted": len(deleted_files),
            "critical_changes": len([x for x in new_files + changed_files if x.get("critical")]),
        },
        "new_files": new_files,
        "changed_files": changed_files,
        "deleted_files": deleted_files,
    }

    # Save current hashes for next comparison
    hash_file.write_text(json.dumps(current_hashes, ensure_ascii=False, indent=2))

    return report


def format_text_report(report: dict) -> str:
    """Format report as readable text."""
    lines = []
    s = report["summary"]
    lines.append(f"=== {report['platform']} 文档变更报告 ===")
    lines.append(f"时间: {report['timestamp']}")
    lines.append(f"总文档数: {s['total_docs']}")
    lines.append(f"新增: {s['new']}, 变更: {s['changed']}, 删除: {s['deleted']}")

    if s["critical_changes"] > 0:
        lines.append(f"⚠️  关键变更 (规则/公告): {s['critical_changes']} 条")

    if report["new_files"]:
        lines.append("\n📄 新增文档:")
        for f in report["new_files"]:
            flag = " 🔴" if f.get("critical") else ""
            lines.append(f"  + {f['title']}{flag}")

    if report["changed_files"]:
        lines.append("\n✏️  内容变更:")
        for f in report["changed_files"]:
            flag = " 🔴" if f.get("critical") else ""
            lines.append(f"  ~ {f['title']}{flag}")

    if report["deleted_files"]:
        lines.append("\n🗑️  已删除:")
        for f in report["deleted_files"]:
            lines.append(f"  - {f['path']}")

    if s["new"] == 0 and s["changed"] == 0 and s["deleted"] == 0:
        lines.append("\n✅ 无变更")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="平台文档变更检测")
    parser.add_argument("--platform", default="xhs", choices=list(PLATFORMS.keys()))
    parser.add_argument("--output", default="text", choices=["text", "json"])
    args = parser.parse_args()

    report = diff_platform(args.platform)

    if args.output == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text_report(report))


if __name__ == "__main__":
    main()
