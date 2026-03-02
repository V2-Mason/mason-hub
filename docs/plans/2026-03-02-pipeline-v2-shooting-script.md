# SurenXuan Content Pipeline v2 — 拍摄脚本层设计 + Pipeline 修正方案

> 基于 01-09 全链路审计的改进建议
> Mason 审批：待确认
> 创建日期：2026-03-02

---

## 一、当前 Pipeline 架构缺陷

```
当前链条（每步都在远离素材，零步在靠近执行）：

  竞品视频 → [01 Gemini拆解] → [02 本地化] → [03 分镜prompt] → AI生图
                  ↓                   ↓                ↓
             客观+主观混合        半改半不改         缺具体动作
             客群假设污染        内部自相矛盾       视觉参数取错源
```

### 各环节问题速查表

| 环节 | 文件 | 核心问题 | 下游影响 |
|------|------|---------|---------|
| 拆解 | 04/01 | prompt预设35+客群假设，污染客观记录 | 分析结果不纯净 |
| 本地化 | 05/02 | 白名单不完整，speaking_pace/emotional_arc未改 | JSON内部两套人格 |
| 本地化 | 05/02 | signature_phrases虚构了原视频不存在的价格信息 | 后续内容基于假数据 |
| 分镜生成 | 06/03 | 从不可修改的visual_analysis取视觉参数 | 风格与品牌指南冲突 |
| 分镜生成 | 06/03 | 角色描述硬编码，hook段也是"从容不夸张" | 缺乏戏剧张力 |
| 分镜生成 | 06/03 | prompt只有情绪描述，无具体动作/构图/物品 | AI生图质量差 |
| 分镜输出 | 03 | 五个prompt高度雷同 | 分镜图之间无差异 |
| 架构 | 全局 | 缺少"拍摄脚本"层，从分析直接跳到图片 | 无人能据此执行拍摄 |

---

## 二、修正后的 Pipeline

```
竞品视频
    │
    ▼
[01 Gemini拆解] ── 纯客观记录 + 新增逐句transcript
    │
    ▼
[02 本地化分析] ── 完整白名单/黑名单，不虚构信息
    │
    ▼
[NEW: 拍摄脚本] ── 纯前向，只描述"我们怎么拍"  ← 关键新增
    │
    ▼
[分镜Prompt] ── 从脚本取参数，不再读分析JSON
    │
    ▼
AI生图 / 实际拍摄指导
```

---

## 三、拍摄脚本 Schema

### 设计原则

1. **纯前向**：不引用原视频参数，只描述素仁轩怎么拍
2. **可执行**：拍摄团队或AI生图都能直接用
3. **每镜独立**：每个shot有完整动作、构图、表情、物品、口播
4. **品牌内建**：视觉风格从voice.md硬编码

### 完整 JSON Schema

```json
{
  "script_metadata": {
    "source_video_id": "competitor_brush_kaishua_55s",
    "brand": "surenxuan",
    "target_account": "号2（韩国好物种草号）",
    "target_platform": "xiaohongshu",
    "script_version": "v1",
    "created_at": "2026-03-02T12:00:00Z",
    "total_duration_seconds": 55,
    "content_type": "教程演示",
    "content_topic": "化妆刷开刷技巧"
  },

  "creative_brief": {
    "one_line_concept": "新买的化妆刷不好用？学会开刷这一招就能救回来",
    "target_audience": "35+女性，有基础化妆习惯，买过百元左右化妆刷但不满意效果",
    "core_value_proposition": "零成本预处理技巧，用家里现有的凡士林和散粉就能做",
    "engagement_goal": "收藏率 — 干货教程类，用户会先存后用",
    "tone": "温和从容，邻家姐姐分享亲测经验",
    "pacing": "中速偏慢，允许停顿和呼吸，每个步骤留足展示时间"
  },

  "visual_style": {
    "color_temperature": "暖色调，自然温暖",
    "lighting": "自然光 + 环形补光灯，避免冷白光",
    "filter": "轻微暖调，不过度美颜，保持皮肤真实质感",
    "subtitle_style": "白色无衬线体，底部居中，中等字号",
    "text_overlay": "关键步骤用稍大字号白色加粗，不用黄底黑字或花哨贴纸",
    "aspect_ratio": "9:16"
  },

  "character": {
    "description": "35岁左右中国女性，面容自然温和",
    "wardrobe": "简洁舒适的家居服或休闲装，干净素雅",
    "makeup_base": "淡妆底妆（需展示上妆过程）",
    "hair": "自然披肩或简单扎起",
    "default_expression": "从容、温和、自然",
    "default_energy": "平稳中偶有轻微惊喜"
  },

  "props": [
    {"name": "扁头粉底刷", "note": "常见百元款"},
    {"name": "眼影刷", "note": "普通晕染刷"},
    {"name": "凡士林", "note": "普通药房款，需拍到瓶身"},
    {"name": "散粉", "note": "展示粉质"},
    {"name": "定妆喷雾", "note": "喷雾瓶型"},
    {"name": "粉底液", "note": "最终上妆用"},
    {"name": "眼影盘", "note": "较深色号，方便展示显色度"}
  ],

  "shots": [
    {
      "shot_id": 1,
      "shot_type": "hook",
      "duration_seconds": "0-8",
      "camera": {
        "framing": "半身到脸部特写，肩膀以上",
        "angle": "正面平视，略微仰角",
        "movement": "固定机位"
      },
      "action": {
        "description": "手持粉底刷蘸粉底液，在脸颊刷两下。脸上留下明显刷痕。看镜头，表情从期待变无奈。",
        "key_gesture": "刷完后把刷子举到脸旁，另一只手指向刷痕",
        "expression_arc": "期待 → 无奈 → 轻微摇头",
        "props_in_frame": ["粉底刷", "粉底液"]
      },
      "voiceover": {
        "text": "姐妹们，新买的粉底刷是不是也这样？一上脸全是痕，感觉钱白花了。",
        "tone": "平静中带无奈，不夸张愤怒",
        "pace": "中速"
      },
      "text_overlay": {"main_text": null, "subtitle": "同步口播字幕"},
      "visual_focus": "脸颊上清晰可见的粉底刷痕",
      "transition_to_next": "自然语气转折"
    },
    {
      "shot_id": 2,
      "shot_type": "hook_extension",
      "duration_seconds": "8-15",
      "camera": {
        "framing": "脸部特写 → 手持眼影刷上眼",
        "angle": "正面平视",
        "movement": "固定机位"
      },
      "action": {
        "description": "眼影刷蘸眼影上眼皮，几乎不上色。对着镜子看，略困惑。",
        "key_gesture": "刷在眼影盘上蹭一蹭，再上眼展示不显色",
        "expression_arc": "困惑 → 微微叹气",
        "props_in_frame": ["眼影刷", "眼影盘"]
      },
      "voiceover": {
        "text": "眼影刷也是，蹭半天都不上色。其实不是刷子不好，是咱们少了一步。",
        "tone": "从困惑转笃定，'其实不是刷子不好'处语气上扬",
        "pace": "中速，句间有停顿"
      },
      "text_overlay": {"main_text": null, "subtitle": "同步口播字幕"},
      "visual_focus": "眼影盘颜色深 vs 眼皮几乎无色的对比",
      "transition_to_next": "口播引出'开刷'概念"
    },
    {
      "shot_id": 3,
      "shot_type": "transition",
      "duration_seconds": "15-22",
      "camera": {
        "framing": "半身，包含桌面工具",
        "angle": "正面略俯（展示桌面操作区）",
        "movement": "固定机位"
      },
      "action": {
        "description": "把粉底刷和凡士林放到桌面。手在刷子和凡士林之间比划介绍。表情从容自信。",
        "key_gesture": "一手拿刷，一手指凡士林",
        "expression_arc": "从容自信，'我来教你'的姐姐感",
        "props_in_frame": ["粉底刷", "凡士林"]
      },
      "voiceover": {
        "text": "之前在韩国采购的时候，店员教了我一个方法叫'开刷'。新刷子买回来先处理一下，上妆效果完全不一样。",
        "tone": "温和笃定，分享经验",
        "pace": "中速偏慢"
      },
      "text_overlay": {
        "main_text": "「开刷」— 新刷子的必做预处理",
        "subtitle": "同步口播字幕"
      },
      "visual_focus": "桌面上整齐摆放的工具",
      "transition_to_next": "直接进入操作"
    },
    {
      "shot_id": 4,
      "shot_type": "tutorial_step",
      "duration_seconds": "22-30",
      "camera": {
        "framing": "手部微距特写（手+刷子+凡士林）",
        "angle": "俯拍45度",
        "movement": "固定，必要时轻微推进"
      },
      "action": {
        "description": "取少量凡士林涂抹刷毛 → 掌心按压让凡士林渗透 → 放纸巾上静置",
        "key_gesture": "取凡士林 → 涂刷毛 → 掌心按 → 放置",
        "expression_arc": "手部特写为主，面部不在画面或只露下巴",
        "props_in_frame": ["粉底刷", "凡士林", "纸巾"]
      },
      "voiceover": {
        "text": "取一点点凡士林，不用多，薄薄一层涂在刷毛上。然后在手心按几下，让它吃进去。放一会儿就行。",
        "tone": "耐心讲解，手把手教",
        "pace": "慢速，配合手部动作节奏"
      },
      "text_overlay": {
        "main_text": "步骤① 凡士林薄涂 → 掌心按压 → 静置",
        "subtitle": "同步口播字幕"
      },
      "visual_focus": "刷毛从干硬变柔软的质感变化",
      "transition_to_next": "口播过渡"
    },
    {
      "shot_id": 5,
      "shot_type": "tutorial_result",
      "duration_seconds": "30-38",
      "camera": {
        "framing": "脸部特写，覆盖半张脸",
        "angle": "正面平视",
        "movement": "固定机位"
      },
      "action": {
        "description": "用处理好的刷子重新上粉底。同一位置刷几下，无刷痕，均匀服帖。轻摸上妆区域，自然满意。",
        "key_gesture": "刷完侧脸展示，手指轻触对比",
        "expression_arc": "专注上妆 → 轻微惊喜 → 满意点头",
        "props_in_frame": ["粉底刷（已处理）", "粉底液"]
      },
      "voiceover": {
        "text": "你看，处理过之后再上，完全不一样了。没有痕了，很服帖。凡士林把刷毛软化了，对皮肤也更温和。",
        "tone": "轻微惊喜但不夸张",
        "pace": "中速"
      },
      "text_overlay": {"main_text": null, "subtitle": "同步口播字幕"},
      "visual_focus": "同一张脸：之前有痕 vs 现在服帖",
      "transition_to_next": "口播：'眼影刷也是同样的道理'"
    },
    {
      "shot_id": 6,
      "shot_type": "tutorial_step",
      "duration_seconds": "38-46",
      "camera": {
        "framing": "手部微距特写",
        "angle": "俯拍45度",
        "movement": "固定机位"
      },
      "action": {
        "description": "眼影刷蘸散粉转几圈 → 定妆喷雾喷刷头2-3下 → 纸巾蹭干",
        "key_gesture": "蘸散粉 → 喷喷雾 → 蹭纸巾",
        "expression_arc": "手部特写为主",
        "props_in_frame": ["眼影刷", "散粉", "定妆喷雾", "纸巾"]
      },
      "voiceover": {
        "text": "眼影刷也类似。先在散粉上蹭几下，再喷一点定妆喷雾，然后擦干。这样刷毛就不会太散，抓粉力会好很多。",
        "tone": "耐心讲解",
        "pace": "慢速，每步间留1秒停顿"
      },
      "text_overlay": {
        "main_text": "步骤② 蘸散粉 → 喷雾湿润 → 擦干",
        "subtitle": "同步口播字幕"
      },
      "visual_focus": "喷雾喷到刷头的瞬间",
      "transition_to_next": "直接进入上眼效果"
    },
    {
      "shot_id": 7,
      "shot_type": "tutorial_result",
      "duration_seconds": "46-52",
      "camera": {
        "framing": "眼部特写",
        "angle": "正面平视，微仰角展示眼妆",
        "movement": "固定机位"
      },
      "action": {
        "description": "处理好的眼影刷蘸眼影上眼。颜色明显上色，晕染均匀。睁闭眼展示效果。",
        "key_gesture": "上完睁眼看镜头展示显色",
        "expression_arc": "专注 → 睁眼 → 自然微笑",
        "props_in_frame": ["眼影刷（已处理）", "眼影盘"]
      },
      "voiceover": {
        "text": "你看这个显色度，比之前强太多了。同一盘眼影，处理一下刷子就是不一样。",
        "tone": "自然满意，不过度惊叹",
        "pace": "中速"
      },
      "text_overlay": {"main_text": null, "subtitle": "同步口播字幕"},
      "visual_focus": "眼影颜色在眼皮上的清晰呈现",
      "transition_to_next": "进入总结"
    },
    {
      "shot_id": 8,
      "shot_type": "closing",
      "duration_seconds": "52-55",
      "camera": {
        "framing": "半身，展示整体妆容",
        "angle": "正面平视",
        "movement": "固定机位"
      },
      "action": {
        "description": "展示完整妆容。自然微笑，对镜头说结束语。",
        "key_gesture": "侧头展示妆容，然后正面看镜头",
        "expression_arc": "自然微笑，满意不夸张",
        "props_in_frame": []
      },
      "voiceover": {
        "text": "就这么简单，家里有凡士林和散粉就能做。感兴趣的姐妹先收藏，下次买新刷子的时候试试。",
        "tone": "温和收束，像聊天自然结尾",
        "pace": "中速"
      },
      "text_overlay": {"main_text": null, "subtitle": "同步口播字幕"},
      "visual_focus": "自然光下通透的整体妆效",
      "transition_to_next": null
    }
  ],

  "post_production_notes": {
    "bgm": "轻柔生活感背景乐，音量低于口播，全程一致，不做风格切换",
    "editing_pace": "中速剪辑，自然衔接，不用快速跳切",
    "color_grading": "整体暖调，提亮肤色保持自然，不用高饱和韩系滤镜",
    "sound_effects": "不使用夸张音效",
    "cover_image": {
      "recommended_frame": "shot 5 的服帖底妆效果帧",
      "title_text": "35+｜新买的化妆刷不好用？试试这个开刷技巧",
      "font": "白色无衬线体，中等粗细，画面下方1/3",
      "background": "温暖自然光下的真实妆容特写"
    }
  },

  "brand_compliance_checklist": {
    "称呼": "✅ 姐妹/姐妹们",
    "语速": "✅ 中速偏慢",
    "情绪": "✅ 平稳中有轻微亮点",
    "禁用词": "✅ 无违规词",
    "滤镜": "✅ 暖调自然",
    "字幕": "✅ 白色简洁",
    "具体性": "✅ 每个效果说了具体好在哪",
    "真诚度": "⚠️ 可补充'油皮效果可能没那么明显'",
    "命令式": "✅ 用'试试'非'一定要冲'"
  }
}
```

---

## 四、脚本生成 Prompt 核心规则

用于 `shooting_script_prompt.py`：

1. 脚本是"前向"的 — 只描述"我们怎么拍"，不引用原视频参数
2. 从原视频提取的仅限：内容结构框架 + 知识点/教程步骤 + 产品使用方法
3. 语言/视觉/人物设定全部来自品牌资料
4. 每个shot必须包含：具体动作指令、构图、表情弧线、手持物品、完整口播文案
5. 口播文案是可直接朗读的完整句子
6. 原视频一个segment可拆成多个shot（如"步骤演示"拆成"操作特写"+"效果展示"）
7. 如原视频使用不适合品牌的创意手法，用品牌适配版替代
8. 视觉风格从voice.md第六章提取，绝不从原视频visual_analysis继承
9. 不虚构原视频不存在的信息（如原视频无价格，脚本也不编造价格）

---

## 五、上游修正要点

### 5.1 拆解 Prompt (gemini_analyze.py)

- 移除第7条的客群假设（35+/100-300元），改为中性记录规则
- 新增 `transcript[]` 字段要求逐句转录口播
- 保持纯客观"记录员"角色

### 5.2 本地化 Prompt (localize.py)

- **白名单 → 黑名单**：除明确不可改的字段外，其余均可适配
- 新增规则：不可虚构原视频不存在的信息
- speaking_pace / emotional_arc / pacing_pattern 纳入可修改范围

### 5.3 分镜生成 (storyboard.py)

- 数据源从 `localized_analysis.json` 改为 `shooting_script.json`
- 视觉参数从脚本的 `visual_style` 取，不从 `visual_analysis` 取
- 角色状态随shot动态变化，不再硬编码

---

## 六、实施优先级

| 优先级 | 任务 | 影响 |
|--------|------|------|
| P0 | 创建 shooting_script_prompt.py | 补上缺失的执行层 |
| P0 | 重构 storyboard_prompt.py 读脚本而非分析JSON | 分镜质量立即提升 |
| P1 | 修正 localize.py 白名单 → 完整适配 | 消除JSON内部矛盾 |
| P1 | 修正 gemini_analyze.py 移除客群假设 | 拆解结果更纯净 |
| P2 | content_pipeline.py 加入 script 步骤 | 端到端集成 |

---

## 七、修正后文件清单

```
01  gemini_original_analysis.json    Gemini拆解原始输出（纯客观）
02  localized_analysis.json          本地化分析（完整适配）
03  shooting_script.json             拍摄脚本（纯前向，可执行）← NEW
04  storyboard_prompts.json          分镜prompt（从脚本生成）
05  gemini_teardown_prompt.py        拆解prompt（修正版）
06  localize_prompt.py               本地化prompt（修正版）
07  shooting_script_prompt.py        脚本生成prompt ← NEW
08  storyboard_prompt.py             分镜代码（改读脚本）
09  brand_brief.md
10  brand_voice.md
```
