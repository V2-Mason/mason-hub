#!/usr/bin/env python3
"""
Scout 情报标准化管道
将 intel/digests/*.md 解析为结构化 JSONL

用法：
  python3 data/pipelines/scout-normalize.py                          # 处理所有 digests
  python3 data/pipelines/scout-normalize.py --file intel/digests/2026-03-08.md  # 单个文件
  python3 data/pipelines/scout-normalize.py --stats                  # 统计信息

输出：intel/processed/scout_normalized.jsonl（追加模式，id 去重）

Owner: EMP_0014 (Data Engineer)
版本: 1.0 (2026-03-10)
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIGESTS_DIR = os.path.join(ROOT, "intel", "digests")
OUTPUT_FILE = os.path.join(ROOT, "intel", "processed", "scout_normalized.jsonl")


def extract_date_from_file(filepath, content):
    """从文件名或正文提取日期"""
    basename = os.path.basename(filepath)

    # 尝试文件名格式: 2026-03-08.md
    m = re.search(r"(\d{4}-\d{2}-\d{2})", basename)
    if m:
        return m.group(1)

    # 尝试文件名格式: 2026-W09-digest.md → 从正文找日期
    # 正文中找: 巡逻日期：2026-02-27 或 情报简报 — 2026-03-08
    m = re.search(r"(\d{4}-\d{2}-\d{2})", content[:500])
    if m:
        return m.group(1)

    # 最后回退到文件修改时间
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def extract_source_from_content(content):
    """从正文提取数据来源"""
    # 数据来源：GitHub API (scout-github, scout-anthropic, scout-trending)
    m = re.search(r"数据来源[：:]\s*(.+)", content[:500])
    if m:
        sources = re.findall(r"scout-\w+", m.group(1))
        if len(sources) == 1:
            return sources[0]
        if sources:
            return "mixed"
    return "mixed"


def extract_url(text):
    """提取第一个 markdown 链接 URL"""
    m = re.search(r"\[([^\]]*)\]\((https?://[^\)]+)\)", text)
    if m:
        return m.group(2)
    return None


def extract_field(text, patterns):
    """从文本中提取指定字段"""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_suggested_owner(text):
    """提取建议负责人"""
    m = re.search(r"(?:建议分配给|建议.*负责)[：:]\s*(EMP_\d+)", text)
    if m:
        return m.group(1)
    return None


def determine_priority(section_header):
    """根据所在 section 标题判断优先级"""
    header_lower = section_header.lower()
    if "🔴" in section_header or "高优" in section_header or "立即行动" in section_header or "action required" in header_lower:
        return "red"
    if "🟡" in section_header or "值得了解" in section_header or "watch" in header_lower or "持续关注" in section_header:
        return "yellow"
    return "info"


def parse_digest(filepath):
    """解析单个 digest 文件，返回情报条目列表"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    date = extract_date_from_file(filepath, content)
    source = extract_source_from_content(content)
    basename = os.path.basename(filepath)
    entries = []

    # 按 ## 分割 sections
    sections = re.split(r"^(## .+)$", content, flags=re.MULTILINE)

    current_priority = "info"
    item_counter = 0

    for i, section in enumerate(sections):
        # 检测 section header
        if section.startswith("## "):
            current_priority = determine_priority(section)
            continue

        # 在 section 内容中找 ### 条目
        items = re.split(r"^(### .+)$", section, flags=re.MULTILINE)

        for j in range(len(items)):
            item_header = items[j]
            if not item_header.startswith("### "):
                continue

            # 提取标题: ### 1. 标题文字 或 ### N. 标题
            title_match = re.match(r"###\s+\d+\.\s*(.+)", item_header)
            if not title_match:
                continue

            title = title_match.group(1).strip()
            item_counter += 1

            # 获取条目正文（到下一个 ### 或 ## 之前）
            body = items[j + 1] if j + 1 < len(items) else ""
            # 截断到下一个 section
            body = body.strip()

            # 提取结构化字段
            url = extract_url(body)
            relevance = extract_field(body, [
                r"\*\*与\s*Mason\s*Hub\s*的关系\*\*[：:]\s*(.+)",
                r"\*\*与素仁轩的关系\*\*[：:]\s*(.+)",
                r"\*\*影响\*\*[：:]\s*(.+)",
            ])
            suggested_action = extract_field(body, [
                r"\*\*建议行动\*\*[：:]\s*(.+)",
                r"\*\*建议\*\*[：:]\s*(.+)",
            ])
            suggested_owner = extract_suggested_owner(body)

            # 构建 summary: 去掉结构化字段行后的前几行
            summary_lines = []
            for line in body.split("\n"):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                # 跳过已提取的结构化字段行
                if any(kw in line_stripped for kw in [
                    "与 Mason Hub 的关系", "与素仁轩的关系",
                    "建议行动", "建议分配给", "**影响**", "**建议**"
                ]):
                    continue
                summary_lines.append(line_stripped.lstrip("- "))
                if len(summary_lines) >= 3:
                    break
            summary = " ".join(summary_lines)

            entry_id = f"{date}-{source}-{item_counter:03d}"

            entry = {
                "id": entry_id,
                "date": date,
                "source": source,
                "priority": current_priority,
                "title": title,
                "summary": summary,
                "digest_file": basename,
            }
            # 只加有值的可选字段
            if url:
                entry["url"] = url
            if relevance:
                entry["relevance"] = relevance
            if suggested_action:
                entry["suggested_action"] = suggested_action
            if suggested_owner:
                entry["suggested_owner"] = suggested_owner

            entries.append(entry)

    return entries


def load_existing_ids(output_file):
    """加载已有 JSONL 中的 id 集合"""
    ids = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    ids.add(obj.get("id", ""))
                except json.JSONDecodeError:
                    continue
    return ids


def run_normalize(files):
    """处理文件列表，追加去重写入 JSONL"""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    existing_ids = load_existing_ids(OUTPUT_FILE)

    all_entries = []
    for filepath in files:
        if not os.path.exists(filepath):
            print(f"[WARN] 文件不存在: {filepath}", file=sys.stderr)
            continue
        entries = parse_digest(filepath)
        all_entries.extend(entries)

    new_entries = [e for e in all_entries if e["id"] not in existing_ids]

    if not new_entries:
        print(f"共解析 {len(all_entries)} 条情报，全部已存在，无新增")
        return all_entries

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for entry in new_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"共解析 {len(all_entries)} 条情报，新增 {len(new_entries)} 条 → {OUTPUT_FILE}")
    return all_entries


def run_stats():
    """输出已有 JSONL 的统计信息"""
    if not os.path.exists(OUTPUT_FILE):
        print(f"[ERROR] 数据文件不存在: {OUTPUT_FILE}", file=sys.stderr)
        sys.exit(1)

    entries = []
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not entries:
        print("无数据")
        return

    print(f"总条目数: {len(entries)}")
    print()

    # 按 priority 分组
    priority_counts = Counter(e["priority"] for e in entries)
    print("按优先级:")
    for p in ["red", "yellow", "info"]:
        symbol = {"red": "🔴", "yellow": "🟡", "info": "ℹ️"}.get(p, "")
        print(f"  {symbol} {p}: {priority_counts.get(p, 0)}")
    print()

    # 按 source 分组
    source_counts = Counter(e["source"] for e in entries)
    print("按来源:")
    for src, cnt in source_counts.most_common():
        print(f"  {src}: {cnt}")
    print()

    # 按 digest 文件分组
    file_counts = Counter(e["digest_file"] for e in entries)
    print("按 digest 文件:")
    for f, cnt in file_counts.most_common():
        print(f"  {f}: {cnt}")
    print()

    # 有 suggested_action 的条目
    actionable = [e for e in entries if e.get("suggested_action")]
    print(f"有建议行动: {len(actionable)}/{len(entries)}")

    # 有 suggested_owner 的条目
    owned = [e for e in entries if e.get("suggested_owner")]
    print(f"有建议负责人: {len(owned)}/{len(entries)}")


def main():
    parser = argparse.ArgumentParser(description="Scout 情报标准化管道")
    parser.add_argument("--file", help="处理单个 digest 文件")
    parser.add_argument("--stats", action="store_true", help="输出统计信息")
    args = parser.parse_args()

    if args.stats:
        run_stats()
        return

    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(os.path.join(DIGESTS_DIR, "*.md")))
        if not files:
            print(f"[WARN] 未找到 digest 文件: {DIGESTS_DIR}/*.md", file=sys.stderr)
            sys.exit(1)

    run_normalize(files)


if __name__ == "__main__":
    main()
