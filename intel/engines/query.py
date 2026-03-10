"""
Scout v2 — QueryEngine: ReflectionNode + 多源搜索

从 SpiderEngine 提取的 topics 出发，通过 UnifiedSearch 搜索多个源，
用 ReflectionNode 评估结果质量并精炼查询，最终写入 scout.db。

参考 BettaFish QueryEngine 的 ReflectionNode 模式。
"""

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from .database import init_db, upsert_intel_items, get_topics_for_week, link_topic_intel
from .llm_client import call_llm_json, load_config
from .search import UnifiedSearch, SearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def _query_config() -> dict:
    """返回 config.yaml 中 query 段。"""
    cfg = load_config()
    return cfg.get("query", {})


# ---------------------------------------------------------------------------
# Priority 映射
# ---------------------------------------------------------------------------

_PRIORITY_MAP = {
    "high": "red",
    "medium": "yellow",
    "low": "green",
}


def _map_priority(topic_priority: str) -> str:
    """topic priority → intel_item priority (red/yellow/green)."""
    return _PRIORITY_MAP.get(topic_priority, "yellow")


# ---------------------------------------------------------------------------
# SearchResult → intel_item 转换
# ---------------------------------------------------------------------------

def _result_to_intel_item(result: SearchResult, topic: dict, today: str) -> dict:
    """将 SearchResult 转为 intel_item dict，可直接传 upsert_intel_items。"""
    # 用 URL 的 hash 做稳定 ID（相同 URL 跨 topic 去重）
    url_hash = hashlib.sha256(result.url.encode("utf-8")).hexdigest()[:16]
    item_id = f"query-{url_hash}"

    raw_json = json.dumps(asdict(result), ensure_ascii=False, default=str)

    return {
        "id": item_id,
        "date": today,
        "title": result.title,
        "summary": result.snippet[:500] if result.snippet else "",
        "url": result.url,
        "source": result.source,
        "priority": _map_priority(topic.get("priority", "medium")),
        "domain": topic.get("domain", "tech"),
    }


# ---------------------------------------------------------------------------
# ReflectionNode
# ---------------------------------------------------------------------------

_REFLECTION_SYSTEM = (
    "You are a search quality evaluator. "
    "Given a search topic and its results, determine if the results are "
    "relevant and diverse enough. Respond with valid JSON only."
)

_REFLECTION_PROMPT = """## Topic
Keyword: {keyword}
Domain: {domain}
Reason: {reason}

## Search Results ({count} items)
{results_text}

## Task
Evaluate these search results:
1. Are they relevant to the topic keyword and reason?
2. Do they provide diverse perspectives (not all from same site)?
3. Are there obvious gaps?

Respond with JSON:
{{
  "sufficient": true/false,
  "refined_query": "a better search query if not sufficient, empty string if sufficient",
  "reasoning": "1-2 sentences explaining your evaluation"
}}
"""


def _format_results_for_reflection(results: list[SearchResult]) -> str:
    """格式化搜索结果供 LLM 评估。"""
    lines = []
    for i, r in enumerate(results[:10], 1):
        lines.append(f"{i}. [{r.source}] {r.title}")
        if r.snippet:
            lines.append(f"   {r.snippet[:150]}")
    return "\n".join(lines) if lines else "(no results)"


def _reflect_on_results(
    topic: dict,
    results: list[SearchResult],
    model: str = "default",
) -> dict:
    """ReflectionNode: LLM 评估搜索结果质量，返回评估结果。

    Returns:
        {"sufficient": bool, "refined_query": str, "reasoning": str}
    """
    prompt = _REFLECTION_PROMPT.format(
        keyword=topic.get("keyword", ""),
        domain=topic.get("domain", ""),
        reason=topic.get("reason", ""),
        count=len(results),
        results_text=_format_results_for_reflection(results),
    )

    try:
        evaluation = call_llm_json(prompt, model=model, system=_REFLECTION_SYSTEM)
    except Exception as e:
        logger.warning("Reflection LLM call failed for '%s': %s", topic.get("keyword"), e)
        return {"sufficient": True, "refined_query": "", "reasoning": "LLM call failed, accepting results"}

    # 规范化返回
    return {
        "sufficient": bool(evaluation.get("sufficient", True)),
        "refined_query": str(evaluation.get("refined_query", "")).strip(),
        "reasoning": str(evaluation.get("reasoning", "")),
    }


# ---------------------------------------------------------------------------
# 单 topic 搜索流程
# ---------------------------------------------------------------------------

def _search_topic(
    topic: dict,
    searcher: UnifiedSearch,
    max_results: int = 10,
    reflection_enabled: bool = True,
    reflection_model: str = "default",
    search_diversity: bool = True,
) -> list[SearchResult]:
    """对单个 topic 执行搜索 + 可选 ReflectionNode 精炼。

    Returns:
        去重后的 SearchResult 列表。
    """
    keyword = topic.get("keyword", "")
    search_source = topic.get("search_source", "auto")

    if not keyword:
        logger.warning("Skipping topic with empty keyword")
        return []

    # --- 初始搜索 ---
    logger.info("Searching '%s' (source=%s)", keyword, search_source)

    if search_diversity and search_source in ("web", "auto"):
        # 多源搜索：同时搜 github + web
        results = searcher.search_multi(
            keyword,
            sources=["github", "web"],
            limit_per_source=max_results // 2,
        )
    else:
        results = searcher.search(keyword, source=search_source, limit=max_results)

    logger.info("Initial search for '%s': %d results", keyword, len(results))

    # --- ReflectionNode ---
    if not reflection_enabled or not results:
        return results[:max_results]

    evaluation = _reflect_on_results(topic, results, model=reflection_model)
    logger.info(
        "Reflection for '%s': sufficient=%s, reasoning=%s",
        keyword,
        evaluation["sufficient"],
        evaluation["reasoning"][:100],
    )

    if evaluation["sufficient"] or not evaluation["refined_query"]:
        return results[:max_results]

    # --- 精炼搜索（最多 1 轮） ---
    refined_query = evaluation["refined_query"]
    logger.info("Refined search for '%s' → '%s'", keyword, refined_query)

    refined_results = searcher.search(refined_query, source=search_source, limit=max_results)
    logger.info("Refined search got %d results", len(refined_results))

    # 合并去重
    seen_urls = {r.url for r in results}
    for r in refined_results:
        if r.url not in seen_urls:
            results.append(r)
            seen_urls.add(r.url)

    return results[:max_results]


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def run_query(topics: list[dict]) -> list[dict]:
    """主函数：对所有 topics 执行搜索 + Reflection，返回 intel_items。

    Args:
        topics: SpiderEngine 输出的话题列表，每项有
                keyword, domain, priority, search_source, reason, source

    Returns:
        list[dict] — intel_item 列表（已写入 scout.db）
    """
    qcfg = _query_config()
    max_results = qcfg.get("max_results_per_topic", 10)
    reflection_enabled = qcfg.get("reflection_enabled", True)
    reflection_model = qcfg.get("reflection_model", "default")
    search_diversity = qcfg.get("search_diversity", True)

    # 从 config 读 searxng url
    cfg = load_config()
    search_config = {}
    for src in qcfg.get("search_sources", []):
        if src.get("type") == "searxng" and src.get("base_url"):
            search_config["searxng_url"] = src["base_url"]
            break

    searcher = UnifiedSearch(search_config)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info(
        "QueryEngine: processing %d topics (reflection=%s, diversity=%s)",
        len(topics),
        reflection_enabled,
        search_diversity,
    )

    # --- 搜索所有 topics ---
    all_items: list[dict] = []
    seen_urls: set[str] = set()

    for topic in topics:
        try:
            results = _search_topic(
                topic,
                searcher,
                max_results=max_results,
                reflection_enabled=reflection_enabled,
                reflection_model=reflection_model,
                search_diversity=search_diversity,
            )
        except Exception as e:
            logger.warning(
                "Search failed for topic '%s': %s",
                topic.get("keyword", "?"),
                e,
            )
            continue

        # 转换为 intel_items，跨 topic 去重
        for result in results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)

            item = _result_to_intel_item(result, topic, today)
            all_items.append(item)

    logger.info("QueryEngine: collected %d unique intel items from %d topics", len(all_items), len(topics))

    # --- 写入数据库 ---
    if all_items:
        try:
            conn = init_db()
            upsert_intel_items(conn, all_items)

            # 建立 topic ↔ intel 关联（如果 topic 有 db id）
            for topic in topics:
                topic_id = topic.get("id")
                if topic_id is None:
                    continue
                keyword_lower = topic.get("keyword", "").lower()
                for item in all_items:
                    # 简单关联：标题或摘要包含关键词
                    title_lower = (item.get("title") or "").lower()
                    summary_lower = (item.get("summary") or "").lower()
                    if keyword_lower in title_lower or keyword_lower in summary_lower:
                        try:
                            link_topic_intel(conn, topic_id, item["id"], score=0.7)
                        except Exception:
                            pass  # 关联失败不影响主流程

            conn.close()
            logger.info("QueryEngine: wrote %d items to scout.db", len(all_items))
        except Exception as e:
            logger.error("QueryEngine: database write failed: %s", e)

    return all_items


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # 从 scout.db 加载本周 topics
    now = datetime.now(timezone.utc)
    week = f"{now.year}-W{now.isocalendar()[1]:02d}"

    print(f"Loading topics for week {week} from scout.db...")
    conn = init_db()
    topics = get_topics_for_week(conn, week)
    conn.close()

    if not topics:
        print("No topics found for this week. Run spider.py first.")
        raise SystemExit(1)

    print(f"Found {len(topics)} topics, starting QueryEngine...")
    items = run_query(topics)
    print(f"\nQueryEngine complete: {len(items)} intel items collected")
    for item in items[:20]:
        print(f"  [{item['priority']}] [{item['domain']}] {item['title'][:80]}")
        print(f"    {item['url']}")
