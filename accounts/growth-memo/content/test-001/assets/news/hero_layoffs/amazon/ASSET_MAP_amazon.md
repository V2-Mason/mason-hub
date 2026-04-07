# Asset Map — Amazon Hero Clip

## Parameters
- Resolution: 1920x1080
- Aspect: 16:9
- Language: en
- Source tier: Tier-1 official news (CNBC Television @CNBCtelevision)
- Topic keywords matched: layoffs, cut

## Asset

| Signal | File | Source | Channel ID | URL | Segment (in source) | Duration | Status |
|--------|------|--------|------------|-----|---------------------|----------|--------|
| Amazon AI layoffs hero | en_layoff_amazon_10000_cnbc.mp4 | CNBC Television | @CNBCtelevision (UCrp_UI8XtuYfpiqluWLD7Lw) | https://www.youtube.com/watch?v=9x0GRFUwSqo | 11.73s - 17.17s | 5.47s | PASS 13/13 |

## Source Video
- Video ID: 9x0GRFUwSqo
- Title: Amazon CEO says layoffs will continue into 2023
- Uploader: CNBC Television
- Uploader ID: @CNBCtelevision
- Upload date: 2022-11-18
- Full duration: 66s

## Transcript of Clip
"...recently 10,000 employees would be cut at that company."

Word-level boundary:
- 'recently' start: 11.880s
- 'company.' end: 17.020s
- Cut points: 11.73s (start - 0.15s lead) to 17.17s (end + 0.15s tail)

## Anchor-Lock 13-Check Results

### Standard 9
| Check | Result | Evidence |
|-------|--------|---------|
| S1 Resolution >= 1920x1080 | PASS | ffprobe: 1920x1080 |
| S2 Aspect ratio 16:9 | PASS | 1920/1080 = 16:9 |
| S3 Encoding H.264 + AAC | PASS | ffprobe: codec=h264, audio=aac |
| S4 Signal completeness (Amazon layoffs number receivable) | PASS | "10,000 employees would be cut" in 5.47s |
| S5 Visual clarity (chyron readable) | PASS | "AMAZON CEO SAYS LAYOFFS WILL CONTINUE INTO 2023" chyron visible all 5 frames |
| S6 AV sync (visual + audio same info) | PASS | Chyron matches audio content |
| S7 Source compliance Tier-1 official | PASS | @CNBCtelevision verified official CNBC channel |
| S8 Technical: first frame no black, speech not truncated | PASS | frame_0_1s has full content; lead 0.15s before word start |
| S9 Uploader verified | PASS | yt-dlp -j: uploader_id=@CNBCtelevision, channel_id=UCrp_UI8XtuYfpiqluWLD7Lw |

### Anchor-Lock 4
| Check | Result | Evidence |
|-------|--------|---------|
| L1 Topic match | PASS | transcript contains "layoffs" (7.18s) and "cut" (16.06s) |
| L2 Single shot: ffmpeg scene detect threshold=0.1 | PASS | 0 cuts detected on clip. 5-frame visual check: same male CNBC anchor in all 5 frames. Right-side OTS graphic changes (Jassy photo -> blue -> AMZN stock chart) but anchor subject is consistent throughout. |
| L3 Anchor present at midpoint | PASS | frame_50pct (2.736s): CNBC male anchor on screen. Not B-roll. |
| L4 No dramatic pause (max gap < 0.4s) | PASS | Target sentence "recently 10,000 employees would be cut at that company" (11.88-17.02s): max inter-word gap = 0.000s (all word timestamps show 0 gap within segment) |

## Files
- en_layoff_amazon_10000_cnbc.mp4 — final clip (PASS 13/13)
- transcript.json — full video word-level whisper output
- frames/frame_0_1s.jpg — 0.10s
- frames/frame_25pct.jpg — 1.37s
- frames/frame_50pct.jpg — 2.74s
- frames/frame_75pct.jpg — 4.10s
- frames/frame_end_m0_1s.jpg — 5.37s
