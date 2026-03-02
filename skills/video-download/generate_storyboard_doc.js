/**
 * 分镜脚本文档生成器（Director's Storyboard）
 *
 * 将 shooting_script.json 转化为可审核的 .docx 分镜文档。
 * Mason 只看这个文档就能完成审核。
 *
 * 用法：node generate_storyboard_doc.js <shooting_script.json> [output.docx]
 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak,
} = require("docx");

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
const W = 9360; // content width

// ═══════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════
function txt(text, opts = {}) {
  return new TextRun({
    text: String(text || ""),
    font: "Arial",
    size: opts.size || 18,
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || C.text,
  });
}

function para(runs, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { before: opts.before || 0, after: opts.after || 40, line: opts.line || 264 },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    border: opts.border || undefined,
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
    width: { size: width, type: WidthType.DXA },
    margins: padWide,
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

// ═══════════════════════════════════════════
// Main
// ═══════════════════════════════════════════
const inputPath = process.argv[2];
const outputPath = process.argv[3] || "storyboard.docx";

if (!inputPath) {
  console.error("Usage: node generate_storyboard_doc.js <shooting_script.json> [output.docx]");
  process.exit(1);
}

const script = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
const meta = script.script_metadata || {};
const gpn = script.global_production_notes || {};

// Flatten shots with segment info
const shots = [];
let cumulSec = 0;
for (const seg of (script.segments || [])) {
  for (const shot of (seg.shots || [])) {
    const dur = shot.duration_seconds || 5;
    const startSec = cumulSec;
    cumulSec += dur;
    shots.push({
      ...shot,
      segType: seg.segment_type || "unknown",
      segFunction: seg.segment_function || "",
      dur,
      startSec,
      endSec: cumulSec,
      time: `${fmtTime(startSec)}–${fmtTime(cumulSec)}`,
      cumul: `${startSec}–${cumulSec}s`,
    });
  }
}

const children = [];

// ──── PAGE 1: COVER ────
children.push(
  new Paragraph({ spacing: { before: 2400 } }),
  para(txt("分 镜 脚 本", { size: 60, bold: true, color: C.dark }), { align: AlignmentType.CENTER, after: 80 }),
  para(txt("STORYBOARD", { size: 22, color: C.muted }), { align: AlignmentType.CENTER, after: 400 }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.accent, space: 8 } }, children: [] }),
  para(txt(meta.content_type || "短视频", { size: 40, bold: true, color: C.primary }), { align: AlignmentType.CENTER, after: 80 }),
  para(txt(meta.brand || "素仁轩", { size: 24, color: C.accent }), { align: AlignmentType.CENTER, after: 600 }),
);

const lw = 1800;
const infoRows = [
  ["视频类型", meta.content_type || ""],
  ["时长 / 比例", `${meta.target_video_duration || meta.source_video_duration || ""} | ${meta.aspect_ratio || "9:16"}`],
  ["目标平台", meta.target_platform || "小红书"],
  ["品牌", meta.brand || ""],
  ["替换模式", meta.replacement_mode === "cross_category" ? "跨品类" : "同品类"],
  ["总镜头数", `${shots.length} shots / ${meta.total_segments || script.segments?.length || 0} segments`],
];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [lw, W - lw],
  rows: infoRows.map(r => labelValueRow(r[0], r[1], lw)),
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── PAGE 2: TIMELINE OVERVIEW ────
children.push(
  para(txt("Timeline Overview", { size: 28, bold: true, color: C.dark }), { after: 60 }),
  para(txt("一网打尽每个镜头的时间分配和核心内容。彩色标记 = 段落类型。", { size: 16, color: C.muted }), { after: 200 }),
);

const tlColW = [600, 900, 1100, 1100, 2200, 3460];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: tlColW,
  rows: [
    new TableRow({ children: ["#", "时间", "类型", "景别", "口播摘要", "画面概述"].map((h, i) =>
      new TableCell({ borders, width: { size: tlColW[i], type: WidthType.DXA },
        shading: { fill: C.dark, type: ShadingType.CLEAR }, margins: pad,
        children: [para(txt(h, { size: 15, bold: true, color: C.white }), { align: AlignmentType.CENTER, after: 0 })]
      })
    )}),
    ...shots.map(s => {
      const style = SEG_STYLE[s.segType] || { color: C.muted, bg: C.cream, label: s.segType };
      const vo = (s.voiceover || "").substring(0, 25) + (s.voiceover && s.voiceover.length > 25 ? "..." : "");
      const fd = (s.frame_description || "").substring(0, 50) + (s.frame_description && s.frame_description.length > 50 ? "..." : "");
      return new TableRow({ children: [
        new TableCell({ borders, width: { size: tlColW[0], type: WidthType.DXA }, margins: pad,
          children: [para(txt(`${s.shot_index}`, { size: 16, bold: true }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[1], type: WidthType.DXA }, margins: pad,
          children: [para(txt(`${s.dur}s`, { size: 14 }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[2], type: WidthType.DXA }, margins: pad,
          shading: { fill: style.bg, type: ShadingType.CLEAR },
          children: [para(txt(style.label, { size: 14, bold: true, color: style.color }), { align: AlignmentType.CENTER, after: 0 })] }),
        new TableCell({ borders, width: { size: tlColW[3], type: WidthType.DXA }, margins: pad,
          children: [para(txt((s.shot_type || "").replace("/", "/"), { size: 14 }), { align: AlignmentType.CENTER, after: 0 })] }),
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

  // Header bar
  children.push(para([
    txt(`  SHOT #${s.shot_index}`, { size: 24, bold: true, color: C.white }),
    txt(`     ${style.label}`, { size: 20, bold: true, color: style.color }),
    txt(`     ${s.time}  (${s.dur}s)`, { size: 18, color: C.beige }),
    txt(`     累计: ${s.cumul}`, { size: 16, color: C.muted }),
  ], { after: 120, shading: C.dark }));

  // Main two-column
  const imgW = 3200;
  const detW = W - imgW;

  children.push(new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [imgW, detW],
    rows: [new TableRow({ children: [
      // LEFT: image placeholder
      new TableCell({
        borders: { ...borders, left: { style: BorderStyle.SINGLE, size: 8, color: style.color } },
        width: { size: imgW, type: WidthType.DXA },
        margins: { top: 120, bottom: 120, left: 120, right: 120 },
        shading: { fill: "F8F8F8", type: ShadingType.CLEAR },
        verticalAlign: VerticalAlign.CENTER,
        children: [
          para(txt("\uD83C\uDFAC", { size: 52 }), { align: AlignmentType.CENTER, before: 400, after: 60 }),
          para(txt("分镜预览图", { size: 18, bold: true, color: C.muted }), { align: AlignmentType.CENTER, after: 40 }),
          para(txt("9:16 竖版", { size: 14, color: C.muted }), { align: AlignmentType.CENTER, after: 40 }),
          para(txt(`[分镜图 #${s.shot_index} — 插入AI生成图或手绘草图]`, { size: 13, italics: true, color: C.accent }), { align: AlignmentType.CENTER, after: 400 }),
        ]
      }),
      // RIGHT: details
      new TableCell({
        borders, width: { size: detW, type: WidthType.DXA }, margins: padWide,
        children: [
          // 画面描述
          para(txt("\uD83C\uDFA8 画面描述", { size: 16, bold: true, color: C.primary }), { before: 40, after: 40 }),
          para(txt(`动作：${s.frame_description || ""}`, { size: 15 }), { after: 20 }),
          para(txt(`光线：${s.lighting_note || "同全局"}`, { size: 15 }), { after: 20 }),
          para(txt(`色调：温暖自然`, { size: 15 }), { after: 20 }),
          para(txt(`氛围：${s.acting_direction ? s.acting_direction.split("，")[0] : "自然"}`, { size: 15 }), { after: 60 }),

          // 镜头语言
          para(txt("\uD83C\uDFA5 镜头语言", { size: 16, bold: true, color: C.primary }), { after: 40 }),
          para(txt(`${s.shot_type || ""} | ${s.camera_movement || "固定"} | 转场: 直切`, { size: 15 }), { after: 60 }),

          // 内容/台词
          para(txt("\uD83C\uDF99 内容 / 台词", { size: 16, bold: true, color: C.primary }), { after: 40 }),
          para(txt(`口播："${s.voiceover || ""}"`, { size: 15, italics: true }), { after: 20 }),
          para(txt(`屏幕文字：${s.text_overlay || "无"}`, { size: 15 }), { after: 20 }),
          para(txt(`表演指导：${s.acting_direction || "自然"}`, { size: 15 }), { after: 60 }),

          // 声音设计
          para(txt("\uD83C\uDFB5 声音设计", { size: 16, bold: true, color: C.primary }), { after: 40 }),
          para(txt(`${s.audio_note || "同全局BGM"}`, { size: 15 }), { after: 20 }),
        ]
      }),
    ]})]
  }));

  // Bottom 4-col
  const qW = Math.floor(W / 4);
  children.push(new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [qW, qW, qW, W - qW * 3],
    rows: [new TableRow({ children: [
      detailBlock("\uD83E\uDDF0 道具", s.props || "无", qW, { fill: C.cream }),
      detailBlock("\uD83D\uDC57 服装", gpn.wardrobe ? gpn.wardrobe.substring(0, 30) : "见全局", qW, { fill: C.cream }),
      detailBlock("\uD83C\uDFAD 表演指导", s.acting_direction || "自然", qW, { fill: C.cream }),
      detailBlock("\u2702 后期备注", s.audio_note || "无特殊", W - qW * 3, { fill: C.cream }),
    ]})]
  }));

  if (idx < shots.length - 1) children.push(new Paragraph({ children: [new PageBreak()] }));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── VOICEOVER SCRIPT ────
children.push(
  para(txt("完整口播稿", { size: 28, bold: true, color: C.dark }), { after: 60 }),
  para(txt("博主拍摄前通读 2–3 遍。标记 [#N] 对应镜头编号。", { size: 16, color: C.muted }), { after: 200 }),
);

if (script.voiceover_full_script) {
  children.push(para(txt(script.voiceover_full_script, { size: 20 }), { after: 200, line: 320 }));
  children.push(para(txt("── 逐镜口播 ──", { size: 16, bold: true, color: C.accent }), { before: 200, after: 120 }));
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
children.push(para(txt("道具清单", { size: 28, bold: true, color: C.dark }), { after: 200 }));

// Extract props
const propsList = [];
if (gpn.props_checklist) {
  const checklist = Array.isArray(gpn.props_checklist) ? gpn.props_checklist : gpn.props_checklist.split(/[、,，\n]/);
  checklist.forEach(p => { if (p && p.trim()) propsList.push([p.trim(), "1", ""]); });
} else {
  const allProps = new Set();
  shots.forEach(s => {
    if (s.props && s.props !== "无") {
      s.props.split(/[、,，]/).forEach(p => { if (p.trim()) allProps.add(p.trim()); });
    }
  });
  [...allProps].forEach(p => propsList.push([p, "1", ""]));
}

const pColW = [500, 3000, 1000, 4860];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: pColW,
  rows: [
    new TableRow({ children: ["\u2610", "道具", "数量", "备注"].map((h, i) =>
      new TableCell({ borders, width: { size: pColW[i], type: WidthType.DXA },
        shading: { fill: C.dark, type: ShadingType.CLEAR }, margins: pad,
        children: [para(txt(h, { size: 15, bold: true, color: C.white }), { align: AlignmentType.CENTER, after: 0 })]
      })
    )}),
    ...propsList.map((p, i) => new TableRow({ children: [
      new TableCell({ borders, width: { size: pColW[0], type: WidthType.DXA }, margins: pad,
        children: [para(txt("\u2610", { size: 18 }), { align: AlignmentType.CENTER, after: 0 })] }),
      new TableCell({ borders, width: { size: pColW[1], type: WidthType.DXA }, margins: pad,
        shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
        children: [para(txt(p[0], { size: 16, bold: true }), { after: 0 })] }),
      new TableCell({ borders, width: { size: pColW[2], type: WidthType.DXA }, margins: pad,
        shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
        children: [para(txt(p[1], { size: 16 }), { align: AlignmentType.CENTER, after: 0 })] }),
      new TableCell({ borders, width: { size: pColW[3], type: WidthType.DXA }, margins: pad,
        shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
        children: [para(txt(p[2], { size: 16 }), { after: 0 })] }),
    ]}))
  ]
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ──── PRODUCTION NOTES ────
children.push(para(txt("拍摄制作备注", { size: 28, bold: true, color: C.dark }), { after: 200 }));

const notes = [
  ["\uD83C\uDFE0 场地", gpn.location || "室内"],
  ["\uD83D\uDCA1 灯光", gpn.lighting_setup || "自然光+补光灯"],
  ["\uD83C\uDFB5 BGM", gpn.bgm_suggestion || "轻快韩系风格"],
  ["\u2702 剪辑", gpn.editing_notes || "中速节奏"],
  ["\uD83D\uDC57 服装", gpn.wardrobe || "见角色设定"],
  ["\uD83D\uDCDD 字幕", "简洁白色字体，底部居中。步骤编号用加粗。不用花哨贴纸。"],
  ["\uD83C\uDFA8 色调", "温暖自然，不用冷白韩系滤镜。轻微提亮，不过度修图。"],
  ["\u26A0\uFE0F 合规", '口播禁用：美白/祛痘/祛斑/抗衰老/治疗。称呼用"姐妹"。不报精确价格。详见 voice.md。'],
  ["\u23F1 预估", gpn.estimated_raw_footage || "15-20分钟原始素材"],
];

const nW = [2000, 7360];
children.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: nW,
  rows: notes.map((n, i) => new TableRow({ children: [
    new TableCell({ borders, width: { size: nW[0], type: WidthType.DXA },
      shading: { fill: C.beige, type: ShadingType.CLEAR }, margins: padWide,
      children: [para(txt(n[0], { size: 16, bold: true }), { after: 0 })] }),
    new TableCell({ borders, width: { size: nW[1], type: WidthType.DXA },
      shading: i % 2 === 0 ? { fill: C.cream, type: ShadingType.CLEAR } : undefined,
      margins: padWide,
      children: [para(txt(n[1], { size: 16 }), { after: 0 })] }),
  ]}))
}));

// ═══════════════════════════════════════════
// BUILD & EXPORT
// ═══════════════════════════════════════════
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 18 } } },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 900, right: 1440, bottom: 900, left: 1440 }
      }
    },
    headers: { default: new Header({ children: [
      para([
        txt(`${meta.brand || "素仁轩"} | ${meta.content_type || ""} | v1.0`, { size: 14, color: C.muted }),
      ], { align: AlignmentType.RIGHT, after: 0 })
    ]})},
    footers: { default: new Footer({ children: [
      para([
        txt("Page ", { size: 14, color: C.muted }),
        new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 14, color: C.muted }),
      ], { align: AlignmentType.CENTER, after: 0 })
    ]})},
    children,
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log(`Generated: ${outputPath} (${(buffer.length / 1024).toFixed(0)}KB, ${shots.length} shots, ${2 + shots.length + 3} pages)`);
});
