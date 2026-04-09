"""
Extract brand/sponsor signals from existing data (0 new HTTP requests).
Scans 3 positions:
  Position 3: video titles (video_list.tsv)
  Position 4: opening 30 lines of each video (full_text.txt)
  Position 5+: round1 272 comments (all_comments_dedup.txt)

Produces: _dictionary/real_sponsors.json
"""
import json
import re
from pathlib import Path
from collections import defaultdict

BASE = Path("c:/Users/hangn/projects/mason-hub/accounts/growth-memo/content/test-001/assets/reference")
DICT_DIR = BASE / "_dictionary"

# 6 accounts to scan
SOURCES = [
    {
        "key": "yupi",
        "name": "程序员鱼皮",
        "tsv": BASE / "batch-2026-04/tier1-programmer-yupi/video_list.tsv",
        "full_text": BASE / "batch-2026-04/tier1-programmer-yupi/full_text.txt",
    },
    {
        "key": "ezindie",
        "name": "ezindie",
        "tsv": BASE / "batch-2026-04/tier1-ezindie/video_list.tsv",
        "full_text": BASE / "batch-2026-04/tier1-ezindie/full_text.txt",
    },
    {
        "key": "xiaolin",
        "name": "小Lin说",
        "tsv": BASE / "batch-2026-04/tier2-xiaolin-shuo/video_list.tsv",
        "full_text": BASE / "batch-2026-04/tier2-xiaolin-shuo/full_text.txt",
    },
    {
        "key": "wushi",
        "name": "巫师财经",
        "tsv": BASE / "batch-2026-04/tier2-wushi-finance/video_list.tsv",
        "full_text": BASE / "batch-2026-04/tier2-wushi-finance/full_text.txt",
    },
    {
        "key": "gougou",
        "name": "网红小狗勾",
        "tsv": BASE / "xiaogougou/selected.tsv",
        "full_text": BASE / "xiaogougou/full_text.txt",
    },
]

ROUND1_COMMENTS = Path("c:/Users/hangn/projects/mason-hub/scripts/all_comments_dedup.txt")

# --- Brand dictionary (canonical name + regex patterns, case-insensitive) ---
BRAND_DEFS = [
    # === AI tools - international ===
    ("Cursor", [r"\bcursor\b"]),
    ("Claude Code", [r"claude\s*code\b"]),
    ("Claude (Anthropic)", [r"\bclaude\b(?!\s*code)", r"anthropic"]),
    ("ChatGPT / OpenAI", [r"chatgpt", r"openai", r"\bgpt-?\d*\b"]),
    ("GitHub Copilot", [r"github\s*copilot", r"\bcopilot\b"]),
    ("Gemini (Google)", [r"\bgemini\b"]),
    ("Windsurf (Codeium)", [r"windsurf", r"codeium"]),
    ("Cline", [r"\bcline\b"]),
    ("Perplexity", [r"perplexity"]),
    ("Zed", [r"\bzed\s*(editor|ide)?\b"]),
    ("Codex", [r"\bcodex\b"]),

    # === AI tools - China ===
    ("Trae 字节", [r"\btrae\b"]),
    ("豆包 字节", [r"豆包"]),
    ("Kimi 月之暗面", [r"\bkimi\b", r"月之暗面", r"moonshot"]),
    ("通义千问 阿里", [r"通义", r"千问", r"\bqwen\b"]),
    ("文心一言 百度", [r"文心"]),
    ("DeepSeek", [r"deepseek", r"深度求索"]),
    ("腾讯元宝", [r"腾讯元宝", r"元宝"]),
    ("秘塔", [r"秘塔"]),
    ("智谱 GLM", [r"智谱", r"\bglm\b"]),
    ("MiniMax", [r"minimax"]),
    ("跃问", [r"跃问"]),

    # === Cloud & infra ===
    ("阿里云", [r"阿里云"]),
    ("腾讯云", [r"腾讯云"]),
    ("火山引擎 字节", [r"火山引擎"]),
    ("华为云", [r"华为云"]),
    ("百度智能云", [r"百度智能云"]),
    ("AWS", [r"\baws\b"]),
    ("Supabase", [r"supabase"]),
    ("Vercel", [r"vercel"]),
    ("Cloudflare", [r"cloudflare"]),
    ("Railway", [r"\brailway\b"]),

    # === Hardware brands (3C) ===
    ("华为", [r"华为(?!云)"]),
    ("小米", [r"小米"]),
    ("荣耀", [r"荣耀(?!\s*王)"]),  # exclude 王者荣耀
    ("OPPO", [r"\boppo\b"]),
    ("vivo", [r"\bvivo\b"]),
    ("大疆 DJI", [r"大疆", r"\bdji\b"]),
    ("苹果 Apple", [r"苹果", r"\bapple\b", r"\bmac(?:book)?\b"]),
    ("联想", [r"联想"]),
    ("戴尔 Dell", [r"戴尔", r"\bdell\b"]),

    # === IDE / Editors ===
    ("VS Code", [r"vs\s*code", r"vscode"]),
    ("JetBrains", [r"jetbrains", r"\bidea\b", r"pycharm", r"webstorm", r"intellij"]),
    ("Notion", [r"\bnotion\b"]),
    ("Obsidian", [r"obsidian"]),
    ("Figma", [r"figma"]),

    # === Office/collaboration ===
    ("飞书 Lark", [r"飞书", r"\blark\b"]),
    ("钉钉", [r"钉钉"]),
    ("企业微信", [r"企业微信"]),
    ("腾讯会议", [r"腾讯会议"]),

    # === E-commerce ===
    ("京东", [r"京东"]),
    ("淘宝 阿里", [r"淘宝", r"天猫"]),
    ("拼多多", [r"拼多多"]),
    ("美团", [r"美团"]),
    ("支付宝", [r"支付宝"]),

    # === Games / entertainment ===
    ("米哈游", [r"米哈游", r"原神", r"崩坏", r"星穹"]),
    ("网易游戏", [r"网易(?:游戏)?"]),
    ("王者荣耀", [r"王者荣耀"]),
    ("和平精英", [r"和平精英"]),

    # === Consumer brands (from 狗勾 videos) ===
    ("云南白药", [r"云南白药"]),
    ("芬达 可口可乐", [r"芬达", r"可口可乐"]),
    ("林肯", [r"林肯(?!公园)"]),
    ("完美日记", [r"完美日记"]),
    ("花西子", [r"花西子"]),
    ("蜜雪冰城", [r"蜜雪冰城"]),
    ("瑞幸", [r"瑞幸"]),
    ("欧莱雅", [r"欧莱雅"]),

    # === MCP and adjacent tech ===
    ("MCP (Anthropic)", [r"\bmcp\b"]),
]

# --- Sponsor declaration keywords (used for context extraction) ---
# If these appear near a brand name, it's a strong sponsor signal
SPONSOR_KEYWORDS = [
    "赞助", "特约", "本期由", "本视频由", "本期合作",
    "合作方", "推广", "广告", "恰饭", "商单", "商务合作",
    "感谢.{0,3}对本期", "感谢.{0,5}支持", "邀请", "鸣谢",
    "官方", "品牌方", "送给大家", "送给粉丝",
]
SPONSOR_PATTERN = re.compile("|".join(SPONSOR_KEYWORDS))


def detect_brands(text: str):
    """Return list of canonical brand names matched in the text."""
    found = []
    tl = text.lower()
    for canonical, patterns in BRAND_DEFS:
        for pat in patterns:
            if re.search(pat, tl, re.IGNORECASE):
                found.append(canonical)
                break
    return found


def parse_full_text(path: Path):
    """Parse full_text.txt into a dict: bvid -> list of lines (the video's transcript)."""
    videos = {}
    current_bvid = None
    current_title = None
    current_lines = []
    header_next = False

    with path.open("r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("=========="):
            # Save previous
            if current_bvid and current_lines:
                videos[current_bvid] = {
                    "title": current_title,
                    "lines": current_lines,
                }
            current_bvid = None
            current_title = None
            current_lines = []
            # Next line should be metadata: BVxxx | date | views | duration
            if i + 1 < len(lines):
                meta_line = lines[i + 1]
                m = re.match(r"^(BV\w+)\s*\|", meta_line)
                if m:
                    current_bvid = m.group(1)
                # Title is line i+2
                if i + 2 < len(lines):
                    current_title = lines[i + 2]
                # Closing ==== is line i+3
                i += 4
                continue
        elif current_bvid:
            current_lines.append(line)
        i += 1

    if current_bvid and current_lines:
        videos[current_bvid] = {
            "title": current_title,
            "lines": current_lines,
        }

    return videos


def parse_tsv(path: Path):
    """Return dict: bvid -> title"""
    if not path.exists():
        return {}
    result = {}
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue  # header
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[0].startswith("BV"):
                result[parts[0]] = parts[1]
    return result


def scan_sources():
    """Scan all 6 sources and collect brand evidence."""
    # brand -> { total_hits, by_source, evidence }
    brand_data = defaultdict(lambda: {
        "total_hits": 0,
        "by_position": {"title": 0, "opening_speech": 0, "opening_sponsor_speech": 0, "comment": 0},
        "by_source_account": defaultdict(int),
        "evidence": [],  # up to 15 pieces
    })

    for src in SOURCES:
        if not src["full_text"].exists():
            print(f"[skip] {src['name']}: full_text not found")
            continue

        print(f"[scan] {src['name']}...")
        titles = parse_tsv(src["tsv"])
        videos = parse_full_text(src["full_text"])

        # Position 3: scan titles
        for bvid, title in titles.items():
            brands = detect_brands(title)
            for brand in brands:
                brand_data[brand]["total_hits"] += 1
                brand_data[brand]["by_position"]["title"] += 1
                brand_data[brand]["by_source_account"][src["name"]] += 1
                if len(brand_data[brand]["evidence"]) < 15:
                    brand_data[brand]["evidence"].append({
                        "position": "title",
                        "account": src["name"],
                        "bvid": bvid,
                        "text": title[:120],
                    })

        # Position 4: scan opening 30 lines of each video's full_text
        for bvid, v in videos.items():
            opening = v["lines"][:30]
            opening_text = "\n".join(opening)

            brands = detect_brands(opening_text)
            is_sponsor = SPONSOR_PATTERN.search(opening_text) is not None

            for brand in brands:
                brand_data[brand]["total_hits"] += 1
                key = "opening_sponsor_speech" if is_sponsor else "opening_speech"
                brand_data[brand]["by_position"][key] += 1
                brand_data[brand]["by_source_account"][src["name"]] += 1

                # Find the specific line that mentions the brand
                for line in opening:
                    if any(re.search(pat, line.lower(), re.IGNORECASE) for _, pats in BRAND_DEFS for pat in pats
                           if re.search(pat, line.lower(), re.IGNORECASE) and any(brand.startswith(bn) or bn in brand for bn, _ in BRAND_DEFS)):
                        # simplified: if brand patterns match this line
                        for bn, pats in BRAND_DEFS:
                            if bn == brand:
                                for pat in pats:
                                    if re.search(pat, line.lower(), re.IGNORECASE):
                                        if len(brand_data[brand]["evidence"]) < 15:
                                            brand_data[brand]["evidence"].append({
                                                "position": "opening_sponsor_speech" if is_sponsor else "opening_speech",
                                                "account": src["name"],
                                                "bvid": bvid,
                                                "title": v["title"][:80] if v["title"] else "",
                                                "text": line[:150],
                                            })
                                        break
                                break
                        break

    # Scan round1 272 comments
    if ROUND1_COMMENTS.exists():
        print(f"[scan] round1 272 comments...")
        with ROUND1_COMMENTS.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                m = re.match(r'^\[\s*(\d+)\]\s*\[([^\]]+)\]\s*\[([^\]]*)\]\s*(.*)$', line)
                if not m:
                    continue
                like, bvid, video_title, content = int(m.group(1)), m.group(2), m.group(3), m.group(4)

                # Check if brand mention + sponsor context (恰饭 / 广告 / 赞助)
                has_sponsor_context = bool(re.search(r"恰饭|广告|赞助|商单|品牌", content))

                brands = detect_brands(content)
                for brand in brands:
                    brand_data[brand]["total_hits"] += 1
                    brand_data[brand]["by_position"]["comment"] += 1
                    brand_data[brand]["by_source_account"]["round1 comments"] += 1
                    if has_sponsor_context and len(brand_data[brand]["evidence"]) < 15:
                        brand_data[brand]["evidence"].append({
                            "position": "comment_sponsor_context",
                            "account": "round1",
                            "bvid": bvid,
                            "like": like,
                            "text": content[:200],
                        })

    # Sort and output
    brand_list = []
    for brand, data in sorted(brand_data.items(), key=lambda x: -x[1]["total_hits"]):
        brand_list.append({
            "brand": brand,
            "total_hits": data["total_hits"],
            "by_position": dict(data["by_position"]),
            "by_source_account": dict(data["by_source_account"]),
            "evidence": data["evidence"],
        })

    return brand_list


def main():
    DICT_DIR.mkdir(parents=True, exist_ok=True)
    brands = scan_sources()

    output = {
        "schema_version": "0.1",
        "generated": "2026-04-08",
        "note": "Phase 1 extraction: 0 HTTP requests. Scanned titles + opening 30 lines + round1 272 comments for brand mentions. Brand list is a keyword dictionary; matches here need human verification for true 'sponsor' vs 'casual mention'.",
        "data_sources": [s["name"] for s in SOURCES] + ["round1 272 comments"],
        "total_brands_detected": len(brands),
        "brands": brands,
    }

    out_path = DICT_DIR / "real_sponsors.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] {out_path} saved")
    print(f"[OK] {len(brands)} brands detected\n")

    # Console summary (top 25)
    print("=== TOP 25 BRANDS BY TOTAL HITS ===")
    print(f"{'Brand':<28} {'Total':>6} {'Title':>6} {'Open':>6} {'OpSpon':>7} {'Comment':>8}")
    print("-" * 75)
    for b in brands[:25]:
        bp = b["by_position"]
        print(f"{b['brand']:<28} {b['total_hits']:>6} {bp['title']:>6} {bp['opening_speech']:>6} {bp['opening_sponsor_speech']:>7} {bp['comment']:>8}")

    # Highlight sponsor-context hits
    print("\n=== BRANDS WITH SPONSOR-CONTEXT EVIDENCE ===")
    sponsor_brands = [b for b in brands if b["by_position"]["opening_sponsor_speech"] > 0]
    for b in sponsor_brands[:15]:
        print(f"  {b['brand']}: {b['by_position']['opening_sponsor_speech']} sponsor-context hits")


if __name__ == "__main__":
    main()
