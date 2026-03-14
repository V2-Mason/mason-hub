#!/usr/bin/env python3
"""cross-correlate.py — 跨数据源关联分析

五维 Gap #3（理解-关联）：Scout×XHS×审计×Agent记忆 不自动交叉。
输入：数据源列表 + 时间范围
输出：JSON 关联矩阵 + 可操作洞察

数据源:
  xhs    — XHS 笔记关键词/话题 (intel/reports/*.json 或 SDK)
  scout  — Scout 情报话题 (intel/reports/*.json)
  audit  — 审计日志失败/成功模式 (logs/audit.jsonl)
  memory — Agent 记忆关键词 (agents/EMP_*/memory/)

用法：
  python3 skills/analytics/cross-correlate.py --sources xhs,scout --days 7
  python3 skills/analytics/cross-correlate.py --sources audit,memory --days 30
  python3 skills/analytics/cross-correlate.py --sources xhs,scout,audit,memory --days 14 --format summary
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
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


# ─── 数据加载器 ───────────────────────────────────────────

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
    # fallback: 从 intel/reports/ 读含 xhs 的 JSON
    reports_dir = HUB_DIR / "intel" / "reports"
    items = []
    if reports_dir.exists():
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        for f in sorted(reports_dir.glob("*.json"), reverse=True)[:5]:
            if f.stem < cutoff:
                break
            try:
                data = json.loads(f.read_text())
                entries = data if isinstance(data, list) else data.get("items", data.get("notes", []))
                for entry in entries[:15]:
                    for kw in entry.get("keywords", []):
                        items.append({"keyword": kw, "source": "xhs",
                                      "date": f.stem[:10]})
            except Exception:
                continue
    return items


def load_scout_topics(days: int) -> list[dict]:
    """提取 Scout 情报话题"""
    if HAS_SDK:
        try:
            intel = get_scout_intel(days=days)
            return [
                {"topic": i.get("topic", i.get("title", "")),
                 "confidence": i.get("confidence", 0),
                 "source": "scout",
                 "date": i.get("date", "")}
                for i in intel[:20]
            ]
        except Exception:
            pass

    # fallback: 从 intel/reports/ 读取
    reports_dir = HUB_DIR / "intel" / "reports"
    topics = []
    if not reports_dir.exists():
        return topics
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    for f in sorted(reports_dir.glob("*.json"), reverse=True)[:5]:
        if f.stem < cutoff:
            break
        try:
            data = json.loads(f.read_text())
            entries = data if isinstance(data, list) else data.get("items", [])
            for item in entries[:10]:
                topics.append({
                    "topic": item.get("topic", item.get("title", ""))[:60],
                    "confidence": item.get("confidence", 0),
                    "source": "scout",
                    "date": f.stem[:10],
                })
        except Exception:
            continue
    return topics


def load_audit_events(days: int) -> list[dict]:
    """从 audit.jsonl 加载事件"""
    audit_path = HUB_DIR / "logs" / "audit.jsonl"
    if not audit_path.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    events = []
    for line in audit_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ts_str = entry.get("timestamp", "")
            if ts_str:
                # 解析 ISO 格式时间
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if ts < cutoff:
                    continue
            events.append({
                "agent": entry.get("agent", "unknown"),
                "task": entry.get("task", entry.get("task_id", ""))[:60],
                "status": entry.get("status", "unknown"),
                "error": _extract_error_type(entry),
                "source": "audit",
                "date": ts_str[:10] if ts_str else "",
                "duration": entry.get("duration", 0),
            })
        except (json.JSONDecodeError, ValueError):
            continue
    return events


def _extract_error_type(entry: dict) -> str:
    """从审计条目提取错误类型"""
    # 检查 attempts 数组（repair 模式）
    attempts = entry.get("attempts", [])
    if attempts:
        last_error = attempts[-1].get("error", "")
        # 提取错误类名
        match = re.match(r"(\w+Error|\w+Exception)", last_error)
        return match.group(1) if match else last_error[:40]
    # 检查 status
    if entry.get("status") in ("failed", "repair_failed"):
        return entry.get("root_cause_guess", "unknown_error")[:40]
    return ""


def load_agent_memory_keywords(days: int) -> list[dict]:
    """从 agent memory 提取近期关键词"""
    agents_dir = HUB_DIR / "agents"
    if not agents_dir.exists():
        return []

    keywords = []
    # 提取有意义的技术/业务关键词
    tech_terms = re.compile(
        r"(部署|性能|超时|失败|成功|重构|修复|回退|权限|配置|API|SDK|"
        r"数据库|缓存|监控|告警|Gemini|Scout|XHS|小红书|"
        r"视频|剪辑|爬虫|Cookie|Token|成本|调度|"
        r"Dispatcher|Gateway|Agent|Skill|Memory|Pipeline)",
        re.IGNORECASE,
    )
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir() or not agent_dir.name.startswith("EMP_"):
            continue
        memory_dir = agent_dir / "memory"
        if not memory_dir.exists():
            continue
        for filename in ("memory.md", "long_term.md", "lessons.md"):
            fp = memory_dir / filename
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8")
            current_date = ""
            for line in content.split("\n"):
                # 尝试提取日期
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
                if date_match:
                    current_date = date_match.group(1)
                # 只看时间范围内的 lesson
                if current_date and current_date < cutoff:
                    continue
                # 提取技术关键词
                found = tech_terms.findall(line)
                for term in found:
                    keywords.append({
                        "keyword": term.lower(),
                        "agent": agent_dir.name,
                        "source": "memory",
                        "date": current_date,
                    })
    return keywords


# ─── 关联引擎 ───────────────────────────────────────────

def find_correlations(sources_data: dict) -> list[dict]:
    """多维关联分析引擎"""
    correlations = []

    # 提取各源的关键词集合（归一化）
    source_terms = {}
    for src, items in sources_data.items():
        terms = defaultdict(int)
        for item in items:
            # 统一提取文本关键词
            text = (item.get("keyword", "") or item.get("topic", "")
                    or item.get("task", "")).lower()
            if text:
                terms[text] += 1
        source_terms[src] = terms

    # ── 关联 1: 话题重叠（两两比较）──
    source_names = list(source_terms.keys())
    for i in range(len(source_names)):
        for j in range(i + 1, len(source_names)):
            src_a, src_b = source_names[i], source_names[j]
            terms_a, terms_b = source_terms[src_a], source_terms[src_b]
            overlaps = _find_term_overlaps(terms_a, terms_b)
            for kw_a, kw_b, score in overlaps:
                correlations.append({
                    "type": "topic_overlap",
                    "sources": [src_a, src_b],
                    "term_a": kw_a,
                    "term_b": kw_b,
                    "overlap_score": round(score, 2),
                    "signal": f"'{kw_a}' ({src_a}) ↔ '{kw_b}' ({src_b}) 关联度 {score:.0%}",
                })

    # ── 关联 2: 审计失败与记忆关键词关联 ──
    if "audit" in sources_data and "memory" in sources_data:
        audit_items = sources_data["audit"]
        memory_items = sources_data["memory"]

        # 失败 agent 列表
        failed_agents = defaultdict(list)
        for item in audit_items:
            if item.get("status") in ("failed", "repair_failed"):
                failed_agents[item["agent"]].append(item)

        # 对应 agent 的记忆热词
        memory_by_agent = defaultdict(list)
        for item in memory_items:
            memory_by_agent[item.get("agent", "")].append(item)

        for agent, failures in failed_agents.items():
            agent_mem = memory_by_agent.get(agent, [])
            if agent_mem:
                mem_keywords = Counter(m.get("keyword", "") for m in agent_mem)
                top_keywords = [kw for kw, _ in mem_keywords.most_common(3) if kw]
                error_types = Counter(f.get("error", "") for f in failures if f.get("error"))
                top_errors = [e for e, _ in error_types.most_common(3) if e]
                if top_keywords and top_errors:
                    correlations.append({
                        "type": "failure_context",
                        "agent": agent,
                        "failure_count": len(failures),
                        "top_errors": top_errors,
                        "memory_focus": top_keywords,
                        "signal": f"{agent} 失败 {len(failures)} 次，"
                                  f"错误类型: {', '.join(top_errors[:2])}，"
                                  f"近期关注: {', '.join(top_keywords[:2])}",
                    })

    # ── 关联 3: 时间聚类 ──
    date_events = defaultdict(lambda: defaultdict(int))
    for src, items in sources_data.items():
        for item in items:
            date = item.get("date", "")[:10]
            if date:
                date_events[date][src] += 1

    # 找多源同日活跃的日期
    multi_source_dates = []
    for date, src_counts in sorted(date_events.items()):
        if len(src_counts) >= 2:
            multi_source_dates.append({
                "date": date,
                "sources": dict(src_counts),
                "total": sum(src_counts.values()),
            })

    if multi_source_dates:
        # 找最密集的日期
        peak = max(multi_source_dates, key=lambda x: x["total"])
        correlations.append({
            "type": "temporal_cluster",
            "peak_date": peak["date"],
            "sources_active": peak["sources"],
            "total_events": peak["total"],
            "multi_source_days": len(multi_source_dates),
            "signal": f"峰值日 {peak['date']}：{len(peak['sources'])} 个数据源共 {peak['total']} 条事件",
        })

    # ── 关联 4: 审计效率趋势 ──
    if "audit" in sources_data:
        audit_items = sources_data["audit"]
        completed = [a for a in audit_items if a.get("status") == "completed"]
        failed = [a for a in audit_items if a.get("status") in ("failed", "repair_failed")]
        if completed or failed:
            total = len(completed) + len(failed)
            success_rate = len(completed) / total if total > 0 else 0
            avg_duration = 0
            durations = [a["duration"] for a in completed if a.get("duration")]
            if durations:
                avg_duration = sum(durations) / len(durations)
            correlations.append({
                "type": "audit_trend",
                "total_tasks": total,
                "success_rate": round(success_rate, 2),
                "avg_duration_s": round(avg_duration, 1),
                "signal": f"任务成功率 {success_rate:.0%} ({len(completed)}/{total})，"
                          f"平均耗时 {avg_duration:.0f}s",
            })

    if not correlations:
        correlations.append({
            "type": "no_correlation_found",
            "sources": list(sources_data.keys()),
            "signal": "未发现显著跨源关联（数据量可能不足）",
        })

    # 排序：overlap_score 或 failure_count 高的优先
    correlations.sort(
        key=lambda c: c.get("overlap_score", 0) + c.get("failure_count", 0) * 0.1,
        reverse=True,
    )
    return correlations


def _find_term_overlaps(terms_a: dict, terms_b: dict,
                        min_score: float = 0.3) -> list[tuple]:
    """模糊匹配两组关键词，返回 (term_a, term_b, score) 列表"""
    overlaps = []
    for ta in terms_a:
        for tb in terms_b:
            if not ta or not tb:
                continue
            score = _similarity(ta, tb)
            if score >= min_score:
                overlaps.append((ta, tb, score))
    # 去重，保留最高分
    seen = set()
    unique = []
    for ta, tb, score in sorted(overlaps, key=lambda x: -x[2]):
        key = (ta, tb) if ta < tb else (tb, ta)
        if key not in seen:
            seen.add(key)
            unique.append((ta, tb, score))
    return unique[:10]  # 最多 10 条


def _similarity(a: str, b: str) -> float:
    """简单相似度：包含关系 → 高分，字符重叠 → 中分"""
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.8
    # Jaccard on character bigrams
    bigrams_a = set(a[i:i+2] for i in range(len(a) - 1)) if len(a) > 1 else {a}
    bigrams_b = set(b[i:i+2] for i in range(len(b) - 1)) if len(b) > 1 else {b}
    if not bigrams_a or not bigrams_b:
        return 0.0
    intersection = bigrams_a & bigrams_b
    union = bigrams_a | bigrams_b
    return len(intersection) / len(union) if union else 0.0


# ─── 输出 ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="跨数据源关联分析")
    parser.add_argument("--sources", default="xhs,scout,audit,memory",
                        help="逗号分隔的数据源: xhs,scout,audit,memory")
    parser.add_argument("--days", type=int, default=7, help="分析时间范围（天）")
    parser.add_argument("--format", default="json", choices=["json", "summary"])
    args = parser.parse_args()

    source_list = [s.strip() for s in args.sources.split(",")]
    sources_data = {}

    loaders = {
        "xhs": load_xhs_keywords,
        "scout": load_scout_topics,
        "audit": load_audit_events,
        "memory": load_agent_memory_keywords,
    }

    for src in source_list:
        if src in loaders:
            sources_data[src] = loaders[src](args.days)

    correlations = find_correlations(sources_data)

    report = {
        "generated_at": datetime.now().isoformat(),
        "period_days": args.days,
        "sources": {k: len(v) for k, v in sources_data.items()},
        "total_data_points": sum(len(v) for v in sources_data.values()),
        "correlations_found": len(correlations),
        "correlations": correlations,
    }

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== 跨源关联分析 ({args.days}天) ===")
        print(f"数据源: {', '.join(f'{k}({len(v)})' for k, v in sources_data.items())}")
        print(f"总数据点: {report['total_data_points']}")
        print(f"\n发现 {len(correlations)} 条关联：\n")
        for c in correlations:
            t = c["type"]
            if t == "topic_overlap":
                print(f"  🔗 {c['signal']}")
            elif t == "failure_context":
                print(f"  ⚠️  {c['signal']}")
            elif t == "temporal_cluster":
                print(f"  📅 {c['signal']}")
            elif t == "audit_trend":
                print(f"  📊 {c['signal']}")
            elif t == "no_correlation_found":
                print(f"  ∅  {c['signal']}")
            else:
                print(f"  •  [{t}] {c.get('signal', '')}")


if __name__ == "__main__":
    main()
