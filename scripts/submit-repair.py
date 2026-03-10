#!/usr/bin/env python3
"""
submit-repair.py — 提交修复请求到 repair_queue.json

Gateway heartbeat 通过 run_command 调用此脚本，将结构化的修复请求写入队列。
repair-dispatch.sh 读取队列启动 claude -p 修复。

用法:
  python3 scripts/submit-repair.py \
    --issue "data_health_check.sh 执行失败" \
    --symptom "date 命令返回错误: invalid date format" \
    --location "scripts/data_health_check.sh:47" \
    --severity medium

  python3 scripts/submit-repair.py --status          # 查看队列
  python3 scripts/submit-repair.py --resolve <id>    # 标记已解决
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
HUB_DIR = os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub"))
QUEUE_FILE = os.path.join(HUB_DIR, "data", "repair_queue.json")


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_queue(queue):
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def submit(args):
    queue = load_queue()
    now = datetime.now(CST)
    item_id = f"repair_{now.strftime('%Y%m%d_%H%M%S')}"

    item = {
        "id": item_id,
        "timestamp": now.isoformat(),
        "issue": args.issue,
        "symptom": args.symptom or "",
        "location": args.location or "",
        "error_log": args.error_log or "",
        "severity": args.severity or "medium",
        "status": "pending",
        "attempts": 0,
        "fix_applied": "",
        "test_result": "",
        "created_by": "gateway_heartbeat",
    }

    queue.append(item)
    save_queue(queue)
    print(f"✅ 修复请求已提交: {item_id}")
    print(f"   问题: {args.issue}")
    print(f"   位置: {args.location or '未指定'}")
    return item_id


def show_status():
    queue = load_queue()
    if not queue:
        print("修复队列: 空")
        return

    print(f"修复队列: {len(queue)} 条")
    for item in queue:
        status = item.get("status", "?")
        icon = {"pending": "🔵", "repair_attempted": "🟡", "resolved": "✅", "pending_mason": "🔴"}.get(status, "?")
        print(f"  {icon} [{status}] {item['id']}: {item['issue']}")
        if item.get("attempts", 0) > 0:
            print(f"     尝试: {item['attempts']} 次")
        if item.get("fix_applied"):
            print(f"     修复: {item['fix_applied']}")


def resolve(item_id):
    queue = load_queue()
    for item in queue:
        if item["id"] == item_id:
            item["status"] = "resolved"
            item["resolved_at"] = datetime.now(CST).isoformat()
            save_queue(queue)
            print(f"✅ {item_id} 已标记为 resolved")
            return
    print(f"❌ 未找到 {item_id}")


def update_status(item_id, status, fix_applied="", test_result=""):
    """供 repair-dispatch.sh 调用，更新修复结果"""
    queue = load_queue()
    for item in queue:
        if item["id"] == item_id:
            item["status"] = status
            item["attempts"] = item.get("attempts", 0) + 1
            if fix_applied:
                item["fix_applied"] = fix_applied
            if test_result:
                item["test_result"] = test_result
            item["last_attempt"] = datetime.now(CST).isoformat()
            save_queue(queue)
            print(f"✅ {item_id} 状态更新为 {status} (第 {item['attempts']} 次尝试)")
            return
    print(f"❌ 未找到 {item_id}")


def main():
    parser = argparse.ArgumentParser(description="修复队列管理")
    sub = parser.add_subparsers(dest="command")

    # submit
    p_submit = sub.add_parser("submit", help="提交修复请求")
    p_submit.add_argument("--issue", required=True, help="问题描述")
    p_submit.add_argument("--symptom", help="症状")
    p_submit.add_argument("--location", help="文件:行号")
    p_submit.add_argument("--error-log", help="错误日志")
    p_submit.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"])

    # status
    sub.add_parser("status", help="查看队列")

    # resolve
    p_resolve = sub.add_parser("resolve", help="标记已解决")
    p_resolve.add_argument("id", help="修复 ID")

    # update (供 repair-dispatch.sh 调用)
    p_update = sub.add_parser("update", help="更新修复结果")
    p_update.add_argument("id", help="修复 ID")
    p_update.add_argument("--status", required=True, choices=["repair_attempted", "resolved", "pending_mason"])
    p_update.add_argument("--fix", default="", help="修复描述")
    p_update.add_argument("--test-result", default="", help="测试结果")

    args = parser.parse_args()

    if args.command == "submit":
        submit(args)
    elif args.command == "status":
        show_status()
    elif args.command == "resolve":
        resolve(args.id)
    elif args.command == "update":
        update_status(args.id, args.status, args.fix, args.test_result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
