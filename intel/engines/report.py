"""Scout v2 ReportEngine — IR 中间表示 → 多格式渲染 + 动态模板选择

BettaFish-inspired: validated items → ReportIR → template selection → render
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from collections import Counter
from datetime import date as date_mod
import json


# ── IR 数据结构 ──────────────────────────────────────────────

@dataclass
class IntelItem:
    id: str
    title: str
    summary: str
    url: str
    priority: str              # red / yellow
    source: str
    date: str
    confidence: str = ""       # high / medium / low / single_source
    relevance: str = ""        # high / medium / low
    internal_context: str = "" # InsightEngine 产出
    consensus: str = ""        # ForumEngine 产出
    dissent: str = ""
    sentiment: str = ""        # positive / negative / neutral
    image_analysis: str = ""   # MediaEngine 产出
    action: str = ""
    owner: str = ""


@dataclass
class Section:
    topic: str
    confidence: str
    items: list[IntelItem]
    consensus: str = ""
    dissent: str = ""
    action_summary: str = ""


@dataclass
class ReportIR:
    date: str
    period: str                        # "2026-W11"
    sections: list[Section]
    data_sources: list[str]
    search_meta: dict                  # 覆盖率、补搜统计、关键词数
    confidence_distribution: dict      # {"high": 3, "medium": 5, ...}
    sentiment_distribution: dict       # {"positive": 5, "negative": 2, ...}
    total_items: int


# ── 动态模板选择 ─────────────────────────────────────────────

TEMPLATES = {
    "alert": {
        "name": "紧急情报",
        "condition": lambda ir: any(
            s.confidence == "high" and any(i.priority == "red" for i in s.items)
            for s in ir.sections
        ),
        "sections_order": ["red_actions"],
    },
    "weekly_full": {
        "name": "周度全量报告",
        "condition": lambda ir: ir.total_items >= 10,
        "sections_order": ["red_actions", "insights", "yellow_watch", "sentiment_overview", "search_meta"],
    },
    "weekly_light": {
        "name": "周度精简报告",
        "condition": lambda ir: ir.total_items < 10,
        "sections_order": ["red_actions", "yellow_watch", "search_meta"],
    },
}

# Evaluation order: alert first (highest priority), then full vs light
_TEMPLATE_PRIORITY = ["alert", "weekly_full", "weekly_light"]


def select_template(ir: ReportIR) -> dict:
    """规则选模板，alert 优先级最高"""
    for key in _TEMPLATE_PRIORITY:
        tpl = TEMPLATES[key]
        if tpl["condition"](ir):
            return tpl
    # fallback
    return TEMPLATES["weekly_light"]


# ── 渲染器 ───────────────────────────────────────────────────

def _render_red_actions(ir: ReportIR) -> str:
    """渲染 🔴 级情报段落"""
    lines = ["## 🔴 需要行动的情报\n"]
    has_items = False
    for section in ir.sections:
        red_items = [i for i in section.items if i.priority == "red"]
        if not red_items:
            continue
        has_items = True
        lines.append(f"### {section.topic}\n")
        if section.consensus:
            lines.append(f"**共识**: {section.consensus}\n")
        if section.dissent:
            lines.append(f"**分歧**: {section.dissent}\n")
        for item in red_items:
            lines.append(f"- **[{item.title}]({item.url})**")
            lines.append(f"  {item.summary}")
            if item.internal_context:
                lines.append(f"  - 💡 内部关联: {item.internal_context}")
            if item.action:
                lines.append(f"  - ➡️ 建议行动: {item.action}")
            elif item.owner:
                lines.append(f"  - 👤 建议负责人: {item.owner}")
            lines.append(f"  - 来源: {item.source} | 日期: {item.date} | 置信度: {item.confidence or 'N/A'}")
            lines.append("")
        if section.action_summary:
            lines.append(f"**行动汇总**: {section.action_summary}\n")
    if not has_items:
        lines.append("_本期无 🔴 级情报_\n")
    return "\n".join(lines)


def _render_insights(ir: ReportIR) -> str:
    """渲染洞察段落（所有 section 的共识/分歧/情感总结）"""
    lines = ["## 💡 洞察总结\n"]
    has_content = False
    for section in ir.sections:
        if section.consensus or section.dissent:
            has_content = True
            lines.append(f"### {section.topic}")
            if section.consensus:
                lines.append(f"- **共识**: {section.consensus}")
            if section.dissent:
                lines.append(f"- **分歧**: {section.dissent}")
            lines.append("")
    if not has_content:
        lines.append("_本期无结构化洞察_\n")
    return "\n".join(lines)


def _render_yellow_watch(ir: ReportIR) -> str:
    """渲染 🟡 级情报段落 — 精简：标题+一句话+链接"""
    lines = ["## 🟡 持续关注\n"]
    has_items = False
    for section in ir.sections:
        yellow_items = [i for i in section.items if i.priority == "yellow"]
        if not yellow_items:
            continue
        has_items = True
        lines.append(f"### {section.topic}\n")
        for item in yellow_items:
            link = f"[链接]({item.url})" if item.url else ""
            first_sentence = item.summary.split("。")[0].split("\n")[0]
            if len(first_sentence) > 120:
                first_sentence = first_sentence[:117] + "..."
            lines.append(f"- **{item.title}** — {first_sentence} {link}")
        lines.append("")
    if not has_items:
        lines.append("_本期无 🟡 级情报_\n")
    return "\n".join(lines)


def _render_sentiment_overview(ir: ReportIR) -> str:
    """渲染情感分布概览"""
    lines = ["## 📊 情感分布\n"]
    dist = ir.sentiment_distribution
    if not any(dist.values()):
        lines.append("_本期无情感标注数据_\n")
        return "\n".join(lines)
    total = sum(dist.values())
    for key in ["positive", "neutral", "negative", "unknown"]:
        count = dist.get(key, 0)
        if count > 0:
            pct = count / total * 100
            emoji = {"positive": "🟢", "neutral": "⚪", "negative": "🔴", "unknown": "❓"}.get(key, "")
            lines.append(f"- {emoji} {key}: {count} ({pct:.0f}%)")
    lines.append("")
    return "\n".join(lines)


def _render_search_meta(ir: ReportIR) -> str:
    """渲染搜索元数据表格 + 置信度分布"""
    lines = ["## 📋 数据来源与质量\n"]

    # 数据来源
    lines.append(f"**数据来源**: {', '.join(ir.data_sources)}\n")
    lines.append(f"**情报总数**: {ir.total_items}\n")

    # 搜索元数据
    meta = ir.search_meta
    if meta:
        lines.append("**搜索元数据**:\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        for k, v in meta.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    # 置信度分布
    conf = ir.confidence_distribution
    if any(conf.values()):
        lines.append("**置信度分布**:\n")
        lines.append("| 级别 | 数量 |")
        lines.append("|------|------|")
        for level in ["high", "medium", "low", "single_source", "unknown"]:
            count = conf.get(level, 0)
            if count > 0:
                lines.append(f"| {level} | {count} |")
        lines.append("")

    return "\n".join(lines)


_SECTION_RENDERERS = {
    "red_actions": _render_red_actions,
    "insights": _render_insights,
    "yellow_watch": _render_yellow_watch,
    "sentiment_overview": _render_sentiment_overview,
    "search_meta": _render_search_meta,
}


def render_markdown(ir: ReportIR) -> str:
    """渲染完整 markdown 周报 — Mason 在 CLI 或 docs 中阅读"""
    tpl = select_template(ir)
    lines = [
        f"# Scout 情报周报 — {ir.period}",
        f"",
        f"> 日期: {ir.date} | 模板: {tpl['name']} | 情报数: {ir.total_items}",
        f"",
    ]
    for section_key in tpl["sections_order"]:
        renderer = _SECTION_RENDERERS.get(section_key)
        if renderer:
            lines.append(renderer(ir))
    return "\n".join(lines)


def render_slack_summary(ir: ReportIR) -> str:
    """渲染 Slack 精简摘要 — 只包含 🔴 级情报，最多 5 条"""
    red_items = []
    for section in ir.sections:
        for item in section.items:
            if item.priority == "red":
                red_items.append(item)
    red_items = red_items[:5]

    if not red_items:
        return f"📡 Scout 周报 {ir.period} — 本期无 🔴 级情报"

    lines = [f"📡 *Scout 周报 {ir.period}* — 🔴 级情报 ({len(red_items)} 条)\n"]
    for item in red_items:
        first_sentence = item.summary.split("。")[0].split("\n")[0]
        if len(first_sentence) > 80:
            first_sentence = first_sentence[:77] + "..."
        lines.append(f"• *<{item.url}|{item.title}>*")
        lines.append(f"  {first_sentence}")
        lines.append("")
    return "\n".join(lines)


def render_json(ir: ReportIR) -> str:
    """序列化为 JSON — 供下游机器消费"""
    return json.dumps(asdict(ir), ensure_ascii=False, indent=2)


# ── 构建 IR ──────────────────────────────────────────────────

def _item_from_dict(d: dict) -> IntelItem:
    """从 validated dict 构建 IntelItem，缺失字段用默认值"""
    return IntelItem(
        id=d.get("id", ""),
        title=d.get("title", ""),
        summary=d.get("summary", ""),
        url=d.get("url", ""),
        priority=d.get("priority", "yellow"),
        source=d.get("source", "unknown"),
        date=d.get("date", ""),
        confidence=d.get("confidence", ""),
        relevance=d.get("relevance", ""),
        internal_context=d.get("internal_context", ""),
        consensus=d.get("consensus", ""),
        dissent=d.get("dissent", ""),
        sentiment=d.get("sentiment", ""),
        image_analysis=d.get("image_analysis", ""),
        action=d.get("suggested_action", d.get("action", "")),
        owner=d.get("suggested_owner", d.get("owner", "")),
    )


def _detect_topic(item: IntelItem, topics: list[dict] | None) -> str:
    """推断 item 所属话题，基于 topics 配置或 source fallback"""
    if topics:
        title_lower = item.title.lower()
        summary_lower = item.summary.lower()
        for t in topics:
            keywords = t.get("keywords", [])
            for kw in keywords:
                if kw.lower() in title_lower or kw.lower() in summary_lower:
                    return t.get("name", t.get("topic", "其他"))
    # fallback: group by source
    source_map = {
        "mixed": "综合情报",
        "github": "技术趋势",
        "xhs": "小红书动态",
        "rss": "行业资讯",
    }
    return source_map.get(item.source, "其他")


def _section_confidence(items: list[IntelItem]) -> str:
    """从 items 的 confidence 推断 section 整体置信度"""
    confs = [i.confidence for i in items if i.confidence]
    if not confs:
        return "unknown"
    c = Counter(confs)
    # 有多个 high → section high; 否则取众数
    if c.get("high", 0) >= 2:
        return "high"
    return c.most_common(1)[0][0]


def _compute_period(items_dates: list[str]) -> str:
    """从 items 日期列表推断周期标识"""
    valid = [d for d in items_dates if d]
    if not valid:
        today = date_mod.today()
        return today.strftime("%Y-W%V")
    latest = max(valid)
    try:
        dt = date_mod.fromisoformat(latest)
        return dt.strftime("%Y-W%V")
    except (ValueError, TypeError):
        return latest[:7] if len(latest) >= 7 else latest


def build_ir(validated_items: list[dict], search_meta: dict = None,
             topics: list[dict] = None) -> ReportIR:
    """从 validated 数据构建 ReportIR"""
    items = [_item_from_dict(d) for d in validated_items]

    # 1. 按话题分组为 Section
    topic_groups: dict[str, list[IntelItem]] = {}
    for item in items:
        topic = _detect_topic(item, topics)
        topic_groups.setdefault(topic, []).append(item)

    sections = []
    for topic_name, group_items in topic_groups.items():
        # 排序：red 在前，然后按日期降序
        group_items.sort(key=lambda i: (0 if i.priority == "red" else 1, i.date or ""), reverse=False)
        # re-sort: red first, then by date descending within priority
        group_items.sort(key=lambda i: (0 if i.priority == "red" else 1, ""))
        sections.append(Section(
            topic=topic_name,
            confidence=_section_confidence(group_items),
            items=group_items,
        ))

    # 排序 sections：含 red+high confidence 的排前面
    def section_sort_key(s: Section):
        has_red = any(i.priority == "red" for i in s.items)
        is_high = s.confidence == "high"
        return (0 if (has_red and is_high) else (1 if has_red else 2), s.topic)

    sections.sort(key=section_sort_key)

    # 2. 计算 distributions
    conf_dist = Counter(i.confidence or "unknown" for i in items)
    sent_dist = Counter(i.sentiment or "unknown" for i in items)

    # 3. 数据来源
    sources = sorted(set(i.source for i in items if i.source))

    # 4. 日期
    all_dates = [i.date for i in items]
    today = date_mod.today().isoformat()
    report_date = max(all_dates) if [d for d in all_dates if d] else today
    period = _compute_period(all_dates)

    return ReportIR(
        date=report_date,
        period=period,
        sections=sections,
        data_sources=sources,
        search_meta=search_meta or {},
        confidence_distribution=dict(conf_dist),
        sentiment_distribution=dict(sent_dist),
        total_items=len(items),
    )


def generate_report(validated_items: list[dict], search_meta: dict = None,
                    topics: list[dict] = None, output_dir: str = None) -> tuple[str, ReportIR]:
    """完整报告生成流程，返回 (markdown_path, ir)"""
    ir = build_ir(validated_items, search_meta, topics)

    # 输出目录
    report_date = ir.date
    output_dir = output_dir or str(Path(__file__).parent.parent / "reports")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    md_content = render_markdown(ir)
    md_path = f"{output_dir}/{report_date}.md"
    Path(md_path).write_text(md_content, encoding="utf-8")

    json_content = render_json(ir)
    json_path = f"{output_dir}/{report_date}.json"
    Path(json_path).write_text(json_content, encoding="utf-8")

    return md_path, ir
