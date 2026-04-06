# Cut Sheet -- Act 1 News Multiscreen (0:03-0:12)

> Brief: "AI 替代了客服 / AI 裁掉了设计部 / 程序员的黄昏"
> 效果: 1个面板 -> 裂变铺满, 新闻标题扑面而来
> Skill: video-clip-select v5 (5 checks: statement, standalone, complete, impact, visual match)

## Selection Criteria (v5)

每个选段必须通过 5 个 Check:
1. **Check 1 -- Statement type:** 主语在做事 (X is cutting Y jobs), 不是评论
2. **Check 2 -- Standalone:** 不听上下文也能理解 WHO did WHAT
3. **Check 3 -- Sentence completeness:** 句子在 out point 结束, 不截断
4. **Check 4 -- Impact words:** 含 layoff/cut/threat/crash/disrupt/replace/eliminate/impact/blame 或 brief 等价词
5. **Check 5 -- Visual match:** 中点帧画面内容与句子说的是同一件事

片段 in/out 由句子边界决定, 不由 scene cut 决定。

## Final Clips

| # | File | In | Out | Dur | Sentence | Visual (verified) | Checks |
|---|------|----|-----|-----|----------|-------------------|--------|
| 1 | 01_en_C4_amzn_10000.mp4 | 19.7s | 23.7s | 4.0s | "Amazon is planning to cut 10,000 workers." | "AMAZON PLANS TO LAY OFF ABOUT 10K STAFF" + AMZN chart | 5/5 pass |
| 2 | 02_en_C1_google_12000.mp4 | 3.0s | 10.0s | 7.0s | "Google parent Alphabet this morning the company announced it's cutting 12,000 jobs shares are higher by three and a half percent." | "ALPHABET CLASS A (GOOGL)" stock chart at midpoint; "ALPHABET SLASHES HEADCOUNT / GOOGLE PARENT ELIMINATING 12K JOBS" at 11.5s | 5/5 pass |
| 3 | 03_en_C2_meta_11000.mp4 | 0s | 5.6s | 5.6s | "another major tech giant is planning to lay off thousands of its workers." | "Meta is Planning to Lay Off Thousands" + Zuckerberg at 4.7s | 5/5 pass |
| 4 | 04_en_C6_chegg_crash.mp4 | 21.5s | 28.0s | 6.5s | "Chegg is the first public company to blame AI and ChatGPT for a major guide down and slower new user growth." | "CHEGG STOCK PLUNGES ON AI THREAT TO NEW USER GROWTH" + CHGG -48.75% | 5/5 pass |
| 5 | 05_en_C3_msft_10000.mp4 | 3.4s | 9.2s | 5.8s | "10,000 jobs being cut by Microsoft roughly 5% of the company's workforce." | "MICROSOFT TO SLASH 10,000 JOBS THROUGH END OF 3Q 2023" at 8s | 5/5 pass |

## Eliminated

| Clip | Reason |
|------|--------|
| en_C7_cnbc_ai_disruption_fears | REJECTED: all sentences are reporter commentary/analysis, zero news statements. Check 1 FAIL on every sentence. |
| cn_C8_huxiu_ai_layoff | Interview format, no news headlines, style mismatch |
| cn_C9_jiqizhixin_meta_layoff | Unofficial source (personal video) |
| en_C5_news18_ibm_7800 | Passed 5/5 but not selected: webcam-style presentation, weaker visual impact vs en_C4 |

## Revision Log

| Version | Date | Changes |
|---------|------|---------|
| v1 (4-check) | 2026-04-06 | Initial selection: C7, C1, C2, C6, C3 |
| v2 (5-check) | 2026-04-06 | Re-verified with video-clip-select v5. C7 REJECTED (all commentary). C4 (Amazon) replaces C7. C6 out point extended 26.2s -> 28.0s (Check 3 sentence completion). C1 in point adjusted 3.5 -> 3.0. All 5 clips re-cut. |
