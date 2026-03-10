"""
Scout v2 — Pipeline Orchestrator

Master script that runs all Scout v2 engines in sequence with checkpoint/resume
support. Each engine is wrapped in try/except for graceful degradation — a failed
engine does not block downstream engines.

Usage:
    python -m intel.engines.pipeline [--resume] [--force spider,query] [--days 3]
"""

import argparse
import json
import logging
import os
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .database import init_db, log_pipeline_run, get_intel_items_for_date
from .llm_client import load_config
from .state import PipelineState, ENGINE_ORDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback keywords (used when SpiderEngine fails)
# ---------------------------------------------------------------------------

FALLBACK_KEYWORDS_PATH = Path(__file__).parent.parent / "data" / "scout_keywords_fixed.json"

HARDCODED_FALLBACK_TOPICS = [
    {"keyword": "小红书电商", "domain": "ecommerce", "priority": "high",
     "search_source": "searxng", "reason": "fallback"},
    {"keyword": "AI agent framework", "domain": "tech", "priority": "high",
     "search_source": "github", "reason": "fallback"},
    {"keyword": "content automation", "domain": "tech", "priority": "medium",
     "search_source": "searxng", "reason": "fallback"},
]

SLACK_NOTIFY_SCRIPT = Path("/home/hangn/slack-bot/slack_notify.sh")


def _load_fallback_topics() -> list[dict]:
    """Load fallback topics from fixed keywords file, or use hardcoded list."""
    if FALLBACK_KEYWORDS_PATH.exists():
        try:
            data = json.loads(FALLBACK_KEYWORDS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                logger.info("Loaded %d fallback topics from %s", len(data), FALLBACK_KEYWORDS_PATH)
                return data
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse %s, using hardcoded fallback", FALLBACK_KEYWORDS_PATH)
    return HARDCODED_FALLBACK_TOPICS


# ---------------------------------------------------------------------------
# Engine runner helpers
# ---------------------------------------------------------------------------

def _run_spider(context: dict, days: int) -> dict:
    """Run SpiderEngine: extract topics from TrendRadar + RSS."""
    from .spider import extract_topics

    topics = extract_topics(days=days)
    context["topics"] = topics
    return {"topic_count": len(topics)}


def _run_query(context: dict) -> dict:
    """Run QueryEngine: search for intel based on topics."""
    from .query import run_query

    topics = context.get("topics", [])
    intel_items = run_query(topics)
    context["intel_items"] = intel_items
    return {"item_count": len(intel_items)}


def _run_media(context: dict) -> dict:
    """Run MediaEngine: enrich intel items with media analysis."""
    from .media import enrich_intel_with_media

    items = context.get("intel_items", [])
    enriched = enrich_intel_with_media(items)
    context["intel_items"] = enriched
    enriched_count = sum(1 for i in enriched if i.get("image_analysis"))
    return {"enriched_count": enriched_count, "total": len(enriched)}


def _run_insight(context: dict) -> dict:
    """Run InsightEngine: enrich with internal data context."""
    from .insight import enrich_with_internal_data

    items = context.get("intel_items", [])
    enriched = enrich_with_internal_data(items)
    context["intel_items"] = enriched
    enriched_count = sum(1 for i in enriched if i.get("relevance"))
    return {"enriched_count": enriched_count, "total": len(enriched)}


def _run_forum(context: dict) -> dict:
    """Run ForumEngine: cross-validate intel items."""
    from .forum import cross_validate

    items = context.get("intel_items", [])
    validated = cross_validate(items)
    context["validated_items"] = validated
    validated_count = sum(1 for i in validated if i.get("confidence"))
    return {"validated_count": validated_count, "total": len(validated)}


def _run_report(context: dict) -> dict:
    """Run ReportEngine: generate the final report."""
    from .report import generate_report

    items = context.get("validated_items", context.get("intel_items", []))
    topics = context.get("topics", [])
    search_meta = context.get("search_meta")
    output_dir = context.get("output_dir")

    report_path, report_ir = generate_report(
        items,
        search_meta=search_meta,
        topics=topics,
        output_dir=output_dir,
    )
    context["report_path"] = report_path
    context["report_ir"] = report_ir
    return {"report_path": report_path, "item_count": len(items)}


# Engine name -> runner function mapping
ENGINE_RUNNERS = {
    "spider": _run_spider,
    "query": _run_query,
    "media": _run_media,
    "insight": _run_insight,
    "forum": _run_forum,
    "report": _run_report,
}


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------

def _send_slack_summary(summary: dict, cfg: dict):
    """Send pipeline summary to Slack via slack_notify.sh."""
    channel = cfg.get("slack", {}).get("channel")
    if not channel:
        logger.debug("No SLACK_CHANNEL configured, skipping notification")
        return
    if not SLACK_NOTIFY_SCRIPT.exists():
        logger.warning("slack_notify.sh not found at %s", SLACK_NOTIFY_SCRIPT)
        return

    status_emoji = "white_check_mark" if summary["status"] == "completed" else "warning"
    engine_lines = []
    for eng in summary.get("engines", []):
        icon = "white_check_mark" if eng["status"] == "success" else "x"
        line = f":{icon}: {eng['engine']} ({eng.get('duration_s', '?')}s)"
        if eng.get("error"):
            line += f" — {eng['error'][:80]}"
        engine_lines.append(line)

    message = (
        f":{status_emoji}: *Scout v2 Pipeline — {summary['date']}*\n"
        f"Duration: {summary.get('total_duration_s', '?')}s | "
        f"Items: {summary.get('total_items', 0)}\n"
        + "\n".join(engine_lines)
    )

    try:
        subprocess.run(
            [str(SLACK_NOTIFY_SCRIPT), channel, message],
            capture_output=True, text=True, timeout=30,
        )
        logger.info("Slack notification sent to %s", channel)
    except Exception as e:
        logger.warning("Failed to send Slack notification: %s", e)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    resume: bool = True,
    force_engines: list[str] | None = None,
    days: int = 3,
) -> dict:
    """
    Main entry point for the Scout v2 pipeline.

    Args:
        resume: If True, check for existing checkpoint and resume from it.
        force_engines: If set, only run these engines (skip others).
        days: Number of days to look back for SpiderEngine.

    Returns:
        Summary dict with status, duration, per-engine results.
    """
    cfg = load_config()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pipeline_start = time.monotonic()

    # --- Database ---
    conn = init_db()

    # --- State: resume or fresh ---
    state = None
    if resume:
        state = PipelineState.load_checkpoint(today)
        if state and state.status == "completed" and not force_engines:
            logger.info("Pipeline already completed for %s, nothing to do", today)
            return {"status": "already_completed", "date": today}
        if state:
            logger.info(
                "Resuming pipeline for %s from checkpoint (completed: %s)",
                today,
                [e.engine if hasattr(e, "engine") else e.get("engine") for e in state.completed_engines],
            )

    if state is None:
        state = PipelineState(run_id=run_id, date=today)
        state.save_checkpoint()

    # Log pipeline start
    log_pipeline_run(conn, state.run_id, date=today, status="running", started_at=run_id)

    # --- Context dict: data flows between engines ---
    context: dict = {}

    # Determine which engines to run
    if force_engines:
        engines_to_run = [e for e in ENGINE_ORDER if e in force_engines]
    else:
        engines_to_run = ENGINE_ORDER

    # --- Run engines ---
    for engine_name in engines_to_run:
        # Skip if already done (and not forced)
        if not force_engines and state.is_engine_done(engine_name):
            logger.info("Skipping %s (already done in checkpoint)", engine_name)
            continue

        runner = ENGINE_RUNNERS.get(engine_name)
        if runner is None:
            logger.error("Unknown engine: %s", engine_name)
            continue

        logger.info("=" * 60)
        logger.info("Starting engine: %s", engine_name)
        logger.info("=" * 60)

        state.start_engine(engine_name)
        engine_start = time.monotonic()

        try:
            # SpiderEngine takes a `days` arg
            if engine_name == "spider":
                metrics = runner(context, days=days)
            else:
                metrics = runner(context)

            duration_s = round(time.monotonic() - engine_start, 1)
            metrics["duration_s"] = duration_s

            state.mark_engine_done(engine_name, status="success", metrics=metrics)
            logger.info(
                "Engine %s completed in %.1fs — %s",
                engine_name, duration_s, metrics,
            )

        except Exception as exc:
            duration_s = round(time.monotonic() - engine_start, 1)
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error("Engine %s FAILED after %.1fs: %s", engine_name, duration_s, error_msg)

            state.mark_engine_done(
                engine_name,
                status="failed",
                error=error_msg,
                metrics={"duration_s": duration_s},
            )

            # --- Graceful degradation ---
            _handle_engine_failure(engine_name, context, conn, today)

    # --- Finalize ---
    total_duration_s = round(time.monotonic() - pipeline_start, 1)

    has_failure = any(
        (e.status if hasattr(e, "status") else e.get("status")) == "failed"
        for e in state.completed_engines
    )
    final_status = "completed" if not has_failure else "completed_with_errors"
    state.status = final_status
    state.save_checkpoint()

    total_items = len(context.get("validated_items", context.get("intel_items", [])))

    # Build summary
    engine_summaries = []
    for e in state.completed_engines:
        if hasattr(e, "engine"):
            engine_summaries.append(asdict(e))
        else:
            engine_summaries.append(e)

    summary = {
        "status": final_status,
        "date": today,
        "run_id": state.run_id,
        "total_duration_s": total_duration_s,
        "total_items": total_items,
        "report_path": context.get("report_path"),
        "engines": engine_summaries,
    }

    # Log to database
    log_pipeline_run(
        conn,
        state.run_id,
        date=today,
        status=final_status,
        finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        engines_completed=[e["engine"] for e in engine_summaries],
        total_items=total_items,
        report_path=context.get("report_path"),
    )

    conn.close()

    # Slack notification
    _send_slack_summary(summary, cfg)

    logger.info("=" * 60)
    logger.info("Pipeline %s in %.1fs — %d items", final_status, total_duration_s, total_items)
    logger.info("=" * 60)

    return summary


def _handle_engine_failure(engine_name: str, context: dict, conn, today: str):
    """Apply fallback logic when an engine fails."""
    if engine_name == "spider":
        # No topics → use fallback keywords
        fallback = _load_fallback_topics()
        context["topics"] = fallback
        logger.warning("Spider failed, using %d fallback topics", len(fallback))

    elif engine_name == "query":
        # No intel items from search → try loading from DB
        try:
            db_items = get_intel_items_for_date(conn, today)
            if db_items:
                context["intel_items"] = db_items
                logger.warning("Query failed, loaded %d items from DB for %s", len(db_items), today)
            else:
                context["intel_items"] = []
                logger.warning("Query failed, no items in DB either — continuing with empty list")
        except Exception as db_err:
            logger.warning("Query failed and DB fallback also failed: %s", db_err)
            context["intel_items"] = []

    elif engine_name in ("media", "insight", "forum"):
        # Enrichment failures: items pass through unchanged
        logger.warning("%s failed — items pass through unchanged", engine_name)
        if engine_name == "forum":
            # Ensure validated_items exists for report
            context.setdefault("validated_items", context.get("intel_items", []))

    elif engine_name == "report":
        logger.error("Report engine failed — no report generated")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scout v2 Pipeline Orchestrator — run all engines in sequence",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from checkpoint if available (default: True)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Force a fresh run, ignoring any checkpoint",
    )
    parser.add_argument(
        "--force",
        type=str,
        default=None,
        help="Comma-separated list of engines to force-run (e.g., spider,query)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="Number of days to look back for SpiderEngine (default: 3)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )

    args = parser.parse_args()

    # Logging setup
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    resume = not args.no_resume
    force_engines = args.force.split(",") if args.force else None

    summary = run_pipeline(resume=resume, force_engines=force_engines, days=args.days)

    # Print summary to stdout
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
