---
name: content-performance
description: 内容效果追踪 — 查看各平台发布内容的互动数据和趋势。五维 Gap #1 感知-数据回流。
user_invocable: true
---

# content-performance — 内容效果追踪

> **触发时机**：Mason 问"内容表现怎么样"、/standup 数据回流、PM 周报、手动调用
> **类型**：Stateless 查询工具，无副作用

## 用法

```bash
# 近 7 天全平台
python3 ~/mason-hub/skills/analytics/content-performance.py

# 指定平台和天数
python3 ~/mason-hub/skills/analytics/content-performance.py --platform xhs --days 14

# 人类可读摘要
python3 ~/mason-hub/skills/analytics/content-performance.py --format summary

# JSON（供下游消费）
python3 ~/mason-hub/skills/analytics/content-performance.py --format json
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--platform` | `all` | `xhs` / `socialmesh` / `all` |
| `--days` | `7` | 回看天数 |
| `--format` | `json` | `json` / `summary` |

## 输出指标

脚本使用 `data/tools/metrics.py` 标准口径：

- **interaction_score**: liked + collected×3 + comment×5 + shared×8
- **engage_rate**: 评赞比 (comment/liked ×100%)
- **save_rate**: 藏赞比 (collected/liked ×100%)
- **fake_traffic_flags**: 高赞低互动检测

### XHS 平台输出
- total_notes, avg_likes, avg_comments, avg_collects
- interaction_score（加权互动分）
- engage_rate, save_rate（质量指标）
- top_5 排行（按 interaction_score 降序）

### SocialMesh 平台输出
- posts_total, posts_success, posts_failed
- content_status 分布

## 数据源优先级

1. `data/mirrors/xhs_notes.db` (SQLite, 主数据源)
2. `data/reports/xhs_*.json` (分析报告, fallback)
3. `~/socialmesh/data/socialmesh.db` (SocialMesh)

## 下游集成

- `/standup` 引用内容数据回流
- PM 周报的内容表现板块
- `cross-correlate.py` 关联分析的输入源

## 注意事项

- 数据源不存在时返回 `status: "no_data"`，不报错
- 指标计算使用 `data/tools/metrics.py` SSOT，禁止本地重复实现
