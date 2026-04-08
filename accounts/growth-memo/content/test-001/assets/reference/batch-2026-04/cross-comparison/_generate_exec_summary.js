// Generate Executive Summary docx for Batch Recon 2026-04
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak, PageOrientation
} = require('docx');
const fs = require('fs');
const path = require('path');

const FONT = "Microsoft YaHei";
const PAGE_WIDTH = 12240;   // US Letter 8.5"
const PAGE_HEIGHT = 15840;  // US Letter 11"
const MARGIN = 1440;        // 1"
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN; // 9360

// ----- Borders -----
const cellBorder = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
const cellBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };

// ----- Helpers -----
function tr(text, opts = {}) {
  return new TextRun({ text, font: FONT, size: opts.size || 22, bold: !!opts.bold, italics: !!opts.italics, color: opts.color });
}

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after || 120, before: opts.before || 0 },
    alignment: opts.align || AlignmentType.LEFT,
    children: Array.isArray(text)
      ? text.map(t => typeof t === 'string' ? tr(t, opts) : new TextRun({ font: FONT, size: opts.size || 22, ...t }))
      : [tr(text, opts)]
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 80 },
    children: [tr(text)]
  });
}

function bulletRich(parts, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 80 },
    children: parts.map(t => typeof t === 'string' ? tr(t) : new TextRun({ font: FONT, size: 22, ...t }))
  });
}

function num(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { after: 80 },
    children: [tr(text)]
  });
}

function cell(content, opts = {}) {
  const width = opts.width;
  const shading = opts.shading;
  const align = opts.align || AlignmentType.LEFT;
  const color = opts.color;
  const children = Array.isArray(content)
    ? content.map(line => new Paragraph({
        alignment: align,
        children: [tr(line, { size: opts.size || 20, bold: opts.bold, color })]
      }))
    : [new Paragraph({
        alignment: align,
        children: [tr(content, { size: opts.size || 20, bold: opts.bold, color })]
      })];
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    shading: shading ? { fill: shading, type: ShadingType.CLEAR } : undefined,
    children
  });
}

function headerCell(text, width) {
  return cell(text, { width, shading: "2E75B6", bold: true, color: "FFFFFF" });
}

function table(columnWidths, headers, rows) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => headerCell(h, columnWidths[i]))
  });
  const bodyRows = rows.map((row, idx) => new TableRow({
    children: row.map((content, i) => cell(content, {
      width: columnWidths[i],
      shading: idx % 2 === 0 ? "F2F2F2" : null
    }))
  }));
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths,
    rows: [headerRow, ...bodyRows]
  });
}

function spacer() { return p("", { after: 60 }); }

// ----- Build content -----
const children = [];

// Cover / Title
children.push(new Paragraph({
  spacing: { after: 240 },
  alignment: AlignmentType.CENTER,
  children: [tr("Batch Recon 2026-04", { size: 44, bold: true })]
}));
children.push(new Paragraph({
  spacing: { after: 120 },
  alignment: AlignmentType.CENTER,
  children: [tr("Executive Summary", { size: 32, bold: true, color: "2E75B6" })]
}));
children.push(new Paragraph({
  spacing: { after: 360 },
  alignment: AlignmentType.CENTER,
  children: [tr("Growth Memo 内容路线决策报告", { size: 24, italics: true, color: "666666" })]
}));

children.push(new Paragraph({
  spacing: { after: 360 },
  alignment: AlignmentType.CENTER,
  children: [
    tr("生成日期: 2026-04-08    版本: v0.1    数据基础: 4 Tier 1 账号 × 57 视频 = 228 条", { size: 18, color: "666666" })
  ]
}));

// TL;DR Box
children.push(p("TL;DR (一句话核心结论)", { size: 26, bold: true, color: "2E75B6", before: 120 }));
const tldrTable = new Table({
  width: { size: CONTENT_WIDTH, type: WidthType.DXA },
  columnWidths: [CONTENT_WIDTH],
  rows: [new TableRow({
    children: [new TableCell({
      borders: {
        top: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6" },
        bottom: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6" },
        left: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6" },
        right: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6" }
      },
      width: { size: CONTENT_WIDTH, type: WidthType.DXA },
      shading: { fill: "EAF2F8", type: ShadingType.CLEAR },
      margins: { top: 200, bottom: 200, left: 240, right: 240 },
      children: [new Paragraph({
        children: [tr("4 个 B 站头部账号 (鱼皮 / ezindie / 小Lin 说 / 巫师财经) 全部不可抄, 但 4 个账号共同的市场空白 = ", { size: 22 }),
                   tr("\"实操产出标题 + 真实数据锚点 + 可抄作业 (Notion 模板/Prompt/源码)\"", { size: 22, bold: true, color: "C00000" }),
                   tr("。这正好是 Mason 受众明确求资料但 4 头部都不提供的领域 — 这是 Growth Memo 的差异化定位。", { size: 22 })]
      })]
    })]
  })]
});
children.push(tldrTable);
children.push(spacer());

// Section 1: 数据基础
children.push(p("1. 数据基础 (避免幻觉)", { size: 28, bold: true, color: "2E75B6", before: 240, after: 120 }));
children.push(p("本报告基于 Session 26 (2026-04-08) 采集的:", {}));
children.push(bullet("4 个 Tier 1 账号: 程序员鱼皮 / ezindie 小产品变现 / 小Lin 说 / 巫师财经"));
children.push(bullet("228 条视频 (每账号 T19+M19+B19=57, 按播放量分层采样)"));
children.push(bullet("219/228 条 Whisper Vulkan GPU 转录成功 (111,983 行 full_text)"));
children.push(bullet("2,736 格 PASS/FAIL 打分 (Tier 1 平均每条视频 9-15 个 check, 双 preset 跑了 2 个财经账号)"));
children.push(bullet("打分由 4 个 Subagent 并行执行, 主对话只读了 patterns.md 二级产物 + 巫师 grid.md 的统计 (没有亲眼看任何一条视频的转录原文)"));
children.push(spacer());

// Section 2: 4 账号画像
children.push(p("2. 4 个头部账号速览", { size: 28, bold: true, color: "2E75B6", before: 240, after: 120 }));
children.push(table(
  [1800, 1300, 1300, 1300, 3660],
  ["账号", "粉丝", "P50 播放", "类型归属", "为什么不可抄"],
  [
    ["程序员鱼皮", "877k", "13 万", "第三种 (无规律)", "877k 粉丝 + 多年 SEO 积累 + 实时事件追踪。9 个 check 全部失灵, 爆款机制不在开场结构层面"],
    ["ezindie", "53k", "4.7k", "单机制编译器", "国外开发者独白 + 美金 tagline。2026 年 6/7 新视频塌陷 → 红利已过, 模板已失效"],
    ["小Lin 说", "7.1M", "241 万", "降级科普长视频", "19-35 分钟长视频 + 宏观题材 + \"一口气了解 XX\" 品牌 prefix → 重成本壁垒"],
    ["巫师财经", "4.18M", "125 万", "弱化版伦巴", "蹭全民话题 (杨幂/春晚/关税) + 限流风险高 → 题材池和 Mason 受众完全错配"],
  ]
));
children.push(p("注: 4/4 都不符合现有狗勾型 preset。狗勾的\"路径 A 故事 + 路径 B SEO 长尾\"双路径模板可能真是 B 站独立异类。", { size: 20, italics: true, color: "666666", after: 120 }));

// PAGE BREAK
children.push(new Paragraph({ children: [new PageBreak()] }));

// Section 3: 4/4 黄金共性
children.push(p("3. 核心发现: 4/4 黄金共性 (★★★)", { size: 28, bold: true, color: "2E75B6", before: 0, after: 120 }));
children.push(p("不是\"找到共同的爆款公式\", 而是\"找到共同的市场空白\"。", { italics: true, color: "666666", after: 200 }));

children.push(p("共性 1: C9 可抄作业 ≈ 0 (4/4)", { size: 24, bold: true, color: "C00000", after: 80 }));
children.push(table(
  [2340, 2340, 4680],
  ["账号", "C9 PASS 数 / 比例", "说明"],
  [
    ["鱼皮", "~5 / 57 (8%)", "极少在简介承诺资料"],
    ["ezindie", "0 / 57 (0%)", "周刊赛道完全不提供"],
    ["小Lin 说", "1 / 57 (1.8%)", "唯一一条是出书宣告"],
    ["巫师财经", "0 / 57 (0%)", "评论型不提供产物"],
  ]
));
children.push(p("含义: B 站头部 dev/财经 UP 主全部不提供可复刻产物。但 Mason 的 AUDIENCE_PERSONAS 里 [37 赞] [35 赞] [197 赞] 多条高赞评论都在求模板/Prompt/源码。", { after: 80 }));
children.push(p("→ 这是一个明确的 product-market fit 缺口。", { bold: true, color: "C00000", after: 200 }));

children.push(p("共性 2: C7 实操产出标题 4/4 反向 (★★)", { size: 24, bold: true, color: "C00000", after: 80 }));
children.push(p("4 个账号的实操标题 (\"我用 X 做了 / 踩了 N 个坑 / 完整指南\") 在 Top 12 段反而比 Bot 12 段更少。", { after: 80 }));
children.push(table(
  [2340, 2340, 4680],
  ["账号", "Δ (Top - Bot)", "Top vs Bot 命中数"],
  [
    ["鱼皮", "-0.25 (反向)", "Top 6/12 vs Bot 9/12"],
    ["ezindie", "-0.33 (反向)", "Top 0/12 vs Bot 4/12"],
    ["小Lin 说", "-0.25 (反向)", "Top 0/12 vs Bot 3/12"],
    ["巫师财经", "-0.25 (反向)", "Top 0/12 vs Bot 3/12"],
  ]
));
children.push(p("含义: 头部账号已退出实操赛道, 实操内容被中腰和 Bot 段占据。两种解释:", { after: 80 }));
children.push(num("头部已成名, 不需要靠实操吸新粉, 转向评论/解读"));
children.push(num("实操是新手赛道 — 但 4/4 头部反向更可能支持 #1"));
children.push(p("→ 头部退出留下空白带, 是新进场账号的机会。", { bold: true, color: "C00000", after: 200 }));

children.push(p("共性 3: 现有 preset 在 3/4 账号上失灵 (★★)", { size: 24, bold: true, color: "C00000", after: 80 }));
children.push(p("9 check 里能有效区分 Top vs Bot 的只有 C6 数字密度 (3/4 账号是最强或次强信号)。其他 8 个 check 在 4 账号上要么反向、要么常量、要么各异。", { after: 80 }));
children.push(p("→ 现有 preset 是从狗勾 1 个样本反推的, 外推效度有限, 不能机械套用到其他账号的爆款分析。", { italics: true, color: "666666", after: 200 }));

// Section 4: 差异化爆款公式
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(p("4. Mason 的差异化爆款公式", { size: 28, bold: true, color: "2E75B6", before: 0, after: 120 }));
children.push(p("从 4/4 共性反向构造。每一项都是\"4 头部都不做\"或\"4 头部都做\"的明确信号。", { italics: true, color: "666666", after: 200 }));

const formulaTable = new Table({
  width: { size: CONTENT_WIDTH, type: WidthType.DXA },
  columnWidths: [CONTENT_WIDTH],
  rows: [new TableRow({
    children: [new TableCell({
      borders: {
        top: { style: BorderStyle.SINGLE, size: 16, color: "C00000" },
        bottom: { style: BorderStyle.SINGLE, size: 16, color: "C00000" },
        left: { style: BorderStyle.SINGLE, size: 16, color: "C00000" },
        right: { style: BorderStyle.SINGLE, size: 16, color: "C00000" }
      },
      width: { size: CONTENT_WIDTH, type: WidthType.DXA },
      shading: { fill: "FDF2F2", type: ShadingType.CLEAR },
      margins: { top: 240, bottom: 240, left: 320, right: 320 },
      children: [
        new Paragraph({ children: [tr("Mason Growth Memo 爆款公式 v0.1", { size: 24, bold: true, color: "C00000" })], alignment: AlignmentType.CENTER, spacing: { after: 200 } }),
        new Paragraph({ children: [tr("[反差/极端数字开场]", { size: 22, bold: true })], spacing: { after: 80 } }),
        new Paragraph({ children: [tr("+ [具名工具 (Cursor / Claude Code / Notion) + Mason 自己作为具名开发者]", { size: 22, bold: true })], spacing: { after: 80 } }),
        new Paragraph({ children: [tr("+ [开场 60s 内 ≥3 个真实数据锚点 (token / 收入 / 天数 / 工具版本)]", { size: 22, bold: true })], spacing: { after: 80 } }),
        new Paragraph({ children: [tr("+ [实操产出型标题: \"我用 X 做了 / 踩了 N 个坑 / 完整流程\"]", { size: 22, bold: true })], spacing: { after: 80 } }),
        new Paragraph({ children: [tr("+ [可抄作业承诺: \"完整 Prompt + Notion 模板 + 工具清单\"]", { size: 22, bold: true })], spacing: { after: 200 } }),
        new Paragraph({ children: [tr("= 4 头部都不做的差异化定位", { size: 22, bold: true, color: "C00000" })], alignment: AlignmentType.CENTER }),
      ]
    })]
  })]
});
children.push(formulaTable);
children.push(spacer());

// Section 5: 3 个钩子题材
children.push(p("5. 立即可试的 3 个钩子题材", { size: 28, bold: true, color: "2E75B6", before: 240, after: 120 }));
children.push(p("每个题材都全 PASS 上述 5 个 check, 且在 4 个头部账号上都不会出现 — 完全占领空白。", { italics: true, color: "666666", after: 200 }));

children.push(p("题材 1 (★ 推荐): \"Cursor 一周吃我 1000 万 token, 1500 美元账单, 我学到的 8 件事\"", { size: 22, bold: true, after: 80 }));
children.push(bullet("反差: \"1000 万 token / 1500 美元\" 极端数字"));
children.push(bullet("具名: Cursor + Mason + Claude 4.5"));
children.push(bullet("数据: 1000万 / 1500美元 / 一周 / 8件事 (4 个真实锚点)"));
children.push(bullet("实操: \"我学到的 8 件事\" 是亲历产出"));
children.push(bullet("可抄作业: 简介承诺 \"我的 Cursor 配置 + Prompt 模板分享\""));
children.push(spacer());

children.push(p("题材 2: \"30 天用 Claude Code 做 9 个项目, 收入 3.2 万: 完整 PRD 模板 + 失败复盘\"", { size: 22, bold: true, after: 80 }));
children.push(bullet("反差: 30 天 + 9 个项目 + 3.2 万 极端节奏"));
children.push(bullet("具名: Claude Code + Mason"));
children.push(bullet("数据: 30 / 9 / 3.2 万 (3 个数字)"));
children.push(bullet("实操: \"完整 PRD 模板 + 失败复盘\""));
children.push(bullet("可抄作业: \"完整 PRD 模板\" 高价值产物"));
children.push(spacer());

children.push(p("题材 3: \"我用 12 个 AI 工具替代了 3 个全职员工, 月成本 200 美金\"", { size: 22, bold: true, after: 80 }));
children.push(bullet("反差: \"12 个工具 vs 3 个员工 vs 200 美金\" 三重反差"));
children.push(bullet("具名: 12 个具体工具名 + Mason"));
children.push(bullet("数据: 12 / 3 / 200 (3 个数字)"));
children.push(bullet("实操: \"我用\" 实操声明"));
children.push(bullet("可抄作业: \"完整工具清单 + 月成本拆解\""));

// Section 6: 死路 + 风险
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(p("6. 不要走的 3 条死路", { size: 28, bold: true, color: "2E75B6", before: 0, after: 120 }));
children.push(p("死路 1: 抄 ezindie 模式 (国外故事编译)", { size: 22, bold: true, color: "C00000", after: 80 }));
children.push(bullet("ezindie 红利已过 (2026 新视频塌陷), 模板已失效"));
children.push(bullet("国外信源对 Mason 没有竞争优势 (语言/时差/深度)"));
children.push(spacer());
children.push(p("死路 2: 抄小Lin 说模式 (品牌化长视频)", { size: 22, bold: true, color: "C00000", after: 80 }));
children.push(bullet("19-35 分钟长视频对新账号是重成本壁垒"));
children.push(bullet("\"一口气了解 XX\" 品牌 prefix 需要先有品牌"));
children.push(bullet("宏观经济题材对程序员受众错配"));
children.push(spacer());
children.push(p("死路 3: 抄巫师模式 (题材出圈追全民热点)", { size: 22, bold: true, color: "C00000", after: 80 }));
children.push(bullet("蹭全民话题 (杨幂/春晚/关税) 和 35+ 程序员受众完全错配"));
children.push(bullet("限流风险高 (敏感话题为主)"));

// Section 7: 风险
children.push(p("7. 关键风险 (诚实交代)", { size: 28, bold: true, color: "2E75B6", before: 240, after: 120 }));
children.push(p("风险 1: 可抄作业不一定真的驱动爆款", { size: 22, bold: true, after: 80 }));
children.push(p("4/4 头部都不做 + 受众在求 = 强信号, 但没有任何账号验证过\"可抄作业能驱动爆款\"。这是 hypothesis 不是事实。", { after: 80 }));
children.push(p("缓解: 第一期同时用 C1+C6+C7 (头部已验证有效) + C9 (差异化), C9 是\"加分项\"不是单一依赖。", { italics: true, color: "666666", after: 160 }));

children.push(p("风险 2: 实操赛道可能真的撑不起头部播放量", { size: 22, bold: true, after: 80 }));
children.push(p("4/4 反向 C7 可能不是\"留下空白\", 而是\"实操内容撑不起头部播放量\"。Mason 的实操定位可能只能做到中腰。", { after: 80 }));
children.push(p("缓解: 中腰播放 (10-50 万) 配合高充电率 + 真实粘性, 商业价值可能优于头部播放量。", { italics: true, color: "666666", after: 160 }));

children.push(p("风险 3: 我没有 spot check 过 subagent 打分准确性", { size: 22, bold: true, after: 80 }));
children.push(p("F 对比的可信度上限 = subagent 打分准确率, 而我没有验证。如果 30% 打分错误, \"4/4 共性\"可能是幻觉。", { after: 80 }));
children.push(p("缓解: 在执行 P0 之前, 建议抽 5-10 条 BV 让 Mason 自己 spot check (尤其是 C9 \"是否真的不提供可抄作业\")。", { italics: true, color: "666666", after: 160 }));

// Section 8: 4 个 P0 决策
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(p("8. Mason 需要回答的 4 个 P0 决策", { size: 28, bold: true, color: "2E75B6", before: 0, after: 120 }));
children.push(p("回答完以下 4 个问题, AI 可立即帮你写第一期 Growth Memo 脚本 + 准备可抄作业模板。", { italics: true, color: "666666", after: 200 }));

children.push(p("决策 1: 内容形态选择", { size: 22, bold: true, after: 80 }));
children.push(table(
  [1500, 1500, 1500, 4860],
  ["选项", "时长", "频次", "数据支撑"],
  [
    ["A ★ 推荐", "3-8 min", "2/周", "头部退出实操赛道留下空白; 短视频更易承载\"实操+可抄\"组合; 鱼皮 Top 12 平均 8 分钟"],
    ["B", "10-20 min", "1/周", "巫师 Top 12 平均 18 分钟; 但需要更深的内容力"],
    ["C", "20+ min", "2/月", "小Lin 说模式; 重成本壁垒, 不建议"],
  ]
));
children.push(spacer());

children.push(p("决策 2: 第一期主题", { size: 22, bold: true, after: 80 }));
children.push(p("从第 5 节的 3 个候选题材里选 1 个, 或自定:", { after: 80 }));
children.push(num("\"Cursor 一周吃我 1000 万 token\" — 工具实战 + 成本焦虑 (推荐)"));
children.push(num("\"30 天用 Claude Code 做 9 个项目\" — 副业变现"));
children.push(num("\"12 个 AI 工具替代 3 个员工\" — Solopreneur 工具栈"));
children.push(num("自定题目 (但要全 PASS C1+C2+C6+C7+C9 五连)"));
children.push(spacer());

children.push(p("决策 3: 可抄作业的形态", { size: 22, bold: true, after: 80 }));
children.push(table(
  [3000, 3180, 3180],
  ["形态", "优点", "缺点"],
  [
    ["Notion 模板", "易分享, 易复刻", "受众需要懂 Notion"],
    ["GitHub 源码", "程序员熟悉", "实操门槛较高"],
    ["Prompt 配置 (markdown)", "立刻可用", "内容相对薄"],
    ["PRD 文档", "高价值, 可深度展示", "写作工作量大"],
    ["完整工具清单", "低成本, 高可复刻", "内容较浅"],
  ]
));
children.push(p("★ 建议: 第一期用 Notion 模板 + Prompt 配置 + 工具清单 三件套 (低成本高复刻), 验证可抄作业是否真的驱动充电/关注。", { color: "C00000", bold: true, after: 200 }));

children.push(p("决策 4: 是否等 P3 Tier 2/3 验证再开始?", { size: 22, bold: true, after: 80 }));
children.push(table(
  [2000, 7360],
  ["选项", "说明"],
  [
    ["A ★ 推荐", "跳过 P3, 直接用 4 Tier 1 数据开始做 Growth Memo (今晚就能动手)"],
    ["B", "等 API 恢复后补完 6 个 Tier 2/3 账号 hook 分析 (再花半天到一天), 验证差异化定位是否真的\"无人占据\""],
  ]
));
children.push(p("理由: P3 是 sanity check 不是 blocking。即便有人在做 C9, 也只是少数, 不影响 Mason 入场。先试爆款公式, 后做体系化验证。", { italics: true, color: "666666", after: 160 }));

// Footer / 文件指针
children.push(p("─".repeat(40), { color: "CCCCCC", after: 80 }));
children.push(p("完整数据和分析在以下文件:", { size: 18, color: "666666", after: 60 }));
children.push(bulletRich([{ text: "F_comparison.md", bold: true }, " — 4 账号 × 9-15 维度横向矩阵 + 4/4 共性发现"]));
children.push(bulletRich([{ text: "mason_track_decision.md", bold: true }, " — Mason 赛道决策完整版 (含 8 节)"]));
children.push(bulletRich([{ text: "preset_iteration_proposal.md", bold: true }, " — preset 体系拆分提案 (4 个新 preset 方向)"]));
children.push(bulletRich([{ text: "tier1-*/analysis/patterns.md", bold: true }, " — 4 个账号各自的规律提炼"]));
children.push(p("位置: accounts/growth-memo/content/test-001/assets/reference/batch-2026-04/", { size: 18, color: "666666", after: 60 }));

// ----- Document -----
const doc = new Document({
  creator: "Claude",
  title: "Batch Recon 2026-04 Executive Summary",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "2E75B6" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "2E75B6" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } } }
        ] },
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } }
        ] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_WIDTH, height: PAGE_HEIGHT },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN }
      }
    },
    children
  }]
});

const outPath = path.join(__dirname, "Executive_Summary.docx");
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("Wrote:", outPath, `(${buffer.length} bytes, ${children.length} top-level elements)`);
});
