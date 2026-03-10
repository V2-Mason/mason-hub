"""
Scout v2 — ForumEngine 交叉验证引擎

对多源情报做聚类、交叉验证、标注置信度。
参考 BettaFish ForumEngine 的主持人机制。

聚类用纯 Python 字符串匹配（无外部 NLP 依赖），
LLM 只对 >=2 条同话题情报做交叉验证（节省成本）。
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .database import init_db, update_intel_enrichment
from .llm_client import call_llm_json, load_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 停用词（中英混合，覆盖常见无意义词）
# ---------------------------------------------------------------------------

_STOP_WORDS_EN = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "and", "but", "or", "nor", "not", "no", "so", "yet", "both", "either",
    "it", "its", "this", "that", "these", "those", "he", "she", "they",
    "we", "you", "i", "me", "my", "your", "his", "her", "our", "their",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "all", "each", "every", "any", "few", "more", "most", "other",
    "some", "such", "than", "too", "very", "just", "about", "also",
})

_STOP_WORDS_ZH = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
    "们", "那", "里", "后", "过", "多", "大", "小", "个", "为",
    "来", "以", "中", "对", "与", "及", "等", "被", "从", "把",
})

# ---------------------------------------------------------------------------
# 文本切分
# ---------------------------------------------------------------------------

_RE_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_RE_EN_WORD = re.compile(r"[a-zA-Z0-9]+")


def _extract_tokens(text: str) -> set[str]:
    """从文本提取 token 集合。

    策略：
    - 中文：字符 bigram（"韩国护肤" → {"韩国", "国护", "护肤"}）
    - 英文：按空格切分，转小写
    - 去停用词
    - 短文本（< 5 字符）用完整文本作为单个 token
    """
    if not text:
        return set()

    text = text.strip()
    if len(text) < 5:
        return {text.lower()}

    tokens: set[str] = set()

    # 中文 bigram
    cjk_chars = _RE_CJK.findall(text)
    for i in range(len(cjk_chars) - 1):
        bigram = cjk_chars[i] + cjk_chars[i + 1]
        if bigram not in _STOP_WORDS_ZH:
            tokens.add(bigram)

    # 英文 token
    en_words = _RE_EN_WORD.findall(text)
    for w in en_words:
        wl = w.lower()
        if wl not in _STOP_WORDS_EN and len(wl) > 1:
            tokens.add(wl)

    return tokens


def _jaccard(a: set, b: set) -> float:
    """Jaccard 相似度。"""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# 聚类
# ---------------------------------------------------------------------------


def cluster_by_topic(items: list[dict], threshold: float = 0.3) -> dict[str, list[dict]]:
    """按话题聚类情报条目。

    策略：
    1. 提取每条情报标题的关键词 token 集
    2. 计算两两之间的 Jaccard 相似度
    3. 重叠度 > threshold 的归为一组（Union-Find）
    4. 用组内第一条的标题前 50 字符作为话题名

    返回 {"话题名": [item1, item2, ...]}
    """
    if not items:
        return {}

    # 预计算每条的 token 集
    token_sets = []
    for item in items:
        title = item.get("title", "")
        token_sets.append(_extract_tokens(title))

    n = len(items)

    # Union-Find
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    # 计算两两相似度，合并
    for i in range(n):
        for j in range(i + 1, n):
            if _jaccard(token_sets[i], token_sets[j]) > threshold:
                union(i, j)

    # 按根节点分组
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # 构建结果
    clusters: dict[str, list[dict]] = {}
    for root, indices in groups.items():
        topic_name = items[root].get("title", f"话题-{root}")[:50]
        clusters[topic_name] = [items[i] for i in indices]

    return clusters


# ---------------------------------------------------------------------------
# LLM 交叉验证
# ---------------------------------------------------------------------------

_FORUM_SYSTEM = (
    "你是情报分析主持人。分析多条不同来源的情报，交叉验证事实一致性。"
    "始终用 JSON 格式回答。"
)


def _build_forum_prompt(topic: str, group: list[dict]) -> str:
    """构建交叉验证 prompt。"""
    lines = [
        f"作为情报分析主持人，以下是关于「{topic}」的 {len(group)} 条来自不同来源的情报：",
        "",
    ]
    for i, item in enumerate(group, 1):
        lines.append(f"--- 情报 {i} ---")
        lines.append(f"标题: {item.get('title', 'N/A')}")
        lines.append(f"来源: {item.get('source', 'N/A')}")
        lines.append(f"摘要: {(item.get('summary', '') or '')[:500]}")
        lines.append(f"日期: {item.get('date', 'N/A')}")
        lines.append("")

    lines.append("请分析：")
    lines.append("1. 共识：多个来源一致认为什么（一句话）")
    lines.append("2. 分歧：来源之间有什么矛盾（没有就说「无明显分歧」）")
    lines.append("3. 置信度：")
    lines.append("   - high: 3+ 来源一致")
    lines.append("   - medium: 2 来源一致")
    lines.append("   - low: 有事实矛盾")
    lines.append("4. 综合判断：对 Mason（跨境电商 + AI 工具创业者）意味着什么")
    lines.append("5. 建议行动：具体到应该让谁做什么（如果有的话）")
    lines.append("")
    lines.append('输出 JSON: {"consensus": "...", "dissent": "...", '
                 '"confidence": "high|medium|low", "synthesis": "...", "action": "..."}')

    return "\n".join(lines)


def _validate_group(topic: str, group: list[dict], model: str = "default") -> dict:
    """对一个话题组做 LLM 交叉验证。

    返回 {"consensus": ..., "dissent": ..., "confidence": ...,
           "synthesis": ..., "action": ...}
    失败时返回 confidence=unknown 的默认值。
    """
    prompt = _build_forum_prompt(topic, group)
    try:
        result = call_llm_json(prompt, model=model, system=_FORUM_SYSTEM)
        # 确保关键字段存在
        result.setdefault("consensus", "")
        result.setdefault("dissent", "无明显分歧")
        result.setdefault("confidence", "medium")
        result.setdefault("synthesis", "")
        result.setdefault("action", "")
        # 规范化 confidence 值
        if result["confidence"] not in ("high", "medium", "low"):
            result["confidence"] = "medium"
        return result
    except Exception as e:
        logger.error("LLM 交叉验证失败 (话题: %s): %s", topic[:30], e)
        return {
            "consensus": "",
            "dissent": "",
            "confidence": "unknown",
            "synthesis": "",
            "action": "",
        }


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------


def cross_validate(items: list[dict], model: str | None = None) -> list[dict]:
    """多源情报交叉验证。

    1. 聚类
    2. 对每个话题组：
       - >= 2 条 → LLM 交叉验证
       - == 1 条 → 标注 confidence: "single_source"
    3. 将验证结果写入每条情报
    4. 更新数据库
    5. 保存到 intel/validated/YYYY-MM-DD.jsonl
    6. 返回所有验证后的 items
    """
    if not items:
        return []

    # 读取配置
    cfg = load_config()
    forum_cfg = cfg.get("forum", {})
    llm_model = model or forum_cfg.get("model", "default")

    # 1. 聚类
    clusters = cluster_by_topic(items)
    logger.info("ForumEngine: %d 条情报 → %d 个话题", len(items), len(clusters))

    # 2. 逐组验证
    validated_items: list[dict] = []

    for topic, group in clusters.items():
        if len(group) >= 2:
            # LLM 交叉验证
            result = _validate_group(topic, group, model=llm_model)
            logger.info(
                "话题「%s」(%d条): confidence=%s",
                topic[:30], len(group), result["confidence"],
            )
        else:
            # 单条情报，不调 LLM
            result = {
                "consensus": "",
                "dissent": "",
                "confidence": "single_source",
                "synthesis": "",
                "action": "",
            }

        # 将验证结果写入每条情报
        for item in group:
            item["confidence"] = result["confidence"]
            item["consensus"] = result["consensus"]
            item["dissent"] = result["dissent"]
            item["forum_synthesis"] = result["synthesis"]
            item["forum_action"] = result["action"]
            item["forum_topic"] = topic
            validated_items.append(item)

    # 3. 更新数据库
    try:
        db_path = cfg.get("database", {}).get("path", "")
        if db_path:
            db_path = os.path.expanduser(db_path)
        conn = init_db(db_path if db_path else None)
        for item in validated_items:
            if item.get("id"):
                update_intel_enrichment(
                    conn,
                    item["id"],
                    confidence=item.get("confidence"),
                    consensus=item.get("consensus"),
                    dissent=item.get("dissent"),
                )
        conn.close()
        logger.info("ForumEngine: 数据库已更新 %d 条", len(validated_items))
    except Exception as e:
        logger.warning("ForumEngine: 数据库更新失败（不影响返回）: %s", e)

    # 4. 保存 validated JSONL
    try:
        output_path = save_validated(validated_items)
        logger.info("ForumEngine: 验证结果已保存到 %s", output_path)
    except Exception as e:
        logger.warning("ForumEngine: 保存 JSONL 失败: %s", e)

    return validated_items


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_validated(items: list[dict], date: str | None = None) -> str:
    """保存验证后的数据到 JSONL 文件。返回文件路径。"""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cfg = load_config()
    validated_dir = cfg.get("report", {}).get(
        "validated_dir", "~/mason-hub/intel/validated/"
    )
    validated_dir = os.path.expanduser(validated_dir)
    Path(validated_dir).mkdir(parents=True, exist_ok=True)

    output_path = os.path.join(validated_dir, f"{date}.jsonl")

    with open(output_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    items = []
    jsonl_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "processed",
        "scout_normalized.jsonl",
    )
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    clusters = cluster_by_topic(items)
    print(f"聚类结果: {len(clusters)} 个话题")
    for topic, group in clusters.items():
        print(f"  [{len(group)}条] {topic[:50]}")
