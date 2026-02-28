#!/bin/bash
# xhs-crawl.sh — XHS 采集调度器
# 用法: xhs-crawl.sh --task <1|2|3|4>
#   1 = 内容灵感 (周二+周五)
#   2 = 选品情报 (周三)
#   3 = 竞品监控 (周四) — 自动从素仁轩产品库提取品牌名
#   4 = 趋势发现 (每月 1+15 号)

set -uo pipefail

HUB_DIR="$HOME/mason-hub"
source "$HUB_DIR/shared/common.sh"

ALIYUN="root@106.14.44.68"
MC_DIR="/opt/mediacrawler"
SLACK_CHANNEL="C0AHTA97EAY"  # #socialmesh

# --- Parse args ---
TASK=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$TASK" ]; then
  echo "Usage: xhs-crawl.sh --task <1|2|3|4>"
  exit 1
fi

# --- Task config ---
case "$TASK" in
  1)
    TASK_NAME="内容灵感"
    KEYWORDS="韩国护肤,韩国好物,韩国美妆教程,韩国零食,韩国代购"
    ;;
  2)
    TASK_NAME="选品情报"
    KEYWORDS="水乳推荐,精华液推荐,面膜推荐,防晒推荐"
    ;;
  3)
    TASK_NAME="竞品监控"
    # 自动从素仁轩产品库提取 Top 品牌（按产品数量排序，取前 5）
    # 每个品牌搜 "品牌名+测评" 更容易找到竞品对比内容
    TOP_BRANDS=$(ssh -o ConnectTimeout=10 "$ALIYUN" bash -c \
      "'sqlite3 /opt/surenxuan/data/kbeauty.db \"SELECT brand_cn FROM products WHERE brand_cn IS NOT NULL AND length(brand_cn)>0 GROUP BY UPPER(brand_cn) ORDER BY COUNT(*) DESC LIMIT 5\"'" 2>/dev/null \
      | while read -r b; do echo "${b}测评"; done \
      | paste -sd, -)
    # 固定竞品维度关键词
    FIXED_KEYWORDS="韩国代购店铺,oliveyoung代购,韩国护肤代购"
    if [ -n "$TOP_BRANDS" ]; then
      KEYWORDS="${TOP_BRANDS},${FIXED_KEYWORDS}"
    else
      KEYWORDS="$FIXED_KEYWORDS"
    fi
    ;;
  4)
    TASK_NAME="趋势发现"
    KEYWORDS="护肤成分趋势,爆款护肤品,新品护肤"
    ;;
  *)
    echo "ERROR: Invalid task number: $TASK (expected 1-4)"
    exit 1
    ;;
esac

echo "=== XHS Crawl: Task $TASK — $TASK_NAME ==="
echo "Time: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"
echo "Keywords: $KEYWORDS"

if [ -z "$KEYWORDS" ]; then
  echo "SKIP: Task $TASK ($TASK_NAME) — 关键词未配置，等 Mason 提供"
  log_event "xhs-crawler" "crawl-task-$TASK" "info" "Skipped: keywords not configured"
  notify_slack "$SLACK_CHANNEL" "⏭️ *XHS 采集跳过*: Task $TASK ($TASK_NAME) — 关键词未配置" "XHS Crawler" ":fast_forward:"
  exit 0
fi

# --- Cookie check ---
echo ""
echo "--- Cookie pre-check ---"
"$HUB_DIR/skills/xhs-cookie-check.sh" --notify
if [ $? -ne 0 ]; then
  echo "ABORT: Cookie expired, cannot crawl"
  log_event "xhs-crawler" "crawl-task-$TASK" "error" "Aborted: cookie expired"
  exit 1
fi

# --- Count before ---
BEFORE_COUNT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "sqlite3 $MC_DIR/database/sqlite_tables.db 'SELECT COUNT(*) FROM xhs_note'" 2>/dev/null || echo "0")
echo ""
echo "Notes before crawl: $BEFORE_COUNT"

# --- Run MediaCrawler ---
log_event "xhs-crawler" "crawl-task-$TASK" "start" "Starting task $TASK ($TASK_NAME), keywords: $KEYWORDS"

echo ""
echo "--- Running MediaCrawler ---"
CRAWL_OUTPUT=$(ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 "$ALIYUN" bash -s << REMOTE_EOF
cd $MC_DIR
source venv/bin/activate

# Run crawler with keywords
python main.py \
  --platform xhs \
  --lt cookie \
  --type search \
  --keywords "$KEYWORDS" \
  --save_data_option sqlite \
  --headless true \
  --enable_ip_proxy true \
  --ip_proxy_provider_name kuaidaili_tunnel \
  2>&1 | tail -50

echo "EXIT_CODE=\${PIPESTATUS[0]}"
REMOTE_EOF
)

SSH_EXIT=$?
echo "$CRAWL_OUTPUT"

# Check exit
if [ $SSH_EXIT -ne 0 ]; then
  echo "ERROR: SSH connection failed"
  log_event "xhs-crawler" "crawl-task-$TASK" "error" "SSH failed (exit $SSH_EXIT)"
  notify_slack "$SLACK_CHANNEL" "❌ *XHS 采集失败*: Task $TASK ($TASK_NAME) — SSH 连接失败" "XHS Crawler" ":x:"
  exit 1
fi

# --- Count after ---
AFTER_COUNT=$(ssh -o ConnectTimeout=10 "$ALIYUN" \
  "sqlite3 $MC_DIR/database/sqlite_tables.db 'SELECT COUNT(*) FROM xhs_note'" 2>/dev/null || echo "0")
NEW_COUNT=$((AFTER_COUNT - BEFORE_COUNT))

echo ""
echo "Notes after crawl: $AFTER_COUNT"
echo "New notes: $NEW_COUNT"

log_event "xhs-crawler" "crawl-task-$TASK" "end" "Task $TASK done, new notes: $NEW_COUNT, total: $AFTER_COUNT"

# --- Slack report ---
MSG="📥 *XHS 采集完成*: Task $TASK ($TASK_NAME)
• 关键词: $KEYWORDS
• 新增笔记: $NEW_COUNT 条
• 数据库总量: $AFTER_COUNT 条
• 时间: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M CST')"

notify_slack "$SLACK_CHANNEL" "$MSG" "XHS Crawler" ":inbox_tray:"
echo ""
echo "=== XHS Crawl Complete ==="
