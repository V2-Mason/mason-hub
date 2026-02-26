#!/usr/bin/env python3
"""
api_logger — 记录 Claude API 调用到 api_usage.jsonl。

用法:
    # Python 内部调用
    from api_logger import log_api_call
    log_api_call(agent_id="EMP_0001", agent_name="素仁轩 PM", action="task_planning",
                 input_tokens=1500, output_tokens=800, cost_usd=0.02)

    # CLI 调用（供 run-agent.sh 使用，传 claude --output-format json 的完整输出）
    python3 api_logger.py --agent-id EMP_0001 --agent-name "素仁轩 PM" \
        --action run-agent --duration 45.2 --json-result '{"usage":...}'

    # CLI 调用（token 未知时）
    python3 api_logger.py --agent-id EMP_0001 --agent-name "素仁轩 PM" \
        --action run-agent --duration 45.2
"""
import json
import os
import sys
import argparse
from datetime import datetime, timezone

LOG_FILE = os.path.expanduser("~/mason-hub/logs/api_usage.jsonl")


def parse_claude_json(json_str: str) -> dict:
    """从 claude --output-format json 的输出中提取 token 用量。

    返回 {"input_tokens": int, "output_tokens": int, "cost_usd": float, "duration_sec": float}
    解析失败时返回空 dict。
    """
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}

    result = {}
    usage = data.get("usage", {})
    if "input_tokens" in usage:
        # input_tokens 包括 cache_creation + cache_read + 实际 input
        cache_creation = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        result["input_tokens"] = usage["input_tokens"] + cache_creation + cache_read
    if "output_tokens" in usage:
        result["output_tokens"] = usage["output_tokens"]
    if "total_cost_usd" in data:
        result["cost_usd"] = data["total_cost_usd"]
    if "duration_ms" in data:
        result["duration_sec"] = data["duration_ms"] / 1000.0

    return result


def log_api_call(
    agent_id: str,
    agent_name: str,
    action: str,
    input_tokens: int = -1,
    output_tokens: int = -1,
    cost_usd: float = -1.0,
    duration_sec: float = -1.0,
):
    """记录一次 API 调用到 api_usage.jsonl。

    token 未知时（子进程调用）传 -1，报告生成时显示为 N/A。
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "agent_name": agent_name,
        "action": action,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "duration_sec": duration_sec,
    }

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="记录 API 调用到 api_usage.jsonl")
    parser.add_argument("--agent-id", required=True, help="Agent ID (如 EMP_0001)")
    parser.add_argument("--agent-name", required=True, help="Agent 名称")
    parser.add_argument("--action", required=True, help="动作类型 (如 run-agent)")
    parser.add_argument("--input-tokens", type=int, default=-1, help="输入 token 数")
    parser.add_argument("--output-tokens", type=int, default=-1, help="输出 token 数")
    parser.add_argument("--cost", type=float, default=-1.0, help="费用 (USD)")
    parser.add_argument("--duration", type=float, default=-1.0, help="耗时 (秒)")
    parser.add_argument("--json-result", default="", help="claude --output-format json 的完整输出")
    args = parser.parse_args()

    input_tokens = args.input_tokens
    output_tokens = args.output_tokens
    cost_usd = args.cost
    duration_sec = args.duration

    # 如果提供了 claude JSON 输出，从中提取精确数据
    if args.json_result:
        parsed = parse_claude_json(args.json_result)
        if parsed:
            input_tokens = parsed.get("input_tokens", input_tokens)
            output_tokens = parsed.get("output_tokens", output_tokens)
            cost_usd = parsed.get("cost_usd", cost_usd)
            if "duration_sec" in parsed and duration_sec < 0:
                duration_sec = parsed["duration_sec"]

    log_api_call(
        agent_id=args.agent_id,
        agent_name=args.agent_name,
        action=args.action,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        duration_sec=duration_sec,
    )


if __name__ == "__main__":
    main()
