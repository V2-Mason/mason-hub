# bilibili-creator-dive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a user-level Claude Code skill that takes a Bilibili UP主 URL and produces raw research materials (channel metadata, selected audio, Whisper transcripts) via 4 composable subcommands.

**Architecture:** Phase-addressable skill with 4 entry scripts (probe/collect/transcribe/dive) sharing helper modules for filter parsing, wbi signing, API calls, and error classification. Idempotent file-based state (skip-if-exists) replaces a dedicated resume system. All tests run locally with mocked network and model calls; real B站 API is exercised only by a manual smoke test at the end.

**Tech Stack:** Python 3.10+, `faster-whisper` (turbo), `onnxruntime-directml`, `yt-dlp`, `requests`, `pyyaml`, `pytest`, `pytest-mock`

**Design spec:** [docs/superpowers/specs/2026-04-07-bilibili-creator-dive-design.md](../specs/2026-04-07-bilibili-creator-dive-design.md)

---

## Task 1: Skill Scaffolding

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/SKILL.md` (stub, filled in Task 12)
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/__init__.py` (empty)
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/common.py`
- Create: `~/.claude/skills/bilibili-creator-dive/tests/__init__.py` (empty)
- Create: `~/.claude/skills/bilibili-creator-dive/presets/.gitkeep` (empty)
- Create: `~/.claude/skills/bilibili-creator-dive/tests/fixtures/sample_video_list.tsv`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p ~/.claude/skills/bilibili-creator-dive/scripts
mkdir -p ~/.claude/skills/bilibili-creator-dive/tests/fixtures
mkdir -p ~/.claude/skills/bilibili-creator-dive/presets
mkdir -p ~/.claude/skills/bilibili-creator-dive/references
touch ~/.claude/skills/bilibili-creator-dive/scripts/__init__.py
touch ~/.claude/skills/bilibili-creator-dive/tests/__init__.py
touch ~/.claude/skills/bilibili-creator-dive/presets/.gitkeep
```

- [ ] **Step 2: Write SKILL.md stub (minimal frontmatter, fill content in Task 12)**

Create `~/.claude/skills/bilibili-creator-dive/SKILL.md`:

```markdown
---
name: bilibili-creator-dive
description: >
  Use when analyzing a Bilibili UP主 channel for methodology extraction, track
  recon, or content research. Downloads metadata + audio (not video) + Whisper
  transcripts. Produces raw materials for conversation-driven analysis.
  Triggers: "开采 UP 主", "分析 B 站创作者", "/bilibili-creator-dive",
  "creator deep dive".
---

# /bilibili-creator-dive

[TASK 12 will fill this in]
```

- [ ] **Step 3: Write common.py with shared constants and helpers**

Create `~/.claude/skills/bilibili-creator-dive/scripts/common.py`:

```python
"""Shared utilities for bilibili-creator-dive scripts."""
import logging
import os
import re
import sys
from pathlib import Path

COOKIES_PATH = Path.home() / ".cookies" / "bilibili.txt"
DEFAULT_WHISPER_MODEL = "turbo"
DEFAULT_WHISPER_LANGUAGE = "zh"
DEFAULT_WHISPER_BEAM = 5
DEFAULT_VAD_SILENCE_MS = 500
MIN_VALID_MP3_BYTES = 10_000
YTDLP_RETRIES = 10

UID_URL_PATTERN = re.compile(r"space\.bilibili\.com/(\d+)")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure stderr logging for a script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    return logging.getLogger("bilibili-creator-dive")


def creator_dir(out_root: Path, slug: str) -> Path:
    """Return the per-creator output directory, creating it if missing."""
    p = Path(out_root) / slug
    p.mkdir(parents=True, exist_ok=True)
    return p


def parse_uid_from_url(url: str) -> str:
    """Extract the numeric UID from a B站 space URL.

    Raises ValueError if the URL does not contain a UID.
    """
    m = UID_URL_PATTERN.search(url)
    if not m:
        raise ValueError(f"Cannot extract UID from URL: {url!r}")
    return m.group(1)


def require_cookies() -> Path:
    """Verify cookies file exists; raise FileNotFoundError with actionable message."""
    if not COOKIES_PATH.exists():
        raise FileNotFoundError(
            f"Bilibili cookies not found at {COOKIES_PATH}. "
            f"Export from browser (e.g. Get cookies.txt extension) and place there."
        )
    return COOKIES_PATH
```

- [ ] **Step 4: Write sample fixture for filter tests**

Create `~/.claude/skills/bilibili-creator-dive/tests/fixtures/sample_video_list.tsv`:

```
BV	title	duration	date	views
BV1A1	小红书运营技巧	600	20230115	12000
BV1A2	抖音算法深度解析	1200	20230320	45000
BV1A3	【直播回放】自媒体问答	7200	20230401	3000
BV1A4	MCN签约避坑指南	900	20230515	28000
BV1A5	B站百大UP主观察	1800	20230810	67000
BV1A6	恰饭方法论入门	450	20231005	22000
BV1A7	短视频文案拆解	150	20231120	800
BV1A8	品牌投放趋势2024	2100	20240118	31000
BV1A9	视频号流量池分析	1500	20240625	18000
BV1A10	AI时代的创作者	1000	20250301	55000
```

- [ ] **Step 5: Verify scaffolding**

```bash
cd ~/.claude/skills/bilibili-creator-dive
ls -la scripts/ tests/ presets/ references/
python -c "from scripts import common; print(common.COOKIES_PATH)"
```

Expected: All directories exist, `common.py` imports cleanly, prints cookies path.

- [ ] **Step 6: Commit**

```bash
cd ~/.claude/skills/bilibili-creator-dive
git init 2>/dev/null || true
git add -A
git commit -m "feat(scaffold): create skill directory, SKILL.md stub, common.py, fixtures"
```

Note: since this is a user-level skill in `~/.claude/skills/`, whether it is a git repo depends on Mason's setup. If not, skip `git init` and commit at the mason-hub project level where this plan lives. Check with: `git rev-parse --show-toplevel` inside the skill dir.

---

## Task 2: Filter Parser — Tokenizer

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/filter_parser.py`
- Create: `~/.claude/skills/bilibili-creator-dive/tests/test_filter_parser.py`

Parses filter expression strings like `"top:30 by:views min_duration:5"` into structured tokens. This task covers tokenization only (splitting the expression); condition/selector semantics come in Task 3.

- [ ] **Step 1: Write failing test for simple tokenization**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_filter_parser.py`:

```python
"""Tests for filter expression parser."""
import pytest
from scripts.filter_parser import tokenize


def test_tokenize_empty_returns_empty_list():
    assert tokenize("") == []


def test_tokenize_single_condition():
    assert tokenize("min_views:5000") == [("min_views", "5000")]


def test_tokenize_multiple_conditions():
    result = tokenize("top:30 by:views min_duration:5")
    assert result == [
        ("top", "30"),
        ("by", "views"),
        ("min_duration", "5"),
    ]


def test_tokenize_bv_list_keeps_brackets():
    # bv:[...] must be tokenized as one token despite containing commas
    result = tokenize("bv:[BV1xxx,BV1yyy,BV1zzz]")
    assert result == [("bv", "[BV1xxx,BV1yyy,BV1zzz]")]


def test_tokenize_title_regex_keeps_slashes():
    result = tokenize("title_exclude:/直播回放|充电预热/")
    assert result == [("title_exclude", "/直播回放|充电预热/")]


def test_tokenize_date_range_keeps_dots():
    assert tokenize("date:2022-01..2024-12") == [("date", "2022-01..2024-12")]


def test_tokenize_open_date_range():
    assert tokenize("date:2022-01..") == [("date", "2022-01..")]


def test_tokenize_rejects_missing_colon():
    with pytest.raises(ValueError, match="malformed token"):
        tokenize("topviews")


def test_tokenize_rejects_empty_key():
    with pytest.raises(ValueError, match="empty key"):
        tokenize(":foo")
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd ~/.claude/skills/bilibili-creator-dive
python -m pytest tests/test_filter_parser.py -v
```

Expected: ImportError — `scripts.filter_parser` does not exist yet.

- [ ] **Step 3: Implement tokenizer**

Create `~/.claude/skills/bilibili-creator-dive/scripts/filter_parser.py`:

```python
"""Filter expression parser for bilibili-creator-dive select phase.

Grammar (see design spec section 9.1):
    <filter_expr> ::= <token> (' ' <token>)*
    <token> ::= <key>:<value>

Special value types handled by tokenizer:
    - bv:[BV1,BV2,...]           brackets may contain commas
    - title_*:/regex/            slashes may contain any char
    - date:YYYY-MM..YYYY-MM      dots are part of value
"""
from typing import List, Tuple


def tokenize(expr: str) -> List[Tuple[str, str]]:
    """Split a filter expression into (key, value) tokens.

    Top-level delimiter is whitespace. Whitespace inside bracketed or
    slash-delimited values is preserved.

    Raises:
        ValueError: if a token is malformed (no colon, empty key).
    """
    expr = expr.strip()
    if not expr:
        return []

    tokens: List[Tuple[str, str]] = []
    i = 0
    n = len(expr)

    while i < n:
        # skip whitespace between tokens
        while i < n and expr[i].isspace():
            i += 1
        if i >= n:
            break

        # read key until colon
        key_start = i
        while i < n and expr[i] != ":":
            if expr[i].isspace():
                raise ValueError(f"malformed token at pos {key_start}: missing colon")
            i += 1
        if i >= n:
            raise ValueError(f"malformed token starting at {key_start}: no colon")
        key = expr[key_start:i]
        if not key:
            raise ValueError(f"empty key at pos {key_start}")
        i += 1  # skip colon

        # read value; stop at top-level whitespace unless inside brackets or slashes
        val_start = i
        depth_bracket = 0
        depth_slash = 0
        while i < n:
            c = expr[i]
            if c == "[" and depth_slash == 0:
                depth_bracket += 1
            elif c == "]" and depth_slash == 0:
                depth_bracket = max(0, depth_bracket - 1)
            elif c == "/":
                depth_slash = 1 - depth_slash
            elif c.isspace() and depth_bracket == 0 and depth_slash == 0:
                break
            i += 1
        value = expr[val_start:i]
        tokens.append((key, value))

    return tokens
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_filter_parser.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/filter_parser.py tests/test_filter_parser.py
git commit -m "feat(filter): tokenizer for filter expressions"
```

---

## Task 3: Filter Parser — AST and Application

**Files:**
- Modify: `~/.claude/skills/bilibili-creator-dive/scripts/filter_parser.py`
- Modify: `~/.claude/skills/bilibili-creator-dive/tests/test_filter_parser.py`

Convert tokens into a structured filter spec and apply it to a video list.

- [ ] **Step 1: Write failing tests for parser + apply**

Append to `tests/test_filter_parser.py`:

```python
from scripts.filter_parser import parse_filter, apply_filter, FilterSpec


# Shared sample video list (mirrors fixtures/sample_video_list.tsv)
SAMPLE_VIDEOS = [
    {"bv": "BV1A1", "title": "小红书运营技巧", "duration": 600, "date": "20230115", "views": 12000},
    {"bv": "BV1A2", "title": "抖音算法深度解析", "duration": 1200, "date": "20230320", "views": 45000},
    {"bv": "BV1A3", "title": "【直播回放】自媒体问答", "duration": 7200, "date": "20230401", "views": 3000},
    {"bv": "BV1A4", "title": "MCN签约避坑指南", "duration": 900, "date": "20230515", "views": 28000},
    {"bv": "BV1A5", "title": "B站百大UP主观察", "duration": 1800, "date": "20230810", "views": 67000},
    {"bv": "BV1A6", "title": "恰饭方法论入门", "duration": 450, "date": "20231005", "views": 22000},
    {"bv": "BV1A7", "title": "短视频文案拆解", "duration": 150, "date": "20231120", "views": 800},
    {"bv": "BV1A8", "title": "品牌投放趋势2024", "duration": 2100, "date": "20240118", "views": 31000},
    {"bv": "BV1A9", "title": "视频号流量池分析", "duration": 1500, "date": "20240625", "views": 18000},
    {"bv": "BV1A10", "title": "AI时代的创作者", "duration": 1000, "date": "20250301", "views": 55000},
]


def test_parse_filter_empty_returns_empty_spec():
    spec = parse_filter("")
    assert spec.conditions == {}
    assert spec.selector is None
    assert spec.bv_list is None


def test_parse_filter_conditions_only():
    spec = parse_filter("min_views:5000 min_duration:5")
    assert spec.conditions == {"min_views": 5000, "min_duration": 5}
    assert spec.selector is None


def test_parse_filter_top_requires_by():
    with pytest.raises(ValueError, match="top requires by:"):
        parse_filter("top:30")


def test_parse_filter_latest_expands_to_top_by_date():
    spec = parse_filter("latest:20")
    assert spec.selector == ("top", 20, "date")


def test_parse_filter_bv_list():
    spec = parse_filter("bv:[BV1xxx,BV1yyy]")
    assert spec.bv_list == ["BV1xxx", "BV1yyy"]


def test_parse_filter_bv_list_overrides_other_tokens():
    # Conditions present but bv_list should still take effect
    spec = parse_filter("min_views:5000 bv:[BV1xxx]")
    assert spec.bv_list == ["BV1xxx"]


def test_parse_filter_date_closed_range():
    spec = parse_filter("date:2023-01..2023-12")
    assert spec.conditions["date_from"] == "202301"
    assert spec.conditions["date_to"] == "202312"


def test_parse_filter_date_open_start():
    spec = parse_filter("date:2024-01..")
    assert spec.conditions["date_from"] == "202401"
    assert "date_to" not in spec.conditions


def test_parse_filter_date_open_end():
    spec = parse_filter("date:..2023-06")
    assert spec.conditions["date_to"] == "202306"
    assert "date_from" not in spec.conditions


def test_apply_filter_min_views():
    spec = parse_filter("min_views:20000")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    assert {v["bv"] for v in result} == {
        "BV1A2", "BV1A4", "BV1A5", "BV1A6", "BV1A8", "BV1A10"
    }


def test_apply_filter_duration_range_minutes():
    # min_duration:5 max_duration:30 → 300-1800 seconds
    spec = parse_filter("min_duration:5 max_duration:30")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    bvs = {v["bv"] for v in result}
    assert "BV1A7" not in bvs  # 150s too short
    assert "BV1A3" not in bvs  # 7200s too long
    assert "BV1A8" not in bvs  # 2100s too long
    assert "BV1A1" in bvs      # 600s in range
    assert "BV1A5" in bvs      # 1800s exactly at max


def test_apply_filter_title_exclude_regex():
    spec = parse_filter("title_exclude:/直播回放/")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    assert "BV1A3" not in {v["bv"] for v in result}
    assert len(result) == len(SAMPLE_VIDEOS) - 1


def test_apply_filter_title_include_regex():
    spec = parse_filter("title_include:/小红书|抖音/")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    assert {v["bv"] for v in result} == {"BV1A1", "BV1A2"}


def test_apply_filter_date_range():
    spec = parse_filter("date:2023-06..2024-06")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    bvs = {v["bv"] for v in result}
    assert bvs == {"BV1A5", "BV1A6", "BV1A7", "BV1A8"}


def test_apply_filter_top_by_views_after_conditions():
    # From videos with min_duration:5 (5min = 300s), take top 3 by views
    spec = parse_filter("top:3 by:views min_duration:5")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    # min_duration:5 excludes BV1A7 (150s). Top 3 by views from remaining:
    # BV1A5 (67000), BV1A10 (55000), BV1A2 (45000)
    assert [v["bv"] for v in result] == ["BV1A5", "BV1A10", "BV1A2"]


def test_apply_filter_latest_n():
    spec = parse_filter("latest:3")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    # Latest 3 by date: BV1A10 (20250301), BV1A9 (20240625), BV1A8 (20240118)
    assert [v["bv"] for v in result] == ["BV1A10", "BV1A9", "BV1A8"]


def test_apply_filter_bv_list_bypasses_conditions():
    # min_duration:1000 would normally exclude BV1A1 (600s) and BV1A7 (150s)
    # but bv: list should override
    spec = parse_filter("min_duration:1000 bv:[BV1A1,BV1A7]")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    assert [v["bv"] for v in result] == ["BV1A1", "BV1A7"]


def test_apply_filter_no_selector_returns_all_passing():
    spec = parse_filter("min_views:20000 min_duration:5")
    result = apply_filter(SAMPLE_VIDEOS, spec)
    # No top/latest → all passing, no truncation
    assert len(result) == 5
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_filter_parser.py -v
```

Expected: import error or 18 new failures for `parse_filter`, `apply_filter`, `FilterSpec`.

- [ ] **Step 3: Implement parser and applier**

Append to `scripts/filter_parser.py`:

```python
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class FilterSpec:
    """Parsed filter expression.

    conditions: dict with keys among min_views, min_duration, max_duration,
                date_from, date_to, title_include, title_exclude
    selector: optional tuple ("top", N, field) where field in {"views", "date"}
    bv_list: optional list of BVs that completely overrides other tokens
    """
    conditions: Dict[str, Any] = field(default_factory=dict)
    selector: Optional[Tuple[str, int, str]] = None
    bv_list: Optional[List[str]] = None


def _parse_date_range(value: str) -> Dict[str, str]:
    """Parse 'YYYY-MM..YYYY-MM' or open-ended variants into date_from/date_to keys.

    Returns dict with 'date_from' and/or 'date_to' as YYYYMM strings.
    """
    if ".." not in value:
        raise ValueError(f"date range must contain '..': {value!r}")
    start, end = value.split("..", 1)
    out: Dict[str, str] = {}
    if start:
        out["date_from"] = start.replace("-", "")
    if end:
        out["date_to"] = end.replace("-", "")
    if not out:
        raise ValueError(f"date range has neither start nor end: {value!r}")
    return out


def _parse_regex_value(value: str, key: str) -> re.Pattern:
    """Parse '/regex/' into a compiled case-insensitive Pattern."""
    if not (value.startswith("/") and value.endswith("/") and len(value) >= 2):
        raise ValueError(f"{key} must be /regex/: got {value!r}")
    pattern = value[1:-1]
    return re.compile(pattern, re.IGNORECASE)


def parse_filter(expr: str) -> FilterSpec:
    """Parse a filter expression into a FilterSpec.

    Raises ValueError on malformed expressions.
    """
    tokens = tokenize(expr)
    spec = FilterSpec()
    pending_top: Optional[int] = None
    pending_by: Optional[str] = None

    for key, value in tokens:
        if key == "min_views":
            spec.conditions["min_views"] = int(value)
        elif key == "min_duration":
            spec.conditions["min_duration"] = int(value)  # minutes
        elif key == "max_duration":
            spec.conditions["max_duration"] = int(value)  # minutes
        elif key == "date":
            spec.conditions.update(_parse_date_range(value))
        elif key == "title_include":
            spec.conditions["title_include"] = _parse_regex_value(value, key)
        elif key == "title_exclude":
            spec.conditions["title_exclude"] = _parse_regex_value(value, key)
        elif key == "top":
            pending_top = int(value)
        elif key == "by":
            if value not in ("views", "date"):
                raise ValueError(f"by: must be views or date, got {value!r}")
            pending_by = value
        elif key == "latest":
            spec.selector = ("top", int(value), "date")
        elif key == "bv":
            # bv:[BV1,BV2,...]
            if not (value.startswith("[") and value.endswith("]")):
                raise ValueError(f"bv: must be bracketed list, got {value!r}")
            inner = value[1:-1].strip()
            spec.bv_list = [b.strip() for b in inner.split(",") if b.strip()]
        else:
            raise ValueError(f"unknown filter key: {key!r}")

    if pending_top is not None:
        if pending_by is None:
            raise ValueError("top: requires by:views or by:date")
        spec.selector = ("top", pending_top, pending_by)
    elif pending_by is not None:
        raise ValueError("by: without top: has no effect")

    return spec


def _passes_conditions(video: dict, conds: Dict[str, Any]) -> bool:
    if "min_views" in conds and video["views"] < conds["min_views"]:
        return False
    if "min_duration" in conds and video["duration"] < conds["min_duration"] * 60:
        return False
    if "max_duration" in conds and video["duration"] > conds["max_duration"] * 60:
        return False
    if "date_from" in conds and video["date"] < conds["date_from"]:
        return False
    if "date_to" in conds:
        # date_to is YYYYMM; video date is YYYYMMDD. Compare via prefix padding.
        if video["date"][:6] > conds["date_to"]:
            return False
    if "title_include" in conds and not conds["title_include"].search(video["title"]):
        return False
    if "title_exclude" in conds and conds["title_exclude"].search(video["title"]):
        return False
    return True


def apply_filter(videos: List[dict], spec: FilterSpec) -> List[dict]:
    """Apply a FilterSpec to a video list. Returns filtered + possibly ordered list.

    Execution order:
        1. If bv_list present, return videos matching those BVs (in bv_list order).
        2. Otherwise apply conditions (AND).
        3. Apply selector (top N by field) if present.
    """
    if spec.bv_list is not None:
        by_bv = {v["bv"]: v for v in videos}
        return [by_bv[b] for b in spec.bv_list if b in by_bv]

    # Apply conditions
    passing = [v for v in videos if _passes_conditions(v, spec.conditions)]

    # Apply selector
    if spec.selector is None:
        return passing
    _, n, field = spec.selector
    key_fn = (lambda v: v["views"]) if field == "views" else (lambda v: v["date"])
    passing.sort(key=key_fn, reverse=True)
    return passing[:n]
```

- [ ] **Step 4: Run tests to verify all pass**

```bash
python -m pytest tests/test_filter_parser.py -v
```

Expected: 27 passed total (9 from Task 2 + 18 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/filter_parser.py tests/test_filter_parser.py
git commit -m "feat(filter): FilterSpec, parse_filter, apply_filter"
```

---

## Task 4: select.py Entry Script

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/select.py`

select.py reads `video_list.tsv`, applies a filter expression, writes `selected.tsv` and `filter_used.yaml`, and prints a preview of the selection + cost estimate + top 5 excluded high-view videos.

Minimal unit testing for this script — it is a thin CLI wrapper. Integration is verified via the smoke test in Task 14.

- [ ] **Step 1: Implement select.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/select.py`:

```python
#!/usr/bin/env python3
"""Phase 2: Apply filter expression to video_list.tsv.

Usage:
    python -m scripts.select <slug> --out <dir> --filter "<expr>"
"""
import argparse
import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import yaml

from scripts.common import creator_dir, setup_logging
from scripts.filter_parser import apply_filter, parse_filter, FilterSpec


def read_video_list(path: Path) -> list[dict]:
    """Read video_list.tsv into a list of dicts with typed fields."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        videos = []
        for row in reader:
            videos.append({
                "bv": row["BV"],
                "title": row["title"],
                "duration": int(row["duration"]),
                "date": row["date"],
                "views": int(row["views"]),
            })
    return videos


def write_selected_tsv(path: Path, videos: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["BV", "title", "duration", "date", "views"])
        for v in videos:
            writer.writerow([v["bv"], v["title"], v["duration"], v["date"], v["views"]])


def compute_tsv_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_filter_used_yaml(
    path: Path,
    expr: str,
    spec: FilterSpec,
    total_pool: int,
    after_exclusions: int,
    final_selected: int,
    video_list_sha: str,
) -> None:
    # Serialize FilterSpec conditions (dropping compiled regex → keep original string)
    parsed = {}
    for k, v in spec.conditions.items():
        if hasattr(v, "pattern"):  # compiled regex
            parsed[k] = v.pattern
        else:
            parsed[k] = v
    if spec.selector is not None:
        parsed["selector"] = {"kind": spec.selector[0], "n": spec.selector[1], "by": spec.selector[2]}
    if spec.bv_list is not None:
        parsed["bv_list"] = spec.bv_list

    data = {
        "filter_expression": expr,
        "parsed": parsed,
        "applied_at": datetime.now().isoformat(timespec="seconds"),
        "total_pool": total_pool,
        "after_exclusions": after_exclusions,
        "final_selected": final_selected,
        "video_list_tsv_sha256": video_list_sha,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def format_duration(total_seconds: int) -> str:
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}min"
    return f"{m}min {s}s"


def print_preview(
    expr: str,
    total_pool: int,
    after_exclusions: int,
    selected: list[dict],
    excluded_high_view: list[dict],
) -> None:
    """Print a markdown preview to stdout."""
    total_dur = sum(v["duration"] for v in selected)
    est_whisper_sec = int(total_dur * 0.25)
    est_disk_mb = int(total_dur * 0.25 / 8)  # ~256kbps audio ≈ 2MB/min → rough

    print("# Filter 结果预览\n")
    print(f"Expression: `{expr}`")
    print(f"Pool: {total_pool} → exclusions → {after_exclusions} → final → {len(selected)}\n")
    print(f"## Selected {len(selected)} videos\n")
    print("| # | BV | 播放量 | 时长 | 日期 | 标题 |")
    print("|---|---|---|---|---|---|")
    for i, v in enumerate(selected, 1):
        dur = format_duration(v["duration"])
        date_fmt = f"{v['date'][:4]}-{v['date'][4:6]}"
        title = (v["title"][:40] + "...") if len(v["title"]) > 40 else v["title"]
        print(f"| {i} | {v['bv']} | {v['views']:,} | {dur} | {date_fmt} | {title} |")
    print()
    print("## 成本估算\n")
    print(f"- 总时长: {format_duration(total_dur)}")
    print(f"- 预计 Whisper 耗时: ~{format_duration(est_whisper_sec)} (RTF 0.25x on turbo+DirectML)")
    print(f"- 预计磁盘: ~{est_disk_mb}MB audio + ~{len(selected)}MB transcripts\n")
    if excluded_high_view:
        print("## 排除的高播放条目 (前 5, 以防误杀)\n")
        print("| BV | 播放量 | 时长 | 标题 |")
        print("|---|---|---|---|")
        for v in excluded_high_view[:5]:
            dur = format_duration(v["duration"])
            title = (v["title"][:40] + "...") if len(v["title"]) > 40 else v["title"]
            print(f"| {v['bv']} | {v['views']:,} | {dur} | {title} |")
        print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 2: apply filter to video_list.tsv")
    ap.add_argument("slug", help="Creator slug (directory name)")
    ap.add_argument("--out", required=True, type=Path, help="Output root directory")
    ap.add_argument("--filter", dest="filter_expr", required=True, help="Filter expression")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    log = setup_logging(args.verbose)
    cdir = creator_dir(args.out, args.slug)
    video_list_path = cdir / "video_list.tsv"

    if not video_list_path.exists():
        log.error(f"video_list.tsv not found at {video_list_path}. Run `probe` first.")
        return 2

    videos = read_video_list(video_list_path)
    total_pool = len(videos)

    try:
        spec = parse_filter(args.filter_expr)
    except ValueError as e:
        log.error(f"Invalid filter expression: {e}")
        return 2

    selected = apply_filter(videos, spec)
    if not selected:
        log.error("Filter matched 0 videos. Adjust expression and retry.")
        return 3

    # Compute "after_exclusions" (before selector truncation) for reporting
    if spec.bv_list is not None:
        after_exclusions = len(selected)  # bv_list bypasses conditions
    else:
        # Re-run conditions only, without selector
        from scripts.filter_parser import _passes_conditions
        after_exclusions = sum(1 for v in videos if _passes_conditions(v, spec.conditions))

    # Compute top-5 excluded high-view videos (for preview safety net)
    selected_bvs = {v["bv"] for v in selected}
    excluded = [v for v in videos if v["bv"] not in selected_bvs]
    excluded.sort(key=lambda v: v["views"], reverse=True)

    # Write outputs
    selected_path = cdir / "selected.tsv"
    write_selected_tsv(selected_path, selected)

    filter_yaml_path = cdir / "filter_used.yaml"
    sha = compute_tsv_sha256(video_list_path)
    write_filter_used_yaml(
        filter_yaml_path, args.filter_expr, spec,
        total_pool, after_exclusions, len(selected), sha,
    )

    print_preview(args.filter_expr, total_pool, after_exclusions, selected, excluded)
    log.info(f"Wrote {selected_path} and {filter_yaml_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add a smoke test for select.py with the fixture**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_select_smoke.py`:

```python
"""Smoke test for select.py end-to-end using fixture data."""
import shutil
from pathlib import Path

import pytest

from scripts.select import main as select_main


@pytest.fixture
def tmp_creator_dir(tmp_path):
    """Create a tmp creator dir with a copy of sample_video_list.tsv as video_list.tsv."""
    fixture = Path(__file__).parent / "fixtures" / "sample_video_list.tsv"
    slug_dir = tmp_path / "testcreator"
    slug_dir.mkdir()
    shutil.copy(fixture, slug_dir / "video_list.tsv")
    return tmp_path


def test_select_writes_selected_tsv(tmp_creator_dir):
    rc = select_main([
        "testcreator",
        "--out", str(tmp_creator_dir),
        "--filter", "top:3 by:views min_duration:5",
    ])
    assert rc == 0
    selected = (tmp_creator_dir / "testcreator" / "selected.tsv").read_text(encoding="utf-8")
    assert "BV1A5" in selected  # top view
    assert "BV1A7" not in selected  # excluded by min_duration
    # Should have header + 3 data rows
    assert len(selected.strip().splitlines()) == 4


def test_select_writes_filter_used_yaml(tmp_creator_dir):
    rc = select_main([
        "testcreator",
        "--out", str(tmp_creator_dir),
        "--filter", "latest:2",
    ])
    assert rc == 0
    import yaml
    data = yaml.safe_load((tmp_creator_dir / "testcreator" / "filter_used.yaml").read_text())
    assert data["filter_expression"] == "latest:2"
    assert data["final_selected"] == 2
    assert "video_list_tsv_sha256" in data


def test_select_empty_match_returns_error(tmp_creator_dir):
    rc = select_main([
        "testcreator",
        "--out", str(tmp_creator_dir),
        "--filter", "min_views:9999999",
    ])
    assert rc == 3  # documented error code for 0-match


def test_select_missing_video_list_returns_error(tmp_path):
    rc = select_main([
        "missingcreator",
        "--out", str(tmp_path),
        "--filter", "latest:5",
    ])
    assert rc == 2
```

- [ ] **Step 3: Run smoke tests**

```bash
cd ~/.claude/skills/bilibili-creator-dive
python -m pytest tests/test_select_smoke.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add scripts/select.py tests/test_select_smoke.py
git commit -m "feat(select): select.py entry script + smoke tests"
```

---

## Task 5: wbi Signer

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/wbi_signer.py`
- Create: `~/.claude/skills/bilibili-creator-dive/tests/test_wbi_signer.py`

Bilibili's wbi ("web bot identification") signature adds a query-string parameter `w_rid` that is a md5 of other params + a time-dependent key derived from two URLs returned by `/x/web-interface/nav`.

Reference algorithm (spec section 7.2): fetch nav, extract img_key and sub_key from `img_url`/`sub_url` basenames, mix them per a fixed permutation table to form `mixin_key`, append `wts` timestamp to request params, sort params alphabetically, URL-encode, append mixin_key, md5.

- [ ] **Step 1: Write failing tests for wbi signer**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_wbi_signer.py`:

```python
"""Tests for Bilibili wbi signature algorithm."""
import pytest
from scripts.wbi_signer import get_mixin_key, sign_params


# Known-good test vector derived from the published algorithm
# (img_key and sub_key are basenames of nav URLs with .png stripped)
IMG_KEY = "7cd084941338484aae1ad9425b84077c"
SUB_KEY = "4932caff0ff746eab6f01bf08b70ac45"
EXPECTED_MIXIN = "ea1db124af3c7062474693fa704f4ff8"  # derived from the fixed permutation table


def test_get_mixin_key_applies_permutation():
    mixin = get_mixin_key(IMG_KEY, SUB_KEY)
    # Must be exactly 32 chars (first 32 of permuted concat)
    assert len(mixin) == 32
    assert mixin == EXPECTED_MIXIN


def test_sign_params_adds_wts_and_w_rid():
    params = {"mid": "123456", "ps": 30, "pn": 1, "order": "pubdate"}
    signed = sign_params(params, IMG_KEY, SUB_KEY, wts=1700000000)
    assert "wts" in signed
    assert signed["wts"] == 1700000000
    assert "w_rid" in signed
    assert len(signed["w_rid"]) == 32  # md5 hex


def test_sign_params_is_deterministic_for_same_inputs():
    params = {"mid": "123456"}
    s1 = sign_params(params, IMG_KEY, SUB_KEY, wts=1700000000)
    s2 = sign_params(params, IMG_KEY, SUB_KEY, wts=1700000000)
    assert s1["w_rid"] == s2["w_rid"]


def test_sign_params_changes_with_wts():
    params = {"mid": "123456"}
    s1 = sign_params(params, IMG_KEY, SUB_KEY, wts=1700000000)
    s2 = sign_params(params, IMG_KEY, SUB_KEY, wts=1700000001)
    assert s1["w_rid"] != s2["w_rid"]


def test_sign_params_original_dict_not_mutated():
    params = {"mid": "123456"}
    original = dict(params)
    sign_params(params, IMG_KEY, SUB_KEY, wts=1700000000)
    assert params == original
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_wbi_signer.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement wbi_signer.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/wbi_signer.py`:

```python
"""Bilibili wbi signature helper.

Reference: references/bilibili-wbi-signing.md

The wbi signature attaches a `w_rid` query parameter to space/video API calls.
Without it, calls return -352 (risk control). The algorithm:

    1. Fetch /x/web-interface/nav → get wbi_img.img_url and wbi_img.sub_url
    2. img_key = basename(img_url) without .png
       sub_key = basename(sub_url) without .png
    3. mixin_key = permute(img_key + sub_key) per a fixed 64-index table, take first 32
    4. Add wts = current unix timestamp
    5. Sort params alphabetically by key; url-encode values; join as query string
    6. w_rid = md5(query_string + mixin_key)
"""
import hashlib
import time
import urllib.parse
from typing import Dict

# Fixed permutation table (from bilibili-api-python reference implementation)
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def get_mixin_key(img_key: str, sub_key: str) -> str:
    """Combine img_key and sub_key via the fixed permutation, return first 32 chars."""
    raw = img_key + sub_key
    return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def sign_params(
    params: Dict[str, object],
    img_key: str,
    sub_key: str,
    wts: int | None = None,
) -> Dict[str, object]:
    """Return a new dict with wts and w_rid added.

    The original params dict is not mutated.
    """
    signed = dict(params)
    signed["wts"] = wts if wts is not None else int(time.time())

    mixin_key = get_mixin_key(img_key, sub_key)

    # Sort params, URL-encode values, join as query string
    sorted_items = sorted(signed.items())
    query = urllib.parse.urlencode(sorted_items)

    signed["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    return signed
```

- [ ] **Step 4: Derive EXPECTED_MIXIN from the algorithm and update test**

The test's `EXPECTED_MIXIN` was a placeholder; compute it from the real algorithm before finalizing.

Run a quick Python one-liner:

```bash
python -c "
from scripts.wbi_signer import get_mixin_key
print(get_mixin_key('7cd084941338484aae1ad9425b84077c', '4932caff0ff746eab6f01bf08b70ac45'))
"
```

Take the output and replace `EXPECTED_MIXIN` in `test_wbi_signer.py` with it.

- [ ] **Step 5: Run tests again**

```bash
python -m pytest tests/test_wbi_signer.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/wbi_signer.py tests/test_wbi_signer.py
git commit -m "feat(wbi): signature algorithm for Bilibili API"
```

---

## Task 6: Bilibili API Client

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/bili_api.py`
- Create: `~/.claude/skills/bilibili-creator-dive/tests/test_bili_api.py`

Wraps three Bilibili API endpoints: `/x/web-interface/nav` (wbi keys), `/x/space/acc/info` (channel meta), and `/x/space/wbi/arc/search` (paginated video list). All network calls are mocked in tests.

- [ ] **Step 1: Write failing tests for API client**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_bili_api.py`:

```python
"""Tests for Bilibili API wrappers (all network calls mocked)."""
from unittest.mock import Mock, patch

import pytest

from scripts.bili_api import (
    BiliAPIError,
    fetch_channel_info,
    fetch_video_list,
    fetch_wbi_keys,
)


def _mock_response(json_data, status=200):
    resp = Mock()
    resp.status_code = status
    resp.json.return_value = json_data
    return resp


@patch("scripts.bili_api.requests.get")
def test_fetch_wbi_keys_extracts_basenames(mock_get):
    mock_get.return_value = _mock_response({
        "code": 0,
        "data": {
            "wbi_img": {
                "img_url": "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png",
                "sub_url": "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png",
            }
        }
    })
    img_key, sub_key = fetch_wbi_keys()
    assert img_key == "7cd084941338484aae1ad9425b84077c"
    assert sub_key == "4932caff0ff746eab6f01bf08b70ac45"


@patch("scripts.bili_api.requests.get")
def test_fetch_wbi_keys_raises_on_error_code(mock_get):
    mock_get.return_value = _mock_response({"code": -101, "message": "not logged in"})
    with pytest.raises(BiliAPIError, match="not logged in"):
        fetch_wbi_keys()


@patch("scripts.bili_api.requests.get")
def test_fetch_channel_info_extracts_fields(mock_get):
    mock_get.return_value = _mock_response({
        "code": 0,
        "data": {
            "mid": 123456,
            "name": "小狗勾",
            "sign": "硬核不注水",
            "follower": 45200,
        }
    })
    info = fetch_channel_info("123456")
    assert info["name"] == "小狗勾"
    assert info["fans"] == 45200
    assert info["sign"] == "硬核不注水"
    assert info["uid"] == "123456"


@patch("scripts.bili_api.requests.get")
def test_fetch_video_list_paginates_and_stops(mock_get):
    # Two pages of data, third returns empty
    page1 = {
        "code": 0,
        "data": {
            "list": {
                "vlist": [
                    {"bvid": "BV1A1", "title": "t1", "length": "10:00", "created": 1700000000, "play": 1000},
                    {"bvid": "BV1A2", "title": "t2", "length": "05:30", "created": 1700100000, "play": 2000},
                ]
            },
            "page": {"count": 4, "pn": 1, "ps": 2},
        }
    }
    page2 = {
        "code": 0,
        "data": {
            "list": {
                "vlist": [
                    {"bvid": "BV1A3", "title": "t3", "length": "1:02:00", "created": 1700200000, "play": 500},
                    {"bvid": "BV1A4", "title": "t4", "length": "00:45", "created": 1700300000, "play": 300},
                ]
            },
            "page": {"count": 4, "pn": 2, "ps": 2},
        }
    }
    mock_get.side_effect = [_mock_response(page1), _mock_response(page2)]

    videos = fetch_video_list("123456", "IMGK", "SUBK", page_size=2)
    assert len(videos) == 4
    assert videos[0]["bv"] == "BV1A1"
    assert videos[0]["duration"] == 600        # 10:00
    assert videos[2]["duration"] == 3720       # 1:02:00
    assert videos[3]["duration"] == 45         # 00:45


@patch("scripts.bili_api.requests.get")
def test_fetch_video_list_handles_empty_channel(mock_get):
    mock_get.return_value = _mock_response({
        "code": 0,
        "data": {
            "list": {"vlist": []},
            "page": {"count": 0, "pn": 1, "ps": 30},
        }
    })
    videos = fetch_video_list("123456", "IMGK", "SUBK")
    assert videos == []


@patch("scripts.bili_api.requests.get")
def test_fetch_video_list_retries_on_transient_error(mock_get):
    # First call returns code -352 (risk), retry returns success with empty
    mock_get.side_effect = [
        _mock_response({"code": -352, "message": "risk control"}),
        _mock_response({"code": 0, "data": {"list": {"vlist": []}, "page": {"count": 0, "pn": 1, "ps": 30}}}),
    ]
    videos = fetch_video_list("123456", "IMGK", "SUBK", retries=2)
    assert videos == []
    assert mock_get.call_count == 2
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_bili_api.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement bili_api.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/bili_api.py`:

```python
"""Bilibili API wrappers for channel metadata collection.

All calls use the shared session with cookies loaded from ~/.cookies/bilibili.txt.
"""
import http.cookiejar
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests

from scripts.common import COOKIES_PATH
from scripts.wbi_signer import sign_params

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
ACC_INFO_URL = "https://api.bilibili.com/x/space/acc/info"
VIDEO_LIST_URL = "https://api.bilibili.com/x/space/wbi/arc/search"


class BiliAPIError(Exception):
    """Raised on API-level errors (non-zero code in response)."""


def _load_session() -> requests.Session:
    """Return a session with cookies and UA preloaded."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Referer": "https://www.bilibili.com/",
    })
    if COOKIES_PATH.exists():
        jar = http.cookiejar.MozillaCookieJar()
        try:
            jar.load(str(COOKIES_PATH), ignore_discard=True, ignore_expires=True)
            session.cookies.update(jar)
        except Exception as e:
            log.warning(f"Failed to load cookies: {e}")
    return session


def _check_code(data: dict) -> None:
    """Raise BiliAPIError if response code is non-zero."""
    code = data.get("code", 0)
    if code != 0:
        raise BiliAPIError(f"code={code}: {data.get('message', 'unknown')}")


def fetch_wbi_keys() -> Tuple[str, str]:
    """Fetch wbi img/sub keys from /x/web-interface/nav.

    Returns (img_key, sub_key). These are the basenames (without .png) of
    wbi_img.img_url and wbi_img.sub_url.
    """
    session = _load_session()
    resp = session.get(NAV_URL, timeout=10)
    data = resp.json()
    _check_code(data)

    wbi_img = data["data"]["wbi_img"]
    img_url = wbi_img["img_url"]
    sub_url = wbi_img["sub_url"]

    def _basename_no_ext(url: str) -> str:
        return url.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    return _basename_no_ext(img_url), _basename_no_ext(sub_url)


def fetch_channel_info(uid: str) -> Dict[str, object]:
    """Fetch basic channel metadata.

    Returns dict with uid, name, sign, fans.
    """
    session = _load_session()
    resp = session.get(ACC_INFO_URL, params={"mid": uid}, timeout=10)
    data = resp.json()
    _check_code(data)
    d = data["data"]
    return {
        "uid": str(d["mid"]),
        "name": d["name"],
        "sign": d.get("sign", ""),
        "fans": d.get("follower", 0),
    }


def _duration_str_to_seconds(s: str) -> int:
    """Convert 'MM:SS' or 'HH:MM:SS' into seconds."""
    parts = s.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    raise ValueError(f"unrecognized duration format: {s!r}")


def fetch_video_list(
    uid: str,
    img_key: str,
    sub_key: str,
    page_size: int = 30,
    retries: int = 3,
) -> List[Dict[str, object]]:
    """Fetch all videos for a channel, paginated.

    Returns list of dicts with keys: bv, title, duration (sec), date (YYYYMMDD), views.
    """
    session = _load_session()
    out: List[Dict[str, object]] = []
    pn = 1
    while True:
        params = {
            "mid": uid,
            "ps": page_size,
            "pn": pn,
            "order": "pubdate",
            "platform": "web",
            "web_location": "1550101",
        }

        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                signed = sign_params(params, img_key, sub_key)
                resp = session.get(VIDEO_LIST_URL, params=signed, timeout=10)
                data = resp.json()
                _check_code(data)
                break
            except BiliAPIError as e:
                last_err = e
                log.warning(f"page {pn} attempt {attempt+1}/{retries}: {e}")
                time.sleep(1.5 * (attempt + 1))
        else:
            raise last_err  # all retries failed

        vlist = data["data"]["list"]["vlist"]
        if not vlist:
            break
        for v in vlist:
            dt = datetime.fromtimestamp(v["created"])
            out.append({
                "bv": v["bvid"],
                "title": v["title"],
                "duration": _duration_str_to_seconds(v["length"]),
                "date": dt.strftime("%Y%m%d"),
                "views": v.get("play", 0),
            })

        total = data["data"]["page"]["count"]
        if pn * page_size >= total:
            break
        pn += 1
        time.sleep(0.5)  # rate-limit courtesy

    return out
```

- [ ] **Step 4: Run tests to verify all pass**

```bash
python -m pytest tests/test_bili_api.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/bili_api.py tests/test_bili_api.py
git commit -m "feat(bili-api): fetch_wbi_keys, fetch_channel_info, fetch_video_list"
```

---

## Task 7: probe_channel.py Entry Script + Summary Formatter

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/probe_channel.py`
- Modify: `~/.claude/skills/bilibili-creator-dive/tests/test_bili_api.py` (add formatter tests)

probe_channel.py ties bili_api together: parse UID, fetch keys + info + video list, write video_list.tsv, META.md, and probe_summary.md. The summary formatter is a pure function, so it's unit-tested in isolation.

- [ ] **Step 1: Write failing tests for summary formatter**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_probe_formatter.py`:

```python
"""Tests for probe_summary.md formatter."""
from scripts.probe_channel import (
    format_duration_buckets,
    format_year_distribution,
    format_view_percentiles,
    find_suspicious_videos,
    build_probe_summary,
)


SAMPLE = [
    {"bv": "BV1A1", "title": "t1", "duration": 200, "date": "20220115", "views": 1000},   # <5min
    {"bv": "BV1A2", "title": "t2", "duration": 600, "date": "20230320", "views": 12000},  # 5-15min
    {"bv": "BV1A3", "title": "【直播回放】xxx", "duration": 7200, "date": "20230401", "views": 3000},  # >60min + 直播
    {"bv": "BV1A4", "title": "t4", "duration": 1200, "date": "20230515", "views": 28000}, # 5-15min
    {"bv": "BV1A5", "title": "t5", "duration": 1800, "date": "20230810", "views": 67000}, # 15-30min
    {"bv": "BV1A6", "title": "t6", "duration": 3000, "date": "20240120", "views": 22000}, # 30-60min
]


def test_format_duration_buckets_counts_correctly():
    result = format_duration_buckets(SAMPLE)
    assert result == {
        "<5min": 1,
        "5-15min": 2,
        "15-30min": 1,
        "30-60min": 1,
        ">60min": 1,
    }


def test_format_year_distribution_drops_zeros():
    result = format_year_distribution(SAMPLE)
    assert result == {"2022": 1, "2023": 4, "2024": 1}


def test_format_view_percentiles():
    result = format_view_percentiles(SAMPLE)
    # Sorted: 1000, 3000, 12000, 22000, 28000, 67000
    assert "P50" in result and "Max" in result
    assert result["Max"] == 67000


def test_find_suspicious_videos_catches_livestream_replay():
    suspicious = find_suspicious_videos(SAMPLE)
    livestream_bvs = [s["bv"] for s in suspicious if s["reason"] == "title_livestream"]
    assert "BV1A3" in livestream_bvs


def test_find_suspicious_videos_catches_long_duration():
    suspicious = find_suspicious_videos(SAMPLE)
    long_bvs = [s["bv"] for s in suspicious if s["reason"] == "duration_gt_2h"]
    assert "BV1A3" in long_bvs


def test_build_probe_summary_includes_all_sections():
    channel = {"uid": "123", "name": "test", "fans": 100, "sign": "", "count": 6}
    md = build_probe_summary(channel, SAMPLE)
    assert "# Probe Summary" in md
    assert "## Channel" in md
    assert "## 时长分布" in md
    assert "## 发布年份分布" in md
    assert "## 播放量分布" in md
    assert "## 最热 10 条" in md
    assert "## 最新 10 条" in md
    assert "## 可疑条目" in md  # because sample contains one
    assert "## 完整列表" in md
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_probe_formatter.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement probe_channel.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/probe_channel.py`:

```python
#!/usr/bin/env python3
"""Phase 1: Probe a Bilibili UP主 channel.

Usage:
    python -m scripts.probe_channel <URL> <slug> --out <dir> [--refresh]
"""
import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from scripts.bili_api import fetch_channel_info, fetch_video_list, fetch_wbi_keys
from scripts.common import creator_dir, parse_uid_from_url, require_cookies, setup_logging


DURATION_BUCKETS = [
    ("<5min", 0, 5 * 60),
    ("5-15min", 5 * 60, 15 * 60),
    ("15-30min", 15 * 60, 30 * 60),
    ("30-60min", 30 * 60, 60 * 60),
    (">60min", 60 * 60, float("inf")),
]

LIVESTREAM_RE = re.compile(r"直播回放|直播录像")


def format_duration_buckets(videos: List[dict]) -> Dict[str, int]:
    out = {name: 0 for name, _, _ in DURATION_BUCKETS}
    for v in videos:
        d = v["duration"]
        for name, lo, hi in DURATION_BUCKETS:
            if lo <= d < hi:
                out[name] += 1
                break
    return out


def format_year_distribution(videos: List[dict]) -> Dict[str, int]:
    years: Dict[str, int] = {}
    for v in videos:
        y = v["date"][:4]
        years[y] = years.get(y, 0) + 1
    return dict(sorted(years.items()))


def format_view_percentiles(videos: List[dict]) -> Dict[str, int]:
    if not videos:
        return {"P25": 0, "P50": 0, "P75": 0, "P90": 0, "Max": 0}
    plays = sorted(v["views"] for v in videos)
    n = len(plays)

    def pct(p: float) -> int:
        idx = min(int(n * p), n - 1)
        return plays[idx]

    return {
        "P25": pct(0.25),
        "P50": pct(0.50),
        "P75": pct(0.75),
        "P90": pct(0.90),
        "Max": plays[-1],
    }


def find_suspicious_videos(videos: List[dict]) -> List[dict]:
    """Flag videos matching heuristics: livestream replay, too short, too long."""
    out = []
    for v in videos:
        if LIVESTREAM_RE.search(v["title"]):
            out.append({"bv": v["bv"], "reason": "title_livestream", "title": v["title"]})
        if v["duration"] < 60:
            out.append({"bv": v["bv"], "reason": "duration_lt_60s", "title": v["title"]})
        if v["duration"] > 7200:
            out.append({"bv": v["bv"], "reason": "duration_gt_2h", "title": v["title"]})
    return out


def _fmt_duration(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _trunc_title(t: str, n: int = 40) -> str:
    return t if len(t) <= n else t[:n] + "..."


def build_probe_summary(channel: dict, videos: List[dict]) -> str:
    lines: List[str] = []
    lines.append(f"# Probe Summary — {channel['name']}\n")
    lines.append("## Channel")
    lines.append(f"- UID: {channel['uid']}")
    lines.append(f"- 粉丝数: {channel['fans']:,}")
    lines.append(f"- 主页: https://space.bilibili.com/{channel['uid']}")
    if channel.get("sign"):
        lines.append(f"- 签名: {channel['sign']}")
    lines.append(f"- 视频总数: {len(videos)}")
    lines.append(f"- 采集时间: {datetime.now().isoformat(timespec='seconds')}\n")

    # Duration buckets
    lines.append("## 时长分布")
    lines.append("| 桶 | 条数 |")
    lines.append("|---|---|")
    for name, count in format_duration_buckets(videos).items():
        flag = ""
        if name == ">60min" and count > 0:
            flag = "  ← 可能是直播回放, 建议 max_duration:60"
        lines.append(f"| {name} | {count} |{flag}")
    lines.append("")

    # Year distribution
    lines.append("## 发布年份分布")
    lines.append("| 年 | 条数 |")
    lines.append("|---|---|")
    for y, count in format_year_distribution(videos).items():
        lines.append(f"| {y} | {count} |")
    lines.append("")

    # Percentiles
    lines.append("## 播放量分布 (分位)")
    for k, v in format_view_percentiles(videos).items():
        lines.append(f"- {k}: {v:,}")
    lines.append("")

    # Top 10 by views
    top_views = sorted(videos, key=lambda x: x["views"], reverse=True)[:10]
    lines.append("## 最热 10 条 (by views)")
    lines.append("| BV | 播放量 | 时长 | 标题 |")
    lines.append("|---|---|---|---|")
    for v in top_views:
        lines.append(f"| {v['bv']} | {v['views']:,} | {_fmt_duration(v['duration'])} | {_trunc_title(v['title'])} |")
    lines.append("")

    # Latest 10
    latest = sorted(videos, key=lambda x: x["date"], reverse=True)[:10]
    lines.append("## 最新 10 条")
    lines.append("| BV | 日期 | 播放量 | 时长 | 标题 |")
    lines.append("|---|---|---|---|---|")
    for v in latest:
        date_fmt = f"{v['date'][:4]}-{v['date'][4:6]}-{v['date'][6:8]}"
        lines.append(f"| {v['bv']} | {date_fmt} | {v['views']:,} | {_fmt_duration(v['duration'])} | {_trunc_title(v['title'])} |")
    lines.append("")

    # Suspicious
    suspicious = find_suspicious_videos(videos)
    if suspicious:
        lines.append("## 可疑条目 (建议人工复核)")
        by_reason: Dict[str, List[str]] = {}
        for s in suspicious:
            by_reason.setdefault(s["reason"], []).append(s["bv"])
        reason_labels = {
            "title_livestream": "标题含直播回放",
            "duration_lt_60s": "时长 < 60s",
            "duration_gt_2h": "时长 > 2h",
        }
        for reason, bvs in by_reason.items():
            lines.append(f"- {len(bvs)} 条 {reason_labels.get(reason, reason)} → {', '.join(bvs)}")
        lines.append("")

    lines.append("## 完整列表")
    lines.append(f"→ `video_list.tsv` ({len(videos)} 行, BV/标题/时长/日期/播放量)")
    return "\n".join(lines) + "\n"


def write_video_list_tsv(path: Path, videos: List[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["BV", "title", "duration", "date", "views"])
        for v in videos:
            w.writerow([v["bv"], v["title"], v["duration"], v["date"], v["views"]])


def write_meta_md(path: Path, channel: dict, count: int) -> None:
    lines = [
        f"# {channel['name']}",
        f"- UID: {channel['uid']}",
        f"- 粉丝数: {channel['fans']:,}",
        f"- 主页: https://space.bilibili.com/{channel['uid']}",
    ]
    if channel.get("sign"):
        lines.append(f"- 签名: {channel['sign']}")
    lines.append(f"- 视频总数: {count}")
    lines.append(f"- Probed: {datetime.now().isoformat(timespec='seconds')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 1: probe a Bilibili UP主 channel")
    ap.add_argument("url", help="B站 space URL, e.g. https://space.bilibili.com/123456")
    ap.add_argument("slug", help="Creator slug (short latin identifier)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--refresh", action="store_true", help="Overwrite existing video_list.tsv")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    log = setup_logging(args.verbose)
    require_cookies()

    cdir = creator_dir(args.out, args.slug)
    video_list_path = cdir / "video_list.tsv"

    if video_list_path.exists() and not args.refresh:
        log.error(
            f"{video_list_path} already exists. "
            f"Use --refresh to overwrite, or delete manually."
        )
        return 2

    uid = parse_uid_from_url(args.url)
    log.info(f"Probing UID {uid} → {cdir}")

    img_key, sub_key = fetch_wbi_keys()
    log.info("wbi keys fetched")

    channel = fetch_channel_info(uid)
    log.info(f"Channel: {channel['name']} ({channel['fans']:,} fans)")

    videos = fetch_video_list(uid, img_key, sub_key)
    log.info(f"Fetched {len(videos)} videos")

    write_video_list_tsv(video_list_path, videos)
    write_meta_md(cdir / "META.md", channel, len(videos))
    summary = build_probe_summary(channel, videos)
    (cdir / "probe_summary.md").write_text(summary, encoding="utf-8")

    log.info(f"Wrote {video_list_path}, META.md, probe_summary.md")
    print(summary)  # stdout for Mason to read
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run formatter tests**

```bash
python -m pytest tests/test_probe_formatter.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/probe_channel.py tests/test_probe_formatter.py
git commit -m "feat(probe): probe_channel.py entry + summary formatter"
```

---

## Task 8: Error Classifier for yt-dlp

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/error_classifier.py`
- Create: `~/.claude/skills/bilibili-creator-dive/tests/test_error_classifier.py`

Classifies yt-dlp stderr output into either `("single_item", <category>, <message>)` (log + continue) or `("infrastructure", <category>, <message>)` (stop immediately).

- [ ] **Step 1: Write failing tests**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_error_classifier.py`:

```python
"""Tests for yt-dlp error classifier."""
from scripts.error_classifier import Classification, classify_ytdlp_error


def test_classify_members_only():
    stderr = "ERROR: [BiliBili] BV1xxx: This video is members-only, requires subscription"
    c = classify_ytdlp_error(stderr)
    assert c.scope == "single_item"
    assert c.category == "members_only"


def test_classify_404():
    stderr = "ERROR: [BiliBili] BV1xxx: Unable to download webpage: HTTP Error 404: Not Found"
    c = classify_ytdlp_error(stderr)
    assert c.scope == "single_item"
    assert c.category == "not_found"


def test_classify_401_is_infrastructure():
    stderr = "ERROR: Unable to download: HTTP Error 401: Unauthorized"
    c = classify_ytdlp_error(stderr)
    assert c.scope == "infrastructure"
    assert c.category == "cookies_expired"


def test_classify_412_is_infrastructure():
    stderr = "ERROR: Unable to download: HTTP Error 412: Precondition Failed"
    c = classify_ytdlp_error(stderr)
    assert c.scope == "infrastructure"
    assert c.category == "rate_limited"


def test_classify_geo_restricted():
    stderr = "ERROR: [BiliBili] BV1xxx: The uploader has not made this video available in your country."
    c = classify_ytdlp_error(stderr)
    assert c.scope == "single_item"
    assert c.category == "geo_restricted"


def test_classify_dns_failure_is_infrastructure():
    stderr = "ERROR: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>"
    c = classify_ytdlp_error(stderr)
    assert c.scope == "infrastructure"
    assert c.category == "network_unreachable"


def test_classify_unknown_defaults_to_single_item():
    # Conservative default: don't halt the whole batch for unfamiliar errors
    stderr = "ERROR: some weird error that's never been seen before"
    c = classify_ytdlp_error(stderr)
    assert c.scope == "single_item"
    assert c.category == "unknown"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_error_classifier.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement error_classifier.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/error_classifier.py`:

```python
"""Classify yt-dlp stderr output into actionable categories.

Single-item errors → log and continue next video.
Infrastructure errors → stop the whole batch immediately.
"""
import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class Classification:
    scope: Literal["single_item", "infrastructure"]
    category: str
    message: str


# Order matters: check infrastructure patterns first (more specific)
_INFRASTRUCTURE_PATTERNS = [
    (re.compile(r"HTTP Error 401"), "cookies_expired",
     "Cookies expired or invalid. Refresh ~/.cookies/bilibili.txt and retry."),
    (re.compile(r"HTTP Error 412"), "rate_limited",
     "Rate limited by B站. Wait and retry, or check for abusive parallel calls."),
    (re.compile(r"\[Errno 11001\] getaddrinfo failed"), "network_unreachable",
     "DNS resolution failed. Check network connectivity."),
    (re.compile(r"\[Errno -3\]|network is unreachable", re.I), "network_unreachable",
     "Network unreachable."),
]

_SINGLE_ITEM_PATTERNS = [
    (re.compile(r"members-only|大会员"), "members_only",
     "Video requires membership."),
    (re.compile(r"HTTP Error 404"), "not_found",
     "Video not found (deleted or private)."),
    (re.compile(r"not made this video available in your country", re.I), "geo_restricted",
     "Geo-restricted video."),
    (re.compile(r"video is private", re.I), "private",
     "Video is private."),
]


def classify_ytdlp_error(stderr: str) -> Classification:
    """Classify a yt-dlp stderr output.

    Defaults to single_item + 'unknown' for unrecognized errors (conservative:
    don't halt the batch for unfamiliar messages).
    """
    for pat, cat, msg in _INFRASTRUCTURE_PATTERNS:
        if pat.search(stderr):
            return Classification("infrastructure", cat, msg)
    for pat, cat, msg in _SINGLE_ITEM_PATTERNS:
        if pat.search(stderr):
            return Classification("single_item", cat, msg)
    return Classification("single_item", "unknown", stderr.strip()[:200])
```

- [ ] **Step 4: Run tests to verify all pass**

```bash
python -m pytest tests/test_error_classifier.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/error_classifier.py tests/test_error_classifier.py
git commit -m "feat(errors): yt-dlp error classifier with scope hierarchy"
```

---

## Task 9: download_audio.py

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/download_audio.py`

Loops over BVs in `selected.tsv`, runs yt-dlp per video, applies skip-if-exists, classifies errors, stops on infrastructure errors, logs single-item errors. Direct subprocess integration — smoke-tested in Task 14, not unit-tested (test-to-mock ratio is bad for CLI wrappers).

- [ ] **Step 1: Implement download_audio.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/download_audio.py`:

```python
#!/usr/bin/env python3
"""Phase 3: Download audio for selected videos.

Usage:
    python -m scripts.download_audio <slug> --out <dir>
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

from scripts.common import (
    MIN_VALID_MP3_BYTES,
    YTDLP_RETRIES,
    creator_dir,
    require_cookies,
    setup_logging,
)
from scripts.error_classifier import classify_ytdlp_error


def read_selected_bvs(selected_path: Path) -> list[str]:
    with open(selected_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return [row["BV"] for row in reader]


def should_skip(mp3_path: Path) -> bool:
    return mp3_path.exists() and mp3_path.stat().st_size > MIN_VALID_MP3_BYTES


def run_ytdlp(bv: str, audio_dir: Path, cookies_path: Path) -> tuple[int, str]:
    """Run yt-dlp for one video. Return (returncode, stderr)."""
    cmd = [
        "yt-dlp",
        "--cookies", str(cookies_path),
        "-f", "bestaudio",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "--retries", str(YTDLP_RETRIES),
        "-o", str(audio_dir / "%(id)s.%(ext)s"),
        f"https://www.bilibili.com/video/{bv}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stderr


def append_download_error(log_path: Path, bv: str, category: str, message: str) -> None:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{bv}\t{category}\t{message}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 3: download audio for selected videos")
    ap.add_argument("slug")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    log = setup_logging(args.verbose)
    cookies = require_cookies()
    cdir = creator_dir(args.out, args.slug)

    selected_path = cdir / "selected.tsv"
    if not selected_path.exists():
        log.error(f"{selected_path} not found. Run `select` first.")
        return 2

    bvs = read_selected_bvs(selected_path)
    audio_dir = cdir / "audio"
    audio_dir.mkdir(exist_ok=True)
    error_log = cdir / "download_errors.log"

    total = len(bvs)
    succeeded = 0
    skipped = 0
    failed = 0

    for i, bv in enumerate(bvs, 1):
        mp3_path = audio_dir / f"{bv}.mp3"
        if should_skip(mp3_path):
            log.info(f"[{i}/{total}] SKIP {bv} (already downloaded)")
            skipped += 1
            continue

        log.info(f"[{i}/{total}] downloading {bv}...")
        rc, stderr = run_ytdlp(bv, audio_dir, cookies)
        if rc == 0 and should_skip(mp3_path):
            succeeded += 1
            log.info(f"[{i}/{total}] ✓ {bv}")
            continue

        # Failure — classify and decide
        c = classify_ytdlp_error(stderr)
        append_download_error(error_log, bv, c.category, c.message)
        if c.scope == "infrastructure":
            log.error(f"INFRASTRUCTURE FAILURE ({c.category}): {c.message}")
            log.error(f"Stopping batch. {succeeded} succeeded, {skipped} skipped, {i - succeeded - skipped} incomplete.")
            return 4
        failed += 1
        log.warning(f"[{i}/{total}] ✗ {bv}: {c.category}")

    log.info(f"Done. {succeeded} succeeded, {skipped} skipped, {failed} failed of {total}.")
    if failed:
        log.info(f"See {error_log} for details.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify script syntax parses**

```bash
cd ~/.claude/skills/bilibili-creator-dive
python -c "from scripts import download_audio; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add scripts/download_audio.py
git commit -m "feat(download): Phase 3 entry with skip-if-exists and error classification"
```

---

## Task 10: transcribe.py with Core Tests

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/transcribe.py`
- Create: `~/.claude/skills/bilibili-creator-dive/tests/test_transcribe_core.py`

Core testable pieces: skip-if-exists logic, JSON schema builder, full_text.txt assembly. The actual Whisper call is mocked in tests.

- [ ] **Step 1: Write failing tests**

Create `~/.claude/skills/bilibili-creator-dive/tests/test_transcribe_core.py`:

```python
"""Tests for transcribe.py core logic (Whisper call mocked)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.transcribe import (
    build_transcript_record,
    generate_full_text,
    is_valid_transcript,
)


def _make_segment(start: float, end: float, text: str):
    s = MagicMock()
    s.start = start
    s.end = end
    s.text = text
    return s


def _make_info(language="zh", prob=0.99):
    info = MagicMock()
    info.language = language
    info.language_probability = prob
    return info


def test_is_valid_transcript_returns_false_for_missing(tmp_path):
    assert is_valid_transcript(tmp_path / "missing.json") is False


def test_is_valid_transcript_returns_false_for_corrupt(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text("{ not valid json", encoding="utf-8")
    assert is_valid_transcript(p) is False


def test_is_valid_transcript_returns_true_for_valid(tmp_path):
    p = tmp_path / "good.json"
    p.write_text('{"bv":"BV1xxx","segments":[]}', encoding="utf-8")
    assert is_valid_transcript(p) is True


def test_build_transcript_record_schema():
    segments_raw = [
        _make_segment(0.0, 3.5, " 大家好 "),
        _make_segment(3.5, 7.2, " 今天我们聊 "),
    ]
    info = _make_info()
    meta = {"bv": "BV1xxx", "title": "Hello", "duration": 600, "date": "20250113", "views": 10405}
    record = build_transcript_record(meta, segments_raw, info, elapsed_sec=45.0)

    assert record["bv"] == "BV1xxx"
    assert record["title"] == "Hello"
    assert record["language_detected"] == "zh"
    assert record["language_probability"] == 0.99
    assert record["transcribe_time_sec"] == 45.0
    assert record["transcribe_rtf"] == 0.075  # 45 / 600
    assert record["segment_count"] == 2
    assert record["segments"][0] == {"start": 0.0, "end": 3.5, "text": "大家好"}
    assert record["full_text"] == "大家好\n今天我们聊"


def test_generate_full_text_concatenates_in_selected_order(tmp_path):
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()

    (transcripts_dir / "BV1A1.json").write_text(json.dumps({
        "bv": "BV1A1", "title": "First", "date": "20230101",
        "views": 1000, "duration": 600, "full_text": "first content",
    }), encoding="utf-8")

    (transcripts_dir / "BV1A2.json").write_text(json.dumps({
        "bv": "BV1A2", "title": "Second", "date": "20230201",
        "views": 2000, "duration": 300, "full_text": "second content",
    }), encoding="utf-8")

    selected_order = ["BV1A2", "BV1A1"]  # intentionally reversed
    out_path = tmp_path / "full_text.txt"
    generate_full_text(selected_order, transcripts_dir, out_path)

    content = out_path.read_text(encoding="utf-8")
    assert content.index("BV1A2") < content.index("BV1A1")
    assert "second content" in content
    assert "first content" in content
    assert "==========" in content


def test_generate_full_text_skips_missing_json(tmp_path):
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    # Only one of the two exists
    (transcripts_dir / "BV1A1.json").write_text(json.dumps({
        "bv": "BV1A1", "title": "t", "date": "20230101",
        "views": 1, "duration": 1, "full_text": "x",
    }), encoding="utf-8")

    out_path = tmp_path / "full_text.txt"
    generate_full_text(["BV1A1", "BV1MISSING"], transcripts_dir, out_path)

    content = out_path.read_text(encoding="utf-8")
    assert "BV1A1" in content
    assert "BV1MISSING" not in content
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_transcribe_core.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement transcribe.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/transcribe.py`:

```python
#!/usr/bin/env python3
"""Phase 4: Transcribe audio files with faster-whisper turbo.

Usage:
    python -m scripts.transcribe <slug> --out <dir>

Scans <slug>/audio/*.mp3 and writes <slug>/transcripts/<BV>.json per audio.
Also regenerates <slug>/full_text.txt covering all current transcripts.
"""
import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

from scripts.common import (
    DEFAULT_VAD_SILENCE_MS,
    DEFAULT_WHISPER_BEAM,
    DEFAULT_WHISPER_LANGUAGE,
    DEFAULT_WHISPER_MODEL,
    creator_dir,
    setup_logging,
)

log = logging.getLogger(__name__)


def is_valid_transcript(json_path: Path) -> bool:
    """Return True if the JSON file exists and parses cleanly."""
    if not json_path.exists():
        return False
    try:
        with open(json_path, encoding="utf-8") as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False


def build_transcript_record(
    meta: Dict[str, object],
    segments_raw,
    info,
    elapsed_sec: float,
) -> Dict[str, object]:
    """Build the JSON dict for one transcript.

    meta must contain bv, title, duration, date, views.
    """
    segments = []
    texts: List[str] = []
    for s in segments_raw:
        t = (s.text or "").strip()
        segments.append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": t,
        })
        if t:
            texts.append(t)

    duration = int(meta.get("duration", 0)) or 1
    rtf = round(elapsed_sec / duration, 3)

    return {
        "bv": meta["bv"],
        "title": meta["title"],
        "duration": meta["duration"],
        "date": meta["date"],
        "views": meta["views"],
        "language_detected": info.language,
        "language_probability": round(info.language_probability, 3),
        "transcribe_time_sec": round(elapsed_sec, 1),
        "transcribe_rtf": rtf,
        "segment_count": len(segments),
        "full_text": "\n".join(texts),
        "segments": segments,
    }


def read_selected_meta(selected_path: Path) -> Dict[str, dict]:
    """Return a dict keyed by BV → metadata dict."""
    out: Dict[str, dict] = {}
    with open(selected_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[row["BV"]] = {
                "bv": row["BV"],
                "title": row["title"],
                "duration": int(row["duration"]),
                "date": row["date"],
                "views": int(row["views"]),
            }
    return out


def _fmt_duration_hms(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def generate_full_text(
    bv_order: List[str],
    transcripts_dir: Path,
    out_path: Path,
) -> None:
    """Concatenate all transcripts into one file in the given BV order.

    Missing transcripts are skipped silently (not an error — caller's job to
    know what's missing via errors.log).
    """
    parts: List[str] = []
    for bv in bv_order:
        jp = transcripts_dir / f"{bv}.json"
        if not jp.exists():
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        date = data.get("date", "")
        date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else date
        views = data.get("views", 0)
        duration = data.get("duration", 0)
        title = data.get("title", "")
        parts.append("==========")
        parts.append(f"{bv} | {date_fmt} | {views:,} views | {_fmt_duration_hms(int(duration))}")
        parts.append(title)
        parts.append("==========")
        parts.append(data.get("full_text", ""))
        parts.append("")
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def load_whisper_model():
    """Import and load the Whisper model lazily (import cost is high)."""
    from faster_whisper import WhisperModel
    return WhisperModel(DEFAULT_WHISPER_MODEL, device="auto", compute_type="float32")


def transcribe_one(model, audio_path: Path):
    """Run faster-whisper on one audio file; return (segments_list, info)."""
    segments_raw, info = model.transcribe(
        str(audio_path),
        language=DEFAULT_WHISPER_LANGUAGE,
        beam_size=DEFAULT_WHISPER_BEAM,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=DEFAULT_VAD_SILENCE_MS),
    )
    return list(segments_raw), info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 4: Whisper transcription")
    ap.add_argument("slug")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    local_log = setup_logging(args.verbose)
    cdir = creator_dir(args.out, args.slug)

    audio_dir = cdir / "audio"
    transcripts_dir = cdir / "transcripts"
    transcripts_dir.mkdir(exist_ok=True)
    errors_log = cdir / "transcribe_errors.log"

    mp3_files = sorted(audio_dir.glob("*.mp3"))
    if not mp3_files:
        local_log.error(f"No mp3 files in {audio_dir}. Run `collect` or place audio manually.")
        return 2

    # Metadata: prefer selected.tsv; fall back to bare BV from filename
    selected_path = cdir / "selected.tsv"
    if selected_path.exists():
        meta_by_bv = read_selected_meta(selected_path)
    else:
        meta_by_bv = {}

    # Build transcription work list
    work: list[tuple[str, Path, dict]] = []
    skipped = 0
    for mp3 in mp3_files:
        bv = mp3.stem
        json_path = transcripts_dir / f"{bv}.json"
        if is_valid_transcript(json_path):
            skipped += 1
            local_log.info(f"SKIP {bv} (already transcribed)")
            continue
        meta = meta_by_bv.get(bv, {
            "bv": bv, "title": bv, "duration": 0, "date": "00000000", "views": 0,
        })
        work.append((bv, mp3, meta))

    if not work:
        local_log.info(f"All {skipped} transcripts up to date. Regenerating full_text.txt.")
    else:
        local_log.info(f"Loading Whisper turbo model...")
        model = load_whisper_model()
        local_log.info(f"Model loaded. Transcribing {len(work)} files ({skipped} skipped).")

        failed = 0
        for i, (bv, mp3, meta) in enumerate(work, 1):
            local_log.info(f"[{i}/{len(work)}] {bv}...")
            t0 = time.time()
            try:
                segments, info = transcribe_one(model, mp3)
                elapsed = time.time() - t0
                record = build_transcript_record(meta, segments, info, elapsed)
                (transcripts_dir / f"{bv}.json").write_text(
                    json.dumps(record, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                local_log.info(f"[{i}/{len(work)}] ✓ {bv} ({elapsed:.0f}s, RTF {record['transcribe_rtf']:.3f})")
            except Exception as e:
                failed += 1
                with open(errors_log, "a", encoding="utf-8") as f:
                    f.write(f"{bv}\texception\t{type(e).__name__}: {e}\n")
                local_log.warning(f"[{i}/{len(work)}] ✗ {bv}: {e}")

        local_log.info(f"Transcription done: {len(work) - failed} succeeded, {failed} failed, {skipped} skipped.")

    # Regenerate full_text.txt from current transcripts/ state
    if selected_path.exists():
        with open(selected_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            bv_order = [row["BV"] for row in reader]
    else:
        bv_order = sorted(p.stem for p in transcripts_dir.glob("*.json"))

    full_text_path = cdir / "full_text.txt"
    generate_full_text(bv_order, transcripts_dir, full_text_path)
    local_log.info(f"Wrote {full_text_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run core tests**

```bash
python -m pytest tests/test_transcribe_core.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/transcribe.py tests/test_transcribe_core.py
git commit -m "feat(transcribe): Phase 4 with Whisper turbo + skip-if-exists + full_text generation"
```

---

## Task 11: collect Orchestration Script

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/scripts/collect.py`

collect is a thin orchestrator that chains select → download_audio → transcribe in one call. It is NOT one of the earlier phase scripts — it's a separate entry point that internally imports and calls each phase's `main()`.

- [ ] **Step 1: Implement collect.py**

Create `~/.claude/skills/bilibili-creator-dive/scripts/collect.py`:

```python
#!/usr/bin/env python3
"""Orchestrator: collect = select + download_audio + transcribe.

Usage:
    python -m scripts.collect <slug> --out <dir> --filter "<expr>"
"""
import argparse
import sys
from pathlib import Path

from scripts.common import setup_logging
from scripts.download_audio import main as download_main
from scripts.select import main as select_main
from scripts.transcribe import main as transcribe_main


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Orchestrator: select → download → transcribe")
    ap.add_argument("slug")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--filter", dest="filter_expr", required=True)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    log = setup_logging(args.verbose)

    verbose_flag = ["-v"] if args.verbose else []

    log.info("=== Phase 2: Select ===")
    rc = select_main([args.slug, "--out", str(args.out), "--filter", args.filter_expr] + verbose_flag)
    if rc != 0:
        log.error(f"select failed (rc={rc})")
        return rc

    log.info("=== Phase 3: Download Audio ===")
    rc = download_main([args.slug, "--out", str(args.out)] + verbose_flag)
    if rc != 0:
        log.error(f"download failed (rc={rc})")
        return rc

    log.info("=== Phase 4: Transcribe ===")
    rc = transcribe_main([args.slug, "--out", str(args.out)] + verbose_flag)
    if rc != 0:
        log.error(f"transcribe failed (rc={rc})")
        return rc

    log.info("✓ collect complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
cd ~/.claude/skills/bilibili-creator-dive
python -c "from scripts import collect; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add scripts/collect.py
git commit -m "feat(collect): orchestrator chaining select + download + transcribe"
```

---

## Task 12: SKILL.md (Full Documentation)

**Files:**
- Modify: `~/.claude/skills/bilibili-creator-dive/SKILL.md` (replace stub with full content)

This is the doc Claude reads at runtime. It must teach Claude how to invoke the 4 commands, how to interpret probe summaries, what filter expressions mean, and how to run the `dive` pseudo-command (which is a conversation-level orchestration, not a script).

- [ ] **Step 1: Write full SKILL.md**

Overwrite `~/.claude/skills/bilibili-creator-dive/SKILL.md`:

````markdown
---
name: bilibili-creator-dive
description: >
  Use when analyzing a Bilibili UP主 channel for methodology extraction, track
  recon, or content research. Downloads metadata + audio (not video) + Whisper
  transcripts. Produces raw materials for conversation-driven analysis.
  Triggers: "开采 UP 主", "分析 B 站创作者", "/bilibili-creator-dive",
  "creator deep dive".
---

# /bilibili-creator-dive

Channel-level research pipeline for Bilibili UP主. Output is raw materials (video list + audio + transcripts) for conversation-driven analysis — this skill does NOT produce templated reports.

## What this skill does NOT do

- Clip videos for production → use `video-asset-collect`
- Scrape comments / do track recon → use a separate tool
- Generate analysis reports → Mason drives analysis in conversation after skill completes
- Handle YouTube / 小红书 / 抖音 → this skill is Bilibili-only

## Subcommands

### `probe` — fetch channel metadata

```
python -m scripts.probe_channel <URL> <slug> --out <dir> [--refresh]
```

Runs Phase 1: wbi signing → channel info + full video list → writes `<dir>/<slug>/video_list.tsv`, `META.md`, `probe_summary.md`. Prints summary to stdout.

Use: first step for any new creator.

Errors out if `video_list.tsv` already exists (use `--refresh` to overwrite).

### `select` — apply filter expression

```
python -m scripts.select <slug> --out <dir> --filter "<expr>"
```

Runs Phase 2: reads `video_list.tsv`, applies filter, writes `selected.tsv` and `filter_used.yaml`, prints preview to stdout.

Prerequisite: `video_list.tsv` exists.

### `download_audio` — pull audio only

```
python -m scripts.download_audio <slug> --out <dir>
```

Runs Phase 3: yt-dlp with cookies, audio-only streams, skip-if-exists.

Prerequisite: `selected.tsv` exists.

### `transcribe` — Whisper turbo

```
python -m scripts.transcribe <slug> --out <dir>
```

Runs Phase 4: faster-whisper turbo on all mp3 in `<slug>/audio/`, writes per-video JSON to `transcripts/`, regenerates `full_text.txt`.

Prerequisite: at least one `.mp3` in `<slug>/audio/`. Does NOT need URL, video_list.tsv, selected.tsv, or filter — this is the escape hatch for re-transcribing or transcribing audio from other sources.

### `collect` — orchestrator for phases 2-4

```
python -m scripts.collect <slug> --out <dir> --filter "<expr>"
```

Runs select → download_audio → transcribe as one call. Use after probe when Mason has decided the filter.

### `dive` (conversation-level, not a script)

A convenience flow Claude runs in a conversation:

1. Run `probe <URL> <slug>` and show the summary.
2. Ask Mason for a filter expression.
3. Run `collect <slug> --filter "..."`.
4. Show final output directory.

There is no `dive.py` script — `dive` is this conversation sequence. Claude should use it when Mason says "开采一个新的 UP 主" with a URL and no further instructions.

## Filter Expression Syntax

Space-separated `key:value` tokens. AND semantics.

### Conditions (exclusion filters, applied first)

| Token | Meaning |
|---|---|
| `min_views:<N>` | Video's play count ≥ N |
| `min_duration:<N>` | Duration ≥ N minutes |
| `max_duration:<N>` | Duration ≤ N minutes |
| `date:<YYYY-MM>..<YYYY-MM>` | Publish date in range (inclusive, month granularity) |
| `date:<YYYY-MM>..` | From month onwards (open end) |
| `date:..<YYYY-MM>` | Up to month (open start) |
| `title_include:/regex/` | Title matches regex (case-insensitive) |
| `title_exclude:/regex/` | Title does NOT match regex |

### Selector (optional, applied after conditions)

| Token | Meaning |
|---|---|
| `top:<N> by:views` | Top N by play count from videos surviving conditions |
| `top:<N> by:date` | Most recent N |
| `latest:<N>` | Alias for `top:<N> by:date` |
| `bv:[BV1,BV2,...]` | Manual list; **overrides all other tokens** |

If no selector given, result = all videos surviving conditions.

### Examples

```
top:30 by:views min_duration:5 max_duration:60    # new creator quick scan
latest:20 min_duration:5                            # recent half-year
title_include:/小红书/ date:2022-01..              # one theme's evolution
min_duration:5 max_duration:60 title_exclude:/直播回放/  # exclude livestream replays
bv:[BV1RZd6YDECz,BV1wsL8zkE7b]                     # manually curated
```

## Output Directory

```
<dir>/<slug>/
├── META.md                     # Channel metadata
├── video_list.tsv              # Full channel video list
├── probe_summary.md            # Human-readable probe report
├── selected.tsv                # Filter result
├── filter_used.yaml            # Reproducibility record
├── audio/*.mp3                 # Audio-only downloads
├── transcripts/*.json          # Per-video Whisper output
├── full_text.txt               # Concatenated transcripts for conversation analysis
├── download_errors.log         # Only if failures occurred
└── transcribe_errors.log       # Only if failures occurred
```

## Runtime requirements

- Python 3.10+
- `pip install faster-whisper onnxruntime-directml yt-dlp requests pyyaml pytest`
- `~/.cookies/bilibili.txt` (netscape format cookies, exported from logged-in browser)

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "Mason probably wants top 30, I'll skip asking" | Never pick the filter for Mason. Run `probe`, show summary, wait for filter expression. |
| "Video download is fine, audio later" | Audio-only is 10x less bandwidth. Always `-f bestaudio`. |
| "Parallel downloads for speed" | B站 rate-limits aggressively. Serial only. |
| "Whisper `base` is enough" | Turbo is noticeably better. Use `turbo`. |
| "I'll auto-detect language" | Always `language=zh` for this skill. Misdetection on background music wastes runtime. |
| "Skip cookies, it probably works" | Without cookies, B站 returns low-bitrate audio. Always use cookies. |
| "Failed clips: retry all" | `collect` is idempotent (skip-if-exists). Just rerun the same command. |
| "No need for filter_used.yaml" | Without it, you can't reproduce which filter produced this dataset 3 months later. |
| "I'll write analysis report automatically" | No templated reports. Mason drives analysis in conversation. |
````

- [ ] **Step 2: Verify the file is non-empty and parseable**

```bash
cat ~/.claude/skills/bilibili-creator-dive/SKILL.md | head -20
```

Expected: frontmatter + "# /bilibili-creator-dive" visible.

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): full SKILL.md with commands, filter syntax, anti-rationalization"
```

---

## Task 13: wbi Signing Reference Doc

**Files:**
- Create: `~/.claude/skills/bilibili-creator-dive/references/bilibili-wbi-signing.md`

A brief reference document capturing the wbi algorithm and key URLs, so future debugging doesn't require re-discovering it.

- [ ] **Step 1: Write reference doc**

Create `~/.claude/skills/bilibili-creator-dive/references/bilibili-wbi-signing.md`:

```markdown
# Bilibili wbi Signature Algorithm

## Why

Bilibili's space/video APIs (e.g. `/x/space/wbi/arc/search`) require a `w_rid` query parameter. Without it, requests return `code=-352` (risk control). The algorithm is called "wbi" (web bot identification).

## Algorithm

### 1. Fetch wbi keys

```
GET https://api.bilibili.com/x/web-interface/nav
```

Response contains:

```json
{
  "code": 0,
  "data": {
    "wbi_img": {
      "img_url": "https://i0.hdslb.com/bfs/wbi/<IMG_KEY>.png",
      "sub_url": "https://i0.hdslb.com/bfs/wbi/<SUB_KEY>.png"
    }
  }
}
```

`IMG_KEY` and `SUB_KEY` are 32-char hex strings — extract by taking the URL basename and stripping `.png`.

### 2. Compute mixin_key

Permute `IMG_KEY + SUB_KEY` using a fixed 64-index table and take the first 32 characters.

The permutation table (from `bilibili-api-python` reference implementation):

```python
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

def get_mixin_key(img_key, sub_key):
    raw = img_key + sub_key
    return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]
```

### 3. Sign request

For any API call that requires wbi:

1. Add `wts = int(time.time())` to the params dict.
2. Sort params alphabetically by key.
3. URL-encode values (standard `urlencode`).
4. Append `mixin_key` to the URL-encoded query string.
5. Compute `w_rid = md5(query_string + mixin_key).hexdigest()`.
6. Add `w_rid` to the params (do NOT re-sort — just add as a regular field).

### 4. Send request

Send with both `wts` and `w_rid` in the query string, plus normal headers (User-Agent + Referer).

## Cache lifetime

wbi keys are rotated daily around midnight UTC+8. If a signed request fails with `code=-352`, the first thing to try is re-fetching nav.

## Alternative

`bilibili-api-python` library handles wbi automatically. This skill re-implements the algorithm directly (one file) to avoid the dependency.

## References

- Mirror of the algorithm: https://github.com/SocialSisterYi/bilibili-API-collect (community-maintained)
- Python reference: https://github.com/Nemo2011/bilibili-api
```

- [ ] **Step 2: Commit**

```bash
git add references/bilibili-wbi-signing.md
git commit -m "docs(refs): wbi signing algorithm reference"
```

---

## Task 14: Manual Smoke Test

**Files:**
- None (manual test on real B站 channel)

The unit tests cover pure logic and mocked I/O. This task verifies the skill works end-to-end against real Bilibili. Pick a small channel (≤ 10 videos) to keep total time under 10 minutes.

- [ ] **Step 1: Verify Python dependencies installed**

```bash
python -c "import faster_whisper, yt_dlp, requests, yaml; print('ok')"
```

Expected: `ok`. If not, run:

```bash
pip install faster-whisper onnxruntime-directml yt-dlp requests pyyaml pytest
```

- [ ] **Step 2: Verify cookies file**

```bash
ls -l ~/.cookies/bilibili.txt
```

Expected: file exists. If missing, Mason should export cookies from browser first.

- [ ] **Step 3: Pick a small test channel**

Ask Mason: "Which Bilibili UP主 should we smoke-test on? Needs to be small (≤ 10 videos) to keep the test fast. One with mostly short videos is ideal."

Record the URL and pick a slug (e.g. `smoketest`).

- [ ] **Step 4: Run probe**

```bash
cd ~/.claude/skills/bilibili-creator-dive
TEST_OUT=/tmp/bilibili-smoke-test
rm -rf $TEST_OUT
python -m scripts.probe_channel <CHANNEL_URL> smoketest --out $TEST_OUT -v
```

Expected:
- `$TEST_OUT/smoketest/video_list.tsv` exists, non-empty, has header + video rows
- `$TEST_OUT/smoketest/META.md` exists with channel name and fan count
- `$TEST_OUT/smoketest/probe_summary.md` exists and prints to stdout

Verify:
```bash
head $TEST_OUT/smoketest/video_list.tsv
wc -l $TEST_OUT/smoketest/video_list.tsv
```

- [ ] **Step 5: Run collect with a narrow filter**

Use a filter that picks just 2-3 videos to keep this fast:

```bash
python -m scripts.collect smoketest --out $TEST_OUT --filter "latest:2" -v
```

Expected:
- `$TEST_OUT/smoketest/selected.tsv` has 2 rows + header
- `$TEST_OUT/smoketest/filter_used.yaml` has `filter_expression: "latest:2"`
- `$TEST_OUT/smoketest/audio/*.mp3` contains 2 mp3s each > 10KB
- `$TEST_OUT/smoketest/transcripts/*.json` contains 2 valid JSON files
- `$TEST_OUT/smoketest/full_text.txt` exists and contains Chinese text

Verify:
```bash
ls -la $TEST_OUT/smoketest/audio/
ls -la $TEST_OUT/smoketest/transcripts/
head -30 $TEST_OUT/smoketest/full_text.txt
cat $TEST_OUT/smoketest/filter_used.yaml
```

- [ ] **Step 6: Test idempotency — rerun and verify skip**

```bash
python -m scripts.collect smoketest --out $TEST_OUT --filter "latest:2" -v 2>&1 | grep -i skip
```

Expected: log lines showing all 2 audio and all 2 transcripts skipped. No new files created.

- [ ] **Step 7: Test transcribe-only command**

Delete transcripts and rerun just transcribe (simulating "re-run Whisper with different model" scenario):

```bash
rm -rf $TEST_OUT/smoketest/transcripts $TEST_OUT/smoketest/full_text.txt
python -m scripts.transcribe smoketest --out $TEST_OUT -v
```

Expected: 2 new JSON files + regenerated full_text.txt. No URL needed, no filter needed.

- [ ] **Step 8: Test probe --refresh protection**

```bash
python -m scripts.probe_channel <CHANNEL_URL> smoketest --out $TEST_OUT
```

Expected: exit code 2 with error "video_list.tsv already exists".

```bash
python -m scripts.probe_channel <CHANNEL_URL> smoketest --out $TEST_OUT --refresh
```

Expected: success, video_list.tsv overwritten.

- [ ] **Step 9: Run full test suite one more time**

```bash
cd ~/.claude/skills/bilibili-creator-dive
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 10: Clean up smoke-test artifacts (optional)**

```bash
rm -rf /tmp/bilibili-smoke-test
```

- [ ] **Step 11: Final commit marking skill as ready**

```bash
git log --oneline | head -20  # should show all 14 task commits
```

If this skill lives in a mason-hub-tracked location (not its own git repo), add the final marker commit at the project level:

```bash
cd ~/projects/mason-hub
git add docs/superpowers/plans/2026-04-07-bilibili-creator-dive.md
git commit -m "docs(plan): bilibili-creator-dive implementation plan complete"
```

---

## Execution Notes

- Tasks are sequential: 1 → 14. Each task commits at least once.
- Tasks 2-4 (filter_parser + select) are the highest-value TDD targets because filter logic is error-prone.
- Tasks 5-7 (wbi + bili_api + probe) are the network boundary; tests use mocks exclusively.
- Task 8 (error classifier) is small but important — wrong classification causes batch failures.
- Tasks 9-10 (download + transcribe) are thin subprocess/library wrappers with targeted unit tests on core logic.
- Task 14 (manual smoke test) is the only thing that touches real B站. Do it last.
- If the skill lives in its own git repo: `cd ~/.claude/skills/bilibili-creator-dive && git init` before Task 1 Step 6.
- If `~/.claude/skills/` is tracked by a different repo (e.g. a dotfiles repo), commit there instead.
