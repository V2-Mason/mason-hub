#!/usr/bin/env python3
"""
Mason Gateway — 永驻 daemon，Mason Hub 的值班员工

架构（对标 OpenClaw Gateway）:
  MASONHUB.md       = 灵魂文件（权限 + 检查清单）
  SYSTEM_MAP.md     = 系统状态（动态，session 写回）
  mason-gateway.py  = Gateway（本文件，永驻 daemon）
  scripts/          = Skills（纯脚本，零成本执行）
  Anthropic API     = 推理引擎（按需调用，$0.005/次）

执行模型:
  任务队列串行执行，一次只跑一个 → 天然无并发冲突
  Mason 开 Claude Code session → Gateway 自动让路
  Mason 不在 → Gateway 自主执行 heartbeat + 纯脚本任务

两层执行:
  Tier 1: 纯脚本（data-sync, health-check）→ 直接 subprocess，零成本
  Tier 2: 需要推理（判断异常, 分析事件）→ 调 Anthropic API，~$0.005/次

成本:
  heartbeat 每小时 1 次 × 14h = ~$0.07/天
  事件触发按需调 API = ~$0.02/天（估）
  合计 ~$3/月

用法:
  python3 mason-gateway.py                # 前台运行
  python3 mason-gateway.py --daemon       # 后台运行（systemd 推荐）
  python3 mason-gateway.py --once         # 只跑一轮（调试）
  python3 mason-gateway.py --status       # 查看状态

systemd:
  [Unit]
  Description=Mason Gateway
  After=network.target

  [Service]
  Type=simple
  ExecStart=/home/hangn/mason-hub/.venv/bin/python3 /home/hangn/mason-hub/scripts/mason-gateway.py
  Restart=always
  RestartSec=30
  Environment=HUB_DIR=/home/hangn/mason-hub

  [Install]
  WantedBy=multi-user.target
"""

import json
import os
import signal
import subprocess
import sys
import time
import fcntl
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- 配置 ---

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
MODEL = os.environ.get("HEARTBEAT_MODEL", "claude-sonnet-4-20250514")
MAX_OUTPUT_TOKENS = 800
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

LOG_FILE = HUB_DIR / "logs" / "gateway.log"
LOCK_FILE = HUB_DIR / "data" / "gateway.lock"
QUEUE_FILE = HUB_DIR / "data" / "events" / "queue.jsonl"
MASONHUB_FILE = HUB_DIR / "MASONHUB.md"

HEARTBEAT_INTERVAL = 3600      # 秒（1 小时）
QUEUE_CHECK_INTERVAL = 60      # 秒（1 分钟检查一次事件队列）
LOCK_TIMEOUT = 600             # 秒（10 分钟无响应自动释放锁）

CST = timezone(timedelta(hours=8))

# 全局状态
running = True
last_heartbeat = 0
task_queue = deque()
queue_file_pos = 0  # 记住 queue.jsonl 读到哪里了


# --- 工具函数 ---

def log(message: str):
    """追加日志"""
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S CST")
    entry = f"[{ts}] {message}"
    print(entry, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def read_file(path: Path, max_lines: int = 0) -> str:
    try:
        text = path.read_text()
        if max_lines > 0:
            return "\n".join(text.strip().split("\n")[:max_lines])
        return text
    except FileNotFoundError:
        return f"[文件不存在: {path}]"


def in_time_window() -> bool:
    """CST 08:00-22:00"""
    return 8 <= datetime.now(CST).hour < 22


def send_slack(message: str, prefix: str = "🫀 Gateway"):
    if not SLACK_WEBHOOK:
        return
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", SLACK_WEBHOOK,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"text": f"{prefix}\n{message}"})],
            capture_output=True, timeout=10,
        )
    except Exception as e:
        log(f"Slack 发送失败: {e}")


# --- Mason Session 检测 ---

def mason_session_active() -> bool:
    """检测 Mason 是否在 Claude Code session 中"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# --- 锁管理 ---

def acquire_lock() -> bool:
    """获取 Gateway 单例锁"""
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_data = {"pid": os.getpid(), "time": time.time()}

        # 检查现有锁
        if LOCK_FILE.exists():
            try:
                existing = json.loads(LOCK_FILE.read_text())
                pid = existing.get("pid", 0)
                lock_time = existing.get("time", 0)

                # 进程还活着 → 已有 Gateway 在跑
                try:
                    os.kill(pid, 0)
                    if time.time() - lock_time < LOCK_TIMEOUT:
                        return False  # 真的在跑
                except ProcessLookupError:
                    pass  # 进程已死，接管

            except (json.JSONDecodeError, KeyError):
                pass  # 锁文件损坏，接管

        LOCK_FILE.write_text(json.dumps(lock_data))
        return True
    except Exception as e:
        log(f"锁获取失败: {e}")
        return False


def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def refresh_lock():
    """刷新锁的时间戳，防止超时"""
    try:
        lock_data = {"pid": os.getpid(), "time": time.time()}
        LOCK_FILE.write_text(json.dumps(lock_data))
    except Exception:
        pass


# --- 事件队列扫描 ---

def scan_event_queue():
    """扫描 queue.jsonl 的新事件，放入任务队列"""
    global queue_file_pos

    if not QUEUE_FILE.exists():
        return

    try:
        with open(QUEUE_FILE) as f:
            f.seek(queue_file_pos)
            new_lines = f.readlines()
            queue_file_pos = f.tell()

        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                task_queue.append({
                    "type": "event",
                    "event": event,
                    "source": "queue.jsonl",
                })
            except json.JSONDecodeError:
                continue

        if new_lines:
            log(f"扫描到 {len(new_lines)} 个新事件")
    except Exception as e:
        log(f"事件队列扫描失败: {e}")


# --- Tier 1: 纯脚本执行（零成本）---

SCRIPT_TASKS = {
    "data-sync": {
        "script": "data/pipelines/data-sync.sh",
        "desc": "数据同步（阿里云→GCP）",
    },
    "health-check": {
        "script": "data/pipelines/data_health_check.sh",
        "desc": "数据健康检查",
    },
    "event-router-process": {
        "script_cmd": [sys.executable, "scripts/event_router.py", "--process-new"],
        "desc": "事件路由处理",
    },
    "dispatcher-scan": {
        "script": "scripts/dispatcher.sh",
        "desc": "Dispatcher 任务扫描",
    },
}


def execute_script(task_id: str) -> dict:
    """Tier 1: 直接执行脚本，零 API 成本"""
    task_def = SCRIPT_TASKS.get(task_id)
    if not task_def:
        return {"ok": False, "error": f"未知脚本任务: {task_id}"}

    log(f"[Tier 1] 执行脚本: {task_def['desc']}")

    try:
        if "script_cmd" in task_def:
            cmd = task_def["script_cmd"]
        else:
            script_path = HUB_DIR / task_def["script"]
            if not script_path.exists():
                return {"ok": False, "error": f"脚本不存在: {script_path}"}
            cmd = ["bash", str(script_path)]

        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            cwd=str(HUB_DIR),
            timeout=300,  # 5 分钟超时
        )

        success = result.returncode == 0
        log(f"[Tier 1] {task_def['desc']}: {'✅' if success else '❌'}")

        return {
            "ok": success,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        log(f"[Tier 1] {task_def['desc']}: ⏰ 超时")
        return {"ok": False, "error": "执行超时 (5min)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Tier 2: API 推理（按需调用）---

def collect_context() -> dict:
    """收集系统上下文"""
    ctx = {}
    ctx["masonhub"] = read_file(MASONHUB_FILE)

    # 最近事件
    if QUEUE_FILE.exists():
        lines = QUEUE_FILE.read_text().strip().split("\n")
        ctx["recent_events"] = "\n".join(lines[-10:])
    else:
        ctx["recent_events"] = "[无事件]"

    # git log
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, cwd=HUB_DIR, timeout=5,
        )
        ctx["recent_commits"] = r.stdout.strip()
    except Exception:
        ctx["recent_commits"] = "[git 失败]"

    # 系统健康
    health = []
    for cmd in [["uptime"], ["free", "-h"], ["df", "-h", "/"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if cmd[0] == "uptime":
                health.append(f"uptime: {r.stdout.strip()}")
            elif cmd[0] == "free":
                health.append("\n".join(r.stdout.strip().split("\n")[:2]))
            else:
                health.append(r.stdout.strip().split("\n")[-1])
        except Exception:
            pass
    ctx["system_health"] = "\n".join(health) if health else "[检查失败]"

    # 阿里云
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "root@106.14.44.68", "echo ok"],
            capture_output=True, text=True, timeout=8,
        )
        ctx["aliyun"] = "✅ 连通" if "ok" in r.stdout else "❌ 不通"
    except Exception:
        ctx["aliyun"] = "❌ 超时"

    # dispatcher 日志
    dlog = HUB_DIR / "logs" / "dispatcher.log"
    ctx["dispatcher_log"] = read_file(dlog, max_lines=5) if dlog.exists() else "[未运行]"

    return ctx


def call_api(prompt: str) -> str:
    """调用 Anthropic API"""
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def run_heartbeat():
    """Tier 2: Heartbeat 检查 — 调 API 判断系统状态"""
    log("[Tier 2] Heartbeat 开始")

    ctx = collect_context()
    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")

    prompt = f"""当前时间: {now_cst}

{ctx['masonhub']}

--- 实时数据 ---

最近事件:
{ctx['recent_events']}

最近 commits:
{ctx['recent_commits']}

系统健康:
{ctx['system_health']}
阿里云: {ctx['aliyun']}

Dispatcher 日志:
{ctx['dispatcher_log']}

---

按照 MASONHUB 检查清单逐项检查。
如果一切正常，只回复"✅ 系统正常"。
如果有异常，格式：[级别] 一句话总结 + 详情 + 建议行动。"""

    try:
        result = call_api(prompt)
        log(f"[Tier 2] Heartbeat 响应: {result[:100]}...")

        is_normal = result.strip().startswith("✅") and len(result.strip()) < 50
        if not is_normal:
            send_slack(result)
            log("[Tier 2] 📨 异常已发 Slack")
        else:
            log("[Tier 2] ✅ 系统正常")

    except Exception as e:
        error_msg = f"❌ Heartbeat API 失败: {e}"
        log(error_msg)
        send_slack(error_msg)


def analyze_event(event: dict):
    """Tier 2: 分析事件 — 需要推理的事件调 API"""
    event_type = event.get("event", "unknown")
    level = event.get("level", 0)

    # Level 0-1: 纯脚本处理，不调 API
    if level <= 1:
        log(f"[Tier 1] 事件 {event_type} (L{level}): 静默处理")
        # 触发对应的脚本
        if event_type == "data-sync-complete":
            execute_script("event-router-process")
        elif event_type in ("health-check-all-green", "health-check-failed"):
            execute_script("event-router-process")
        return

    # Level 2-3: 需要推理
    log(f"[Tier 2] 事件 {event_type} (L{level}): 需要推理")
    masonhub = read_file(MASONHUB_FILE)
    now_cst = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")

    prompt = f"""当前时间: {now_cst}

{masonhub}

--- 需要处理的事件 ---

{json.dumps(event, ensure_ascii=False, indent=2)}

---

分析这个事件，判断：
1. 这个事件意味着什么
2. 是否需要通知 Mason
3. 有没有可以自动执行的脚本来处理
回复格式：[行动] 具体建议（一行即可）"""

    try:
        result = call_api(prompt)
        log(f"[Tier 2] 事件分析: {result[:100]}...")

        # Level 3 事件必须通知 Mason
        if level >= 3:
            send_slack(f"🔴 L3 事件: {event_type}\n{result}", prefix="🫀 Gateway 事件")
        elif "通知" in result or "告警" in result:
            send_slack(f"⚠️ {event_type}\n{result}", prefix="🫀 Gateway 事件")

    except Exception as e:
        log(f"[Tier 2] 事件分析失败: {e}")


# --- 主循环 ---

def process_queue():
    """处理任务队列（串行，一次一个）"""
    if not task_queue:
        return

    # Mason 在 session 中 → 让路
    if mason_session_active():
        log("🛑 Mason session 活跃，Gateway 让路")
        return

    task = task_queue.popleft()
    task_type = task.get("type", "unknown")

    try:
        if task_type == "heartbeat":
            run_heartbeat()
        elif task_type == "event":
            analyze_event(task["event"])
        elif task_type == "script":
            execute_script(task["task_id"])
        else:
            log(f"未知任务类型: {task_type}")
    except Exception as e:
        log(f"任务执行异常: {e}")


def schedule_heartbeat():
    """检查是否需要调度 heartbeat"""
    global last_heartbeat
    now = time.time()

    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        if in_time_window():
            task_queue.append({"type": "heartbeat"})
            last_heartbeat = now
            log("📅 Heartbeat 已排入队列")
        else:
            log("⏰ 窗口外，跳过 heartbeat")
            last_heartbeat = now  # 避免窗口外反复检查


def main_loop():
    """Gateway 主循环"""
    global running

    log("🚀 Mason Gateway 启动")
    send_slack("🚀 Mason Gateway 已启动", prefix="")

    # 立即跑一次 heartbeat
    last_check = time.time()
    schedule_heartbeat()

    while running:
        try:
            now = time.time()

            # 1. 定期调度 heartbeat
            schedule_heartbeat()

            # 2. 扫描事件队列（每分钟）
            if now - last_check >= QUEUE_CHECK_INTERVAL:
                scan_event_queue()
                last_check = now

            # 3. 处理任务队列
            process_queue()

            # 4. 刷新锁
            refresh_lock()

            # 5. 休眠（30 秒一轮）
            time.sleep(30)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"主循环异常: {e}")
            time.sleep(60)  # 异常后等 1 分钟再继续


def show_status():
    """显示 Gateway 状态"""
    print("Mason Gateway 状态:")

    # 锁状态
    if LOCK_FILE.exists():
        try:
            lock = json.loads(LOCK_FILE.read_text())
            pid = lock.get("pid", "?")
            lock_time = lock.get("time", 0)
            age = time.time() - lock_time
            alive = False
            try:
                os.kill(pid, 0)
                alive = True
            except (ProcessLookupError, TypeError):
                pass
            print(f"  锁: PID {pid} ({'运行中' if alive else '已死'}, {age:.0f}s 前)")
        except Exception:
            print("  锁: 损坏")
    else:
        print("  锁: 无（Gateway 未运行）")

    # Mason session
    print(f"  Mason session: {'🟢 活跃' if mason_session_active() else '⚪ 不在'}")

    # 时间窗口
    print(f"  时间窗口: {'✅ CST 08-22 内' if in_time_window() else '❌ 窗口外'}")

    # 事件队列
    if QUEUE_FILE.exists():
        lines = QUEUE_FILE.read_text().strip().split("\n")
        print(f"  事件队列: {len(lines)} 条总记录")
    else:
        print("  事件队列: 无")

    # 脚本任务
    print(f"  可用脚本: {len(SCRIPT_TASKS)} 个")
    for tid, tdef in SCRIPT_TASKS.items():
        print(f"    - {tid}: {tdef['desc']}")


def handle_signal(signum, frame):
    global running
    log(f"收到信号 {signum}，准备关闭...")
    running = False


def main():
    args = sys.argv[1:]

    if "--status" in args:
        show_status()
        return

    if "--once" in args:
        # 只跑一轮（调试用）
        log("--- 单次运行模式 ---")
        scan_event_queue()
        if not mason_session_active() and in_time_window():
            run_heartbeat()
        else:
            log("跳过 heartbeat（Mason 活跃或窗口外）")
        return

    # 获取锁
    if not acquire_lock():
        print("Gateway 已在运行，退出")
        sys.exit(1)

    # 信号处理
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        main_loop()
    finally:
        release_lock()
        log("🛑 Mason Gateway 已关闭")
        send_slack("🛑 Mason Gateway 已关闭", prefix="")


if __name__ == "__main__":
    main()
