"""
Scout v2 — SpiderEngine: 采集调度 + 话题提取引擎

从 TrendRadar 热榜 + RSS 数据中，用 LLM 自动提取本周搜索关键词，
替代手动维护的固定关键词。同时整合 Radar 关注率反馈。

参考 BettaFish MindSpider 的 BroadTopicExtraction 模块。
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .database import get_topics_for_week, init_db, upsert_topics
from .llm_client import call_llm_json, load_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def _spider_config() -> dict:
    """返回 config.yaml 中 spider 段。"""
    cfg = load_config()
    return cfg.get("spider", {})


def _resolve_path(p: str) -> Path:
    """展开 ~ 并返回 Path。"""
    return Path(p).expanduser().resolve()


def _current_week() -> str:
    """返回当前 ISO 周标识，格式 '2026-W11'。"""
    now = datetime.now(timezone.utc)
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


# ---------------------------------------------------------------------------
# TrendRadar 热榜标题
# ---------------------------------------------------------------------------

def read_trendradar_titles(days: int = 3) -> list[dict]:
    """读 TrendRadar 最近 N 天的热榜标题。

    返回 [{"title": "...", "source": "baidu/weibo/...", "rank": 1}]
    数据源：~/mason-hub/tools/trendradar/output/news/YYYY-MM-DD.db
    表：news_items (title, platform_id, rank)
    """
    scfg = _spider_config()
    news_dir = _resolve_path(scfg.get(
        "trendradar_news_dir",
        "~/mason-hub/tools/trendradar/output/news/",
    ))

    results = []
    today = datetime.now(timezone.utc).date()

    for offset in range(days):
        date = today - timedelta(days=offset)
        db_path = news_dir / f"{date.isoformat()}.db"
        if not db_path.exists():
            logger.debug("News DB not found: %s", db_path)
            continue

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT title, platform_id, rank FROM news_items ORDER BY rank ASC"
            ).fetchall()
            for r in rows:
                results.append({
                    "title": r["title"],
                    "source": r["platform_id"],
                    "rank": r["rank"],
                })
            conn.close()
        except Exception as e:
            logger.warning("Error reading news DB %s: %s", db_path, e)

    return results


# ---------------------------------------------------------------------------
# TrendRadar RSS 标题
# ---------------------------------------------------------------------------

def read_rss_titles(days: int = 3) -> list[dict]:
    """读 TrendRadar 最近 N 天的 RSS 标题。

    返回 [{"title": "...", "source": "hacker-news/36kr/..."}]
    数据源：~/mason-hub/tools/trendradar/output/rss/YYYY-MM-DD.db
    表：rss_items (title, feed_id)
    """
    scfg = _spider_config()
    rss_dir = _resolve_path(scfg.get(
        "trendradar_rss_dir",
        "~/mason-hub/tools/trendradar/output/rss/",
    ))

    results = []
    today = datetime.now(timezone.utc).date()

    for offset in range(days):
        date = today - timedelta(days=offset)
        db_path = rss_dir / f"{date.isoformat()}.db"
        if not db_path.exists():
            logger.debug("RSS DB not found: %s", db_path)
            continue

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT title, feed_id FROM rss_items"
            ).fetchall()
            for r in rows:
                results.append({
                    "title": r["title"],
                    "source": r["feed_id"],
                })
            conn.close()
        except Exception as e:
            logger.warning("Error reading RSS DB %s: %s", db_path, e)

    return results


# ---------------------------------------------------------------------------
# Radar 关注率
# ---------------------------------------------------------------------------

def read_focus_rates() -> dict:
    """读 Radar 关注率反馈。

    返回 {"high_focus": ["topic1", ...], "dismissed": ["topic2", ...]}
    数据源：~/mason-hub/tools/radar-tracker/tracker.db
    - read_items 表 → 高关注（用户主动阅读）
    - dismissals 表 → 被忽略（用户划走）
    如果 tracker.db 不存在，返回空 dict。
    """
    tracker_path = _resolve_path("~/mason-hub/tools/radar-tracker/tracker.db")
    if not tracker_path.exists():
        logger.info("Radar tracker DB not found: %s", tracker_path)
        return {}

    result = {"high_focus": [], "dismissed": []}
    try:
        conn = sqlite3.connect(str(tracker_path))
        conn.row_factory = sqlite3.Row

        # 最近 7 天的阅读记录 → 高关注话题
        read_rows = conn.execute(
            "SELECT DISTINCT news_title FROM read_items "
            "WHERE read_at >= date('now', '-7 days') "
            "ORDER BY read_at DESC LIMIT 50"
        ).fetchall()
        result["high_focus"] = [r["news_title"] for r in read_rows]

        # 最近 7 天的忽略记录 → 不感兴趣的话题
        dismiss_rows = conn.execute(
            "SELECT DISTINCT news_title FROM dismissals "
            "WHERE dismissed_at >= date('now', '-7 days') "
            "ORDER BY dismissed_at DESC LIMIT 50"
        ).fetchall()
        result["dismissed"] = [r["news_title"] for r in dismiss_rows]

        conn.close()
    except Exception as e:
        logger.warning("Error reading tracker DB: %s", e)

    return result


# ---------------------------------------------------------------------------
# 固定关键词
# ---------------------------------------------------------------------------

_DEFAULT_FIXED_KEYWORDS = [
    {"keyword": "claude code agent", "domain": "tech", "priority": "high", "search_source": "github"},
    {"keyword": "AI agent framework", "domain": "tech", "priority": "high", "search_source": "github"},
    {"keyword": "MCP server", "domain": "tech", "priority": "medium", "search_source": "github"},
    {"keyword": "小红书 运营", "domain": "ecom", "priority": "high", "search_source": "web"},
    {"keyword": "跨境电商 韩国护肤", "domain": "ecom", "priority": "high", "search_source": "web"},
    {"keyword": "DTC brand", "domain": "ecom", "priority": "medium", "search_source": "github"},
    {"keyword": "content automation", "domain": "content", "priority": "medium", "search_source": "github"},
    {"keyword": "video generation AI", "domain": "content", "priority": "medium", "search_source": "github"},
    {"keyword": "social media trend", "domain": "content", "priority": "medium", "search_source": "web"},
    {"keyword": "GEO generative engine optimization", "domain": "content", "priority": "medium", "search_source": "web"},
]


def load_fixed_keywords() -> list[dict]:
    """读固定关键词文件。如果文件不存在，创建默认关键词。"""
    scfg = _spider_config()
    kw_path = _resolve_path(scfg.get(
        "fixed_keywords_file",
        "~/mason-hub/data/scout_keywords_fixed.json",
    ))

    if not kw_path.exists():
        logger.info("Fixed keywords file not found, creating default: %s", kw_path)
        kw_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kw_path, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_FIXED_KEYWORDS, f, ensure_ascii=False, indent=2)
        return list(_DEFAULT_FIXED_KEYWORDS)

    with open(kw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        logger.warning("Fixed keywords file is not a list, returning default")
        return list(_DEFAULT_FIXED_KEYWORDS)

    return data


# ---------------------------------------------------------------------------
# LLM 话题提取
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM = (
    "You are a trend analyst for a small team that operates in three domains: "
    "ecommerce (ecom), technology (tech), and content creation (content). "
    "Your job is to extract actionable search keywords from trending news headlines. "
    "Respond with valid JSON only."
)

_EXTRACT_PROMPT_TEMPLATE = """Below are trending headlines from the past few days.

## Hot News Headlines (top items from Chinese trending platforms)
{news_titles}

## RSS Feed Headlines (tech/business)
{rss_titles}

## User Focus Signals
{focus_signals}

## Domain Definitions
- ecom: 跨境电商、韩国护肤、小红书运营、DTC品牌、电商平台政策
- tech: AI 工具、Agent 框架、Claude/Anthropic、MCP、开源项目、开发者工具
- content: 内容自动化、视频生成、社交媒体趋势、GEO、内容运营

## Task
From these headlines, extract 10-20 search keywords that are worth investigating this week.
Focus on trends that are relevant to our three domains.

Rules:
- Each keyword should be a concise search query (2-5 words)
- Assign domain: ecom | tech | content
- Assign priority: high (directly relevant) | medium (worth watching)
- Assign search_source: github (for code/tools) | web (for news/analysis)
- Include a brief reason (1 sentence) explaining why this is worth searching
- Prioritize topics that the user has shown interest in (high_focus) and deprioritize dismissed topics
- Output ONLY a JSON array, no extra text

Output format:
[
  {{"keyword": "...", "domain": "ecom|tech|content", "priority": "high|medium", "search_source": "github|web", "reason": "..."}}
]
"""


def _build_extract_prompt(
    news: list[dict],
    rss: list[dict],
    focus: dict,
) -> str:
    """构建 LLM 提取 prompt。"""
    # 热榜：取 top 50 去重标题
    seen_titles = set()
    news_lines = []
    for item in news[:200]:
        title = item["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        news_lines.append(f"- [{item['source']}] {title}")
        if len(news_lines) >= 50:
            break

    # RSS：取前 30 去重
    rss_lines = []
    for item in rss[:100]:
        title = item["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        rss_lines.append(f"- [{item['source']}] {title}")
        if len(rss_lines) >= 30:
            break

    # 关注率信号
    focus_lines = []
    if focus.get("high_focus"):
        focus_lines.append("User READ these (high interest):")
        for t in focus["high_focus"][:10]:
            focus_lines.append(f"  + {t}")
    if focus.get("dismissed"):
        focus_lines.append("User DISMISSED these (low interest):")
        for t in focus["dismissed"][:10]:
            focus_lines.append(f"  - {t}")
    if not focus_lines:
        focus_lines.append("No user focus data available.")

    return _EXTRACT_PROMPT_TEMPLATE.format(
        news_titles="\n".join(news_lines) if news_lines else "(no news data)",
        rss_titles="\n".join(rss_lines) if rss_lines else "(no RSS data)",
        focus_signals="\n".join(focus_lines),
    )


def _llm_extract_topics(
    news: list[dict],
    rss: list[dict],
    focus: dict,
) -> list[dict]:
    """调用 LLM 从热榜标题中提取关键词。失败时返回空列表。"""
    prompt = _build_extract_prompt(news, rss, focus)

    try:
        result = call_llm_json(prompt, system=_EXTRACT_SYSTEM)
    except Exception as e:
        logger.error("LLM topic extraction failed: %s", e)
        return []

    # 结果可能是 dict 包裹或直接 list
    if isinstance(result, dict):
        # 尝试找 list 值
        for v in result.values():
            if isinstance(v, list):
                result = v
                break
        else:
            logger.warning("LLM returned dict without list value: %s", result)
            return []

    if not isinstance(result, list):
        logger.warning("LLM returned unexpected type: %s", type(result))
        return []

    # 验证并规范化每个条目
    valid = []
    for item in result:
        if not isinstance(item, dict) or "keyword" not in item:
            continue
        valid.append({
            "keyword": str(item["keyword"]).strip(),
            "domain": item.get("domain", "tech") if item.get("domain") in ("ecom", "tech", "content") else "tech",
            "priority": item.get("priority", "medium") if item.get("priority") in ("high", "medium") else "medium",
            "search_source": item.get("search_source", "web") if item.get("search_source") in ("github", "web") else "web",
            "reason": str(item.get("reason", "")),
        })

    return valid


# ---------------------------------------------------------------------------
# 去重合并
# ---------------------------------------------------------------------------

def _merge_and_dedup(
    llm_topics: list[dict],
    fixed_keywords: list[dict],
) -> list[dict]:
    """合并 LLM 提取的关键词和固定关键词，去重。

    固定关键词优先级不被 LLM 覆盖（source='fixed'）。
    """
    seen = {}  # keyword_lower -> topic dict

    # 固定关键词先放
    for kw in fixed_keywords:
        key = kw["keyword"].strip().lower()
        entry = {
            "keyword": kw["keyword"].strip(),
            "domain": kw.get("domain", "tech"),
            "priority": kw.get("priority", "medium"),
            "search_source": kw.get("search_source", "web"),
            "reason": kw.get("reason", "固定关注关键词"),
            "source": "fixed",
        }
        seen[key] = entry

    # LLM 提取的关键词：如果和固定关键词重复，跳过
    for topic in llm_topics:
        key = topic["keyword"].strip().lower()
        if key in seen:
            continue
        topic["source"] = "auto"
        seen[key] = topic

    return list(seen.values())


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def extract_topics(days: int = None) -> list[dict]:
    """主函数：从热榜提取本周搜索话题。

    1. 读 TrendRadar 热榜 + RSS 标题
    2. 读 Radar 关注率
    3. 调 LLM 提取关键词
    4. 合并固定关键词
    5. 去重
    6. 写入 database (upsert_topics)
    7. 返回合并后的关键词列表
    """
    scfg = _spider_config()
    if days is None:
        days = scfg.get("lookback_days", 3)

    logger.info("SpiderEngine: 开始提取话题 (lookback=%d days)", days)

    # 1. 读数据源
    news = read_trendradar_titles(days=days)
    rss = read_rss_titles(days=days)
    logger.info("读取热榜 %d 条, RSS %d 条", len(news), len(rss))

    # 2. 读关注率
    focus = read_focus_rates()
    logger.info(
        "关注率: high_focus=%d, dismissed=%d",
        len(focus.get("high_focus", [])),
        len(focus.get("dismissed", [])),
    )

    # 3. 调 LLM 提取
    llm_topics = _llm_extract_topics(news, rss, focus)
    logger.info("LLM 提取 %d 个关键词", len(llm_topics))

    # 4+5. 合并固定关键词 + 去重
    fixed = load_fixed_keywords()
    merged = _merge_and_dedup(llm_topics, fixed)
    logger.info("合并后共 %d 个关键词 (固定 %d + LLM %d)", len(merged), len(fixed), len(llm_topics))

    # 6. 写入数据库
    week = _current_week()
    try:
        conn = init_db()
        db_topics = []
        for t in merged:
            db_topics.append({**t, "week": week})
        upsert_topics(conn, db_topics)
        conn.close()
        logger.info("已写入数据库, week=%s", week)
    except Exception as e:
        logger.error("写入数据库失败: %s", e)

    # 7. 返回
    return merged


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    topics = extract_topics()
    print(f"\n提取 {len(topics)} 个关键词:")
    for t in topics:
        print(f"  [{t['domain']}] {t['keyword']} ({t['priority']}) — {t.get('reason', '')}")
