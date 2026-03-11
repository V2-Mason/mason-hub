"""Fetch details for all discovered articles — API interception + DOM fallback."""
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path("intel/raw/xhs-school-docs")
INDEX_FILE = BASE_DIR / "index.json"
ARTICLE_LIST = BASE_DIR / "_article_list.json"
ET = timezone(timedelta(hours=-4))  # Mason 标准时区：美东

CAT_NAMES = {
    134: "规则公告/意见征集", 16: "规则公告/规则汇编", 17: "规则公告/规则修订",
    18: "规则公告/规则新增", 19: "规则公告/平台秩序公告",
    106: "内容发布/内容创作管理", 109: "内容发布/笔记管理",
    115: "内容发布/交易管理", 124: "内容发布/直播管理",
    131: "本地生活/商户管理", 132: "本地生活/服务商管理", 133: "本地生活/公告专区",
    26: "招商入驻/入驻要求", 27: "招商入驻/资费管理", 28: "招商入驻/规则解读",
    39: "经营管理/基础规则", 41: "经营管理/续签考核", 42: "经营管理/违规申诉",
    43: "经营管理/违规处罚", 44: "经营管理/权益说明",
    135: "商品管理/商品质量安全", 136: "商品管理/商品发布", 48: "商品管理/总则",
    49: "商品管理/商品质量管理规范", 50: "商品管理/品质负向反馈考核",
    46: "营销推广/营销活动", 35: "消费者保障/基础保障", 36: "消费者保障/争议处理",
    123: "规则解读/商品质量问题", 137: "规则解读/内容推广规范",
    61: "规则解读/履约发货", 63: "规则解读/提供虚假资质问题",
    65: "规则解读/商品描述问题", 67: "规则解读/重复铺货问题",
    68: "规则解读/账单问题", 69: "规则解读/服务分", 70: "规则解读/小红书号",
    72: "规则解读/直播", 73: "规则解读/短标题和首图规则", 74: "规则解读/山寨假货",
    97: "法律声明及协议/协议", 92: "历史规则及协议/历史规则", 93: "历史规则及协议/历史协议",
    151: "流程说明/商品发布流程", 57: "流程说明/TM标特邀申请流程",
    58: "流程说明/店铺名修改流程", 59: "流程说明/身份证开通流程",
    111: "违规公示/警示等处罚公告", 85: "违规公示/终止服务公告",
    87: "专业号/基础规则", 89: "知产维权规则/知产维权投诉规则",
    90: "知产维权规则/知产维权申诉规则", 149: "其他/资料模板",
}

NOISE_WORDS = [
    "首页", "买手专区", "课程中心", "规则中心", "专题直播", "认证讲师", "千帆",
    "您好，", "请登录", "查看历史版本", "查看目录", "规则中心 / 规则详情",
    "规则公告", "内容发布", "本地生活", "招商入驻", "经营管理", "商品管理",
    "营销推广", "消费者保障", "规则解读", "法律声明及协议", "历史规则及协议",
    "流程说明", "违规公示", "专业号", "知产维权规则", "其他",
    "意见征集", "规则汇编", "规则修订", "规则新增", "平台秩序公告",
]


def sanitize_filename(title):
    title = re.sub(r'[/\\:*?"<>|]', "", title)
    return title.strip()[:80] or "untitled"


def rich_json_to_markdown(content_json):
    try:
        data = json.loads(content_json)
    except (json.JSONDecodeError, TypeError):
        return content_json if isinstance(content_json, str) else ""
    parts = []
    _extract_text(data, parts)
    return "\n".join(parts)


def _extract_text(node, parts, depth=0):
    if depth > 20:
        return
    if isinstance(node, str):
        parts.append(node)
        return
    if isinstance(node, list):
        for item in node:
            _extract_text(item, parts, depth)
        return
    if not isinstance(node, dict):
        return

    node_type = node.get("type", "")
    text = node.get("text", "")
    children = node.get("children", [])

    if text:
        if node.get("bold"):
            text = f"**{text}**"
        if node.get("italic"):
            text = f"*{text}*"
        parts.append(text)

    if node_type == "heading":
        level = node.get("level", 1)
        prefix = "#" * min(level, 6)
        ct = []
        for c in children:
            _extract_text(c, ct, depth + 1)
        parts.append(f"\n{prefix} {''.join(ct)}\n")
        return
    if node_type == "paragraph":
        ct = []
        for c in children:
            _extract_text(c, ct, depth + 1)
        parts.append("".join(ct))
        parts.append("")
        return
    if node_type in ("ordered-list", "unordered-list"):
        for i, item in enumerate(children):
            pf = f"{i+1}. " if node_type == "ordered-list" else "- "
            ct = []
            _extract_text(item, ct, depth + 1)
            parts.append(f"{pf}{''.join(ct)}")
        parts.append("")
        return
    if node_type == "table":
        rows = node.get("children", [])
        for row in rows:
            cells = row.get("children", [])
            cell_texts = []
            for cell in cells:
                cp = []
                _extract_text(cell, cp)
                cell_texts.append(" ".join(cp).strip())
            parts.append("| " + " | ".join(cell_texts) + " |")
            if row == rows[0]:
                parts.append("|" + "|".join(["---"] * len(cell_texts)) + "|")
        parts.append("")
        return
    if node_type == "image":
        url = node.get("url", "")
        if url:
            parts.append(f"![image]({url})")
        return
    if node_type == "link":
        url = node.get("url", "")
        ct = []
        for c in children:
            _extract_text(c, ct, depth + 1)
        parts.append(f"[{''.join(ct) or url}]({url})")
        return
    if "content" in node and isinstance(node["content"], dict):
        _extract_text(node["content"], parts, depth)
        return
    for c in children:
        _extract_text(c, parts, depth + 1)


async def extract_from_dom(page, expected_title=""):
    """Fallback: extract content directly from rendered page DOM."""
    data = await page.evaluate("""() => {
        // Title
        let title = '';
        const titleEl = document.querySelector('[class*=detail] [class*=title], [class*=rule] [class*=title], h1, h2');
        if (titleEl) {
            const t = (titleEl.innerText || '').trim();
            if (t.length > 3 && t.length < 200) title = t;
        }
        if (!title) title = document.title.replace('规则中心', '').trim();

        // Content - find the main content area
        let content = '';
        const selectors = [
            '[class*=detail-content]',
            '[class*=rule-content]',
            '[class*=article-content]',
            '[class*=rich-text]',
            '[class*=content-wrap]',
            'article',
            'main',
        ];
        for (const s of selectors) {
            const els = document.querySelectorAll(s);
            for (const el of els) {
                const text = (el.innerText || '').trim();
                if (text.length > content.length && text.length > 50) {
                    content = text;
                }
            }
        }

        // Broader fallback
        if (content.length < 100) {
            const body = document.body.innerText || '';
            content = body;
        }

        return {title, content, url: window.location.href};
    }""")

    # Clean noise
    content = data.get("content", "")
    for noise in NOISE_WORDS:
        content = content.replace(noise + "\n", "", 1)

    return {
        "title": data.get("title") or expected_title,
        "content": content.strip(),
    }


async def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ET).isoformat()

    articles = json.loads(ARTICLE_LIST.read_text())
    print(f"Loaded {len(articles)} articles")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # Capture API responses
        api_details = {}

        async def on_response(response):
            if response.status != 200:
                return
            try:
                if "query_article_detail" in response.url:
                    data = await response.json()
                    if data.get("success"):
                        detail = data.get("data", {}).get("data", {})
                        if detail and detail.get("articleId"):
                            api_details[detail["articleId"]] = detail
            except:
                pass

        page.on("response", on_response)

        # Session init
        await page.goto("https://school.xiaohongshu.com/rule", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Process each article
        results = {}  # aid -> {title, content_md, online_time, ...}

        for i, art in enumerate(articles):
            aid = art.get("articleId")
            cid = art.get("categoryId")
            title = art.get("title", "?")

            print(f"  [{i+1}/{len(articles)}] {title[:60]}...")
            url = f"https://school.xiaohongshu.com/rule/detail/{cid}/{aid}"

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                await asyncio.sleep(4)  # Longer wait for SPA render

                # Check if API captured it
                if aid in api_details:
                    detail = api_details[aid]
                    content_md = rich_json_to_markdown(detail.get("content", ""))
                    if content_md and len(content_md) > 30:
                        results[aid] = {
                            "title": detail.get("title", title),
                            "content_md": content_md,
                            "online_time": detail.get("onlineTime", ""),
                            "first_online": detail.get("firstOnlineTime", ""),
                            "source": "api",
                        }
                        continue

                # Fallback: DOM extraction
                dom_data = await extract_from_dom(page, title)
                if dom_data["content"] and len(dom_data["content"]) > 50:
                    results[aid] = {
                        "title": dom_data["title"] or title,
                        "content_md": dom_data["content"],
                        "online_time": "",
                        "first_online": "",
                        "source": "dom",
                    }

            except Exception as e:
                print(f"    Error: {e}")

            await asyncio.sleep(1.5)

        print(f"\nResults: {len(results)} articles ({sum(1 for r in results.values() if r['source']=='api')} via API, {sum(1 for r in results.values() if r['source']=='dom')} via DOM)")
        await browser.close()

    # Save to files
    index = {"pages": [], "crawl_start": now}
    stats = {"ok": 0, "empty": 0}

    for aid, res in results.items():
        art = next((a for a in articles if a["articleId"] == aid), {})
        cid = art.get("categoryId")
        cat_name = CAT_NAMES.get(cid, "未分类")

        leaf_cat = cat_name.split("/")[-1]
        safe_cat = sanitize_filename(leaf_cat)
        safe_title = sanitize_filename(res["title"])
        out_dir = BASE_DIR / safe_cat
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{safe_title}.md"

        md = f"""---
title: "{res['title']}"
article_id: {aid}
category: "{cat_name}"
online_time: "{res.get('online_time', '')}"
first_online_time: "{res.get('first_online', '')}"
crawl_date: "{datetime.now(ET).isoformat()}"
source: "{res['source']}"
---

{res['content_md']}
"""
        out_path.write_text(md, encoding="utf-8")

        index["pages"].append({
            "status": "ok", "title": res["title"], "article_id": aid,
            "category": cat_name, "path": str(out_path),
            "size": len(res["content_md"]), "online_time": res.get("online_time", ""),
            "source": res["source"], "crawl_date": datetime.now(ET).isoformat(),
        })
        stats["ok"] += 1

    index["crawl_end"] = datetime.now(ET).isoformat()
    index["stats"] = stats
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2))

    print(f"\n=== Complete ===")
    print(f"OK: {stats['ok']}, Empty: {stats['empty']}")

    if stats["ok"] > 0:
        merge_docs(index)


def merge_docs(index):
    output_path = Path("intel/processed/小红书商家学堂-规则中心完整文档.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pages = [p for p in index["pages"] if p.get("status") == "ok"]
    by_cat = {}
    for pg in pages:
        by_cat.setdefault(pg.get("category", "未分类"), []).append(pg)

    parts = [
        "# 小红书商家学堂 — 规则中心完整文档\n",
        f"> 爬取时间: {index.get('crawl_end', 'unknown')}",
        f"> 共 {len(pages)} 篇规则文档\n",
        "---\n",
        "## 目录\n",
    ]
    for cat, cat_pages in sorted(by_cat.items()):
        parts.append(f"### {cat}\n")
        for pg in cat_pages:
            parts.append(f"- {pg['title']}")
        parts.append("")
    parts.append("---\n")

    for cat, cat_pages in sorted(by_cat.items()):
        parts.append(f"\n# {cat}\n")
        for pg in cat_pages:
            fp = Path(pg["path"])
            if fp.exists():
                content = fp.read_text(encoding="utf-8")
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        content = content[end + 3:].strip()
                parts.append(f"\n## {pg['title']}\n")
                if pg.get("online_time"):
                    parts.append(f"> 生效时间: {pg['online_time']}\n")
                parts.append(content)
                parts.append("\n---\n")

    merged = "\n".join(parts)
    output_path.write_text(merged, encoding="utf-8")
    print(f"\nMerged: {output_path}")
    print(f"  {merged.count(chr(10))} lines, {len(merged.encode())/1024:.0f} KB")


if __name__ == "__main__":
    asyncio.run(main())
