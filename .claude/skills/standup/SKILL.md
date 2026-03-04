---
name: standup
description: "晨会报告：昨日工作回顾、系统健康、今日待办、Scout 情报、成本概览"
---

# /standup — 晨会

执行以下步骤，汇总为一份简洁的晨会报告：

## 1. 昨日工作回顾
- 读取 logs/audit.jsonl 最近 24 小时的记录
- 统计：完成了几个任务、失败了几个、正在进行几个
- 列出每个完成任务的一句话摘要

## 2. 系统健康状态
运行以下检查：
```bash
# GCP 系统状态
uptime
df -h / | tail -1
free -h | head -2

# 检查关键服务
systemctl is-active cron 2>/dev/null || echo "cron: 未运行"

# 检查 crontab 任务是否注册
crontab -l 2>/dev/null | grep -c mason-hub || echo "cron 任务: 0 条"

# 检查阿里云连通性
timeout 5 ssh -o ConnectTimeout=3 root@106.14.44.68 "echo ok" 2>/dev/null && echo "阿里云: ✅ 连通" || echo "阿里云: ❌ 不通"

# 检查 Git 状态
cd ~/mason-hub && git status --short | head -5
cd ~/surenxuan && git status --short | head -5
```

## 3. 今日待办
- 读取 tasks/backlog.md，列出所有 status: ready 的任务
- 按优先级排序（P0 > P1 > P2）
- 如果没有待办，说"今日无待办任务"

## 4. Scout 情报摘要
- 读取 ~/mason-hub/intel/raw/ 目录下最近的情报文件（按日期排序取最新）
- 读取 ~/mason-hub/intel/digests/ 目录下最近一期周度简报
- 汇总：最近有几条新情报，其中 🔴 级几条（重点标注给 Mason）
- 如果 intel/ 目录不存在或为空，显示"暂无情报"
- 🔴 级情报必须逐条列出标题和建议行动

## 5. 成本概览
- 如果 logs/token-usage.log 存在，显示最近 7 天的 API 消耗趋势
- 如果不存在，跳过此项

## 输出格式
用简洁的结构化格式输出，不要过度格式化。一屏能看完最好。
例如：
```
📋 晨会 2026-02-28

昨日：完成 3 个任务，失败 0 个
  ✅ FIX-042: report 日期 bug
  ✅ FIX-043: 客户提示修复
  ✅ FEAT-012: 销售摘要 API

系统：GCP ✅ | 阿里云 ✅ | 磁盘 33% | cron 6 条
Git：mason-hub clean | surenxuan clean

今日待办：
  P1: 实现自定义日期范围报告
  P2: 优化产品列表加载速度

API 消耗：本周 $3.20（日均 $0.46）
```
