#!/bin/bash
# xhs-crawl.sh — XHS 两层采集调度器（多账号 + 拟人化）
# 用法: xhs-crawl.sh --task <1|2|3|4> [--account A] [--pages 1] [--top-n 10] [--no-delay]
#
# 账号分配:
#   A 号（内容博主） → Task 1 内容灵感 + Task 4 趋势发现
#   B 号（选品生意） → Task 2 选品情报 + Task 3 竞品监控
#
# 拟人化:
#   - Cron 触发后随机延迟 0-45 分钟再开始（--no-delay 跳过）
#   - 每次只搜部分关键词（随机选 2-3 个），不全搜
#   - Python 脚本内部有浏览延迟和首页暖场

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh

# --- Parse args ---
TASK=""
ACCOUNT=""
PAGES=1
TOP_N=10
NO_DELAY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    --account) ACCOUNT="$2"; shift 2 ;;
    --pages) PAGES="$2"; shift 2 ;;
    --top-n) TOP_N="$2"; shift 2 ;;
    --no-delay) NO_DELAY=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$TASK" ]; then
  echo "Usage: xhs-crawl.sh --task <1|2|3|4> [--account A] [--pages 1] [--top-n 10] [--no-delay]"
  exit 1
fi

# --- Task config ---
# KW_PER_RUN: 每次随机选几个关键词（不全搜，分散风险）
case "$TASK" in
  1)
    TASK_NAME="内容灵感"
    DEFAULT_ACCOUNT="A"
    ALL_KEYWORDS="韩国护肤,韩国好物,韩国美妆教程,韩国零食,韩国代购"
    KW_PER_RUN=3
    ;;
  2)
    TASK_NAME="选品情报"
    DEFAULT_ACCOUNT="B"
    ALL_KEYWORDS="水乳推荐,精华液推荐,面膜推荐,防晒推荐"
    KW_PER_RUN=2
    ;;
  3)
    TASK_NAME="竞品监控"
    DEFAULT_ACCOUNT="B"
    TOP_BRANDS=$(ssh -o ConnectTimeout=10 "$ALIYUN" bash -c \
      "'sqlite3 /opt/surenxuan/data/kbeauty.db \"SELECT brand_cn FROM products WHERE brand_cn IS NOT NULL AND length(brand_cn)>0 GROUP BY UPPER(brand_cn) ORDER BY COUNT(*) DESC LIMIT 5\"'" 2>/dev/null \
      | while read -r b; do echo "${b}测评"; done \
      | paste -sd, -)
    FIXED_KEYWORDS="韩国代购店铺,oliveyoung代购,韩国护肤代购"
    if [ -n "$TOP_BRANDS" ]; then
      ALL_KEYWORDS="${TOP_BRANDS},${FIXED_KEYWORDS}"
    else
      ALL_KEYWORDS="$FIXED_KEYWORDS"
    fi
    KW_PER_RUN=3
    ;;
  4)
    TASK_NAME="趋势发现"
    DEFAULT_ACCOUNT="A"
    ALL_KEYWORDS="护肤成分趋势,爆款护肤品,新品护肤"
    KW_PER_RUN=3
    ;;
  *)
    echo "ERROR: Invalid task: $TASK (expected 1-4)"
    exit 1
    ;;
esac

# Auto-select account if not specified
if [ -z "$ACCOUNT" ]; then
  ACCOUNT="$DEFAULT_ACCOUNT"
fi

# Keyword rotation: shuffle and pick subset
KEYWORDS=$(echo "$ALL_KEYWORDS" | tr ',' '\n' | shuf | head -"$KW_PER_RUN" | paste -sd, -)

echo "=== XHS Crawl: Task $TASK — $TASK_NAME ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"
echo "Account: $ACCOUNT"
echo "Keywords (this run): $KEYWORDS"
echo "Full pool: $ALL_KEYWORDS"
echo "Pages: $PAGES, Top-N: $TOP_N"

# --- Random startup delay (0-45 min) ---
if [ "$NO_DELAY" = false ]; then
  DELAY=$((RANDOM % 2700))
  echo ""
  echo "Random delay: ${DELAY}s (~$((DELAY / 60))min)"
  sleep "$DELAY"
fi

if [ -z "$KEYWORDS" ]; then
  echo "SKIP: no keywords"
  log_event "xhs-crawler" "crawl-task-$TASK" "info" "Skipped: keywords empty"
  exit 0
fi

# --- Ensure accounts.json exists on Aliyun ---
ssh -o ConnectTimeout=10 "$ALIYUN" "test -f $MC_DIR/accounts.json" 2>/dev/null
if [ $? -ne 0 ]; then
  echo ""
  echo "--- Initializing accounts.json on Aliyun ---"
  scp -o ConnectTimeout=10 "$HUB_DIR/shared/accounts.template.json" "$ALIYUN:$MC_DIR/accounts.json"
fi

# --- Count before ---
BEFORE_COUNT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "sqlite3 $MC_DIR/database/sqlite_tables.db 'SELECT COUNT(*) FROM xhs_note'" 2>/dev/null || echo "0")
echo ""
echo "Notes before: $BEFORE_COUNT"

# --- Sync crawl script ---
echo ""
echo "--- Syncing crawl script ---"
scp -o ConnectTimeout=10 "$HUB_DIR/skills/_two_tier_crawl.py" "$ALIYUN:$MC_DIR/two_tier_crawl.py"

# --- Run two-tier crawl ---
log_event "xhs-crawler" "crawl-task-$TASK" "start" "Task $TASK ($TASK_NAME), account: $ACCOUNT, keywords: $KEYWORDS"

echo ""
echo "--- Running two-tier crawl ---"
CRAWL_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 "$ALIYUN" \
  "cd $MC_DIR && source venv/bin/activate && python two_tier_crawl.py --account '$ACCOUNT' --keywords '$KEYWORDS' --pages $PAGES --top-n $TOP_N 2>&1")

CRAWL_EXIT=$?
echo "$CRAWL_OUTPUT"

# Check for cookie expiration (exit code 2 from Python)
if echo "$CRAWL_OUTPUT" | grep -q "Cookie EXPIRED"; then
  echo ""
  echo "ABORT: Cookie expired for account $ACCOUNT"
  log_event "xhs-crawler" "crawl-task-$TASK" "error" "Cookie expired for account $ACCOUNT"
  MSG="🍪 *XHS Cookie 过期*: 账号 $ACCOUNT
• 任务 $TASK ($TASK_NAME) 无法执行
• 请登录该账号的小红书网页版 → F12 → Cookies → 复制整串
• 然后告诉我更新 accounts.json"
  notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Crawler" ":cookie:"
  exit 1
fi

if [ $CRAWL_EXIT -ne 0 ]; then
  echo "ERROR: Crawl failed (exit $CRAWL_EXIT)"
  log_event "xhs-crawler" "crawl-task-$TASK" "error" "Crawl failed (exit $CRAWL_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 采集失败*: Task $TASK ($TASK_NAME) 账号 $ACCOUNT — exit $CRAWL_EXIT" "XHS Crawler" ":x:"
  exit 1
fi

# --- Count after ---
AFTER_COUNT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "sqlite3 $MC_DIR/database/sqlite_tables.db 'SELECT COUNT(*) FROM xhs_note'" 2>/dev/null || echo "0")
NEW_COUNT=$((AFTER_COUNT - BEFORE_COUNT))

# --- Extract detail stats from output ---
DETAIL_OK=$(echo "$CRAWL_OUTPUT" | grep -c '  OK   ' || echo "0")

echo ""
echo "Notes after: $AFTER_COUNT"
echo "New: $NEW_COUNT (${DETAIL_OK} with detail)"

log_event "xhs-crawler" "crawl-task-$TASK" "end" "Task $TASK done, account: $ACCOUNT, new: $NEW_COUNT, detail: $DETAIL_OK, total: $AFTER_COUNT"

# --- Slack report ---
MSG="📥 *XHS 采集完成*: Task $TASK ($TASK_NAME)
• 账号: $ACCOUNT
• 关键词: $KEYWORDS
• 新增: $NEW_COUNT 条（${DETAIL_OK} 条含完整内容）
• 数据库: $AFTER_COUNT 条
• 模式: ${PAGES} 页/词 + Top ${TOP_N} 深挖
• 时间: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Crawler" ":inbox_tray:"
echo ""
echo "=== XHS Crawl Complete ==="
