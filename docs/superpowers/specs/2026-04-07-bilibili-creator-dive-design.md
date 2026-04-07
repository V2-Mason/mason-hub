# bilibili-creator-dive — Design Spec

**Date:** 2026-04-07
**Status:** Draft, awaiting user review
**Author:** Claude (brainstorming with Mason)
**Target location:** `~/.claude/skills/bilibili-creator-dive/` (user-level skill)

---

## 1. Background and Motivation

### 1.1 Origin
On 2026-04-06 (Session 19), Mason did a deep analysis of Bilibili UP主 "网红小狗勾" to study MCN industry insights. The workflow was executed ad-hoc across two sessions:

- **S15 (2026-04-05 evening):** fetched 93 videos' metadata via Bilibili wbi API, downloaded audio for all 93 (~1.5GB)
- **S19 (2026-04-06 EOD):** hand-picked 31 representative videos, transcribed with faster-whisper turbo (onnxruntime-directml), produced 5 analysis reports

The pipeline worked but was not reusable:
- Collection script was ad-hoc (no wbi signing code retained as a tool)
- `batch_transcribe.py` had the 31 BV numbers hard-coded
- Filter logic (grouping videos by theme A-F) was manual, done by Claude without Mason's input
- No way to "only re-transcribe existing audio" without editing code

### 1.2 Need
Mason wants to analyze more Bilibili creators systematically. The goal is **methodology extraction / track recon / audience research** — understanding a creator's content at a channel level, not clipping specific seconds for video production.

### 1.3 Scope boundaries
This skill does NOT:
- Clip video for production (→ use existing `video-asset-collect`)
- Collect marketplace data (→ use existing `research-collect`)
- Generate analysis reports (→ Mason drives analysis in conversation, per the decision below)

---

## 2. Key Design Decisions (from brainstorming)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Channel-level** pipeline, not signal-based clip extraction | Different job from video-asset-collect — want to understand the creator, not reuse clips |
| D2 | **Bilibili only** (for now) | UP主 is B站 terminology; YAGNI on YouTube/xhs/抖音 until proven |
| D3 | **Probe-first flow** — skill probes channel, Mason decides quantity | Xiaogougou incident: Claude picked 31/93 without Mason — violated `/multi-filter` rule |
| D4 | **Raw materials only, no templated reports** | Analysis angles vary per creator; templates cause "false precision"; Mason drives analysis in conversation |
| D5 | **Phase-addressable** (4 subcommands: probe/collect/transcribe/dive) | Real use cases are asynchronous across sessions; supports "only transcribe existing audio" without friction |
| D6 | **Multi-dimensional filter** (top/latest/date/min_views/min/max duration/title regex/bv list, AND-combined) | Captures the real selection logic Mason used manually on xiaogougou |
| D7 | **Audio-only download** (not video) | Only transcription is needed; video is 10x bandwidth waste |
| D8 | **Idempotent skip-if-exists per file** | Natural resume support; no separate resume logic |

---

## 3. Skill Identity

| Field | Value |
|---|---|
| Name | `bilibili-creator-dive` |
| Location | `~/.claude/skills/bilibili-creator-dive/` |
| Type | Rigid (hard preconditions per command) |
| Triggers | `"开采 UP 主"`, `"分析 B 站创作者"`, `"/bilibili-creator-dive"`, `"creator deep dive"` |
| Description (frontmatter) | Use when analyzing a Bilibili UP主 channel for methodology extraction, track recon, or content research. Downloads metadata + audio (not video) + Whisper transcripts. Produces raw materials for conversation-driven analysis. Triggers: "开采 UP 主", "creator deep dive". |

---

## 4. Skill Directory Layout

```
~/.claude/skills/bilibili-creator-dive/
├── SKILL.md                     # Main doc: 4 commands, filter语法, phase contracts
├── scripts/
│   ├── probe_channel.py         # Phase 1: wbi sign + fetch metadata → video_list.tsv
│   ├── select.py                # Phase 2: apply filter expr → selected.tsv
│   ├── download_audio.py        # Phase 3: yt-dlp + cookies → audio/*.mp3
│   └── transcribe.py            # Phase 4: faster-whisper turbo → transcripts/*.json
├── presets/
│   └── .gitkeep                 # Future filter presets (e.g. "top-representative-works.yaml")
└── references/
    └── bilibili-wbi-signing.md  # wbi signing algo (for future debugging)
```

**Rule:** do NOT copy code from `accounts/growth-memo/content/test-001/assets/reference/xiaogougou/batch_transcribe.py` — that script has hard-coded BVs. Re-extract the working logic into proper parameterized scripts.

---

## 5. Per-Creator Output Layout

Every creator gets its own directory under Mason-specified `--out`:

```
<output_dir>/<creator_slug>/
├── META.md                      # Channel info (name, UID, fans, URL, probe date)
├── video_list.tsv               # Full channel metadata (BV|title|duration|date|views)
├── probe_summary.md             # Human-readable stats for filter decision
├── selected.tsv                 # Filter result (subset of video_list.tsv)
├── filter_used.yaml             # Reproducibility record of applied filter
├── audio/
│   ├── BV1xxx.mp3               # One mp3 per selected video
│   └── ...
├── transcripts/
│   ├── BV1xxx.json              # faster-whisper output with timestamps
│   └── ...
├── full_text.txt                # All transcripts concatenated (for conversation analysis)
├── download_errors.log          # Only if failures occurred
└── transcribe_errors.log        # Only if failures occurred
```

**Rules:**
- `<creator_slug>` is Mason-supplied (short latin slug), not auto-generated
- `<output_dir>` is a CLI parameter, not hard-coded
- `META.md` is mechanical metadata only; no analysis or interpretation
- File names are deterministic → basis for skip-if-exists idempotency

---

## 6. Four Subcommands

### 6.1 Overview

```
probe <URL> <slug> --out <dir>
    Prerequisite: none (fails if video_list.tsv already exists, unless --refresh)
    Runs: Phase 1
    Produces: video_list.tsv + probe_summary.md + META.md
    Terminates: after Mason sees summary, before filter decision

collect <slug> --out <dir> --filter "<expr>"
    Prerequisite: video_list.tsv exists AND --filter provided AND filter yields ≥ 1 video
    Runs: Phase 2 → 3 → 4
    Produces: selected.tsv + filter_used.yaml + audio/ + transcripts/ + full_text.txt
    Use: Mason already saw probe summary, decided filter, now executes
    Gate: NONE — prints filter preview for audit but does not pause. Issuing `collect`
          is the commit signal. If preview surprises Mason, abort with Ctrl+C and rerun.
    Edge case: filter expression that matches 0 videos → error out, do not create empty dirs

transcribe <slug> --out <dir>
    Prerequisite: audio/ directory contains at least one .mp3
    Runs: Phase 4 only
    Produces: transcripts/*.json + full_text.txt
    Use: "I have audio, just re-transcribe" (e.g. different Whisper model, resume after crash)
    Notes: Does NOT need URL, video_list.tsv, or filter

dive <URL> <slug> --out <dir>
    Prerequisite: none (new creator first-time collection)
    Runs: probe → [conversation waits for filter] → collect
    Produces: all of the above
    Use: one-shot convenience for new creators; NOT required if Mason prefers separate steps
```

### 6.2 Phase-to-command mapping

| Phase | In which command(s) |
|---|---|
| Phase 1: PROBE | `probe`, `dive` |
| Phase 2: SELECT | `collect`, `dive` |
| Phase 3: DOWNLOAD AUDIO | `collect`, `dive` |
| Phase 4: TRANSCRIBE | `collect`, `transcribe`, `dive` |

### 6.3 Idempotency rules (all commands share these)

| File check | Behavior |
|---|---|
| `audio/{BV}.mp3` exists and > 10KB | Phase 3 skips that BV |
| `transcripts/{BV}.json` exists and parses as valid JSON | Phase 4 skips that BV |
| `video_list.tsv` exists | `probe` command errors with "already probed, use --refresh to force" |
| `selected.tsv` exists | `collect` regenerates it (filter may have changed) |

### 6.4 Error handling policy

| Error type | Behavior |
|---|---|
| Single video download fails (404, members-only, geo-block) | Log to `download_errors.log`, continue next video |
| Single video transcribe fails (audio corrupt) | Log to `transcribe_errors.log`, continue next |
| Cookies expired (401 from B站) | **STOP immediately**, error out, ask Mason to refresh cookies |
| Model load fails (faster-whisper init error) | STOP immediately, error out |
| wbi signing fails (nav API error) | Retry 3 times, then STOP |
| Network timeout during metadata fetch | Retry 3 times, then STOP |

Rule of thumb: **single-item failures continue, infrastructure failures stop.**

### 6.5 Common scenarios

| Scenario | Command |
|---|---|
| First-time open a new creator | `dive <URL> <slug>` |
| Creator posted new videos, refresh metadata | `probe <URL> <slug> --refresh` then `collect <slug> --filter ...` |
| Already probed, try a different filter | `collect <slug> --filter "latest:20 min_views:5000"` |
| Re-run Whisper with different model | `rm -rf <dir>/<slug>/transcripts/` then `transcribe <slug>` |
| Some downloads failed, retry | Re-run same `collect` command (idempotent skip handles the rest) |
| Have mp3s from somewhere else, want to transcribe | Manually place in `<slug>/audio/`, then `transcribe <slug>` |

---

## 7. Phase 1: Probe

### 7.1 Inputs
- Bilibili space URL (format: `https://space.bilibili.com/<UID>` or with query string)
- `creator_slug` (short latin identifier)
- `--out` directory

### 7.2 Implementation
- Parse UID from URL with regex `/space\.bilibili\.com/(\d+)`
- Fetch `https://api.bilibili.com/x/web-interface/nav` to get wbi keys (img_url, sub_url)
- Compute wbi signature per Bilibili's algorithm (reference: `references/bilibili-wbi-signing.md`)
- Fetch `https://api.bilibili.com/x/space/wbi/arc/search?mid=<UID>&ps=30&pn=<page>&order=pubdate` with signature
- Loop pages until empty response
- Fetch `https://api.bilibili.com/x/space/acc/info?mid=<UID>` for channel metadata (name, fans, sign)
- Cookies from `~/.cookies/bilibili.txt` (netscape format, shared with yt-dlp)

### 7.3 video_list.tsv format
Tab-separated, one video per row, header included:
```
BV	title	duration	date	views
BV1Xp9LBcEMV	如何从零开始自学成为博主...	972	20260401	3258
```
- `duration` in seconds
- `date` in `YYYYMMDD` format

### 7.4 META.md format
```markdown
# <channel name>
- UID: <UID>
- 粉丝数: <fans formatted>
- 主页: <URL>
- 签名: <sign>
- 视频总数: <count>
- Probed: 2026-04-07 14:32
```

### 7.5 probe_summary.md format
See section 8 below.

---

## 8. probe_summary.md Structure

This is the human-readable one-pager Mason reads to decide the filter.

```markdown
# Probe Summary — <creator name>

## Channel
- UID: <UID>
- 粉丝数: <formatted>
- 主页: <URL>
- 视频总数: <N>
- 采集时间: <ISO date>

## 时长分布
| 桶 | 条数 |
|---|---|
| <5min    | <n> |
| 5-15min  | <n> |
| 15-30min | <n> |
| 30-60min | <n> |
| >60min   | <n> |  ← flag if non-zero: "可能是直播回放, 建议 max_duration:60"

## 发布年份分布
| 年 | 条数 |
| <year> | <n> |
(compact table, only non-zero years)

## 播放量分布 (分位)
- P25: <n>
- P50: <n>
- P75: <n>
- P90: <n>
- Max: <n>

## 最热 10 条 (by views)
| BV | 播放量 | 时长 | 标题 |
(10 rows, title truncated to ~40 chars)

## 最新 10 条
| BV | 日期 | 播放量 | 时长 | 标题 |
(10 rows)

## 可疑条目 (建议人工复核)
- <N> 条标题含 "直播回放" → <BVs>
- <N> 条时长 < 60s → <BVs>
- <N> 条时长 > 7200s (2h) → <BVs>
(skip section if no suspicious items)

## 完整列表
→ `video_list.tsv` (<total> 行, BV/标题/时长/日期/播放量)
```

**Design principles:**
- One-screen scannable; full data in `video_list.tsv`
- Percentile distribution (not mean) because view counts are long-tailed
- Automatic flagging of suspicious items without deciding for Mason

---

## 9. Phase 2: Select — Filter Syntax

### 9.1 Filter expression grammar

Space-separated key:value tokens, AND semantics.

```
<filter_expr> ::= <token> (' ' <token>)*
<token> ::= <condition> | <selector>

<condition>:
  min_views:<N>
  min_duration:<N>         (minutes)
  max_duration:<N>         (minutes)
  date:<YYYY-MM>..<YYYY-MM>  (inclusive both ends, month granularity)
  date:<YYYY-MM>..            (open-ended: from date onwards)
  date:..<YYYY-MM>            (open-ended: up to date)
  title_include:/<regex>/  (case-insensitive)
  title_exclude:/<regex>/  (case-insensitive)

<selector> (optional, at most one):
  top:<N> by:<field>       (field = views | date)
  latest:<N>               (= top:<N> by:date)
  bv:[<BV>,<BV>,...]       (manual list; OVERRIDES all other tokens)
```

If no `<selector>` is given, the result = all videos surviving the `<condition>` filters (no top-N truncation). Example: `min_duration:5 max_duration:60` takes every video in 5-60min range.

### 9.2 Execution order

```
full pool (93)
    ↓
apply <condition> tokens (exclusion filters)
    ↓
<selector> applied to remaining pool (takes top/latest/bv)
    ↓
final selected
```

**Key:** `top:30` runs AFTER exclusion filters. So `top:30 min_duration:5` means "from videos with duration ≥ 5min, take the top 30 by views."

**Special case:** If `bv:[...]` is present, it completely overrides all other tokens — no exclusions applied.

### 9.3 Examples

```
# new creator quick scan
top:30 by:views min_duration:5 max_duration:60

# recent half-year trajectory
latest:20 min_duration:5

# complete evolution of one theme
title_include:/小红书/ date:2022-01..

# exclude livestreams and short tests
min_duration:5 max_duration:60 title_exclude:/直播回放|充电预热/

# manually curated (xiaogougou approach)
bv:[BV1RZd6YDECz,BV1wsL8zkE7b,...]
```

### 9.4 filter_used.yaml (reproducibility record)

Written after `collect` completes Phase 2:

```yaml
filter_expression: "top:30 by:views min_duration:5 max_duration:60"
parsed:
  top: 30
  by: views
  min_duration: 5
  max_duration: 60
applied_at: 2026-04-07T14:45:12
total_pool: 93
after_exclusions: 67
final_selected: 30
video_list_tsv_sha256: <hash>
```

The sha256 of `video_list.tsv` ensures Mason can later verify the filter was applied to the same metadata snapshot.

### 9.5 Filter preview (shown to Mason before download)

After Phase 2, the skill shows:

```
# Filter 结果预览

Expression: top:30 by:views min_duration:5 max_duration:60
Pool: 93 → exclusions → 67 → top:30 → 30 final

## Selected 30 videos
| # | BV | 播放量 | 时长 | 日期 | 标题 |
(30 rows)

## 成本估算
- 总时长: <formatted>
- 预计 Whisper 耗时: <est> (RTF 0.25x on turbo+DirectML)
- 预计磁盘: <est>MB audio + <est>MB transcripts

## 排除的高播放条目 (前 5, 以防误杀)
| BV | 播放量 | 时长 | 被哪条排除 | 标题 |
(5 rows showing highest-viewed videos that were filtered OUT)
```

**Design principle:** show the top 5 excluded videos to catch cases where Mason's filter accidentally removes videos he'd clearly want to keep.

**For `collect` command:** After showing this preview, the command continues automatically to Phase 3 (no interactive gate — Mason already committed when issuing `collect`).

**For `dive` command:** After this preview, pauses for Mason to confirm ("确认开始") or refine filter.

---

## 10. Phase 3: Download Audio

### 10.1 Tool: yt-dlp with cookies

Per-video command:
```bash
yt-dlp \
  --cookies ~/.cookies/bilibili.txt \
  -f "bestaudio" \
  -x --audio-format mp3 \
  --audio-quality 0 \
  --retries 10 \
  -o "<slug_dir>/audio/%(id)s.%(ext)s" \
  "https://www.bilibili.com/video/<BV>"
```

### 10.2 Key parameter rationale

| Parameter | Why |
|---|---|
| `-f bestaudio` | Download audio stream only, not video (saves ~10x bandwidth) |
| `-x --audio-format mp3` | Extract to mp3 for faster-whisper compatibility |
| `--audio-quality 0` | Highest VBR quality (~256kbps) |
| `--retries 10` | yt-dlp's built-in retry; sufficient for transient network issues |
| `--cookies ...` | Without login, B站 returns low-bitrate audio streams only. Cookies unlock normal-quality audio. Also grants access to members-only content if Mason is subscribed. |

### 10.3 Concurrency
**Serial only.** B站 rate-limits aggressively on concurrent requests. Parallel downloads cause 412 errors and account cooldowns. A single-threaded loop is correct.

### 10.4 Idempotency
Before downloading each BV, check:
```python
mp3_path = audio_dir / f"{bv}.mp3"
if mp3_path.exists() and mp3_path.stat().st_size > 10_000:
    log.info(f"SKIP {bv} (already downloaded)")
    continue
```

### 10.5 Error taxonomy

| yt-dlp error | Classification | Action |
|---|---|---|
| `ERROR: [BiliBili] <BV>: Geo restricted` | single-item | log + continue |
| `ERROR: [BiliBili] <BV>: This video is members-only` | single-item | log + continue |
| `HTTP Error 404` | single-item | log + continue |
| `HTTP Error 401` | **infrastructure** | STOP, error "cookies expired, refresh and retry" |
| `HTTP Error 412` | **infrastructure** | STOP, error "rate limited; wait and retry" |
| `URLError: [Errno 11001]` (DNS) | **infrastructure** | STOP, error "network unreachable" |

### 10.6 download_errors.log format
```
BV1xxx  members-only  This video is members-only, requires subscription
BV1yyy  404           Video deleted or private
```
Tab-separated, appendable (collect command re-runs append, not overwrite).

---

## 11. Phase 4: Transcribe

### 11.1 Tool: faster-whisper turbo + onnxruntime-directml

Proven working in session 19 (2026-04-06) for AMD RDNA3 on Windows.

### 11.2 Model loading
```python
from faster_whisper import WhisperModel
model = WhisperModel("turbo", device="auto", compute_type="float32")
```

`device="auto"` causes faster-whisper to pick DirectML backend when `onnxruntime-directml` is installed.

### 11.3 Transcription parameters
```python
segments_raw, info = model.transcribe(
    str(audio_path),
    language="zh",
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
)
```

| Parameter | Value | Rationale |
|---|---|---|
| `language` | `"zh"` | Target UP主 are Chinese; auto-detect wastes time and occasionally misdetects |
| `beam_size` | 5 | Good accuracy/speed tradeoff for turbo model |
| `vad_filter` | True | Skip silent gaps (common in editing cuts) |
| `vad_parameters.min_silence_duration_ms` | 500 | Balances false positives vs missed short pauses |

**Non-Chinese UP主 policy:** For this skill version, language is hard-coded to `zh`. If a future UP主 is English/Japanese, add a `--lang` flag later (YAGNI for now).

### 11.4 Output JSON schema (per video)

File: `transcripts/{BV}.json`

```json
{
  "bv": "BV1xxx",
  "title": "...",
  "duration": 1234,
  "date": "20250113",
  "views": 10405,
  "language_detected": "zh",
  "language_probability": 0.994,
  "transcribe_time_sec": 123.4,
  "transcribe_rtf": 0.1,
  "segment_count": 456,
  "full_text": "<全文拼接, segments 的 text 用换行连接>",
  "segments": [
    {"start": 0.0, "end": 3.5, "text": "大家好..."},
    {"start": 3.5, "end": 7.2, "text": "今天我们聊..."}
  ]
}
```

Metadata fields (bv, title, duration, date, views) are copied from selected.tsv for self-contained analysis.

### 11.5 Idempotency
```python
json_path = transcripts_dir / f"{bv}.json"
if json_path.exists():
    try:
        with open(json_path) as f:
            json.load(f)
        log.info(f"SKIP {bv} (already transcribed)")
        continue
    except json.JSONDecodeError:
        log.warning(f"REDO {bv} (json corrupt)")
```

### 11.6 full_text.txt generation

After all transcriptions complete, regenerate `full_text.txt` from scratch (always a full rebuild from current transcripts/ state):

```
==========
BV1xxx | 2025-01-13 | 10,405 views | 26:05
一口气说完2025年抖音: 从流量赌场到数字社会
==========
<full_text of BV1xxx>

==========
BV1yyy | ...
...
```

Order: same as `selected.tsv` (deterministic).

Purpose: Mason can `Read` this single file in conversation to access all transcripts at once.

### 11.7 transcribe_errors.log format
Same TSV style as download_errors.log.

---

## 12. Runtime Requirements

### 12.1 Python environment
- Python 3.10+
- Packages: `faster-whisper`, `onnxruntime-directml`, `yt-dlp`, `pyyaml`, `requests`
- (No separate venv required — skill scripts assume global install of these)

### 12.2 Files
- `~/.cookies/bilibili.txt` — netscape-format cookies for Bilibili (shared with yt-dlp, existing file from prior work)

### 12.3 Hardware assumptions
- AMD RDNA3 GPU with DirectML support (Mason's current machine)
- faster-whisper turbo runs at ~0.25x RTF (4x realtime)

### 12.4 First-run preflight check
Each script checks its dependencies on startup and prints actionable errors:
```
ERROR: faster-whisper not installed. Run:
  pip install faster-whisper onnxruntime-directml
```

---

## 13. Anti-Rationalization Table

Standard skill-discipline checklist:

| Excuse | Reality |
|---|---|
| "Video download is fine, I'll extract audio later" | Audio-only is 10x less bandwidth; always use `-f bestaudio` |
| "Whisper base is good enough" | Turbo is noticeably better accuracy and fast enough on turbo+DirectML; use turbo |
| "I can parallelize downloads for speed" | B站 rate-limits; parallel = 412 errors. Serial only. |
| "Skip cookies — bestaudio works anyway" | Without cookies you get degraded audio quality on some videos; always use cookies |
| "I'll pick which videos to transcribe for Mason" | No. Probe → show summary → Mason decides filter. Never pick for Mason. |
| "It's just the same 30 videos, no need for filter_used.yaml" | Without the yaml, you can't reproduce "which filter produced this dataset" 3 months later |
| "ad-hoc script is fine for one creator" | That's what we said about xiaogougou, then had to do this whole spec |
| "language auto-detect is safer" | For Chinese UP主, explicit `zh` is faster and avoids misdetection on background music |
| "I can add resume logic later" | Idempotent skip-if-exists IS the resume logic. Design for it from day 1. |

---

## 14. Out of Scope (Explicitly)

These are NOT part of this skill. Adding them = scope creep:

1. **Analysis reports** — Mason drives analysis in conversation; no templated report generation
2. **YouTube / 小红书 / 抖音 support** — future separate skills per platform
3. **Comment scraping / 评论考古** — was part of xiaogougou TRACK_RECON report, handled by a separate tool
4. **Video clipping** — use `video-asset-collect` for clip-level work
5. **Signal-based selection** — use `video-asset-collect` for signal-driven collection
6. **Multi-language support** — Chinese only for v1; `--lang` flag can be added later
7. **Automatic theme clustering** — selection is manual via filter; clustering adds ML complexity with low value
8. **Whisper model selection flag** — turbo only for v1; change requires editing transcribe.py

---

## 15. Success Criteria

The skill is successful if:

1. Mason can run `dive <URL> <slug> --out <dir>` on a new UP主 and get full raw materials without hand-editing any code
2. Re-running the same command after interruption resumes cleanly (no duplicated work, no corruption)
3. `transcribe <slug>` works on an audio directory produced by any source (not just this skill)
4. `filter_used.yaml` captures enough state to reproduce the exact same selection 3 months later
5. No single-item failure stops the whole batch; all failures are logged and reported at the end
6. Mason does not have to read any Python code to operate the skill

---

## 16. Open Questions (none currently)

All decisions resolved in brainstorming. This section kept for future design revisions.
