#!/usr/bin/env python3
"""pattern-extract.py — 跨任务规律提炼

五维 Gap #5（学习-模式识别）：cold memory 里的 pattern 没人挖。
输入：agent memory 文件集
输出：JSON 模式清单

用法：
  python3 skills/learning/pattern-extract.py --agent all
  python3 skills/learning/pattern-extract.py --agent EMP_0002
  python3 skills/learning/pattern-extract.py --agent all --min-count 3
"""

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
AGENTS_DIR = HUB_DIR / "agents"


def extract_lessons(agent_id: str) -> list[dict]:
    """从 agent 的 long_term.md 提取结构化 lesson"""
    memory_dir = AGENTS_DIR / agent_id / "memory"
    lessons = []

    for filename in ("long_term.md", "lessons.md"):
        filepath = memory_dir / filename
        if not filepath.exists():
            continue

        content = filepath.read_text(encoding="utf-8")
        current_section = ""
        current_date = ""

        for line in content.split("\n"):
            # 提取 section header
            if line.startswith("### "):
                current_section = line.lstrip("# ").strip()
                # 尝试提取日期
                date_match = re.search(r"\((\d{4}-\d{2}-\d{2})", line)
                current_date = date_match.group(1) if date_match else ""
            elif line.startswith("- ") and current_section:
                lesson_text = line.lstrip("- ").strip()
                if len(lesson_text) > 10:  # 过滤太短的
                    lessons.append({
                        "agent": agent_id,
                        "section": current_section,
                        "date": current_date,
                        "text": lesson_text,
                        "source": filename,
                    })

    return lessons


def find_patterns(all_lessons: list[dict], min_count: int = 2) -> list[dict]:
    """从 lessons 中找重复出现的模式"""
    patterns = []

    # 模式 1: 关键词频率分析
    keyword_agents = {}  # keyword -> set of agents
    keywords_to_find = [
        "bug", "修复", "失败", "崩溃", "超时", "回退", "重试",
        "权限", "配置", "路径", "编码", "格式",
        "性能", "成本", "token", "上下文",
        "设计缺口", "文档", "测试",
    ]

    for lesson in all_lessons:
        text_lower = lesson["text"].lower()
        for kw in keywords_to_find:
            if kw in text_lower:
                if kw not in keyword_agents:
                    keyword_agents[kw] = set()
                keyword_agents[kw].add(lesson["agent"])

    for kw, agents in keyword_agents.items():
        if len(agents) >= min_count:
            related = [l for l in all_lessons if kw in l["text"].lower()]
            patterns.append({
                "type": "recurring_keyword",
                "keyword": kw,
                "agent_count": len(agents),
                "agents": sorted(agents),
                "occurrence_count": len(related),
                "examples": [l["text"][:80] for l in related[:3]],
            })

    # 模式 2: Gap 类型统计
    gap_counter = Counter()
    for lesson in all_lessons:
        gap_match = re.search(r"Gap\s*类型[：:]\s*(.+?)(?:\s*[—-]|$)", lesson["text"])
        if gap_match:
            gap_type = gap_match.group(1).strip()
            gap_counter[gap_type] += 1

    for gap_type, count in gap_counter.most_common():
        if count >= min_count:
            patterns.append({
                "type": "recurring_gap",
                "gap_type": gap_type,
                "count": count,
                "signal": f"'{gap_type}' 反复出现 {count} 次，可能是系统性问题",
            })

    # 模式 3: 同一 agent 重复踩坑
    agent_sections = Counter()
    for lesson in all_lessons:
        key = f"{lesson['agent']}:{lesson['section']}"
        agent_sections[key] += 1

    for key, count in agent_sections.most_common():
        if count >= 5:  # 同一 section 5+ 条 lesson = 频繁踩坑
            agent, section = key.split(":", 1)
            patterns.append({
                "type": "frequent_area",
                "agent": agent,
                "section": section,
                "lesson_count": count,
                "signal": f"{agent} 在 '{section}' 领域积累了 {count} 条经验，是高频工作区",
            })

    # 按 occurrence_count / count 降序
    patterns.sort(key=lambda x: x.get("occurrence_count", x.get("count", 0)), reverse=True)
    return patterns


def main():
    parser = argparse.ArgumentParser(description="跨任务规律提炼")
    parser.add_argument("--agent", default="all", help="EMP_XXXX 或 all")
    parser.add_argument("--min-count", type=int, default=2, help="最少出现次数")
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    args = parser.parse_args()

    # 收集 lessons
    all_lessons = []
    if args.agent == "all":
        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if agent_dir.is_dir() and agent_dir.name.startswith("EMP_"):
                all_lessons.extend(extract_lessons(agent_dir.name))
    else:
        all_lessons = extract_lessons(args.agent)

    # 找模式
    patterns = find_patterns(all_lessons, min_count=args.min_count)

    report = {
        "generated_at": datetime.now().isoformat(),
        "agents_scanned": len(set(l["agent"] for l in all_lessons)),
        "total_lessons": len(all_lessons),
        "patterns_found": len(patterns),
        "patterns": patterns,
    }

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== 模式识别报告 ===")
        print(f"扫描 {report['agents_scanned']} 个 agent，{report['total_lessons']} 条 lesson")
        print(f"发现 {report['patterns_found']} 个模式：\n")
        for p in patterns:
            if p["type"] == "recurring_keyword":
                print(f"  🔑 关键词 '{p['keyword']}' 出现 {p['occurrence_count']} 次，跨 {p['agent_count']} 个 agent")
            elif p["type"] == "recurring_gap":
                print(f"  🏗️ Gap '{p['gap_type']}' 重复 {p['count']} 次")
            elif p["type"] == "frequent_area":
                print(f"  📍 {p['agent']} 高频区: {p['section']} ({p['lesson_count']} 条)")


if __name__ == "__main__":
    main()
