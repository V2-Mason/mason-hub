"""
拆分小红书开放平台 API 完整文档为独立 md 文件，整合到 intel/raw/xhs-docs/

用法: python skills/_split_xhs_api_docs.py [--dry-run]

输入: intel/raw/xhs-docs/小红书开放平台API完整文档.md
输出: intel/raw/xhs-docs/{分类}/{子分类}/{标题}.md
"""

import argparse
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path("intel/raw/xhs-docs")
INPUT_FILE = BASE_DIR / "小红书开放平台API完整文档.md"
INDEX_FILE = BASE_DIR / "index.json"

# API 接口按关键词分类
API_CATEGORIES = {
    "商品": ["分类", "规格", "属性", "品牌", "商品", "ITEM", "SKU", "素材", "库存", "物流方案", "运费", "价格", "主图"],
    "订单": ["订单", "发货", "快递", "备注", "物流轨迹", "海关", "取消申请", "跨境", "小包", "开票", "发票"],
    "售后": ["售后", "退款", "换货", "收货"],
    "通用": ["解密", "脱敏", "索引串", "地址", "快递公司", "物流模式", "授权", "资质", "达人", "结算", "电子面单", "面单"],
}


def classify_api(title: str) -> str:
    """按标题关键词归类 API 接口"""
    for category, keywords in API_CATEGORIES.items():
        for kw in keywords:
            if kw in title:
                return category
    return "通用"


def sanitize_filename(title: str) -> str:
    """清理文件名"""
    # Remove numbering prefix like "35. "
    title = re.sub(r'^\d+\.\s+', '', title)
    # Remove illegal chars
    title = re.sub(r'[/\\:*?"<>|]', '', title)
    # Trim whitespace
    title = title.strip()
    return title[:80] if title else "untitled"


def check_existing(title: str, existing_files: set) -> bool:
    """检查是否已有同名文件（来自 open.xiaohongshu.com 的版本优先）"""
    clean = sanitize_filename(title)
    for f in existing_files:
        if clean in f:
            return True
    return False


def parse_sections(content: str) -> list:
    """解析大文件为独立章节"""
    sections = re.split(r'\n---\n', content)
    results = []

    for sec in sections[2:]:  # skip header and TOC
        sec = sec.strip()
        if not sec:
            continue

        # Extract title
        title_match = re.search(r'^## \d+\.\s+(.+)', sec, re.MULTILINE)
        if not title_match:
            continue
        title = title_match.group(1).strip()

        # Extract source URL
        source_match = re.search(r'\*\*来源:\*\*\s*(https://\S+)', sec)
        source_url = source_match.group(1) if source_match else ""

        # Determine type
        if '/api-' in source_url:
            doc_type = "api"
        elif '/schema-' in source_url:
            doc_type = "schema"
        else:
            doc_type = "doc"

        # Extract body (everything after the source line)
        body_start = sec.find('\n', sec.find('**来源:**')) if '**来源:**' in sec else 0
        body = sec[body_start:].strip() if body_start > 0 else sec

        # Clean up trailing "Built with" noise
        body = re.sub(r'LLMs\.txt.*?Built with\s*$', '', body, flags=re.DOTALL).strip()

        results.append({
            "title": title,
            "source_url": source_url,
            "doc_type": doc_type,
            "body": body,
        })

    return results


def determine_path(section: dict) -> Path:
    """确定文件输出路径"""
    title = sanitize_filename(section["title"])
    doc_type = section["doc_type"]

    if doc_type == "api":
        category = classify_api(section["title"])
        return BASE_DIR / "SDK文档" / category / f"{title}.md"
    elif doc_type == "schema":
        return BASE_DIR / "SDK文档" / "通用" / f"{title}.md"
    else:
        # Developer docs — check if it's a rule, announcement, or general doc
        t = section["title"]
        if any(kw in t for kw in ["规则", "协议", "规范", "保证金", "审核标准", "承诺函"]):
            return BASE_DIR / "开发文档" / "规则中心" / f"{title}.md"
        elif any(kw in t for kw in ["公告", "通知", "变更", "上线"]):
            return BASE_DIR / "平台公告" / "产品发布" / f"{title}.md"
        elif any(kw in t for kw in ["消息", "新建", "上下架", "审核驳回", "删除"]):
            # These are message event docs
            return BASE_DIR / "消息文档" / "商品消息" / f"{title}.md"
        else:
            return BASE_DIR / "开发文档" / "开发文档" / f"{title}.md"


def format_markdown(section: dict, output_path: Path) -> str:
    """格式化为带 frontmatter 的 markdown"""
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    return f"""---
title: "{section['title']}"
source_url: "{section['source_url']}"
source: "apifox"
category: "{output_path.parent.name}"
doc_type: "{output_path.parent.parent.name}"
crawl_date: "{now}"
---

{section['body']}
"""


def main():
    parser = argparse.ArgumentParser(description="拆分 XHS API 文档")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = parser.parse_args()

    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found")
        return

    content = INPUT_FILE.read_text(encoding="utf-8")
    sections = parse_sections(content)
    print(f"Parsed {len(sections)} sections from {INPUT_FILE.name}")

    # Collect existing files
    existing_files = set()
    for f in BASE_DIR.rglob("*.md"):
        if f.name != INPUT_FILE.name:
            existing_files.add(f.stem)

    # Load existing index
    index = {"pages": []}
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            index = json.load(f)

    existing_titles_in_index = {p.get("title") for p in index["pages"]}

    created = 0
    skipped = 0

    for sec in sections:
        output_path = determine_path(sec)
        clean_title = sanitize_filename(sec["title"])

        # Skip if already exists with same name
        if clean_title in existing_files:
            skipped += 1
            if args.dry_run:
                print(f"  SKIP (exists): {clean_title}")
            continue

        if args.dry_run:
            print(f"  CREATE: {output_path}")
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            md_content = format_markdown(sec, output_path)
            output_path.write_text(md_content, encoding="utf-8")

        # Add to index if not already there
        if sec["title"] not in existing_titles_in_index:
            index["pages"].append({
                "status": "ok",
                "title": sec["title"],
                "source_url": sec["source_url"],
                "source": "apifox",
                "category": output_path.parent.name,
                "doc_type": output_path.parent.parent.name,
                "path": str(output_path),
                "size": len(sec["body"]),
            })

        created += 1

    print(f"\nResults: {created} created, {skipped} skipped (already exist)")
    print(f"Index total: {len(index['pages'])} pages")

    if not args.dry_run:
        index["last_merge"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        index["stats"] = {
            "ok": len([p for p in index["pages"] if p.get("status") == "ok"]),
            "errors": len([p for p in index["pages"] if p.get("status") != "ok"]),
        }
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"Updated {INDEX_FILE}")


if __name__ == "__main__":
    main()
