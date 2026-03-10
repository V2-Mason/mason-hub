"""
Scout v2 — InsightEngine

把外部情报和内部数据（XHS 笔记、销售数据、历史情报）关联，
从「通用情报」变成「对我们意味着什么」。附加 DeepSeek 情感分析。

内部数据源：
- mirror DB (data/mirror/sqlite_tables.db) — XHS 笔记 1168 条
- 素仁轩 sales API (106.14.44.68:8000) — JWT 认证
- scout_normalized.jsonl — 历史情报
"""

import json
import logging
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path

import requests

from .database import init_db, update_intel_enrichment
from .llm_client import call_llm_json, load_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

_HUB_DIR = Path(__file__).resolve().parents[2]


def _get_insight_config() -> dict:
    cfg = load_config()
    return cfg.get("insight", {})


def _get_sentiment_config() -> dict:
    cfg = load_config()
    return cfg.get("sentiment", {})


# ---------------------------------------------------------------------------
# XHS 数据摘要
# ---------------------------------------------------------------------------


def read_xhs_summary() -> dict:
    """从 mirror DB 读 XHS 数据摘要。

    返回 {"total_notes": N, "top_topics": [...], "recent_notes": [...]}
    """
    icfg = _get_insight_config()
    db_path = os.path.expanduser(icfg.get("mirror_db", "~/mason-hub/data/mirror/sqlite_tables.db"))

    if not os.path.exists(db_path):
        logger.warning("Mirror DB not found: %s", db_path)
        return {"error": f"Mirror DB not found: {db_path}"}

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # 总笔记数
        total = conn.execute("SELECT COUNT(*) FROM xhs_note").fetchone()[0]

        # 热门话题：从 tag_list 和 source_keyword 提取
        topic_counter: Counter = Counter()

        # source_keyword 统计
        rows = conn.execute(
            "SELECT source_keyword, COUNT(*) as cnt FROM xhs_note "
            "WHERE source_keyword IS NOT NULL AND source_keyword != '' "
            "GROUP BY source_keyword ORDER BY cnt DESC LIMIT 20"
        ).fetchall()
        for r in rows:
            topic_counter[r["source_keyword"]] += r["cnt"]

        # tag_list 统计（格式：JSON 字符串 "tag1,tag2,..." 或 JSON 数组）
        tag_rows = conn.execute(
            "SELECT tag_list FROM xhs_note WHERE tag_list IS NOT NULL AND tag_list != ''"
        ).fetchall()
        for r in tag_rows:
            raw = r["tag_list"]
            try:
                parsed = json.loads(raw) if raw else []
                if isinstance(parsed, str):
                    # JSON 字符串如 "oliveyoung,韩系彩妆,..." → 逗号分割
                    tags = [t.strip() for t in parsed.split(",") if t.strip()]
                elif isinstance(parsed, list):
                    tags = []
                    for tag in parsed:
                        if isinstance(tag, dict):
                            tags.append(tag.get("name", ""))
                        else:
                            tags.append(str(tag))
                else:
                    tags = []
                for t in tags:
                    if t and len(t) >= 2:
                        topic_counter[t] += 1
            except (json.JSONDecodeError, TypeError):
                for t in str(raw).strip('"').split(","):
                    t = t.strip()
                    if t and len(t) >= 2:
                        topic_counter[t] += 1

        top_topics = [t for t, _ in topic_counter.most_common(15)]

        # 最近笔记（按 time 降序，取 10 条）
        recent_rows = conn.execute(
            "SELECT note_id, title, desc, type, liked_count, collected_count, "
            "comment_count, share_count, source_keyword, time "
            "FROM xhs_note ORDER BY time DESC LIMIT 10"
        ).fetchall()

        recent_notes = []
        for r in recent_rows:
            recent_notes.append({
                "note_id": r["note_id"],
                "title": r["title"] or "",
                "desc": (r["desc"] or "")[:100],
                "type": r["type"],
                "liked_count": r["liked_count"],
                "collected_count": r["collected_count"],
                "comment_count": r["comment_count"],
                "source_keyword": r["source_keyword"],
            })

        # 互动汇总
        stats = conn.execute(
            "SELECT "
            "  SUM(CAST(liked_count AS INTEGER)) as total_likes, "
            "  SUM(CAST(collected_count AS INTEGER)) as total_collects, "
            "  SUM(CAST(comment_count AS INTEGER)) as total_comments "
            "FROM xhs_note"
        ).fetchone()

        conn.close()

        return {
            "total_notes": total,
            "top_topics": top_topics,
            "recent_notes": recent_notes,
            "total_likes": stats["total_likes"] or 0,
            "total_collects": stats["total_collects"] or 0,
            "total_comments": stats["total_comments"] or 0,
        }

    except Exception as e:
        logger.error("Failed to read XHS summary: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# 销售数据
# ---------------------------------------------------------------------------


def read_sales_summary() -> dict:
    """调素仁轩 sales API 获取销售摘要。

    需要先 POST /api/auth/login 获取 JWT token。
    从 .env 读 SRX_API_EMAIL + SRX_API_PASSWORD。
    返回 API response dict，失败返回 {"error": "..."}。
    """
    icfg = _get_insight_config()
    base_url = icfg.get("sales_api_url", "http://106.14.44.68:8000")

    email = os.environ.get("SRX_API_EMAIL", "")
    password = os.environ.get("SRX_API_PASSWORD", "")

    if not email or not password:
        return {"error": "SRX_API_EMAIL or SRX_API_PASSWORD not set in .env"}

    # 1. Login
    try:
        login_resp = requests.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        login_resp.raise_for_status()
        token = login_resp.json().get("access_token", "")
        if not token:
            return {"error": "Login succeeded but no access_token in response"}
    except requests.RequestException as e:
        return {"error": f"Login failed: {e}"}

    # 2. Get sales summary
    headers = {"Authorization": f"Bearer {token}"}
    try:
        sales_resp = requests.get(
            f"{base_url}/api/sales/summary",
            headers=headers,
            timeout=15,
        )
        sales_resp.raise_for_status()
        return sales_resp.json()
    except requests.RequestException as e:
        return {"error": f"Sales API failed: {e}"}


# ---------------------------------------------------------------------------
# 历史情报关联
# ---------------------------------------------------------------------------


def _extract_keywords(text: str) -> set[str]:
    """从文本提取关键词（简单分词：中文按字符 bigram，英文按空格分词）。"""
    words: set[str] = set()
    # 英文单词（3 字符以上）
    for w in re.findall(r"[a-zA-Z]{3,}", text.lower()):
        words.add(w)
    # 中文：bigram
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    for segment in chinese:
        for i in range(len(segment) - 1):
            words.add(segment[i : i + 2])
    return words


def find_related_historical(
    item: dict, historical: list[dict], top_n: int = 3
) -> list[dict]:
    """从历史情报中找相关条目。简单匹配：标题关键词重叠度。"""
    item_text = f"{item.get('title', '')} {item.get('summary', '')}"
    item_kw = _extract_keywords(item_text)

    if not item_kw:
        return []

    scored = []
    for h in historical:
        h_text = f"{h.get('title', '')} {h.get('summary', '')}"
        h_kw = _extract_keywords(h_text)
        if not h_kw:
            continue
        overlap = len(item_kw & h_kw)
        if overlap > 0:
            # Jaccard-like score
            score = overlap / len(item_kw | h_kw)
            scored.append((score, h))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored[:top_n]]


# ---------------------------------------------------------------------------
# 情感分析
# ---------------------------------------------------------------------------


def analyze_sentiment(text: str) -> dict:
    """用 DeepSeek 做情感分析。

    返回 {"sentiment": "positive|negative|neutral", "score": 0.0-1.0,
           "key_phrases": [...]}
    """
    scfg = _get_sentiment_config()
    model = scfg.get("model", "default")

    prompt = f"""分析以下文本的情感倾向：
{text}

输出 JSON: {{
    "sentiment": "positive|negative|neutral",
    "score": 0.0-1.0,
    "key_phrases": ["关键短语1", ...]
}}

其中 score: 1.0=极度正面, 0.0=极度负面, 0.5=中性"""

    try:
        return call_llm_json(prompt, model=model)
    except Exception as e:
        logger.warning("Sentiment analysis failed: %s", e)
        return {"sentiment": "neutral", "score": 0.5, "key_phrases": [], "error": str(e)}


# ---------------------------------------------------------------------------
# 批量富化（核心）
# ---------------------------------------------------------------------------

_BATCH_SIZE = 5


def _build_batch_prompt(
    batch: list[dict],
    xhs_summary: dict,
    sales_summary: dict,
    all_related: dict[int, list[dict]],
) -> str:
    """为一批情报构建合并 prompt（情感分析 + 关联分析一次搞定）。"""

    # 内部数据摘要（全局，只写一次）
    xhs_part = "数据不可用" if "error" in xhs_summary else (
        f"{xhs_summary['total_notes']} 条笔记, "
        f"总点赞 {xhs_summary.get('total_likes', 'N/A')}, "
        f"总收藏 {xhs_summary.get('total_collects', 'N/A')}, "
        f"热门话题: {', '.join(xhs_summary.get('top_topics', [])[:8])}"
    )

    sales_part = "数据不可用" if "error" in sales_summary else json.dumps(
        sales_summary, ensure_ascii=False, default=str
    )[:500]

    items_block = []
    for idx, item in enumerate(batch):
        related = all_related.get(idx, [])
        related_text = "无" if not related else "; ".join(
            f"[{r.get('date', '?')}] {r.get('title', '?')}" for r in related
        )
        items_block.append(
            f"--- 情报 {idx + 1} ---\n"
            f"标题: {item.get('title', '无标题')}\n"
            f"摘要: {item.get('summary', '无摘要')[:300]}\n"
            f"来源: {item.get('source', '?')} | 日期: {item.get('date', '?')}\n"
            f"历史相关情报: {related_text}"
        )

    prompt = f"""你是一个商业情报分析师，服务于一家韩国护肤品跨境电商（主营小红书渠道）。

我们的内部数据：
- XHS 笔记库: {xhs_part}
- 销售数据: {sales_part}

请对以下 {len(batch)} 条外部情报逐条分析，输出一个 JSON 数组，每条包含：
1. sentiment: "positive" / "negative" / "neutral"
2. sentiment_score: 0.0-1.0 (1.0=极度正面, 0.0=极度负面)
3. key_phrases: 情感关键短语列表 (最多3个)
4. relevance: "high" / "medium" / "low" — 与我们业务的相关性
5. internal_context: 一段话说明这条情报和我们的具体关联
6. action_impact: 如果要行动影响哪个业务环节，或 "none"

{chr(10).join(items_block)}

输出格式（严格 JSON 数组）:
[
  {{"sentiment": "...", "sentiment_score": 0.7, "key_phrases": [...], "relevance": "...", "internal_context": "...", "action_impact": "..."}},
  ...
]"""

    return prompt


def enrich_with_internal_data(items: list[dict]) -> list[dict]:
    """主函数：用内部数据给外部情报加上下文 + 情感分析。

    1. 读内部数据源（XHS 摘要 + 销售数据 + 历史情报）—— 只读一次
    2. 分批处理（每批 5 条），一次 LLM 调用完成情感 + 关联分析
    3. 更新 scout.db
    4. 返回富化后的 items
    """
    if not items:
        return items

    # --- 1. 读内部数据（一次性） ---
    logger.info("Reading internal data sources...")

    xhs_summary = read_xhs_summary()
    if "error" in xhs_summary:
        logger.warning("XHS data unavailable: %s", xhs_summary["error"])
    else:
        logger.info("XHS: %d notes loaded", xhs_summary["total_notes"])

    sales_summary = read_sales_summary()
    if "error" in sales_summary:
        logger.warning("Sales data unavailable: %s", sales_summary["error"])
    else:
        logger.info("Sales data loaded")

    # 历史情报
    icfg = _get_insight_config()
    hist_path = os.path.expanduser(
        icfg.get("historical_intel", "~/mason-hub/intel/processed/scout_normalized.jsonl")
    )
    historical: list[dict] = []
    if os.path.exists(hist_path):
        with open(hist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        historical.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        logger.info("Historical intel: %d items", len(historical))
    else:
        logger.warning("Historical intel not found: %s", hist_path)

    # --- 2. 打开 scout.db 准备写入 ---
    conn = init_db()

    # --- 3. 分批处理 ---
    scfg = _get_sentiment_config()
    model = scfg.get("model", "default")

    enriched = list(items)  # shallow copy
    total_batches = (len(enriched) + _BATCH_SIZE - 1) // _BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * _BATCH_SIZE
        end = min(start + _BATCH_SIZE, len(enriched))
        batch = enriched[start:end]

        logger.info(
            "Processing batch %d/%d (%d items)...",
            batch_idx + 1, total_batches, len(batch),
        )

        # 找历史相关情报（按 batch 内 index）
        all_related: dict[int, list[dict]] = {}
        for idx, item in enumerate(batch):
            related = find_related_historical(item, historical, top_n=3)
            if related:
                all_related[idx] = related

        # 构建合并 prompt
        prompt = _build_batch_prompt(batch, xhs_summary, sales_summary, all_related)

        try:
            results = call_llm_json(prompt, model=model)

            # 兼容：LLM 可能返回 {"results": [...]} 而非直接数组
            if isinstance(results, dict):
                results = results.get("results", results.get("data", [results]))
            if not isinstance(results, list):
                results = [results]

            # 映射回 items
            for idx, item in enumerate(batch):
                if idx < len(results):
                    r = results[idx]
                    item["sentiment"] = r.get("sentiment", "neutral")
                    item["sentiment_score"] = r.get("sentiment_score", 0.5)
                    item["relevance"] = r.get("relevance", "low")
                    item["internal_context"] = r.get("internal_context", "")
                    item["action_impact"] = r.get("action_impact", "none")

                    # key_phrases 存为逗号分隔字符串
                    kp = r.get("key_phrases", [])
                    if isinstance(kp, list):
                        kp = ", ".join(kp)
                    item["key_phrases"] = kp

                    # 写入 scout.db
                    if item.get("id"):
                        try:
                            update_intel_enrichment(
                                conn,
                                item["id"],
                                relevance=item.get("relevance"),
                                internal_context=item.get("internal_context"),
                                sentiment=item.get("sentiment"),
                                sentiment_score=item.get("sentiment_score"),
                            )
                        except Exception as e:
                            logger.warning("DB update failed for %s: %s", item.get("id"), e)
                else:
                    logger.warning(
                        "Batch %d: LLM returned %d results for %d items, item %d skipped",
                        batch_idx + 1, len(results), len(batch), idx,
                    )

        except Exception as e:
            logger.error("Batch %d LLM call failed: %s", batch_idx + 1, e)
            # Graceful degrade: 标记为未分析
            for item in batch:
                item.setdefault("sentiment", "unknown")
                item.setdefault("relevance", "unknown")

    conn.close()
    logger.info("Enrichment complete: %d items processed", len(enriched))
    return enriched


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # 读现有 JSONL 测试
    items: list[dict] = []
    hist_path = os.path.expanduser(
        _get_insight_config().get(
            "historical_intel",
            "~/mason-hub/intel/processed/scout_normalized.jsonl",
        )
    )
    if os.path.exists(hist_path):
        with open(hist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    xhs = read_xhs_summary()
    sales = read_sales_summary()

    print(f"XHS: {xhs.get('total_notes', 'N/A')} 条笔记")
    if "error" not in xhs:
        print(f"  Top topics: {xhs.get('top_topics', [])[:5]}")
        print(f"  Total likes: {xhs.get('total_likes', 'N/A')}")
    else:
        print(f"  Error: {xhs['error']}")

    print(f"Sales: {'OK' if 'error' not in sales else sales['error']}")
    print(f"情报: {len(items)} 条待富化")
