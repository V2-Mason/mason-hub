#!/usr/bin/env python3
"""
Daily API Usage Report — 读取 api_usage.jsonl，汇总过去 24 小时消耗，发到 Slack。
纯模板渲染，不调 AI。

Usage:
    python3 daily_usage_report.py          # 发送到 Slack
    python3 daily_usage_report.py --dry    # 仅打印，不发送
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────────────
LOG_FILE = os.path.expanduser("~/mason-hub/logs/api_usage.jsonl")
CH_SYSTEM_ALERTS = "C0AHCMUC057"

# Load bot token from slack-bot .env
ENV_FILE = os.path.expanduser("~/slack-bot/.env")


def load_env(env_path):
    """Load .env file into dict."""
    env = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def load_records(hours=24):
    """Load records from the last N hours."""
    if not os.path.exists(LOG_FILE):
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = []

    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["timestamp"])
                if ts >= cutoff:
                    records.append(rec)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    return records


def format_number(n):
    """Format number with commas."""
    if n < 0:
        return "N/A"
    return f"{n:,}"


def generate_report(records):
    """Generate the report text."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not records:
        return f"\U0001f4ca API Token \u65e5\u62a5 \u2014 {today}\n\n\u8fc7\u53bb 24 \u5c0f\u65f6\u65e0 API \u8c03\u7528\u8bb0\u5f55\u3002"

    # ── By Agent ────────────────────────────────────────────────────────
    agent_stats = defaultdict(lambda: {
        "name": "",
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0,
        "has_token_data": False,
    })

    for rec in records:
        aid = rec.get("agent_id", "unknown")
        stats = agent_stats[aid]
        stats["name"] = rec.get("agent_name", aid)
        stats["calls"] += 1
        inp = rec.get("input_tokens", -1)
        out = rec.get("output_tokens", -1)
        cost = rec.get("cost_usd", -1)
        if inp >= 0:
            stats["input_tokens"] += inp
            stats["has_token_data"] = True
        if out >= 0:
            stats["output_tokens"] += out
        if cost >= 0:
            stats["cost"] += cost

    # ── By Action ───────────────────────────────────────────────────────
    action_stats = defaultdict(lambda: {
        "agent_id": "",
        "agent_name": "",
        "calls": 0,
        "cost": 0.0,
    })

    for rec in records:
        action = rec.get("action", "unknown")
        aid = rec.get("agent_id", "unknown")
        key = f"{action}|{aid}"
        stats = action_stats[key]
        stats["action"] = action
        stats["agent_id"] = aid
        stats["agent_name"] = rec.get("agent_name", aid)
        stats["calls"] += 1
        cost = rec.get("cost_usd", -1)
        if cost >= 0:
            stats["cost"] += cost

    # ── Format ──────────────────────────────────────────────────────────
    lines = [f"\U0001f4ca API Token \u65e5\u62a5 \u2014 {today}", ""]

    # Agent table
    lines.append("\u6309 Agent \u6c47\u603b:")
    total_calls = 0
    total_tokens = 0
    total_cost = 0.0
    unknown_token_agents = []

    for aid in sorted(agent_stats.keys()):
        s = agent_stats[aid]
        total_calls += s["calls"]
        tokens = s["input_tokens"] + s["output_tokens"]
        total_tokens += tokens
        total_cost += s["cost"]

        name_col = f"{aid} {s['name']}"
        calls_col = f"{s['calls']} \u6b21"
        if s["has_token_data"]:
            tokens_col = f"{format_number(tokens)} tokens"
            cost_col = f"${s['cost']:.2f}"
        else:
            tokens_col = "N/A*"
            cost_col = "N/A*"
            unknown_token_agents.append(aid)

        lines.append(f"  {name_col:<28s}| {calls_col:<8s}| {tokens_col:<18s}| {cost_col}")

    lines.append(f"  {'─' * 65}")
    lines.append(f"  {'总计':<28s}| {total_calls} \u6b21{'':4s}| {format_number(total_tokens)} tokens{'':4s}| ${total_cost:.2f}")

    if unknown_token_agents:
        lines.append(f"\n  *N/A = \u901a\u8fc7 run-agent.sh \u5b50\u8fdb\u7a0b\u8c03\u7528\uff0ctoken \u6570\u6682\u65e0\u6cd5\u91c7\u96c6")

    # Top 5 actions
    lines.append("")
    lines.append("\u6d88\u8017 Top 5 \u52a8\u4f5c:")
    sorted_actions = sorted(action_stats.values(), key=lambda x: x["cost"], reverse=True)[:5]
    for i, a in enumerate(sorted_actions, 1):
        cost_str = f"${a['cost']:.2f}" if a["cost"] >= 0 else "N/A"
        lines.append(f"  {i}. {a['action']} ({a['agent_id']}) \u2014 {cost_str} ({a['calls']}\u6b21)")

    # Suggestion
    if sorted_actions and sorted_actions[0]["cost"] > 0:
        top = sorted_actions[0]
        lines.append(f"\n\U0001f4a1 \u5efa\u8bae: {top['action']} \u6d88\u8017\u6700\u9ad8\uff0c\u8003\u8651\u6539\u4e3a\u6a21\u677f\u6e32\u67d3\u6216\u964d\u4f4e\u8c03\u7528\u9891\u7387")

    return "\n".join(lines)


def send_to_slack(token, channel, text):
    """Post message to Slack using urllib (no extra deps)."""
    url = "https://slack.com/api/chat.postMessage"
    data = json.dumps({
        "channel": channel,
        "text": text,
        "username": "API Usage Reporter",
        "icon_emoji": ":bar_chart:",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    })

    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        print(f"Slack API error: {result.get('error', 'unknown')}", file=sys.stderr)
        sys.exit(1)
    return result


def main():
    dry_run = "--dry" in sys.argv

    records = load_records(hours=24)
    report = generate_report(records)

    print(report)

    if dry_run:
        print("\n--- DRY RUN: not sending to Slack ---")
        return

    env = load_env(ENV_FILE)
    token = os.environ.get("SLACK_BOT_TOKEN") or env.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not found in env or .env", file=sys.stderr)
        sys.exit(1)

    send_to_slack(token, CH_SYSTEM_ALERTS, report)
    print(f"\nSent to #{CH_SYSTEM_ALERTS}")


if __name__ == "__main__":
    main()
