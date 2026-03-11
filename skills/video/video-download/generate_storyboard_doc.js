/**
 * 分镜脚本文档生成器（Director's Storyboard）
 *
 * 将 shooting_script.json 转化为可审核的 .docx 分镜文档。
 * 包含：活动上下文 + 产品信息 + AI分镜图 + 逐镜详情。
 *
 * 用法：
 *   node generate_storyboard_doc.js <shooting_script.json> <output.docx> \
 *     [--storyboard-dir <dir>] [--products <product_recommendations.json>] \
 *     [--project <project.json>]
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak, ImageRun,
} = require("docx");

// ═══════════════════════════════════════════
// CLI args
// ═══════════════════════════════════════════
const args = process.argv.slice(2);
let inputPath, outputPath = "storyboard.docx";
let storyboardDir, productsPath, projectPath;

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--storyboard-dir") { storyboardDir = args[++i]; continue; }
  if (args[i] === "--products") { productsPath = args[++i]; continue; }
  if (args[i] === "--project") { projectPath = args[++i]; continue; }
  if (!inputPath) { inputPath = args[i]; continue; }
  outputPath = args[i];
}

if (!inputPath) {
  console.error("Usage: node generate_storyboard_doc.js <script.json> [output.docx] [--storyboard-dir dir] [--products recs.json] [--project project.json]");
  process.exit(1);
}

// ═══════════════════════════════════════════
// Design system
// ═══════════════════════════════════════════
const C = {
  dark: "1A1A2E", primary: "2C3E50", accent: "C0926F",
  beige: "E8D5C4", cream: "FDF8F4", white: "FFFFFF",
  text: "333333", muted: "999999", border: "D5C4B3",
  hook: "E74C3C", transition: "F39C12", demo: "27AE60",
  effect: "3498DB", cta: "9B59B6",
  hookBg: "FDEDED", transitionBg: "FEF9E7",
  demoBg: "EAFAF1", effectBg: "EBF5FB",
};

const SEG_STYLE = {
  "hook":     { color: C.hook,       bg: C.hookBg,       label: "HOOK" },
  "过渡":     { color: C.transition, bg: C.transitionBg, label: "过渡" },
  "使用演示": { color: C.demo,       bg: C.demoBg,       label: "演示" },
  "产品介绍": { color: C.demo,       bg: C.demoBg,       label: "演示" },
  "效果展示": { color: C.effect,     bg: C.effectBg,     label: "效果" },
  "互动引导": { color: C.cta,        bg: "F5EEF8",       label: "CTA" },
  "outro":    { color: C.cta,        bg: "F5EEF8",       label: "CTA" },
};

const thin = { style: BorderStyle.SINGLE, size: 1, color: C.border };
const borders = { top: thin, bottom: thin, left: thin, right: thin };
const noBorder = { style: BorderStyle.NONE, size: 0 };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
const pad = { top: 60, bottom: 60, left: 100, right: 100 };
const padWide = { top: 80, bottom: 80, left: 120, right: 120 };
const W = 9360;

// ═══════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════
function txt(text, opts = {}) {
  return new TextRun({
    text: String(text || ""), font: "Arial", size: opts.size || 18,
    bold: opts.bold || false, italics: opts.italics || false,
    color: opts.color || C.text,
  });
}

function para(runs, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { before: opts.before || 0, after: opts.after || 40, line: opts.line || 264 },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    children: Array.isArray(runs) ? runs : [runs],
  });
}

function labelValueRow(label, value, labelWidth) {
  return new TableRow({ children: [
    new TableCell({ borders: noBorders, width: { size: labelWidth, type: WidthType.DXA }, margins: pad,
      children: [para(txt(label, { size: 16, bold: true, color: C.accent }))] }),
    new TableCell({ borders: noBorders, width: { size: W - labelWidth, type: WidthType.DXA }, margins: pad,
      children: [para(txt(value, { size: 16 }))] }),
  ]});
}

function detailBlock(label, value, width, opts = {}) {
  return new TableCell({
    borders: { top: thin, bottom: thin,
      left: opts.accentBorder ? { style: BorderStyle.SINGLE, size: 8, color: opts.accentBorder } : thin,
      right: thin },
    width: { size: width, type: WidthType.DXA }, margins: padWide,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [
      para(txt(label, { size: 14, bold: true, color: C.accent }), { after: 20 }),
      para(txt(value, { size: 16 }), { after: 0 }),
    ]
  });
}

function fmtTime(sec) {
  return `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
}

function findShotImage(shotIndex, shotType) {
  if (!storyboardDir) return null;
  const safeType = (shotType || "unknown").replace(/\//g, "_");
  const num = String(shotIndex).padStart(3, "0");
  const candidate = path.join(storyboardDir, `shot_${num}_${safeType}.png`);
  if (fs.existsSync(candidate)) return candidate;
  // Fallback: glob for shot_NNN_*.png
  try {
    const files = fs.readdirSync(storyboardDir).filter(f => f.startsWith(`shot_${num}_`) && f.endsWith(".png"));
    if (files.length > 0) return path.join(storyboardDir, files[0]);
  } catch (e) {}
  return null;
}

// ═══════════════════════════════════════════
// Load data
// ═══════════════════════════════════════════
const script = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
const meta = script.script_metadata || {};
const gpn = script.global_production_notes || {};

const proj = projectPath && fs.existsSync(projectPath)
  ? JSON.parse(fs.readFileSync(projectPath, "utf-8")) : {};

const products = productsPath && fs.existsSync(productsPath)
  ? JSON.parse(fs.readFileSync(productsPath, "utf-8")) : [];

// Flatten shots
const shots = [];
let cumulSec = 0;
for (const seg of (script.segments || [])) {
  for (const shot of (seg.shots || [])) {
    const dur = shot.duration_seconds || 5;
    const startSec = cumulSec;
    cumulSec += dur;
    shots.push({
      ...shot, segType: seg.segment_type || "unknown",
      segFunction: seg.segment_function || "", dur, startSec, endSec: cumulSec,
      time: `${fmtTime(startSec)}\u2013${fmtTime(cumulSec)}`,
      cumul: `${startSec}\u2013${cumulSec}s`,
    });
  }
}

let imageCount = 0;
const children = [];

// ──── PAGE 1: COVER + 活动上下文 ────
children.push(
  new Paragraph({ spacing: { before: 2400 } }),
  para(txt("\u5206 \u955C \u811A \u672C", { size: 60, bold: true, color: C.dark }), { align: AlignmentType.CENTER, after: 80 }),
  para(txt("STORYBOARD", { size: 22, color: C.muted }), { align: AlignmentType.CENTER, after: 400 }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.accent, space: 8 } }, children: [] }),
  para(txt(proj.topic || meta.content_type || "\u77ED\u89C6\u9891", { size: 40, bold: true, color: C.primary }), { align: AlignmentType.CENTER, after: 80 }),
  para(txt(meta.brand || "\u7D20\u4EC1\u8F69", { size: 24, color: C.accent }), { align: AlignmentType.CENTER, after: 600 }),
);

const lw = 2200;
const infoRows = [
  ["\u9009\u9898", proj.topic || meta.content_type || ""],
  ["\u53C2\u7167\u89C6\u9891", proj.reference_video_url || "\u672A\u6307\u5B9A"],
  ["\u53C2\u7167\u5E73\u53F0", proj.reference_platform || ""],
  ["\u76EE\u6807\u5E73\u53F0", (proj.target_platforms || []).join(", ") || meta.target_platform || "\u5C0F\u7EA2\u4E66"],
  ["\u54C1\u724C", meta.brand || ""],
  ["\u89C6\u9891\u7C7B\u578B", meta.content_type || ""],
  ["\u65F6\u957F / \u6BD4\u4F8B", `${meta.target_video_duration || meta.source_video_duration || ""} | ${meta.aspect_ratio || "9:16"}`],
  ["\u66FF\u6362\u6A21\u5F0F", meta.replacement_mode === "cross_category" ? "\u8DE8\u54C1\u7C7B" : "\u540C\u54C1\u7C7B"],
  ["\u603B\u955C\u5934\u6570", `${shots.length} shots / ${meta.total_segments || script.segments?.length || 0} segments`],
];
if (proj.notes) infoRows.push(["\u5907\u6CE8", proj.notes]);

children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [lw, W - lw],
  rows: infoRows.map(r => labelValueRow(r[0], r[1], lw)),
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── PAGE 2: 产品信息 ────
if (products.length > 0) {
  children.push(
    para(txt("\u63A8\u8350\u4EA7\u54C1", { size: 28, bold: true, color: C.dark }), { after: 60 }),
    para(txt("\u4EA7\u54C1\u5339\u914D\u7ED3\u679C\uFF08\u6765\u81EA match \u6B65\u9AA4\uFF09\u3002\u7B2C 1 \u540D\u5DF2\u81EA\u52A8\u5E94\u7528\u5230\u811A\u672C\uFF0CMason \u53EF\u624B\u52A8\u66FF\u6362\u3002", { size: 16, color: C.muted }), { after: 200 }),
  );

  const pColW = [400, 2600, 1200, 1600, 1800, 1760];
  children.push(new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: pColW,
    rows: [
      new TableRow({ children: ["#", "\u4EA7\u54C1\u540D", "\u54C1\u724C", "\u4EF7\u683C", "\u5356\u70B9", "\u5339\u914D\u7406\u7531"].map((h, i) =>
        new TableCell({ borders, width: { size: pColW[i], type: WidthType.DXA },
          shading: { fill: C.dark, type: ShadingType.CLEAR }, margins: pad,
          children: [para(txt(h, { size: 14, bold: true, color: C.white }), { align: AlignmentType.CENTER, after: 0 })]
        })
      )}),
      ...products.map((p, i) => {
        const isTop = i === 0;
        return new TableRow({ children: [
          new TableCell({ borders, width: { size: pColW[0], type: WidthType.DXA }, margins: pad,
            shading: isTop ? { fill: C.demoBg, type: ShadingType.CLEAR } : undefined,
            children: [para(txt(`${p.rank || i + 1}`, { size: 16, bold: true }), { align: AlignmentType.CENTER, after: 0 })] }),
          new TableCell({ borders, width: { size: pColW[1], type: WidthType.DXA }, margins: pad,
            shading: isTop ? { fill: C.demoBg, type: ShadingType.CLEAR } : undefined,
            children: [para(txt(p.product_name || "", { size: 15, bold: isTop }), { after: 0 })] }),
          new TableCell({ borders, width: { size: pColW[2], type: WidthType.DXA }, margins: pad,
            children: [para(txt(p.brand || "", { size: 14 }), { align: AlignmentType.CENTER, after: 0 })] }),
          new TableCell({ borders, width: { size: pColW[3], type: WidthType.DXA }, margins: pad,
            children: [para(txt(p.actual_retail_price ? `\xA5${p.actual_retail_price}` : (p.price_signal || ""), { size: 14 }), { align: AlignmentType.CENTER, after: 0 })] }),
          new TableCell({ borders, width: { size: pColW[4], type: WidthType.DXA }, margins: pad,
            children: [para(txt(p.core_selling_point || "", { size: 13 }), { after: 0 })] }),
          new TableCell({ borders, width: { size: pColW[5], type: WidthType.DXA }, margins: pad,
            children: [para(txt(p.reasoning || "", { size: 13 }), { after: 0 })] }),
        ]});
      })
    ]
  }));

  // Product details for top pick
  const top = products[0];
  if (top) {
    children.push(
      para(txt(""), { after: 100 }),
      para(txt(`\u2605 \u5F53\u524D\u4F7F\u7528: ${top.product_name || ""}`, { size: 18, bold: true, color: C.demo }), { after: 40 }),
      para(txt(`\u6F14\u793A\u52A8\u4F5C: ${top.demo_action || ""}`, { size: 16 }), { after: 20 }),
      para(txt(`\u76EE\u6807\u808C\u80A4: ${(top.target_concerns || []).join("\u3001") || ""}`, { size: 16 }), { after: 20 }),
      para(txt(`\u5E93\u5B58: ${top.stock || "\u672A\u77E5"} | \u4F18\u5148\u7EA7: ${top.priority || ""}`, { size: 14, color: C.muted }), { after: 0 }),
    );
  }

  children.push(new Paragraph({ children: [new PageBreak()] }));
}

// ──── PAGE 3: TIMELINE OVERVIEW ────
children.push(
  para(txt("Timeline Overview", { size: 28, bold: true, color: C.dark }), { after: 60 }),
  para(txt("\u4E00\u7F51\u6253\u5C3D\u6BCF\u4E2A\u955C\u5934\u7684\u65F6\u95F4\u5206\u914D\u548C\u6838\u5FC3\u5185\u5BB9\u3002\u5F69\u8272\u6807\u8BB0 = \u6BB5\u843D\u7C7B\u578B\u3002", { size: 16, color: C.muted }), { after: 200 }),
);

const tlColW = [600, 900, 1100, 1100, 2200, 3460];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: tlColW,
  rows: [
    new TableRow({ children: ["#", "\u65F6\u95F4", "\u7C7B\u578B", "\u666F\u522B", "\u53E3\u64AD\u6458\u8981", "\u753B\u9762\u6982\u8FF0"].map((h, i) =>
      new TableCell({ borders, width: { size: tlColW[i], type: WidthType.DXA },
        shading: { fill: C.dark, type: ShadingType.CLEAR }, margins: pad,
        children: [para(txt(h, { size: 15, bold: true, color: C.white }), { align: AlignmentType.CENTER, after: 0 })]
      })
    )}),
    ...shots.map(s => {
      const style = SEG_STYLE[s.segType] || { color: C.muted, bg: C.cream, label: s.segType };
      const vo = (s.voiceover || "").substring(0, 25) + (s.voiceover && s.voiceover.length > 25 ? "\u2026" : "");
      const fd = (s.frame_description || "").substring(0, 50) + (s.frame_description && s.frame_description.length > 50 ? "\u2026" : "");
      return new TableRow({ children: [
        new TableCell({ borders, width: { size: tlColW[0], type: WidthType.DXA }, margins: pad,
          children: [para(txt(`${s.shot_index}`, { size: 16, bold: true }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[1], type: WidthType.DXA }, margins: pad,
          children: [para(txt(`${s.dur}s`, { size: 14 }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[2], type: WidthType.DXA }, margins: pad,
          shading: { fill: style.bg, type: ShadingType.CLEAR },
          children: [para(txt(style.label, { size: 14, bold: true, color: style.color }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[3], type: WidthType.DXA }, margins: pad,
          children: [para(txt(s.shot_type || "", { size: 14 }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[4], type: WidthType.DXA }, margins: pad,
          children: [para(txt(vo, { size: 14 }), { after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[5], type: WidthType.DXA }, margins: pad,
          children: [para(txt(fd, { size: 14 }), { after: 0 })] }),
      ]});
    })
  ]
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── SHOT PAGES ────
shots.forEach((s, idx) => {
  const style = SEG_STYLE[s.segType] || { color: C.muted, bg: C.cream, label: s.segType };

  children.push(para([
    txt(`  SHOT #${s.shot_index}`, { size: 24, bold: true, color: C.white }),
    txt(`     ${style.label}`, { size: 20, bold: true, color: style.color }),
    txt(`     ${s.time}  (${s.dur}s)`, { size: 18, color: C.beige }),
    txt(`     \u7D2F\u8BA1: ${s.cumul}`, { size: 16, color: C.muted }),
  ], { after: 120, shading: C.dark }));

  // 4-column grid: Row1 = A(col1-2 merged) + B(col3-4 merged), Row2 = C1+C2+D1+D2
  const qW = Math.floor(W / 4);  // each quarter ~2340 DXA
  const halfW = qW * 2;           // each half ~4680 DXA

  // Check for storyboard image
  const imgPath = findShotImage(s.shot_index, s.shot_type);
  let imgChildren;

  if (imgPath) {
    imageCount++;
    const imgData = fs.readFileSync(imgPath);
    imgChildren = [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 80, after: 40 },
        children: [new ImageRun({ data: imgData, transformation: { width: 280, height: 498 }, type: "png" })],
      }),
      para(txt(`Shot #${s.shot_index}`, { size: 12, color: C.muted }), { align: AlignmentType.CENTER, after: 0 }),
    ];
  } else {
    imgChildren = [
      para(txt("\uD83C\uDFAC", { size: 52 }), { align: AlignmentType.CENTER, before: 400, after: 60 }),
      para(txt("\u5206\u955C\u9884\u89C8\u56FE", { size: 18, bold: true, color: C.muted }), { align: AlignmentType.CENTER, after: 40 }),
      para(txt("9:16 \u7AD6\u7248", { size: 14, color: C.muted }), { align: AlignmentType.CENTER, after: 40 }),
      para(txt(`[\u5206\u955C\u56FE #${s.shot_index}]`, { size: 13, italics: true, color: C.accent }), { align: AlignmentType.CENTER, after: 400 }),
    ];
  }

  children.push(new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: [qW, qW, qW, W - qW * 3],
    rows: [
      // Row 1: A (image, colspan=2) + B (details, colspan=2)
      new TableRow({ children: [
        new TableCell({
          columnSpan: 2,
          borders: { ...borders, left: { style: BorderStyle.SINGLE, size: 8, color: style.color } },
          width: { size: halfW, type: WidthType.DXA },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          shading: { fill: "F8F8F8", type: ShadingType.CLEAR },
          verticalAlign: VerticalAlign.CENTER,
          children: imgChildren,
        }),
        new TableCell({
          columnSpan: 2,
          borders, width: { size: halfW, type: WidthType.DXA }, margins: padWide,
          children: [
            para(txt("\uD83C\uDFA8 \u753B\u9762\u63CF\u8FF0", { size: 16, bold: true, color: C.primary }), { before: 40, after: 40 }),
            para(txt(`\u52A8\u4F5C\uFF1A${s.frame_description || ""}`, { size: 15 }), { after: 20 }),
            para(txt(`\u5149\u7EBF\uFF1A${s.lighting_note || "\u540C\u5168\u5C40"}`, { size: 15 }), { after: 20 }),
            para(txt(`\u6C1B\u56F4\uFF1A${s.acting_direction ? s.acting_direction.split("\uFF0C")[0] : "\u81EA\u7136"}`, { size: 15 }), { after: 60 }),

            para(txt("\uD83C\uDFA5 \u955C\u5934\u8BED\u8A00", { size: 16, bold: true, color: C.primary }), { after: 40 }),
            para(txt(`${s.shot_type || ""} | ${s.camera_movement || "\u56FA\u5B9A"} | \u8F6C\u573A: \u76F4\u5207`, { size: 15 }), { after: 60 }),

            para(txt("\uD83C\uDF99 \u5185\u5BB9 / \u53F0\u8BCD", { size: 16, bold: true, color: C.primary }), { after: 40 }),
            para(txt(`\u53E3\u64AD\uFF1A\u201C${s.voiceover || ""}\u201D`, { size: 15, italics: true }), { after: 20 }),
            para(txt(`\u5C4F\u5E55\u6587\u5B57\uFF1A${s.text_overlay || "\u65E0"}`, { size: 15 }), { after: 20 }),
            para(txt(`\u8868\u6F14\u6307\u5BFC\uFF1A${s.acting_direction || "\u81EA\u7136"}`, { size: 15 }), { after: 60 }),

            para(txt("\uD83C\uDFB5 \u58F0\u97F3\u8BBE\u8BA1", { size: 16, bold: true, color: C.primary }), { after: 40 }),
            para(txt(`${s.audio_note || "\u540C\u5168\u5C40BGM"}`, { size: 15 }), { after: 20 }),
          ]
        }),
      ]}),
      // Row 2: C1(道具) + C2(服装) + D1(表演指导) + D2(后期备注)
      new TableRow({ children: [
        detailBlock("\uD83E\uDDF0 \u9053\u5177", s.props || "\u65E0", qW, { fill: C.cream }),
        detailBlock("\uD83D\uDC57 \u670D\u88C5", gpn.wardrobe ? gpn.wardrobe.substring(0, 30) : "\u89C1\u5168\u5C40", qW, { fill: C.cream }),
        detailBlock("\uD83C\uDFAD \u8868\u6F14\u6307\u5BFC", s.acting_direction || "\u81EA\u7136", qW, { fill: C.cream }),
        detailBlock("\u2702 \u540E\u671F\u5907\u6CE8", s.audio_note || "\u65E0\u7279\u6B8A", W - qW * 3, { fill: C.cream }),
      ]}),
    ]
  }));

  if (idx < shots.length - 1) children.push(new Paragraph({ children: [new PageBreak()] }));
});
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── VOICEOVER SCRIPT ────
children.push(
  para(txt("\u5B8C\u6574\u53E3\u64AD\u7A3F", { size: 28, bold: true, color: C.dark }), { after: 60 }),
  para(txt("\u535A\u4E3B\u62CD\u6444\u524D\u901A\u8BFB 2\u20133 \u904D\u3002\u6807\u8BB0 [#N] \u5BF9\u5E94\u955C\u5934\u7F16\u53F7\u3002", { size: 16, color: C.muted }), { after: 200 }),
);

if (script.voiceover_full_script) {
  children.push(para(txt(script.voiceover_full_script, { size: 20 }), { after: 200, line: 320 }));
  children.push(para(txt("\u2500\u2500 \u9010\u955C\u53E3\u64AD \u2500\u2500", { size: 16, bold: true, color: C.accent }), { before: 200, after: 120 }));
}

shots.forEach(s => {
  const style = SEG_STYLE[s.segType] || { color: C.muted };
  children.push(
    para(txt(`[#${s.shot_index} ${(SEG_STYLE[s.segType] || {}).label || s.segType} ${s.time}]`, { size: 14, bold: true, color: style.color }), { before: 160, after: 40 }),
    para(txt(s.voiceover || "", { size: 20 }), { after: 80, line: 320 }),
  );
});
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── PROPS CHECKLIST ────
children.push(para(txt("\u9053\u5177\u6E05\u5355", { size: 28, bold: true, color: C.dark }), { after: 200 }));

const propsList = [];
if (gpn.props_checklist) {
  const checklist = Array.isArray(gpn.props_checklist) ? gpn.props_checklist : gpn.props_checklist.split(/[、,，\n]/);
  checklist.forEach(p => { if (p && p.trim()) propsList.push([p.trim(), "1", ""]); });
} else {
  const allProps = new Set();
  shots.forEach(s => {
    if (s.props && s.props !== "\u65E0") s.props.split(/[、,，]/).forEach(p => { if (p.trim()) allProps.add(p.trim()); });
  });
  [...allProps].forEach(p => propsList.push([p, "1", ""]));
}

const pColW2 = [500, 3000, 1000, 4860];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: pColW2,
  rows: [
    new TableRow({ children: ["\u2610", "\u9053\u5177", "\u6570\u91CF", "\u5907\u6CE8"].map((h, i) =>
      new TableCell({ borders, width: { size: pColW2[i], type: WidthType.DXA },
        shading: { fill: C.dark, type: ShadingType.CLEAR }, margins: pad,
        children: [para(txt(h, { size: 15, bold: true, color: C.white }), { align: AlignmentType.CENTER, after: 0 })]
      })
    )}),
    ...propsList.map((p, i) => new TableRow({ children: [
      new TableCell({ borders, width: { size: pColW2[0], type: WidthType.DXA }, margins: pad,
        children: [para(txt("\u2610", { size: 18 }), { align: AlignmentType.CENTER, after: 0 })] }),
      new TableCell({ borders, width: { size: pColW2[1], type: WidthType.DXA }, margins: pad,
        shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
        children: [para(txt(p[0], { size: 16, bold: true }), { after: 0 })] }),
      new TableCell({ borders, width: { size: pColW2[2], type: WidthType.DXA }, margins: pad,
        shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
        children: [para(txt(p[1], { size: 16 }), { align: AlignmentType.CENTER, after: 0 })] }),
      new TableCell({ borders, width: { size: pColW2[3], type: WidthType.DXA }, margins: pad,
        shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
        children: [para(txt(p[2], { size: 16 }), { after: 0 })] }),
    ]}))
  ]
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── PRODUCTION NOTES ────
children.push(para(txt("\u62CD\u6444\u5236\u4F5C\u5907\u6CE8", { size: 28, bold: true, color: C.dark }), { after: 200 }));

const notes = [
  ["\uD83C\uDFE0 \u573A\u5730", gpn.location || "\u5BA4\u5185"],
  ["\uD83D\uDCA1 \u706F\u5149", gpn.lighting_setup || "\u81EA\u7136\u5149+\u8865\u5149\u706F"],
  ["\uD83C\uDFB5 BGM", gpn.bgm_suggestion || "\u8F7B\u5FEB\u97E9\u7CFB\u98CE\u683C"],
  ["\u2702 \u526A\u8F91", gpn.editing_notes || "\u4E2D\u901F\u8282\u594F"],
  ["\uD83D\uDC57 \u670D\u88C5", gpn.wardrobe || "\u89C1\u89D2\u8272\u8BBE\u5B9A"],
  ["\uD83D\uDCDD \u5B57\u5E55", "\u7B80\u6D01\u767D\u8272\u5B57\u4F53\uFF0C\u5E95\u90E8\u5C45\u4E2D\u3002\u6B65\u9AA4\u7F16\u53F7\u7528\u52A0\u7C97\u3002\u4E0D\u7528\u82B1\u54E8\u8D34\u7EB8\u3002"],
  ["\uD83C\uDFA8 \u8272\u8C03", "\u6E29\u6696\u81EA\u7136\uFF0C\u4E0D\u7528\u51B7\u767D\u97E9\u7CFB\u6EE4\u955C\u3002\u8F7B\u5FAE\u63D0\u4EAE\uFF0C\u4E0D\u8FC7\u5EA6\u4FEE\u56FE\u3002"],
  ["\u26A0\uFE0F \u5408\u89C4", '\u53E3\u64AD\u7981\u7528\uFF1A\u7F8E\u767D/\u7960\u75D8/\u7960\u6591/\u6297\u8870\u8001/\u6CBB\u7597\u3002\u79F0\u547C\u7528\u201C\u59D0\u59B9\u201D\u3002\u4E0D\u62A5\u7CBE\u786E\u4EF7\u683C\u3002'],
  ["\u23F1 \u9884\u4F30", gpn.estimated_raw_footage || "15-20\u5206\u949F\u539F\u59CB\u7D20\u6750"],
];

const nW = [2000, 7360];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: nW,
  rows: notes.map((n, i) => new TableRow({ children: [
    new TableCell({ borders, width: { size: nW[0], type: WidthType.DXA },
      shading: { fill: C.beige, type: ShadingType.CLEAR }, margins: padWide,
      children: [para(txt(n[0], { size: 16, bold: true }), { after: 0 })] }),
    new TableCell({ borders, width: { size: nW[1], type: WidthType.DXA },
      shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined, margins: padWide,
      children: [para(txt(n[1], { size: 16 }), { after: 0 })] }),
  ]}))
}));

// ═══════════════════════════════════════════
// BUILD & EXPORT
// ═══════════════════════════════════════════
const doc = new Document({
  styles: { default: { document: { run: { font: "Arial", size: 18 } } } },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 900, right: 1440, bottom: 900, left: 1440 } }
    },
    headers: { default: new Header({ children: [
      para([txt(`${meta.brand || "\u7D20\u4EC1\u8F69"} | ${proj.topic || meta.content_type || ""} | v1.0`, { size: 14, color: C.muted })], { align: AlignmentType.RIGHT, after: 0 })
    ]})},
    footers: { default: new Footer({ children: [
      para([txt("Page ", { size: 14, color: C.muted }), new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 14, color: C.muted })], { align: AlignmentType.CENTER, after: 0 })
    ]})},
    children,
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  const pages = 1 + (products.length > 0 ? 1 : 0) + 1 + shots.length + 3;
  console.log(`Generated: ${outputPath} (${(buffer.length / 1024).toFixed(0)}KB, ${shots.length} shots, ${imageCount} images, ${pages} pages)`);
});
