"""
Scout v2 — MediaEngine: 多模态内容理解引擎

用 Gemini 分析 XHS 笔记封面图片，提取视觉风格、营销价值等结构化信息。
当前只做图片分析，不做视频。

依赖:
- intel/engines/llm_client.py — call_llm_with_images()
- intel/engines/config.yaml — media 配置段
- intel/engines/database.py — update_intel_enrichment()
- data/mirror/sqlite_tables.db — XHS 笔记数据 (xhs_note 表)
"""

import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path

from .llm_client import call_llm_with_images, load_config, _repair_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_MIRROR_DB_DEFAULT = os.path.expanduser("~/mason-hub/data/mirror/sqlite_tables.db")

_XHS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.xiaohongshu.com",
}

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
_DOWNLOAD_TIMEOUT = 10  # seconds

_ANALYSIS_PROMPT_TEMPLATE = """分析这张小红书笔记封面图片：
笔记标题：{note_title}

请描述：
1. 图片内容（产品/场景/人物）
2. 视觉风格（配色/构图/滤镜）
3. 对于韩国护肤品跨境电商，这张图的营销价值（高/中/低）
4. 可借鉴的元素

输出 JSON: {{
    "content": "...",
    "style": "...",
    "marketing_value": "high|medium|low",
    "takeaways": "..."
}}"""


# ---------------------------------------------------------------------------
# 辅助：解析互动数（"3.1万" → 31000）
# ---------------------------------------------------------------------------

def _parse_count(val) -> int:
    """将 XHS 互动数文本转为整数。支持 '3.1万' 格式。"""
    if val is None:
        return 0
    s = str(val).strip()
    if not s:
        return 0
    # "3.1万" → 31000
    m = re.match(r"^([\d.]+)\s*万$", s)
    if m:
        return int(float(m.group(1)) * 10000)
    # 纯数字
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def _parse_image_list(image_list_raw: str | None) -> list[str]:
    """解析 xhs_note.image_list 字段为 URL 列表。

    字段格式：用引号包裹的逗号分隔 URL 字符串。
    例：'"http://url1,http://url2"'
    """
    if not image_list_raw:
        return []
    # 去掉首尾引号
    s = image_list_raw.strip().strip('"').strip("'")
    if not s:
        return []
    urls = [u.strip() for u in s.split(",") if u.strip().startswith("http")]
    return urls


# ---------------------------------------------------------------------------
# 数据读取
# ---------------------------------------------------------------------------

def get_xhs_notes_with_images(
    limit: int = 10,
    mirror_db: str | None = None,
) -> list[dict]:
    """从 mirror DB 读取有图片的 XHS 笔记，按互动量降序。

    返回 [{"note_id": "...", "title": "...", "image_urls": [...],
            "liked_count": int, "collected_count": int, ...}]
    """
    db_path = mirror_db or _get_mirror_db_path()
    if not os.path.exists(db_path):
        logger.warning("Mirror DB not found: %s", db_path)
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT note_id, title, "desc", type, image_list,
                   liked_count, collected_count, comment_count, share_count,
                   nickname, source_keyword
            FROM xhs_note
            WHERE image_list IS NOT NULL AND image_list != ''
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    notes = []
    for row in rows:
        r = dict(row)
        image_urls = _parse_image_list(r.get("image_list"))
        if not image_urls:
            continue

        liked = _parse_count(r.get("liked_count"))
        collected = _parse_count(r.get("collected_count"))
        comment = _parse_count(r.get("comment_count"))
        share = _parse_count(r.get("share_count"))

        notes.append({
            "note_id": r["note_id"],
            "title": r.get("title") or "",
            "desc": r.get("desc") or "",
            "type": r.get("type") or "normal",
            "image_urls": image_urls,
            "liked_count": liked,
            "collected_count": collected,
            "comment_count": comment,
            "share_count": share,
            "engagement": liked + collected + comment + share,
            "nickname": r.get("nickname") or "",
            "source_keyword": r.get("source_keyword") or "",
        })

    # 按互动量降序排序
    notes.sort(key=lambda n: n["engagement"], reverse=True)
    return notes[:limit]


def _get_mirror_db_path() -> str:
    """从 config.yaml 读取 mirror DB 路径，fallback 到默认值。"""
    try:
        cfg = load_config()
        path = cfg.get("insight", {}).get("mirror_db", _MIRROR_DB_DEFAULT)
        return os.path.expanduser(path)
    except Exception:
        return _MIRROR_DB_DEFAULT


# ---------------------------------------------------------------------------
# 图片下载
# ---------------------------------------------------------------------------

def download_image(url: str, save_dir: str) -> str | None:
    """下载图片到指定目录，返回本地路径。失败返回 None。

    限制：
    - 超时 10s
    - 只接受 jpg/png/webp
    - 单张最大 5MB
    """
    import requests

    try:
        resp = requests.get(
            url,
            headers=_XHS_HEADERS,
            timeout=_DOWNLOAD_TIMEOUT,
            stream=True,
        )
        resp.raise_for_status()

        # 检查 Content-Length
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > _MAX_IMAGE_BYTES:
            logger.warning("Image too large (%s bytes), skipping: %s", content_length, url)
            return None

        # 从 URL 推断扩展名
        ext = _guess_extension(url, resp.headers.get("Content-Type", ""))
        if ext not in _ALLOWED_EXTENSIONS:
            logger.warning("Unsupported image type '%s', skipping: %s", ext, url)
            return None

        # 下载到临时文件
        file_path = os.path.join(save_dir, f"xhs_img_{hash(url) & 0xFFFFFFFF:08x}{ext}")
        size = 0
        with open(file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                size += len(chunk)
                if size > _MAX_IMAGE_BYTES:
                    logger.warning("Image exceeds 5MB during download, aborting: %s", url)
                    f.close()
                    os.remove(file_path)
                    return None
                f.write(chunk)

        logger.debug("Downloaded image (%d bytes): %s → %s", size, url, file_path)
        return file_path

    except Exception as e:
        logger.warning("Failed to download image: %s — %s", url, e)
        return None


def _guess_extension(url: str, content_type: str) -> str:
    """根据 URL 路径和 Content-Type 推断图片扩展名。"""
    # XHS CDN URL 通常以 !nd_dft_wlteh_webp_3 结尾，实际是 webp
    if "webp" in url.lower() or "webp" in content_type.lower():
        return ".webp"
    if "png" in content_type.lower():
        return ".png"
    if "jpeg" in content_type.lower() or "jpg" in content_type.lower():
        return ".jpg"
    # URL 路径里找
    path_lower = url.split("?")[0].lower()
    for ext in _ALLOWED_EXTENSIONS:
        if path_lower.endswith(ext):
            return ext
    # XHS 默认 webp
    return ".webp"


# ---------------------------------------------------------------------------
# 图片分析
# ---------------------------------------------------------------------------

def analyze_image(image_path: str, note_title: str = "") -> dict:
    """用 Gemini 分析单张图片，返回结构化 JSON。

    返回: {"content": "...", "style": "...", "marketing_value": "high|medium|low",
           "takeaways": "..."}
    失败返回: {"error": "..."}
    """
    cfg = load_config()
    media_cfg = cfg.get("media", {})
    model = media_cfg.get("model", "gemini")

    prompt = _ANALYSIS_PROMPT_TEMPLATE.format(note_title=note_title or "未知")

    try:
        raw = call_llm_with_images(
            prompt=prompt,
            image_paths=[image_path],
            model=model,
        )
        result = _repair_json(raw)
        # 校验必需字段
        for key in ("content", "style", "marketing_value", "takeaways"):
            if key not in result:
                result[key] = ""
        return result

    except Exception as e:
        logger.error("Image analysis failed for %s: %s", image_path, e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# 批量分析
# ---------------------------------------------------------------------------

def analyze_batch(
    notes: list[dict] | None = None,
    max_images: int = 10,
    mirror_db: str | None = None,
) -> list[dict]:
    """批量分析笔记封面图片。

    1. 如果 notes 未提供，从 mirror DB 读取
    2. 按互动量排序，取 top N
    3. 下载每条笔记的第一张封面图
    4. 调 Gemini 分析
    5. 返回带 image_analysis 字段的笔记列表

    注意:
    - Gemini API key 未配置时 graceful 返回空结果
    - 图片下载失败跳过该笔记
    - 分析完清理临时图片文件
    """
    cfg = load_config()
    media_cfg = cfg.get("media", {})

    if not media_cfg.get("enabled", False):
        logger.info("MediaEngine disabled in config (media.enabled=false). Skipping.")
        return []

    max_images = min(max_images, media_cfg.get("max_images_per_batch", 10))

    # 检查 Gemini API key
    model_name = media_cfg.get("model", "gemini")
    models_cfg = cfg.get("llm", {}).get("models", {})
    model_cfg = models_cfg.get(model_name, {})
    api_key_env = model_cfg.get("api_key_env", "GEMINI_API_KEY")
    if not os.environ.get(api_key_env):
        logger.warning(
            "Gemini API key (%s) not configured. MediaEngine skipping batch analysis.",
            api_key_env,
        )
        return []

    if notes is None:
        notes = get_xhs_notes_with_images(limit=max_images, mirror_db=mirror_db)

    # 取 top N（已按互动量排序）
    notes = notes[:max_images]
    if not notes:
        logger.info("No notes with images to analyze.")
        return []

    tmp_dir = tempfile.mkdtemp(prefix="scout_media_")
    results = []

    try:
        for note in notes:
            image_urls = note.get("image_urls", [])
            if not image_urls:
                continue

            # 只下载第一张封面图
            cover_url = image_urls[0]
            local_path = download_image(cover_url, tmp_dir)
            if not local_path:
                logger.info("Skipping note %s: cover download failed.", note.get("note_id"))
                continue

            analysis = analyze_image(local_path, note_title=note.get("title", ""))
            note["image_analysis"] = analysis
            results.append(note)

            logger.info(
                "Analyzed note %s [%s]: marketing_value=%s",
                note.get("note_id"),
                note.get("title", "")[:30],
                analysis.get("marketing_value", "N/A"),
            )
    finally:
        # 清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.debug("Cleaned up temp dir: %s", tmp_dir)

    return results


# ---------------------------------------------------------------------------
# 情报附加
# ---------------------------------------------------------------------------

def enrich_intel_with_media(
    intel_items: list[dict],
    mirror_db: str | None = None,
) -> list[dict]:
    """主函数：给情报条目附加图片分析。

    1. 找出与 XHS 相关的情报条目（source 包含 xhs 或 domain=ecom）
    2. 从 mirror DB 获取相关笔记的图片
    3. 分析图片
    4. 将分析结果写入 intel_items 的 image_analysis 字段
    5. 更新数据库 (intel/scout.db)
    6. 返回更新后的 items

    如果 Gemini API key 未配置，log warning 并返回原始 items 不修改。
    """
    cfg = load_config()
    media_cfg = cfg.get("media", {})

    if not media_cfg.get("enabled", False):
        logger.info("MediaEngine disabled in config. Returning items unchanged.")
        return intel_items

    # 检查 Gemini API key
    model_name = media_cfg.get("model", "gemini")
    models_cfg = cfg.get("llm", {}).get("models", {})
    model_cfg = models_cfg.get(model_name, {})
    api_key_env = model_cfg.get("api_key_env", "GEMINI_API_KEY")
    if not os.environ.get(api_key_env):
        logger.warning(
            "Gemini API key (%s) not configured. Returning items unchanged.",
            api_key_env,
        )
        return intel_items

    # 筛选 XHS/电商相关条目
    xhs_items = [
        item for item in intel_items
        if _is_xhs_related(item)
    ]

    if not xhs_items:
        logger.info("No XHS-related intel items found. Skipping media enrichment.")
        return intel_items

    logger.info("Found %d XHS-related intel items for media enrichment.", len(xhs_items))

    # 获取图片分析结果
    max_images = media_cfg.get("max_images_per_batch", 10)
    analyzed_notes = analyze_batch(max_images=max_images, mirror_db=mirror_db)

    if not analyzed_notes:
        logger.info("No image analysis results. Returning items unchanged.")
        return intel_items

    # 构建分析摘要（所有分析结果聚合）
    analysis_summary = _build_analysis_summary(analyzed_notes)

    # 将摘要附加到 XHS 相关情报条目
    from .database import init_db, update_intel_enrichment

    try:
        conn = init_db()
    except Exception as e:
        logger.error("Failed to connect to scout.db: %s", e)
        conn = None

    for item in xhs_items:
        item["image_analysis"] = json.dumps(analysis_summary, ensure_ascii=False)
        if conn and item.get("id"):
            try:
                update_intel_enrichment(
                    conn,
                    item["id"],
                    image_analysis=item["image_analysis"],
                )
            except Exception as e:
                logger.error("Failed to update enrichment for %s: %s", item.get("id"), e)

    if conn:
        conn.close()

    return intel_items


def _is_xhs_related(item: dict) -> bool:
    """判断情报条目是否与 XHS 相关。"""
    source = str(item.get("source", "")).lower()
    domain = str(item.get("domain", "")).lower()
    title = str(item.get("title", "")).lower()

    if "xhs" in source or "xiaohongshu" in source or "小红书" in source:
        return True
    if domain == "ecom":
        return True
    if "小红书" in title or "xhs" in title:
        return True
    return False


def _build_analysis_summary(analyzed_notes: list[dict]) -> dict:
    """从多条笔记的图片分析中构建聚合摘要。"""
    high_value = []
    styles = []
    takeaways = []

    for note in analyzed_notes:
        analysis = note.get("image_analysis", {})
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except (json.JSONDecodeError, TypeError):
                continue
        if "error" in analysis:
            continue

        mv = analysis.get("marketing_value", "")
        if mv == "high":
            high_value.append({
                "note_id": note.get("note_id"),
                "title": note.get("title", "")[:50],
                "content": analysis.get("content", ""),
            })
        if analysis.get("style"):
            styles.append(analysis["style"])
        if analysis.get("takeaways"):
            takeaways.append(analysis["takeaways"])

    return {
        "total_analyzed": len(analyzed_notes),
        "high_value_count": len(high_value),
        "high_value_notes": high_value[:5],  # 最多 5 条
        "common_styles": styles[:5],
        "key_takeaways": takeaways[:5],
    }


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # 独立运行测试：只测数据读取，不需要 Gemini API
    notes = get_xhs_notes_with_images(limit=5)
    print(f"找到 {len(notes)} 条有图片的笔记")
    for n in notes[:3]:
        print(f"  [{n['note_id']}] {n.get('title', 'N/A')[:50]}: "
              f"{len(n.get('image_urls', []))} 张图, "
              f"互动={n['engagement']}")
