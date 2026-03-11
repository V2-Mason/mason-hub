#!/usr/bin/env python3
"""
slack-ask.py — Slack /ask 查询入口 (Socket Mode)
Mason 在 Slack 发 /ask <问题>，系统读取最新状态 + 调 Claude API 回答。

Socket Mode = 应用主动连 Slack WebSocket，不需要公网端口/防火墙。

用法:
  python3 scripts/slack-ask.py                        # 启动 Socket Mode
  python3 scripts/slack-ask.py --test "现在什么状态"   # 本地测试（不需要 Slack）

Slack 配置:
  1. api.slack.com → Your App → Socket Mode → Enable
  2. App-Level Token: 生成一个带 connections:write scope 的 token (xapp-...)
  3. Slash Commands → /ask (无需 Request URL，Socket Mode 自动路由)
  4. OAuth & Permissions → Bot Token Scopes: chat:write
  5. Install App → 复制 Bot User OAuth Token (xoxb-...)
  6. .env 添加:
     SLACK_APP_TOKEN=xapp-...
     SLACK_BOT_TOKEN=xoxb-...
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", Path.home() / "mason-hub"))
LOG_FILE = HUB_DIR / "logs" / "slack-ask.log"
ENV_FILE = HUB_DIR / ".env"


def load_env():
    """从 .env 加载环境变量"""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# === 上下文收集 ===

def gather_context() -> str:
    """收集系统状态上下文"""
    sections = []

    # 1. Gateway 最近记忆（最近 15 条）
    memory_file = HUB_DIR / "data" / "gateway-memory.jsonl"
    if memory_file.exists():
        lines = memory_file.read_text().strip().splitlines()
        recent = lines[-15:]
        memories = []
        for line in recent:
            try:
                m = json.loads(line)
                ts = m.get("timestamp", "?")[:16]
                status = m.get("status", "")
                severity = m.get("severity", "")
                finding = m.get("finding", "")
                action = m.get("action_taken", "")
                entry = f"[{ts}] [{severity}/{status}] {finding}"
                if action:
                    entry += f" → {action}"
                memories.append(entry)
            except json.JSONDecodeError:
                continue
        if memories:
            sections.append("## Gateway 最近记忆\n" + "\n".join(memories))

    # 2. SYSTEM_MAP 摘要
    sysmap = HUB_DIR / "SYSTEM_MAP.md"
    if sysmap.exists():
        content = sysmap.read_text()
        lines = content.splitlines()[:80]
        sections.append("## SYSTEM_MAP（能力线状态）\n" + "\n".join(lines))

    # 3. 最新 heartbeat 日志
    health_log = HUB_DIR / "logs" / "heartbeat.log"
    if health_log.exists():
        lines = health_log.read_text().strip().splitlines()
        recent = lines[-20:]
        sections.append("## 最近 Heartbeat 日志\n" + "\n".join(recent))

    # 4. pending_mason 事项
    if memory_file.exists():
        lines = memory_file.read_text().strip().splitlines()
        pending = []
        for line in lines:
            try:
                m = json.loads(line)
                if m.get("status") == "pending_mason":
                    ts = m.get("timestamp", "?")[:16]
                    pending.append(f"[{ts}] {m.get('finding', '')}")
            except json.JSONDecodeError:
                continue
        if pending:
            sections.append("## 待 Mason 决策的事项\n" + "\n".join(pending))

    # 5. Gateway 进程状态
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "mason-gateway"],
            capture_output=True, text=True, timeout=5
        )
        gw_status = result.stdout.strip()
    except Exception:
        gw_status = "unknown"
    sections.append(f"## Gateway 进程状态: {gw_status}")

    return "\n\n".join(sections)


def query_claude(question: str, context: str) -> str:
    """调用 Claude API 回答问题"""
    import anthropic

    client = anthropic.Anthropic()

    system_prompt = """你是 Mason Hub 的系统状态助手。Mason 通过 Slack 问你系统的运行状况。

你的职责：
- 基于提供的系统上下文，简洁准确地回答 Mason 的问题
- 重点突出需要人工介入的事项（status=pending_mason）
- 如果系统正常就简短说正常，不要啰嗦
- 如果有问题，说清楚：什么问题、持续多久、影响什么、需不需要介入
- 用中文回答，语气简洁直接（像值班员汇报）
- 不要用 markdown 标题，Slack 不渲染。用 emoji + 粗体即可
- 时间用美东时间 (ET) 标注"""

    user_msg = f"""Mason 问：{question}

--- 系统状态上下文 ---
{context}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )

    return response.content[0].text


def handle_question(question: str) -> str:
    """处理问题，返回回答"""
    log(f"收到问题: {question}")
    context = gather_context()
    log(f"上下文: {len(context)} 字符")
    answer = query_claude(question, context)
    log(f"回答: {answer[:100]}...")
    return answer


# === Socket Mode ===

def start_socket_mode():
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    @app.command("/ask")
    def handle_ask(ack, command, respond):
        # 立即 ack，Slack 要求 3 秒内响应
        ack("🤔 查询中...")

        text = command.get("text", "").strip()
        if not text:
            text = "现在什么状态"

        user = command.get("user_name", "unknown")
        log(f"Slack /ask from {user}: {text}")

        try:
            answer = handle_question(text)
            respond(answer)
            log("已回复 Slack")
        except Exception as e:
            error_msg = f"❌ 查询失败: {e}"
            log(error_msg)
            respond(error_msg)

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    log("🚀 Slack Ask 服务启动 (Socket Mode)")
    handler.start()


# === 入口 ===

if __name__ == "__main__":
    load_env()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        question = sys.argv[2] if len(sys.argv) > 2 else "现在什么状态"
        context = gather_context()
        print(f"上下文长度: {len(context)} 字符\n")
        answer = query_claude(question, context)
        print(answer)
    else:
        # 检查必要的环境变量
        missing = []
        for key in ["SLACK_APP_TOKEN", "SLACK_BOT_TOKEN"]:
            if not os.environ.get(key):
                missing.append(key)
        if missing:
            print(f"❌ 缺少环境变量: {', '.join(missing)}")
            print("请在 .env 中添加:")
            print("  SLACK_APP_TOKEN=xapp-...  (App-Level Token, connections:write)")
            print("  SLACK_BOT_TOKEN=xoxb-...  (Bot User OAuth Token)")
            sys.exit(1)

        start_socket_mode()
