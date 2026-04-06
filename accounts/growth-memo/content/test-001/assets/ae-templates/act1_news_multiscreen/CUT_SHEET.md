# Cut Sheet -- Act 1 News Multiscreen (0:03-0:12)

> Brief: "AI 替代了客服 / AI 裁掉了设计部 / 程序员的黄昏"
> 效果: 1个面板 -> 裂变铺满, 新闻标题扑面而来
> 方法: Whisper 转写 + ffmpeg 场景检测 (0.1) + 逐帧 Read 验证 + 4条选句标准

## Selection Criteria

每个选段必须满足:
1. **News statement > commentary** -- 报道事实, 不是分析评论
2. **Standalone understandable** -- 不听上下文也能理解
3. **Impact words** -- 含 layoff/cut/threat/disrupt/impact 等
4. **Audio-visual match** -- 语音内容和画面文字说同一件事

片段 in/out 由句子边界决定, 不由 scene cut 决定。

## Final Clips

| # | File | In | Out | Dur | Sentence | Visual (verified) | Criteria |
|---|------|----|-----|-----|----------|-------------------|----------|
| 1 | 01_en_C7_ai_disruption.mp4 | 17.8s | 21.0s | 3.2s | "So that post was viral and we should add it was divisive." | "AI DISRUPTION FEARS RATTLE STOCKS" lower-third | 1 compromise (commentary), 2/3/4 pass |
| 2 | 02_en_C1_google_12000.mp4 | 3.5s | 11.5s | 8s | "...cutting 12,000 jobs..." | "DEVELOPING STORY" -> stock chart -> "12K JOBS" | Visual sequence strong, audio segment imprecise |
| 3 | 03_en_C2_meta_11000.mp4 | 0s | 5.6s | 5.6s | "another major tech giant is planning to lay off thousands of its workers." | "'Meta' Planning to Lay Off Thousands" + Zuckerberg at 4.7s | 4/4 pass |
| 4 | 04_en_C6_chegg_crash.mp4 | 21.5s | 26.2s | 4.7s | "Chegg is the first public company to blame AI and ChatGPT for a major guide down" | "CHEGG STOCK PLUNGES ON AI THREAT" + -48.78% chart | 4/4 pass |
| 5 | 05_en_C3_msft_10000.mp4 | 3.4s | 9.2s | 5.8s | "10,000 jobs being cut by Microsoft, roughly 5% of the company's workforce." | "BREAKING NEWS: MICROSOFT TO SLASH 10,000 JOBS" at 8s | 4/4 pass |

## Eliminated (this round + previous)

| Clip | Reason |
|------|--------|
| cn_C8_huxiu_ai_layoff | Interview format, no news headlines, style mismatch |
| cn_C9_jiqizhixin_meta_layoff | Unofficial source (personal video) |
| en_C4_bloomberg_amzn_10000 | Opening discusses stock price, not layoffs |

## Revision Log

| Clip | Previous | Current | What changed |
|------|----------|---------|-------------|
| en_C7 | 17.8-24.0s | 17.8-21.0s | Shortened to sentence end |
| en_C1 | 11.5-14.4s | 3.5-11.5s | Extended to cover news statement + visual sequence |
| en_C2 | 0-5.0s | 0-5.6s | Extended to sentence natural end (5.6s) |
| en_C6 | 7.7-13.0s | 21.5-26.2s | Completely re-selected: commentary -> news statement with visual match |
| en_C3 | 0-4.0s | 3.4-9.2s | Re-selected: generic "BREAKING NEWS" -> specific "10,000 jobs" with title |
