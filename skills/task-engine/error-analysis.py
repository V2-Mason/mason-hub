#!/usr/bin/env python3
"""error-analysis.py — 错误追踪与分析管道

能力：
  1. Error Trace: 从 task YAML + audit.jsonl 追踪错误源头
  2. Error Classification: 分类错误类型（拆解/执行/评估/外部）
  3. Error Pattern: 跨任务错误模式识别
  4. Pass Rate: 按任务类型/agent 统计历史通过率
  5. Root Cause Suggestion: 基于分类和模式给出改进建议

用法：
  # 分析单个失败任务
  python3 skills/task-engine/error-analysis.py trace --task-id task_EMP_0002_xxx

  # 统计通过率
  python3 skills/task-engine/error-analysis.py pass-rate --days 7

  # 错误模式分析
  python3 skills/task-engine/error-analysis.py patterns --days 30

  # 完整报告
  python3 skills/task-engine/error-analysis.py report --days 7
"""

import argparse
import json
import os
import re
import sys
import yaml
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))

# 错误分类体系
ERROR_CATEGORIES = {
    "decomposition": {
        "description": "拆解问题 — 任务定义不清、粒度不对",
        "markers": ["需求不清", "目标不明", "任务太大", "范围", "scope"],
    },
    "execution": {
        "description": "执行问题 — 代码错误、逻辑错误",
        "markers": ["syntax", "import", "TypeError", "NameError", "bug", "错误", "失败"],
    },
    "evaluation": {
        "description": "评估问题 — 测试不对、验收标准不合理",
        "markers": ["test", "assert", "验证", "测试", "检查失败"],
    },
    "external": {
        "description": "外部问题 — API 故障、权限不足、资源不可用",
        "markers": ["timeout", "connection", "permission", "404", "500", "rate limit", "quota"],
    },
    "context": {
        "description": "上下文问题 — 缺少必要信息、记忆不足",
        "markers": ["not found", "找不到", "缺少", "不存在", "unknown"],
    },
}


def load_audit_records(days: int = 7) -> list[dict]:
    """加载审计记录"""
    audit_file = HUB_DIR / "logs" / "audit.jsonl"
    if not audit_file.exists():
        return []

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    records = []
    with open(audit_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("timestamp", "") >= cutoff:
                    records.append(d)
            except json.JSONDecodeError:
                continue
    return records


def load_task_yamls() -> dict:
    """加载所有 task YAML"""
    tasks_dir = HUB_DIR / "data" / "tasks"
    tasks = {}
    if tasks_dir.exists():
        for f in tasks_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text())
                if data and isinstance(data, dict):
                    tasks[data.get("id", f.stem)] = data
            except Exception:
                continue
    return tasks


def classify_error(error_text: str) -> tuple[str, float]:
    """分类错误类型，返回 (category, confidence)"""
    error_lower = error_text.lower()
    scores = {}

    for cat, info in ERROR_CATEGORIES.items():
        match_count = sum(1 for m in info["markers"] if m.lower() in error_lower)
        if match_count > 0:
            scores[cat] = match_count / len(info["markers"])

    if scores:
        best = max(scores, key=scores.get)
        return best, round(scores[best], 2)

    return "unknown", 0.0


def trace_error(task_id: str) -> dict:
    """追踪单个任务的错误链路"""
    records = load_audit_records(days=30)
    tasks = load_task_yamls()

    task_records = [r for r in records if r.get("task_id") == task_id]
    task_yaml = tasks.get(task_id, {})

    if not task_records and not task_yaml:
        return {"error": f"task_id '{task_id}' not found in audit or tasks"}

    # 构建错误链
    chain = []
    for r in sorted(task_records, key=lambda x: x.get("timestamp", "")):
        status = r.get("status", "")
        error = r.get("root_cause_guess", r.get("error", ""))
        agent = r.get("agent", "")
        rounds = r.get("verify_rounds", 0)

        category, confidence = classify_error(str(error))

        chain.append({
            "timestamp": r.get("timestamp", ""),
            "agent": agent,
            "status": status,
            "error": str(error)[:200],
            "category": category,
            "confidence": confidence,
            "rounds": rounds,
        })

    # 分析
    categories = Counter(c["category"] for c in chain if c["category"] != "unknown")
    root_category = categories.most_common(1)[0][0] if categories else "unknown"

    suggestions = {
        "decomposition": "任务定义需要更具体的验收标准和更细的拆分",
        "execution": "代码质量问题，建议加强验证或用不同 agent 重试",
        "evaluation": "检查测试用例是否合理，可能是测试太严或方向不对",
        "external": "外部依赖问题，需要重试或换方案绕过",
        "context": "agent 缺少必要信息，需要注入更多上下文或检查文件路径",
        "unknown": "错误信息不足，建议查看 logs/tasks/ 下的原始输出",
    }

    return {
        "task_id": task_id,
        "total_attempts": len(chain),
        "error_chain": chain,
        "root_category": root_category,
        "suggestion": suggestions.get(root_category, ""),
        "task_yaml": {k: v for k, v in task_yaml.items() if k != "lessons_extracted"} if task_yaml else None,
    }


def compute_pass_rate(days: int = 7) -> dict:
    """计算通过率"""
    records = load_audit_records(days)

    by_agent = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "cost": 0})
    by_type = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

    for r in records:
        agent = r.get("agent", "unknown")
        status = r.get("status", "")
        task_type = r.get("task_type", "unknown")
        cost = r.get("cost_usd", 0) or 0

        by_agent[agent]["total"] += 1
        by_agent[agent]["cost"] += float(cost) if isinstance(cost, (int, float, str)) and cost else 0

        by_type[task_type]["total"] += 1

        if status in ("completed",):
            by_agent[agent]["passed"] += 1
            by_type[task_type]["passed"] += 1
        elif status in ("failed", "repair_failed", "escalated"):
            by_agent[agent]["failed"] += 1
            by_type[task_type]["failed"] += 1

    # 计算比率
    for stats in list(by_agent.values()) + list(by_type.values()):
        if stats["total"] > 0:
            stats["pass_rate"] = round(stats["passed"] / stats["total"] * 100, 1)
        else:
            stats["pass_rate"] = 0

    return {
        "period_days": days,
        "total_tasks": sum(s["total"] for s in by_agent.values()),
        "overall_pass_rate": round(
            sum(s["passed"] for s in by_agent.values()) /
            max(1, sum(s["total"] for s in by_agent.values())) * 100, 1
        ),
        "by_agent": {k: dict(v) for k, v in sorted(by_agent.items())},
        "by_type": {k: dict(v) for k, v in by_type.items()},
    }


def find_error_patterns(days: int = 30) -> dict:
    """跨任务错误模式识别"""
    records = load_audit_records(days)
    failed = [r for r in records if r.get("status") in ("failed", "repair_failed", "escalated")]

    # 分类统计
    category_counts = Counter()
    category_agents = defaultdict(set)
    category_examples = defaultdict(list)

    for r in failed:
        error = str(r.get("root_cause_guess", r.get("error", r.get("task", ""))))
        cat, conf = classify_error(error)
        category_counts[cat] += 1
        category_agents[cat].add(r.get("agent", "?"))
        if len(category_examples[cat]) < 3:
            category_examples[cat].append(error[:100])

    patterns = []
    for cat, count in category_counts.most_common():
        patterns.append({
            "category": cat,
            "description": ERROR_CATEGORIES.get(cat, {}).get("description", "未知"),
            "count": count,
            "agents_affected": sorted(category_agents[cat]),
            "examples": category_examples[cat],
        })

    return {
        "period_days": days,
        "total_failures": len(failed),
        "patterns": patterns,
    }


def full_report(days: int = 7) -> dict:
    """完整错误分析报告"""
    pass_rate = compute_pass_rate(days)
    patterns = find_error_patterns(days)

    return {
        "generated_at": datetime.now().isoformat(),
        "pass_rate": pass_rate,
        "error_patterns": patterns,
    }


def main():
    parser = argparse.ArgumentParser(description="错误追踪与分析")
    subparsers = parser.add_subparsers(dest="command")

    trace_p = subparsers.add_parser("trace", help="追踪单个任务错误")
    trace_p.add_argument("--task-id", required=True)

    rate_p = subparsers.add_parser("pass-rate", help="通过率统计")
    rate_p.add_argument("--days", type=int, default=7)

    pat_p = subparsers.add_parser("patterns", help="错误模式分析")
    pat_p.add_argument("--days", type=int, default=30)

    rep_p = subparsers.add_parser("report", help="完整报告")
    rep_p.add_argument("--days", type=int, default=7)

    args = parser.parse_args()

    if args.command == "trace":
        print(json.dumps(trace_error(args.task_id), indent=2, ensure_ascii=False))
    elif args.command == "pass-rate":
        print(json.dumps(compute_pass_rate(args.days), indent=2, ensure_ascii=False))
    elif args.command == "patterns":
        print(json.dumps(find_error_patterns(args.days), indent=2, ensure_ascii=False))
    elif args.command == "report":
        print(json.dumps(full_report(args.days), indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
