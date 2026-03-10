#!/usr/bin/env python3
"""
汇报聚合器 — 读取 /data/reports/ 下的结构化汇报，按过滤规则聚合。

用法:
  python3 aggregate_reports.py                  # 聚合今天的汇报
  python3 aggregate_reports.py --date 2026-03-10  # 聚合指定日期
  python3 aggregate_reports.py --since 3d       # 聚合最近 3 天
  python3 aggregate_reports.py --slack           # 聚合后发 Slack

输出:
  - Level 0: 计数统计（"N 个任务静默完成"）
  - Level 1: 逐条一句话摘要
  - Level 2: 标记 ⚠️，需要 Mason 知道
  - Level 3: 标记 🔴，需要 Mason 决策

设计文档: docs/plans/2026-03-10-autonomous-loop.md
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
REPORTS_DIR = HUB_DIR / "data" / "reports"
EVENTS_DIR = HUB_DIR / "data" / "events"
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")


def get_dates(args: list) -> list[str]:
    """解析日期参数，返回日期字符串列表"""
    today = datetime.now().strftime("%Y-%m-%d")

    if "--date" in args:
        idx = args.index("--date")
        return [args[idx + 1]]

    if "--since" in args:
        idx = args.index("--since")
        val = args[idx + 1]
        days = int(val.rstrip("d"))
        dates = []
        for i in range(days):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            dates.append(d)
        return dates

    return [today]


def load_reports(dates: list[str]) -> list[dict]:
    """加载指定日期的所有汇报"""
    reports = []
    for date_str in dates:
        day_dir = REPORTS_DIR / date_str
        if not day_dir.exists():
            continue
        for f in sorted(day_dir.glob("*.json")):
            try:
                report = json.loads(f.read_text())
                report["_file"] = str(f)
                reports.append(report)
            except (json.JSONDecodeError, Exception):
                pass
    return reports


def load_system_map_updates() -> list[dict]:
    """读取 event_router 标记的 SYSTEM_MAP 待更新项"""
    marker = EVENTS_DIR / "system_map_updates.jsonl"
    updates = []
    if marker.exists():
        for line in marker.read_text().strip().split("\n"):
            if line.strip():
                try:
                    updates.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return updates


def aggregate(reports: list[dict]) -> dict:
    """按过滤级别聚合汇报"""
    result = {
        "level_0": [],  # 静默
        "level_1": [],  # 聚合
        "level_2": [],  # 需要知道
        "level_3": [],  # 需要决策
        "by_agent": defaultdict(list),
        "stats": {
            "total": len(reports),
            "success": 0,
            "failed": 0,
            "partial": 0,
        },
    }

    for r in reports:
        level = r.get("level", 0)
        status = r.get("status", "unknown")
        agent = r.get("agent_id", "unknown")

        # 统计
        if status == "success":
            result["stats"]["success"] += 1
        elif status == "failed":
            result["stats"]["failed"] += 1
        elif status == "partial":
            result["stats"]["partial"] += 1

        # 按级别分类
        entry = {
            "agent": agent,
            "summary": r.get("summary", "无摘要"),
            "status": status,
            "blockers_resolved": r.get("blockers_resolved", []),
            "blockers_found": r.get("blockers_found", []),
        }

        if level == 0:
            result["level_0"].append(entry)
        elif level == 1:
            result["level_1"].append(entry)
        elif level == 2:
            result["level_2"].append(entry)
        elif level >= 3:
            result["level_3"].append(entry)

        result["by_agent"][agent].append(entry)

    return result


def format_briefing(agg: dict, map_updates: list[dict]) -> str:
    """生成 Mason briefing 文本"""
    stats = agg["stats"]
    lines = []

    # 标题
    lines.append(f"📊 Agent 汇报聚合 — {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # 统计
    lines.append(f"总计: {stats['total']} 个任务 | ✅ {stats['success']} | ❌ {stats['failed']} | ⚡ {stats['partial']}")
    lines.append("")

    # Level 3: 需要决策（最优先展示）
    if agg["level_3"]:
        lines.append("🔴 需要决策:")
        for e in agg["level_3"]:
            lines.append(f"  - [{e['agent']}] {e['summary']}")
            if e["blockers_found"]:
                lines.append(f"    新 blocker: {', '.join(e['blockers_found'])}")
        lines.append("")

    # Level 2: 需要知道
    if agg["level_2"]:
        lines.append("⚠️ 需要知道:")
        for e in agg["level_2"]:
            lines.append(f"  - [{e['agent']}] {e['summary']}")
            if e["blockers_resolved"]:
                lines.append(f"    已解除: {', '.join(e['blockers_resolved'])}")
        lines.append("")

    # Level 1: 聚合上报
    if agg["level_1"]:
        lines.append("📋 已处理:")
        for e in agg["level_1"]:
            status_icon = "✅" if e["status"] == "success" else "⚡"
            lines.append(f"  {status_icon} [{e['agent']}] {e['summary']}")
        lines.append("")

    # Level 0: 静默统计
    if agg["level_0"]:
        lines.append(f"🔇 静默完成: {len(agg['level_0'])} 个任务（日常运维，无需关注）")
        lines.append("")

    # SYSTEM_MAP 待更新
    if map_updates:
        lines.append("🗺️ SYSTEM_MAP 待更新:")
        for u in map_updates:
            lines.append(f"  - {u.get('line', '?')} → {u.get('new_status', '?')} (触发: {u.get('triggered_by', '?')})")
        lines.append("")

    if not any([agg["level_0"], agg["level_1"], agg["level_2"], agg["level_3"]]):
        lines.append("（无汇报）")

    return "\n".join(lines)


def send_slack(message: str):
    if not SLACK_WEBHOOK:
        print("Slack webhook 未配置，跳过")
        return
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", SLACK_WEBHOOK,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"text": message})],
            capture_output=True, timeout=10,
        )
        print("Slack 已发送")
    except Exception as e:
        print(f"Slack 发送失败: {e}")


if __name__ == "__main__":
    dates = get_dates(sys.argv)
    reports = load_reports(dates)
    map_updates = load_system_map_updates()
    agg = aggregate(reports)
    briefing = format_briefing(agg, map_updates)

    print(briefing)

    if "--slack" in sys.argv:
        send_slack(briefing)
