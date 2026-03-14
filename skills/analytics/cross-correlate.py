#!/usr/bin/env python3
"""cross-correlate.py — 跨数据源关联分析

五维 Gap #3（理解-关联）：Scout×XHS×销售数据不自动交叉。
输入：数据源列表 + 时间范围
输出：JSON 关联矩阵

用法：
  python3 skills/analytics/cross-correlate.py --sources xhs,scout --days 7
  python3 skills/analytics/cross-correlate.py --sources xhs,sales,scout --days 30
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))

# 尝试导入 SDK，fallback 到直接文件读取
try:
    sys.path.insert(0, str(HUB_DIR))
    from data.tools import get_xhs_notes, get_scout_intel, get_srx_history
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


def load_xhs_keywords(days: int) -> list[dict]:
    """提取 XHS 热门关键词和话题"""
    if HAS_SDK:
        try:
            notes = get_xhs_notes(days=days)
            keywords = {}
            for n in notes:
                for kw in n.get("keywords", []):
                    keywords[kw] = keywords.get(kw, 0) + 1
            return [{"keyword": k, "count": v, "source": "xhs"} for k, v in
                    sorted(keywords.items(), key=lambda x: -x[1])[:20]]
        except Exception:
            pass
    return []


def load_scout_topics(days: int) -> list[dict]:
    """提取 Scout 情报话题"""
    if HAS_SDK:
        try:
            intel = get_scout_intel(days=days)
            return [
                {"topic": i.get("topic", i.get("title", "")), "confidence": i.get("confidence", 0),
                 "source": "scout"}
                for i in intel[:20]
            ]
        except Exception:
            pass

    # fallback: 从 intel/reports/ 读取
    reports_dir = HUB_DIR / "intel" / "reports"
    topics = []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    for f in sorted(reports_dir.glob("*.json"), reverse=True)[:3]:
        if f.stem < cutoff:
            break
        try:
            data = json.loads(f.read_text())
            items = data if isinstance(data, list) else data.get("items", [])
            for item in items[:10]:
                topics.append({
                    "topic": item.get("topic", item.get("title", ""))[:60],
                    "confidence": item.get("confidence", 0),
                    "source": "scout",
                })
        except Exception:
            continue
    return topics


def load_sales_trends(days: int) -> list[dict]:
    """提取销售趋势"""
    if HAS_SDK:
        try:
            history = get_srx_history(days=days)
            return [{"metric": k, "value": v, "source": "sales"} for k, v in history.items()]
        except Exception:
            pass
    return []


def find_correlations(sources_data: dict) -> list[dict]:
    """寻找跨数据源关联"""
    correlations = []

    xhs_keywords = {item["keyword"].lower() for item in sources_data.get("xhs", [])
                    if "keyword" in item}
    scout_topics = {item["topic"].lower() for item in sources_data.get("scout", [])
                    if "topic" in item}

    # XHS ∩ Scout: 同时出现在两个数据源的话题
    if xhs_keywords and scout_topics:
        overlap = set()
        for kw in xhs_keywords:
            for topic in scout_topics:
                if kw in topic or topic in kw:
                    overlap.add((kw, topic))

        for kw, topic in overlap:
            correlations.append({
                "type": "topic_overlap",
                "sources": ["xhs", "scout"],
                "xhs_keyword": kw,
                "scout_topic": topic,
                "signal": "XHS 热词与 Scout 情报话题重叠，可能是上升趋势",
            })

    if not correlations:
        correlations.append({
            "type": "no_correlation_found",
            "sources": list(sources_data.keys()),
            "signal": "未发现显著跨源关联（数据量可能不足）",
        })

    return correlations


def main():
    parser = argparse.ArgumentParser(description="跨数据源关联分析")
    parser.add_argument("--sources", default="xhs,scout",
                        help="逗号分隔的数据源: xhs,scout,sales")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    args = parser.parse_args()

    source_list = [s.strip() for s in args.sources.split(",")]
    sources_data = {}

    loaders = {
        "xhs": load_xhs_keywords,
        "scout": load_scout_topics,
        "sales": load_sales_trends,
    }

    for src in source_list:
        if src in loaders:
            sources_data[src] = loaders[src](args.days)

    correlations = find_correlations(sources_data)

    report = {
        "generated_at": datetime.now().isoformat(),
        "period_days": args.days,
        "sources": {k: len(v) for k, v in sources_data.items()},
        "correlations": correlations,
        "raw_data": sources_data if args.format == "json" else "omitted",
    }

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== 跨源关联分析 ({args.days}天) ===")
        for k, v in sources_data.items():
            print(f"  {k}: {len(v)} 条数据")
        print(f"\n关联发现: {len(correlations)} 条")
        for c in correlations:
            print(f"  - [{c['type']}] {c['signal']}")


if __name__ == "__main__":
    main()
