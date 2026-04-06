# Cut Sheet -- Act 1 News Multiscreen (0:03-0:12)

> Brief: "AI 替代了客服 / AI 裁掉了设计部 / 程序员的黄昏"
> 效果: 1个面板 -> 裂变铺满, 新闻标题扑面而来
> Skill: video-clip-select v7+ (Hero 5-check + Fill 3-check, PySceneDetect-based)

## Hero Clips (audio-prominent, 5-check)

每个选段必须通过 5 个 Check:
1. **Check 1 -- Statement type:** 主语在做事 (X is cutting Y jobs), 不是评论
2. **Check 2 -- Standalone:** 不听上下文也能理解 WHO did WHAT
3. **Check 3 -- Sentence completeness:** 句子在 out point 结束, 不截断
4. **Check 4 -- Impact words:** 含 layoff/cut/threat/crash/disrupt/replace/eliminate/impact/blame 或 brief 等价词
5. **Check 5 -- Visual match:** 中点帧画面内容与句子说的是同一件事

片段 in/out 由句子边界决定, 不由 scene cut 决定。

| # | File | In | Out | Dur | Sentence | Visual (verified) | Checks |
|---|------|----|-----|-----|----------|-------------------|--------|
| 1 | 01_en_C4_amzn_10000.mp4 | 19.7s | 23.7s | 4.0s | "Amazon is planning to cut 10,000 workers." | "AMAZON PLANS TO LAY OFF ABOUT 10K STAFF" + AMZN chart | 5/5 pass |
| 2 | 02_en_C1_google_12000.mp4 | 3.0s | 10.0s | 7.0s | "Google parent Alphabet this morning the company announced it's cutting 12,000 jobs shares are higher by three and a half percent." | "ALPHABET CLASS A (GOOGL)" stock chart at midpoint; "ALPHABET SLASHES HEADCOUNT" at 11.5s | 5/5 pass |
| 3 | 03_en_C2_meta_11000.mp4 | 0s | 5.6s | 5.6s | "another major tech giant is planning to lay off thousands of its workers." | "Meta is Planning to Lay Off Thousands" + Zuckerberg at 4.7s | 5/5 pass |
| 4 | 04_en_C6_chegg_crash.mp4 | 21.5s | 28.0s | 6.5s | "Chegg is the first public company to blame AI and ChatGPT for a major guide down and slower new user growth." | "CHEGG STOCK PLUNGES ON AI THREAT" + CHGG -48.75% | 5/5 pass |
| 5 | 05_en_C3_msft_10000.mp4 | 3.4s | 9.2s | 5.8s | "10,000 jobs being cut by Microsoft roughly 5% of the company's workforce." | "MICROSOFT TO SLASH 10,000 JOBS" at 8s | 5/5 pass |

## Fill Clips (visual-only, 3-check)

每个选段通过 3 个 Fill Check (基于 PySceneDetect shot 边界):
1. **Check F1 -- Thumbnail readability:** 200x112 缩略图大小可识别
2. **Check F2 -- Theme relevance:** 画面与 AI/科技/裁员主题相关
3. **Check F3 -- Frame cleanliness:** 静态帧, 非转场

切片规则: 选 PySceneDetect mid-frame, 用所在 shot 的边界作 cut 范围, 取 3s 居中窗口。

| # | File | Source | In | Dur | Visual | Layer |
|---|------|--------|----|-----|--------|-------|
| 01 | fill_01_en_A1_google_gemini_era.mp4 | en_A1 | 1.0s | 3.0s | Google homepage with AI sparkle in 'g' + "Generate"/"Help me write" buttons | 1a-demo |
| 02 | fill_02_en_A3_openai_sora.mp4 | en_A3 | 4.0s | 3.0s | "Sora is a new AI model that can create realistic and imaginative scenes from text prompts." 文字卡 | 1a-demo |
| 03 | fill_03_en_A5_nvidia_gtc26.mp4 | en_A5 | 61.8s | 3.0s | Jensen Huang on dark stage in leather jacket (NVIDIA GTC keynote) | 1a-demo |
| 04 | fill_04_en_A6_anthropic_opus46.mp4 | en_A6 | 32.7s | 3.0s | "Opus 4.6 is now our default model" 大字 (Anthropic 发布) | 1a-demo |
| 05 | fill_05_en_A8_cnbc_deepseek_breakthrough.mp4 | en_A8 | 111.8s | 3.0s | CNBC anchor + "INSIDE DEEPSEEK'S BREAKTHROUGH" lower-third | 1a-demo |
| 06 | fill_06_cn_A13_cctv_ai_videogen.mp4 | cn_A13 | 92.5s | 3.0s | "旗舰模型 GLM-5" + 模型规格表 (智谱 AI 发布) | 1a-demo |
| 07 | fill_07_en_B1_cnbc_anthropic_30b.mp4 | en_B1 | 14.9s | 3.0s | CNBC anchor + "ANTHROPIC TO SPEND $30B IN COMPUTE THROUGH NVIDIA AND MICROSOFT" | 1b-hype |
| 08 | fill_08_en_B3_cnbc_nvidia_1t.mp4 | en_B3 | 43.2s | 3.0s | NVDA stock chart + "JENSEN HUANG'S $1T AI CHIP FORECAST" | 1b-hype |
| 09 | fill_09_en_B4_cnbc_trillion_deals.mp4 | en_B4 | 1.0s | 3.0s | Reuters "From OpenAI to Meta, firms channel billions into AI infrastructure" 标题卡 | 1b-hype |
| 10 | fill_10_en_B4b_bloomberg_openai_msft.mp4 | en_B4b | 42.2s | 3.0s | Caroline Hyde + MSFT stock + "MICROSOFT SIGNS A NEW PACT WITH OPENAI" | 1b-hype |
| 11 | fill_11_en_B6_bloomberg_deepseek_shocks.mp4 | en_B6 | 249.0s | 3.0s | Stacy Rasgon + BIG TECH STOCKS panel (NVDA -11%, MSFT -4%, META -2.6%, GOOG -3.4%) + "DON'T THINK DEEPSEEK TECH IS A 'MIRACLE'" | 1b-hype |
| 12 | fill_12_en_B7_cnbc_deepseek_chip_selloff.mp4 | en_B7 | 44.3s | 3.0s | Apple App Store top apps "#1 DeepSeek, #2 ChatGPT, #3 Paramount+, #4 Threads, #5 Temu" | 1b-hype |
| 13 | fill_13_en_B8_bloomberg_nvidia_465b_wipeout.mp4 | en_B8 | 28.5s | 3.0s | Gregory Allen (CSIS) + "DEEPSEEK BUZZ PUTS TECH ON TRACK FOR $1T DROP" | 1b-hype |
| 14 | fill_14_cn_B10_36kr_deepseek.mp4 | cn_B10 | 31.2s | 3.0s | "FT The Economic Times" 文章 + DeepSeek 用 2048 张 NVIDIA H800 GPU + GPU 图 | 1b-hype |
| 15 | fill_15_cn_B11_jiqizhixin_nvidia_gtc.mp4 | cn_B11 | 42.6s | 3.0s | Jensen Huang 黑色皮衣 + "最新 LATEST" 红色徽章 + 中文字幕"英伟达正在构建三种AI基础设施" | 1b-hype |
| 16 | fill_16_cn_B12_jiqizhixin_deepseek_nature.mp4 | cn_B12 | 4.0s | 3.0s | Nature 杂志封面 "SELF-HELP / Reinforcement learning teaches AI model to improve itself" | 1b-hype |
| 17 | fill_17_en_C5_news18_ibm_7800.mp4 | en_C5 | 20.4s | 3.0s | 男主播脸部 + "7,800" 数字浮雕动画 (IBM 7,800 岗位影响) | 2-layoffs |

## Fill Eliminated

| Clip | Reason |
|------|--------|
| en_A2_openai_gpt5 | 所有长 shot 都是文档/UI 截图 (MRR表/聊天气泡/搜索框), 无明显 OpenAI/AI 品牌信号 |
| en_A4_openai_sora2 | Sora 2 生成内容太逼真 (滑水/牛仔), 无文字标识时观众无法识别为 AI |
| en_A7_anthropic_opus45 | 全是访谈式 talking head + 字幕, F1 fail (preset 明示禁用) |
| cn_A9_cctv_deepseek | CCTV 演播室 + 缅北诈骗滚动字幕 (画面跟 AI 主题脱节) |
| cn_A10_cctv_70ai_civil | CCTV "新闻 1+1" 演播室 + 国家发改委字幕, 无 AI 视觉信号 |
| cn_A11_cctv_renda_deepseek | NPC 发布会画面, 与 AI 内容仅音频关联, 视觉无 AI 元素 |
| cn_A12_xinhua_deepseek_praised | 商务部部长 + 外贸数据字幕, 跟 AI 主题脱节 |
| en_B5_nvidia_jensen_keynote | PySceneDetect 只检测到 1 个 shot (静态长镜头), mid-frame 是历史 HP 工厂照片 |
| en_B9_bloomberg_deepseek_wakeup | Trump 在 Congressional Institute 演讲, 视觉无 AI/tech 元素 |

## Hero Eliminated

| Clip | Reason |
|------|--------|
| en_C7_cnbc_ai_disruption_fears | 5-check REJECT: 全是评论/分析, Check 1 FAIL on every sentence |
| cn_C8_huxiu_ai_layoff | 访谈格式, 无新闻标题, 风格不匹配 |
| cn_C9_jiqizhixin_meta_layoff | 非官方源 (个人账号上传) |

## Stats

- **Hero**: 5 clips (5/9 from Layer 2 Layoffs)
- **Fill**: 17 clips (5/8 Layer 1a EN + 1/5 Layer 1a CN + 7/9 Layer 1b EN + 3/3 Layer 1b CN + 1 Layer 2 leftover)
- **Total Act 1 clips**: 22
- **AE Multiscreen template panels**: ~40 (剩余 18 panel 用循环或 hero 复用填充)
- **Fill 通过率**: 17/26 = 65%

## Revision Log

| Version | Date | Changes |
|---------|------|---------|
| v1 (4-check) | 2026-04-06 | Initial selection: C7, C1, C2, C6, C3 |
| v2 (5-check) | 2026-04-06 | Re-verified with v5. C7 REJECTED. C4 替代 C7. 全部 5 clips 重切. |
| v3 (Hero+Fill) | 2026-04-06 | Added 17 fill clips using v7 Phase 3-Fill (PySceneDetect-based, 3-check F1/F2/F3). Replaces ffmpeg scene detect with PySceneDetect for better shot boundary accuracy. |
