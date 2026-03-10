#!/usr/bin/env python3
"""
mason CLI — Terminal 交互入口

用法:
  mason "检查阿里云状态"
  mason "分析数据管道健康"
  mason "SYSTEM_MAP 有什么变化"
  mason status                    # Gateway 状态
  mason log                       # 最近日志
  mason memory                    # 最近记忆
  mason heartbeat                 # 手动触发一次 heartbeat

直接调用 agentic loop，结果实时打印在 terminal。
不经过 Gateway 队列（交互式场景不需要排队）。
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
CST = timezone(timedelta(hours=8))

# 加载 .env
env_file = HUB_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text().strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# 导入 gateway 模块
sys.path.insert(0, str(HUB_DIR / "scripts"))
from importlib.machinery import SourceFileLoader
gw = SourceFileLoader("gateway", str(HUB_DIR / "scripts" / "mason-gateway.py")).load_module()


def cmd_status():
    gw.show_status()


def cmd_log(n: int = 20):
    log_file = HUB_DIR / "logs" / "gateway.log"
    if not log_file.exists():
        print("无日志")
        return
    lines = log_file.read_text().strip().split("\n")
    for line in lines[-n:]:
        print(line)


def cmd_memory(n: int = 10):
    mem_file = HUB_DIR / "data" / "gateway-memory.jsonl"
    if not mem_file.exists():
        print("无记忆")
        return
    lines = mem_file.read_text().strip().split("\n")
    for line in lines[-n:]:
        try:
            entry = json.loads(line)
            sev = entry.get("severity", "?")
            ts = entry.get("timestamp", "?")[:19]
            finding = entry.get("finding", "?")
            action = entry.get("action_taken", "")
            icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}.get(sev, "?")
            print(f"  {icon} [{ts}] {finding}")
            if action:
                print(f"     → {action}")
        except json.JSONDecodeError:
            pass


def cmd_heartbeat():
    print("🫀 手动触发 heartbeat...\n")
    gw.run_heartbeat()


def cmd_ask(question: str):
    """交互式提问 — agentic loop"""
    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    memories = gw.load_recent_memories()

    system_prompt = f"""你是 Mason Hub 的 AI 助手，通过 terminal 与 Mason 交互。当前时间: {now_cst}

你有工具可以读取文件、执行命令、写入状态文件、发 Slack 通知。
Mason 在 terminal 直接跟你对话，简洁回答。

安全规则同 heartbeat：
- 不执行危险命令
- 不确定就说不确定
- 可以读任何 mason-hub 内的文件
- 只能写白名单文件"""

    user_prompt = f"""最近系统记忆:
{memories}

Mason 的问题: {question}"""

    print(f"⏳ 思考中...\n")
    start = time.time()
    result = gw.run_agentic_session(system_prompt, user_prompt)
    elapsed = time.time() - start

    print(f"\n{'─' * 50}")
    print(result)
    print(f"{'─' * 50}")
    print(f"⏱️  {elapsed:.1f}s")


def main():
    if len(sys.argv) < 2:
        print("用法: mason <命令或问题>")
        print("")
        print("  mason \"检查阿里云状态\"    交互式提问")
        print("  mason status              Gateway 状态")
        print("  mason log                 最近日志")
        print("  mason memory              最近记忆")
        print("  mason heartbeat           手动触发 heartbeat")
        return

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "log":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        cmd_log(n)
    elif cmd == "memory":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_memory(n)
    elif cmd == "heartbeat":
        cmd_heartbeat()
    else:
        # 所有其他输入当作问题
        question = " ".join(sys.argv[1:])
        cmd_ask(question)


if __name__ == "__main__":
    main()
