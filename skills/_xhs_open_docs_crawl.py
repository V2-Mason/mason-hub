"""
XHS 开放平台文档 Playwright 爬虫 — 从 open.xiaohongshu.com 抓取全部文档

用法:
  python skills/_xhs_open_docs_crawl.py [--incremental] [--max-id 400] [--delay 3]

功能:
  1. 遍历 /document/developer/file/{1..max_id} 抓取开发者文档
  2. 等 JS 渲染后提取 DOM 内容
  3. 输出为 Markdown 文件到 intel/raw/xhs-docs/
  4. 更新 index.json
  5. --incremental 模式只抓新增/变更

依赖: playwright (已安装在 .venv)
"""

import argparse
import asyncio
import hashlib
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path("intel/raw/xhs-docs")
INDEX_FILE = BASE_DIR / "index.json"
HASH_FILE = BASE_DIR / ".content_hashes.json"

# From socialmesh PlaywrightManager
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-first-run",
    "--no-default-browser-check",
]

CST = timezone(timedelta(hours=8))

# Category mapping based on sidebar navigation labels
CATEGORY_MAP = {
    "开发文档": "开发文档",
    "规则中心": "规则中心",
    "API调用场景": "API调用场景",
    "数据加解密": "数据加解密",
    "电子面单": "电子面单",
    "平台公告": "平台公告",
    "产品发布": "产品发布",
    "技术变更": "技术变更",
    "其他公告": "其他公告",
    "消息文档": "消息文档",
    "SDK文档": "SDK文档",
}


def sanitize_filename(title: str) -> str:
    title = re.sub(r'[/\\:*?"<>|]', '', title)
    return title.strip()[:80] or "untitled"


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def load_hashes() -> dict:
    if HASH_FILE.exists():
        return json.loads(HASH_FILE.read_text())
    return {}


def save_hashes(hashes: dict):
    HASH_FILE.write_text(json.dumps(hashes, ensure_ascii=False, indent=2))


def load_index() -> dict:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {"pages": []}


def save_index(index: dict):
    index["stats"] = {
        "ok": len([p for p in index["pages"] if p.get("status") == "ok"]),
        "errors": len([p for p in index["pages"] if p.get("status") not in ("ok",)]),
    }
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2))


async def extract_page_content(page) -> dict:
    """Extract title and content from a rendered XHS doc page."""
    # Wait for content to render
    try:
        await page.wait_for_selector(".doc-content, .api-content, .markdown-body, article", timeout=8000)
    except Exception:
        pass

    # Try multiple selectors for content
    content = ""
    for selector in [".doc-content", ".api-content", ".markdown-body", "article", ".content", "main"]:
        try:
            el = await page.query_selector(selector)
            if el:
                content = await el.inner_text()
                if len(content) > 50:
                    break
        except Exception:
            continue

    # Get title
    title = ""
    for selector in ["h1", ".doc-title", ".page-title", "title"]:
        try:
            el = await page.query_selector(selector)
            if el:
                title = (await el.inner_text()).strip()
                if title:
                    break
        except Exception:
            continue

    if not title:
        title = await page.title()

    return {"title": title, "content": content.strip()}


def determine_category(title: str, file_id: int) -> tuple:
    """Determine doc_type and category from title and known patterns."""
    # Known ID ranges from previous crawl
    if any(kw in title for kw in ["规则", "协议", "规范", "保证金", "审核标准", "承诺函"]):
        return "开发文档", "规则中心"
    elif any(kw in title for kw in ["公告", "通知", "变更", "上线"]):
        return "平台公告", "技术变更"
    elif any(kw in title for kw in ["消息", "msg_"]):
        return "消息文档", "消息文档"
    elif any(kw in title for kw in ["加密", "解密"]):
        return "开发文档", "数据加解密"
    elif any(kw in title for kw in ["面单"]):
        return "开发文档", "电子面单"
    else:
        return "开发文档", "开发文档"


async def crawl_developer_docs(max_id: int = 400, incremental: bool = False, delay: float = 3.0):
    """Main crawl loop."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    index = load_index()
    hashes = load_hashes()
    existing_file_ids = {str(p.get("file_id")) for p in index["pages"] if p.get("source") != "apifox"}

    now = datetime.now(CST).isoformat()
    stats = {"ok": 0, "empty": 0, "error": 0, "skipped": 0, "updated": 0}

    print(f"Starting crawl at {now}")
    print(f"Max file ID: {max_id}, Incremental: {incremental}, Delay: {delay}s")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=_STEALTH_ARGS,
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        for file_id in range(1, max_id + 1):
            url = f"https://open.xiaohongshu.com/document/developer/file/{file_id}"

            # Incremental: skip already crawled IDs
            if incremental and str(file_id) in existing_file_ids:
                old_hash = hashes.get(str(file_id))
                if old_hash:
                    stats["skipped"] += 1
                    continue

            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=15000)
                if resp and resp.status == 404:
                    continue

                # Small delay for JS rendering
                await asyncio.sleep(1.5)

                data = await extract_page_content(page)
                title = data["title"]
                body = data["content"]

                if not body or len(body) < 30:
                    stats["empty"] += 1
                    print(f"  [{file_id}] EMPTY: {title[:40]}")
                    continue

                # Check if content changed (incremental)
                new_hash = content_hash(body)
                old_hash = hashes.get(str(file_id))
                if incremental and old_hash == new_hash:
                    stats["skipped"] += 1
                    continue

                if old_hash and old_hash != new_hash:
                    stats["updated"] += 1
                    print(f"  [{file_id}] UPDATED: {title[:40]}")
                else:
                    stats["ok"] += 1
                    print(f"  [{file_id}] OK: {title[:40]}")

                # Determine output path
                doc_type, category = determine_category(title, file_id)
                safe_title = sanitize_filename(title)
                out_dir = BASE_DIR / doc_type / category
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{safe_title}.md"

                # Write markdown
                md = f"""---
title: "{title}"
source_url: "{url}"
file_id: "{file_id}"
category: "{category}"
doc_type: "{doc_type}"
crawl_date: "{datetime.now(CST).isoformat()}"
---

{body}
"""
                out_path.write_text(md, encoding="utf-8")

                # Update index
                found = False
                for entry in index["pages"]:
                    if str(entry.get("file_id")) == str(file_id):
                        entry["status"] = "ok"
                        entry["title"] = title
                        entry["path"] = str(out_path)
                        entry["size"] = len(body)
                        entry["crawl_date"] = datetime.now(CST).isoformat()
                        found = True
                        break
                if not found:
                    index["pages"].append({
                        "status": "ok",
                        "file_id": file_id,
                        "title": title,
                        "category": category,
                        "doc_type": doc_type,
                        "path": str(out_path),
                        "size": len(body),
                        "crawl_date": datetime.now(CST).isoformat(),
                    })

                hashes[str(file_id)] = new_hash

            except Exception as e:
                stats["error"] += 1
                print(f"  [{file_id}] ERROR: {e}")

            # Polite delay
            await asyncio.sleep(delay + (time.time() % 1))  # jitter

        await browser.close()

    # Save results
    index["crawl_end"] = datetime.now(CST).isoformat()
    save_index(index)
    save_hashes(hashes)

    print(f"\n=== Crawl Complete ===")
    print(f"OK: {stats['ok']}, Updated: {stats['updated']}, Empty: {stats['empty']}, "
          f"Error: {stats['error']}, Skipped: {stats['skipped']}")
    print(f"Index: {len(index['pages'])} total pages")

    return stats


def main():
    parser = argparse.ArgumentParser(description="XHS 开放平台文档爬虫")
    parser.add_argument("--incremental", action="store_true", help="增量模式：只抓新增/变更")
    parser.add_argument("--max-id", type=int, default=400, help="最大 file ID（默认 400）")
    parser.add_argument("--delay", type=float, default=3.0, help="页面间延迟秒数（默认 3）")
    args = parser.parse_args()

    asyncio.run(crawl_developer_docs(
        max_id=args.max_id,
        incremental=args.incremental,
        delay=args.delay,
    ))


if __name__ == "__main__":
    main()
