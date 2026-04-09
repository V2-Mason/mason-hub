"""
Round1 Comment Brand Frequency Analysis
=========================================
Parse scripts/all_comments_dedup.txt and generate:
- _dictionary/brands.json: brand mention counts + contexts
- _dictionary/brand_map.json: brand -> needs linkage

Input format (one comment per line):
  [like_count] [BVID] [video_title] comment_content

Usage:
  python scripts/analyze_round1_brands.py
"""
import json
import re
from pathlib import Path
from collections import defaultdict

# Paths
INPUT = Path("scripts/all_comments_dedup.txt")
DICT_DIR = Path("accounts/growth-memo/content/test-001/assets/reference/_dictionary")

# Brand list to search for (case-insensitive, with aliases)
# Each brand has: canonical_name, patterns (regex, case-insensitive)
BRAND_DEFINITIONS = [
    ("Cursor", [r"\bcursor\b"]),
    ("Claude Code", [r"claude\s*code\b", r"\bccode\b"]),
    ("Claude", [r"\bclaude\b(?!\s*code)"]),  # Claude but NOT Claude Code
    ("Trae", [r"\btrae\b"]),
    ("Vibe Coding", [r"vibe\s*coding", r"\bvibe\b"]),
    ("Notion", [r"\bnotion\b"]),
    ("GitHub Copilot", [r"github\s*copilot", r"\bcopilot\b"]),
    ("Windsurf", [r"\bwindsurf\b"]),
    ("Cline", [r"\bcline\b"]),
    ("OpenAI GPT", [r"\bgpt\b", r"chatgpt"]),
    ("OpenAI Codex", [r"\bcodex\b"]),
    ("Google Gemini", [r"\bgemini\b"]),
    ("DeepSeek", [r"deepseek", r"\bds\b"]),
    ("Doubao 豆包", [r"豆包"]),
    ("Qwen 千问/通义", [r"千问", r"通义"]),
    ("Kimi", [r"\bkimi\b"]),
    ("Meta Llama", [r"\bllama\b"]),
    ("Anthropic", [r"anthropic"]),
    ("OpenAI (org)", [r"openai"]),
    ("VS Code", [r"vs\s*code", r"vscode"]),
    ("JetBrains", [r"jetbrains", r"idea\b"]),
    ("MCP", [r"\bmcp\b"]),
    ("Supabase", [r"supabase"]),
    ("Vercel", [r"vercel"]),
    ("飞书", [r"飞书"]),
    ("腾讯元宝", [r"元宝"]),
]

# Sentiment keywords (very rough, just signals)
POSITIVE_KEYWORDS = ["好用", "强", "不错", "爱了", "牛", "推荐", "省时间", "真香", "方便", "厉害"]
NEGATIVE_KEYWORDS = ["贵", "限额", "太差", "垃圾", "坑", "废", "烂", "吐槽", "失望", "难用", "不行"]
QUESTION_KEYWORDS = ["怎么", "如何", "求", "问一下", "有没有", "能不能", "?", "？", "？"]


def parse_comment_line(line: str):
    """Parse one line: [like] [BVID] [title] content"""
    # Match: [like] [bvid] [title] content
    m = re.match(r'^\[\s*(\d+)\]\s*\[([^\]]+)\]\s*\[([^\]]*)\]\s*(.*)$', line)
    if not m:
        return None
    return {
        "like": int(m.group(1)),
        "bvid": m.group(2).strip(),
        "title": m.group(3).strip(),
        "content": m.group(4).strip(),
    }


def detect_brands(text: str):
    """Return list of brand canonical names that appear in the text."""
    text_lower = text.lower()
    found = []
    for canonical, patterns in BRAND_DEFINITIONS:
        for pat in patterns:
            if re.search(pat, text_lower, re.IGNORECASE):
                found.append(canonical)
                break
    return found


def detect_sentiment(text: str):
    """Very rough sentiment: return dict with positive/negative/question flags."""
    return {
        "positive": any(kw in text for kw in POSITIVE_KEYWORDS),
        "negative": any(kw in text for kw in NEGATIVE_KEYWORDS),
        "question": any(kw in text for kw in QUESTION_KEYWORDS),
    }


def main():
    if not INPUT.exists():
        print(f"[ERROR] Input not found: {INPUT}")
        return

    DICT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse all comments
    comments = []
    with INPUT.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            parsed = parse_comment_line(line)
            if parsed:
                comments.append(parsed)

    print(f"[OK] Parsed {len(comments)} comments")

    # Step 2: For each brand, find all mentioning comments
    brand_data = defaultdict(lambda: {
        "total_mentions": 0,
        "sentiment": {"positive": 0, "negative": 0, "question": 0, "neutral": 0},
        "top_comments": [],       # Top 20 by like count
        "bvid_coverage": set(),   # Set of BVIDs where this brand appeared
    })

    for c in comments:
        full_text = f"{c['title']} {c['content']}"
        brands = detect_brands(full_text)
        sentiment = detect_sentiment(c['content'])

        for brand in brands:
            data = brand_data[brand]
            data["total_mentions"] += 1
            data["bvid_coverage"].add(c["bvid"])
            data["top_comments"].append({
                "like": c["like"],
                "bvid": c["bvid"],
                "title": c["title"][:80],
                "content": c["content"],
                "sentiment": sentiment,
            })

            if sentiment["negative"]:
                data["sentiment"]["negative"] += 1
            elif sentiment["positive"]:
                data["sentiment"]["positive"] += 1
            elif sentiment["question"]:
                data["sentiment"]["question"] += 1
            else:
                data["sentiment"]["neutral"] += 1

    # Step 3: Sort top_comments by like, keep top 20
    for brand, data in brand_data.items():
        data["top_comments"].sort(key=lambda x: -x["like"])
        data["top_comments"] = data["top_comments"][:20]
        data["bvid_coverage"] = sorted(list(data["bvid_coverage"]))
        data["unique_videos"] = len(data["bvid_coverage"])

    # Step 4: Generate brands.json
    brands_sorted = sorted(brand_data.items(), key=lambda x: -x[1]["total_mentions"])
    brands_output = {
        "schema_version": "1.0",
        "last_updated": "2026-04-08",
        "source": "round1 272 deduped comments from 15 Top videos (2026-04-06)",
        "total_brands_detected": len(brands_sorted),
        "brands": []
    }

    for brand, data in brands_sorted:
        if data["total_mentions"] == 0:
            continue
        brands_output["brands"].append({
            "brand": brand,
            "total_mentions": data["total_mentions"],
            "unique_videos": data["unique_videos"],
            "bvid_coverage": data["bvid_coverage"],
            "sentiment": data["sentiment"],
            "top_comments": data["top_comments"],
        })

    with (DICT_DIR / "brands.json").open("w", encoding="utf-8") as f:
        json.dump(brands_output, f, ensure_ascii=False, indent=2)

    print(f"[OK] brands.json: {len(brands_output['brands'])} brands detected")

    # Step 5: Generate brand_map.json (simplified: brand -> needs mapping, needs manual)
    # For now, just the brand -> top_evidence linkage
    brand_map = {
        "schema_version": "1.0",
        "last_updated": "2026-04-08",
        "note": "Manual mapping of brand -> needs_model.md needs is TODO. For now contains brand + top 5 evidence comments for quick reference.",
        "brand_to_needs": {}
    }

    for b in brands_output["brands"]:
        brand_map["brand_to_needs"][b["brand"]] = {
            "mentions": b["total_mentions"],
            "top_5_evidence": [
                {
                    "like": c["like"],
                    "content": c["content"][:200],
                    "bvid": c["bvid"],
                }
                for c in b["top_comments"][:5]
            ],
            "needs_links": [],  # to be filled manually
        }

    with (DICT_DIR / "brand_map.json").open("w", encoding="utf-8") as f:
        json.dump(brand_map, f, ensure_ascii=False, indent=2)

    print(f"[OK] brand_map.json: {len(brand_map['brand_to_needs'])} brands mapped")

    # Step 6: Console summary
    print("\n=== BRAND FREQUENCY SUMMARY ===")
    print(f"{'Brand':<25} {'Mentions':>10} {'Videos':>8} {'Sentiment (+/-/?/:)':>25}")
    print("-" * 75)
    for b in brands_output["brands"][:20]:
        s = b["sentiment"]
        sentiment_str = f"+{s['positive']}/-{s['negative']}/?{s['question']}/:{s['neutral']}"
        print(f"{b['brand']:<25} {b['total_mentions']:>10} {b['unique_videos']:>8} {sentiment_str:>25}")


if __name__ == "__main__":
    main()
