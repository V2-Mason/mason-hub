#!/usr/bin/env node
// ae-to-remotion.mjs
// Task 1+2+3+4+5+6: AE JSON → Remotion JSX generator
// Usage: node ae-to-remotion.mjs <ae_full_export.json> <output.jsx>

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { dirname } from "path";

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Sanitize comp name to a valid JS identifier */
function safeName(name) {
  return name
    .replace(/[^a-zA-Z0-9]/g, "_")  // non-alphanumeric → _
    .replace(/_+/g, "_")             // merge consecutive _
    .replace(/^_+|_+$/g, "");       // trim leading/trailing _
}

/** Convert AE solidColor [r,g,b] (0-1 floats) to CSS hex */
function solidColorToHex(color) {
  if (!color || !Array.isArray(color) || color.length < 3) return null;
  const r = Math.round(color[0] * 255);
  const g = Math.round(color[1] * 255);
  const b = Math.round(color[2] * 255);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

/** Check if a layer name suggests it's a control/matte layer we should skip rendering */
function isControlLayer(layer) {
  const name = (layer.name || "").toLowerCase().trim();
  return (
    name === "controls" ||
    name === "matte" ||
    name === "camera position" ||
    name === "scale_text" ||
    name === "position"
  );
}

// ── Task 6: Text style lookup ─────────────────────────────────────────────────
// Maps layer name (lowercased) → style overrides for text layers
const TEXT_STYLE_MAP = {
  "clean":       { fontSize: 340, color: "#fcf9f9", letterSpacing: "-0.07em", mixBlendMode: "difference" },
  "fresh":       { fontSize: 60,  color: "#fcf9f9", letterSpacing: "-0.07em" },
  "&smart":      { fontSize: 60,  color: "#fcf9f9", letterSpacing: "-0.07em" },
  "titles":      { fontSize: 60,  color: "#fcf9f9", letterSpacing: "-0.07em" },
  "from mixkit": { fontSize: 70,  color: "#101010", letterSpacing: "-0.07em" },
};

/** Known placeholder comp names (case-insensitive match) */
function isPlaceholderComp(name) {
  return /^placeholder(_\d+)?$/i.test((name || "").trim()) ||
    (name || "").toLowerCase().startsWith("placeholder_0") ||
    (name || "").toLowerCase().startsWith("placeholder_text");
}

/** Is this a Photo/Video comp used for placeholder? */
function isPhotoVideoComp(name) {
  return /photo.*video|video.*photo/i.test(name || "");
}

// ── Task 3: Keyframe animation code generation ────────────────────────────────

/**
 * Generate a bezier easing expression from a cubicBezier array entry.
 * AE exports cubicBezier as an array where index=dimension.
 * BUT many comps export only ONE entry (index 0) for all dims → fall back to [0].
 */
function bezExpr(cubicBezier, dimIndex = 0) {
  if (!cubicBezier || cubicBezier.length === 0) return null;
  // Try the dimension-specific entry first, fall back to index 0
  const cb = cubicBezier[dimIndex] || cubicBezier[0];
  if (!cb || cb.length < 4) return null;
  const [x1, y1, x2, y2] = cb;
  return `bez(${x1}, ${y1}, ${x2}, ${y2})`;
}

/**
 * Generate interpolate() expression for a single dimension.
 *
 * keyframes: array of { frame, value (scalar), cubicBezier }
 * varName: JS variable name to assign
 *
 * For baked expressions (many keyframes with linear interp), uses lookup array approach.
 * For normal keyframes (2+), uses chained ternary.
 */
function genInterpolate1D(varName, keyframes, dimIndex = 0) {
  const n = keyframes.length;
  if (n < 2) return null;

  // Baked expression: many linear keyframes → lookup table approach
  const allLinear = keyframes.every(kf => kf.interpOut === "linear" || !kf.cubicBezier || kf.cubicBezier.length === 0);
  if (n > 10 && allLinear) {
    const frames = keyframes.map(kf => kf.frame);
    const values = keyframes.map(kf => Array.isArray(kf.value) ? kf.value[dimIndex] : kf.value);
    const lines = [];
    lines.push(`  const ${varName}_frames = [${frames.join(", ")}];`);
    lines.push(`  const ${varName}_vals = [${values.join(", ")}];`);
    lines.push(`  // Find segment`);
    lines.push(`  let ${varName}_i = ${varName}_frames.length - 2;`);
    lines.push(`  for (let _i = 0; _i < ${varName}_frames.length - 1; _i++) {`);
    lines.push(`    if (frame <= ${varName}_frames[_i + 1]) { ${varName}_i = _i; break; }`);
    lines.push(`  }`);
    lines.push(`  const ${varName} = interpolate(`);
    lines.push(`    frame,`);
    lines.push(`    [${varName}_frames[${varName}_i], ${varName}_frames[${varName}_i + 1]],`);
    lines.push(`    [${varName}_vals[${varName}_i], ${varName}_vals[${varName}_i + 1]],`);
    lines.push(`    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }`);
    lines.push(`  );`);
    return lines.join("\n");
  }

  // Normal keyframes: chained ternary with bezier easing
  if (n === 2) {
    const f0 = keyframes[0].frame;
    const f1 = keyframes[1].frame;
    const v0 = Array.isArray(keyframes[0].value) ? keyframes[0].value[dimIndex] : keyframes[0].value;
    const v1 = Array.isArray(keyframes[1].value) ? keyframes[1].value[dimIndex] : keyframes[1].value;
    const easing = bezExpr(keyframes[0].cubicBezier, dimIndex);
    const easingStr = easing ? `, easing: ${easing}` : "";
    return `  const ${varName} = interpolate(frame, [${f0}, ${f1}], [${v0}, ${v1}], { extrapolateLeft: "clamp", extrapolateRight: "clamp"${easingStr} });`;
  }

  // 3+ keyframes: chained ternary
  const lines = [];
  lines.push(`  const ${varName} =`);
  for (let i = 0; i < n - 2; i++) {
    const f0 = keyframes[i].frame;
    const f1 = keyframes[i + 1].frame;
    const v0 = Array.isArray(keyframes[i].value) ? keyframes[i].value[dimIndex] : keyframes[i].value;
    const v1 = Array.isArray(keyframes[i + 1].value) ? keyframes[i + 1].value[dimIndex] : keyframes[i + 1].value;
    const easing = bezExpr(keyframes[i].cubicBezier, dimIndex);
    const easingStr = easing ? `, easing: ${easing}` : "";
    lines.push(`    frame < ${f1}`);
    lines.push(`    ? interpolate(frame, [${f0}, ${f1}], [${v0}, ${v1}], { extrapolateLeft: "clamp", extrapolateRight: "clamp"${easingStr} })`);
    lines.push(`    :`);
  }
  // Last segment
  const last = n - 2;
  const f0 = keyframes[last].frame;
  const f1 = keyframes[last + 1].frame;
  const v0 = Array.isArray(keyframes[last].value) ? keyframes[last].value[dimIndex] : keyframes[last].value;
  const v1 = Array.isArray(keyframes[last + 1].value) ? keyframes[last + 1].value[dimIndex] : keyframes[last + 1].value;
  const easing = bezExpr(keyframes[last].cubicBezier, dimIndex);
  const easingStr = easing ? `, easing: ${easing}` : "";
  lines.push(`    interpolate(frame, [${f0}, ${f1}], [${v0}, ${v1}], { extrapolateLeft: "clamp", extrapolateRight: "clamp"${easingStr} });`);
  return lines.join("\n");
}

/**
 * Generate all animation variable declarations for a layer.
 * Returns { varDecls: string[], styleOverrides: object, transformParts: string[] }
 */
function genLayerAnimation(layer, layerVarPrefix) {
  const t = layer.transform;
  if (!t) return { varDecls: [], styleOverrides: {}, transformParts: [] };

  const varDecls = [];
  const styleOverrides = {};
  const transformParts = [];

  // Position (multi-dimensional: x, y, z)
  const pos = t["Position"];
  if (pos && pos.animated && pos.keyframes.length >= 2) {
    const kfs = pos.keyframes;
    const anchor = (t["Anchor Point"] && t["Anchor Point"].value) || [0, 0, 0];
    const anchorX = Array.isArray(anchor) ? anchor[0] : 0;
    const anchorY = Array.isArray(anchor) ? anchor[1] : 0;

    const xDecl = genInterpolate1D(`${layerVarPrefix}_posX`, kfs, 0);
    const yDecl = genInterpolate1D(`${layerVarPrefix}_posY`, kfs, 1);
    const zDecl = genInterpolate1D(`${layerVarPrefix}_posZ`, kfs, 2);
    if (xDecl) varDecls.push(xDecl);
    if (yDecl) varDecls.push(yDecl);
    if (zDecl) varDecls.push(zDecl);

    if (xDecl) styleOverrides.left = `${layerVarPrefix}_posX - ${anchorX}`;
    if (yDecl) styleOverrides.top = `${layerVarPrefix}_posY - ${anchorY}`;
  }

  // Scale (multi-dimensional: sx, sy)
  const scale = t["Scale"];
  if (scale && scale.animated && scale.keyframes.length >= 2) {
    const firstVal = JSON.stringify(scale.keyframes[0].value);
    const allSame = scale.keyframes.every(kf => JSON.stringify(kf.value) === firstVal);
    if (!allSame) {
      const sxDecl = genInterpolate1D(`${layerVarPrefix}_scaleX`, scale.keyframes, 0);
      const syDecl = genInterpolate1D(`${layerVarPrefix}_scaleY`, scale.keyframes, 1);
      if (sxDecl) varDecls.push(sxDecl);
      if (syDecl) varDecls.push(syDecl);
      transformParts.push(`scale(${layerVarPrefix}_scaleX / 100, ${layerVarPrefix}_scaleY / 100)`);
    }
  }

  // Rotation (scalar)
  const rot = t["Rotation"] || t["Z Rotation"];
  if (rot && rot.animated && rot.keyframes.length >= 2) {
    const rotDecl = genInterpolate1D(`${layerVarPrefix}_rot`, rot.keyframes, 0);
    if (rotDecl) varDecls.push(rotDecl);
    transformParts.push(`rotate(${`${layerVarPrefix}_rot`}deg)`);
  }

  // Opacity (scalar)
  const opacity = t["Opacity"];
  if (opacity && opacity.animated && opacity.keyframes.length >= 2) {
    const opDecl = genInterpolate1D(`${layerVarPrefix}_op`, opacity.keyframes, 0);
    if (opDecl) varDecls.push(opDecl);
    styleOverrides.opacity = `${layerVarPrefix}_op / 100`;
  }

  return { varDecls, styleOverrides, transformParts };
}

// ── Task 5: Matte pair analysis ───────────────────────────────────────────────

/**
 * Analyze comp layers for matte pairs.
 * Returns { mattePairs: Map<contentLayer, matteLayer>, splitScreenGroupIds: Set<contentLayerId> }
 *
 * In AE JSON: layers are sorted by index ascending. A matte layer (disabled, solid/shape)
 * precedes the content layer (index = contentLayer.index - 1).
 * The content layer has trackMatteType set.
 *
 * For split-screen detection: look for 2+ content layers sharing the same sourceCompId.
 */
function analyzeMattePairs(layers) {
  // Build map from index → layer for fast lookup
  const byIndex = new Map();
  for (const l of layers) byIndex.set(l.index, l);

  // Find content layers that have trackMatteType
  const mattePairs = new Map(); // contentLayer → matteLayer
  for (const l of layers) {
    if (l.trackMatteType) {
      // The matte is the layer directly ABOVE the content layer in the stack.
      // In AE JSON, lower index = higher in stack (rendered on top).
      // So the matte layer has index = contentLayer.index - 1.
      const matteLayer = byIndex.get(l.index - 1);
      if (matteLayer) {
        mattePairs.set(l, matteLayer);
      }
    }
  }

  // Detect split-screen: 2 content layers with same sourceCompId using matte=5013
  const splitPairGroups = new Map(); // sourceCompId → [contentLayer, ...]
  for (const [contentLayer] of mattePairs) {
    if (contentLayer.trackMatteType === 5013 && contentLayer.sourceCompId != null) {
      const key = String(contentLayer.sourceCompId);
      if (!splitPairGroups.has(key)) splitPairGroups.set(key, []);
      splitPairGroups.get(key).push(contentLayer);
    }
  }

  // Split screen: pairs where 2+ layers share the same sourceCompId
  const splitScreenLayerIds = new Set();
  for (const [, group] of splitPairGroups) {
    if (group.length >= 2) {
      for (const l of group) splitScreenLayerIds.add(l.index);
    }
  }

  return { mattePairs, splitScreenLayerIds };
}

// ── Task 1: JSON loader + comp walker ────────────────────────────────────────

const [,, inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("Usage: node ae-to-remotion.mjs <ae_full_export.json> <output.jsx>");
  process.exit(1);
}

const data = JSON.parse(readFileSync(inputPath, "utf8"));

// Find main comp by name
const mainCompEntry = Object.entries(data.comps).find(
  ([, comp]) => comp.name === data.mainComp
);
if (!mainCompEntry) {
  console.error(`ERROR: Could not find main comp "${data.mainComp}" in JSON.`);
  process.exit(1);
}
const [mainCompId, mainComp] = mainCompEntry;
console.log(`Main comp: "${mainComp.name}" (id: ${mainCompId}), ${mainComp.totalFrames} frames`);

// DFS: collect all reachable comps from main comp
const visitedIds = new Set();
const orderedComps = []; // DFS post-order (leaves first)

function dfsWalk(compId) {
  if (visitedIds.has(compId)) return;
  visitedIds.add(compId);

  const comp = data.comps[compId];
  if (!comp) {
    console.warn(`  WARNING: comp id ${compId} not found in data.comps`);
    return;
  }

  // Recurse into precomp children first (DFS)
  for (const layer of comp.layers) {
    if (layer.type === "precomp" && layer.sourceCompId != null) {
      dfsWalk(String(layer.sourceCompId));
    }
  }

  // Post-order: push after children
  orderedComps.push(comp);
}

dfsWalk(mainCompId);
console.log(`Collected ${orderedComps.length} reachable comps (DFS post-order, leaves first):`);
orderedComps.forEach((c, i) => console.log(`  ${i + 1}. ${c.name}`));

// ── Task 2+3+4+5+6: Generate .jsx ─────────────────────────────────────────────────

const lines = [];

// Header
lines.push(`// Auto-generated from ae_full_export.json`);
lines.push(`// Source: "${data.mainComp}" — ${mainComp.width}x${mainComp.height} @ ${mainComp.fps}fps, ${mainComp.totalFrames} frames`);
lines.push(`// DO NOT EDIT by hand — regenerate with ae-to-remotion.mjs`);
lines.push(``);
lines.push(`import React from "react";`);
lines.push(`import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";`);
lines.push(``);
lines.push(`const bez = (x1, y1, x2, y2) => Easing.bezier(`);
lines.push(`  Math.max(0, Math.min(1, x1)),`);
lines.push(`  Math.max(-2, Math.min(2, y1)),`);
lines.push(`  Math.max(0, Math.min(1, x2)),`);
lines.push(`  Math.max(-2, Math.min(2, y2))`);
lines.push(`);`);
lines.push(``);

// ── Task 6: Shared helper components ──────────────────────────────────────────
lines.push(`// ── Task 6: Shared helpers ──`);
lines.push(`const FONT = "Open Sans, Arial Black, Arial";`);
lines.push(``);

// PlaceholderImage component
lines.push(`const PlaceholderImage = ({ scale = 1, clipCircle = false, opacity = 1 }) => (`);
lines.push(`  <div style={{`);
lines.push(`    position: "absolute", left: "50%", top: "50%",`);
lines.push(`    transform: \`translate(-50%, -50%) scale(\${scale})\`,`);
lines.push(`    width: ${mainComp.width}, height: ${mainComp.height}, opacity,`);
lines.push(`    ...(clipCircle ? { clipPath: "ellipse(578px 578px at 960px 540px)" } : {}),`);
lines.push(`  }}>`);
lines.push(`    <div style={{ position: "absolute", inset: 0, backgroundColor: "#009a5a" }} />`);
lines.push(`    <div style={{`);
lines.push(`      position: "absolute", inset: 0,`);
lines.push(`      display: "flex", alignItems: "center", justifyContent: "center",`);
lines.push(`      transform: "rotate(-44deg) scale(3.07)", opacity: 0.15,`);
lines.push(`    }}>`);
lines.push(`      <div style={{ fontFamily: "Arial", fontSize: 12, color: "#222", whiteSpace: "nowrap" }}>`);
lines.push(`        {"PLACEHOLDER ".repeat(100)}`);
lines.push(`      </div>`);
lines.push(`    </div>`);
lines.push(`  </div>`);
lines.push(`);`);
lines.push(``);

// FrameRect component
lines.push(`const FrameRect = ({ strokeWidth = 10, color = "#fcf9f9", opacity = 1, widthPx = 760, heightPx = 234 }) => (`);
lines.push(`  <div style={{`);
lines.push(`    position: "absolute", left: "50%", top: "50%",`);
lines.push(`    transform: "translate(-50%, -50%)",`);
lines.push(`    width: widthPx, height: heightPx,`);
lines.push(`    border: \`\${strokeWidth}px solid \${color}\`,`);
lines.push(`    boxSizing: "border-box", opacity,`);
lines.push(`  }} />`);
lines.push(`);`);
lines.push(``);

// SplitMatte component
lines.push(`// Task 5: Split-screen matte component`);
lines.push(`const SplitMatte = ({ children, frame, startFrame, endFrame, topStartY, bottomStartY, topEase, botEase }) => {`);
lines.push(`  const topOffset = interpolate(frame, [startFrame, endFrame], [topStartY - 540, 0], {`);
lines.push(`    extrapolateLeft: "clamp", extrapolateRight: "clamp",`);
lines.push(`    ...(topEase ? { easing: topEase } : {}),`);
lines.push(`  });`);
lines.push(`  const botOffset = interpolate(frame, [startFrame, endFrame], [bottomStartY - 540, 0], {`);
lines.push(`    extrapolateLeft: "clamp", extrapolateRight: "clamp",`);
lines.push(`    ...(botEase ? { easing: botEase } : {}),`);
lines.push(`  });`);
lines.push(`  return (`);
lines.push(`    <>`);
lines.push(`      {/* Top half — overflow hidden */}`);
lines.push(`      <div style={{ position: "absolute", left: 0, top: 0, width: ${mainComp.width}, height: ${mainComp.height / 2}, overflow: "hidden" }}>`);
lines.push(`        <div style={{ position: "absolute", left: 0, top: topOffset, width: ${mainComp.width}, height: ${mainComp.height} }}>`);
lines.push(`          {children}`);
lines.push(`        </div>`);
lines.push(`      </div>`);
lines.push(`      {/* Bottom half — overflow hidden */}`);
lines.push(`      <div style={{ position: "absolute", left: 0, top: ${mainComp.height / 2}, width: ${mainComp.width}, height: ${mainComp.height / 2}, overflow: "hidden" }}>`);
lines.push(`        <div style={{ position: "absolute", left: 0, top: botOffset - ${mainComp.height / 2}, width: ${mainComp.width}, height: ${mainComp.height} }}>`);
lines.push(`          {children}`);
lines.push(`        </div>`);
lines.push(`      </div>`);
lines.push(`    </>`);
lines.push(`  );`);
lines.push(`};`);
lines.push(``);

// Track which split groups have been emitted (to avoid duplicate rendering)
const emittedSplitGroups = new Set();

// Per comp: one React component
for (const comp of orderedComps) {
  const fnName = `Comp_${safeName(comp.name)}`;

  // ── Task 5: Matte pair analysis ──
  const { mattePairs, splitScreenLayerIds } = analyzeMattePairs(comp.layers);

  // ── Task 4: Camera detection for Scene_02_main ──
  const cameraLayer = comp.layers.find(l => l.type === "camera");
  const camPosLayer = comp.layers.find(
    l => l.name === "Camera position" && l.type === "solid" && l.threeDLayer
  );
  const hasCamera = !!(cameraLayer && camPosLayer);

  lines.push(`// ── ${comp.name} (${comp.totalFrames} frames, ${comp.width || mainComp.width}x${comp.height || mainComp.height}) ──`);
  lines.push(`const ${fnName} = ({ parentFrame = 0 }) => {`);
  lines.push(`  const frame = parentFrame;`);
  lines.push(``);

  // ── Task 4: Camera perspective variables ──
  if (hasCamera) {
    const zoom = cameraLayer.camera && cameraLayer.camera.Zoom
      ? cameraLayer.camera.Zoom.value
      : 1866.667;
    lines.push(`  // Task 4: 3D camera perspective`);
    lines.push(`  const zoom = ${zoom.toFixed(3)};`);

    const camPosKfs = camPosLayer.transform && camPosLayer.transform.Position && camPosLayer.transform.Position.keyframes;
    if (camPosKfs && camPosKfs.length >= 2) {
      const camZDecl = genInterpolate1D("camZ", camPosKfs, 2);
      if (camZDecl) lines.push(camZDecl);
    } else {
      lines.push(`  const camZ = 0;`);
    }
    lines.push(`  const camScale = zoom / (zoom - camZ);`);
    lines.push(``);

    const phLayer = comp.layers.find(
      l => l.name === "PLACEHOLDER_02" && l.transform && l.transform.Position && l.transform.Position.animated
    );
    if (phLayer) {
      const phKfs = phLayer.transform.Position.keyframes;
      const phZDecl = genInterpolate1D("placeZ", phKfs, 2);
      if (phZDecl) lines.push(phZDecl);
      lines.push(`  const placeZScale = zoom / (zoom - placeZ);`);
      lines.push(``);
    }
  }

  // ── Per-layer animation variable declarations ──
  const layerAnimMap = new Map();
  const enabledLayers = comp.layers.filter((l) => l.enabled !== false);
  const sortedLayers = [...enabledLayers].sort((a, b) => b.index - a.index);

  for (const layer of sortedLayers) {
    if (isControlLayer(layer) || layer.type === "camera" || layer.type === "shape") continue;
    const prefix = `l${layer.index}_${safeName(layer.name)}`;
    const anim = genLayerAnimation(layer, prefix);
    if (anim.varDecls.length > 0) {
      for (const decl of anim.varDecls) {
        lines.push(decl);
      }
    }
    layerAnimMap.set(layer, { prefix, ...anim });
  }

  if ([...layerAnimMap.values()].some(a => a.varDecls.length > 0)) {
    lines.push(``);
  }

  // ── Task 5: Generate SplitMatte ease variables if needed ──
  // Group split-screen pairs: find all content layers in split groups
  const splitGroups = new Map(); // sourceCompId → [contentLayer sorted by index desc]
  for (const layer of sortedLayers) {
    if (splitScreenLayerIds.has(layer.index)) {
      const key = String(layer.sourceCompId);
      if (!splitGroups.has(key)) splitGroups.set(key, []);
      splitGroups.get(key).push(layer);
    }
  }

  lines.push(`  return (`);

  if (hasCamera) {
    lines.push(`    <AbsoluteFill>`);
    lines.push(`      {/* Camera perspective wrapper */}`);
    lines.push(`      <div style={{ position: "absolute", left: "50%", top: "50%", transform: \`translate(-50%,-50%) scale(\${camScale})\`, width: ${mainComp.width}, height: ${mainComp.height} }}>`);

    for (const layer of sortedLayers) {
      emitLayer(layer, comp, "        ", layerAnimMap, true, mattePairs, splitScreenLayerIds, splitGroups);
    }

    lines.push(`      </div>`);
    lines.push(`    </AbsoluteFill>`);
  } else {
    lines.push(`    <AbsoluteFill>`);
    for (const layer of sortedLayers) {
      emitLayer(layer, comp, "      ", layerAnimMap, false, mattePairs, splitScreenLayerIds, splitGroups);
    }
    lines.push(`    </AbsoluteFill>`);
  }

  lines.push(`  );`);
  lines.push(`};`);
  lines.push(``);
}

// ── Layer emitter (used inline above) ────────────────────────────────────────

function emitLayer(layer, comp, indent, layerAnimMap, inCameraComp, mattePairs, splitScreenLayerIds, splitGroups) {
  // ── Task 5: Skip disabled matte source layers ──
  // Matte layers are disabled and have name "Matte" or "frame N" (shape) — they're already skipped
  // because we only iterate enabledLayers above. But check anyway.

  const needsVisGate =
    (layer.inFrame != null && layer.inFrame > 0) ||
    (layer.outFrame != null && layer.outFrame < comp.totalFrames);

  const inF = layer.inFrame ?? 0;
  const outF = layer.outFrame ?? comp.totalFrames;

  lines.push(`${indent}{/* [${layer.index}] ${layer.name} (${layer.type}) f${inF}-${outF} */}`);

  const isCommentOnly = layer.type === "camera";

  // ── Task 5: Handle split-screen matte pairs ──
  if (splitScreenLayerIds.has(layer.index)) {
    const key = String(layer.sourceCompId);
    if (emittedSplitGroups.has(`${comp.name}:${key}`)) {
      // Already emitted the SplitMatte for this group — skip duplicate
      lines.push(`${indent}{/* split-screen duplicate — already emitted above */}`);
      return;
    }
    emittedSplitGroups.add(`${comp.name}:${key}`);

    const group = splitGroups.get(key) || [];
    // group is sorted by index desc; we need to find which is "top" and which is "bottom"
    // by looking at their starting Y: lower Y = top half, higher Y = bottom half
    // Actually from our analysis: the content with lower starting Y is the "top" pair
    // (it slides from low Y UP into center) → this is the top container

    let topLayer = null, botLayer = null;
    for (const gl of group) {
      // Use the MATTE layer's Y position to determine display region, not the content layer's Y.
      // In AE Track Matte, the matte's position defines the visible area:
      //   matte Y < 540 (≈0)    → TOP region
      //   matte Y >= 540 (≈1080) → BOTTOM region
      const matteLayer = mattePairs.get(gl);
      const matteY = matteLayer && matteLayer.transform && matteLayer.transform.Position
        ? matteLayer.transform.Position.value[1]
        : null;
      if (matteY !== null) {
        if (matteY < 540) {
          topLayer = gl; // matte defines top region → this content fills top half
        } else {
          botLayer = gl; // matte defines bottom region → this content fills bottom half
        }
      }
    }

    if (!topLayer || !botLayer) {
      // Fallback: use group[0] and group[1]
      [topLayer, botLayer] = group.length >= 2 ? [group[0], group[1]] : [group[0], group[0]];
    }

    const topKfs = topLayer.transform && topLayer.transform.Position && topLayer.transform.Position.keyframes;
    const botKfs = botLayer.transform && botLayer.transform.Position && botLayer.transform.Position.keyframes;

    const topStartY = topKfs ? topKfs[0].value[1] : 0;
    const botStartY = botKfs ? botKfs[0].value[1] : mainComp.height;
    const startFrame = topKfs ? topKfs[0].frame : 0;
    const endFrame = topKfs ? topKfs[topKfs.length - 1].frame : 15;

    // Extract bezier easing for each
    const topBez = topKfs && topKfs[0].cubicBezier ? bezExpr(topKfs[0].cubicBezier, 1) : null;
    const botBez = botKfs && botKfs[0].cubicBezier ? bezExpr(botKfs[0].cubicBezier, 1) : null;
    const topEaseStr = topBez || "null";
    const botEaseStr = botBez || "null";

    const childComp = data.comps[String(topLayer.sourceCompId)];
    const childFnName = childComp ? `Comp_${safeName(childComp.name)}` : `Comp_UNKNOWN`;
    const startFrame2 = topLayer.startFrame ?? 0;
    const stretch = topLayer.stretch ?? 100;
    const stretchFactor = stretch / 100;
    const frameExpr = startFrame2 === 0 && stretchFactor === 1
      ? `frame`
      : startFrame2 === 0 ? `frame / ${stretchFactor}`
      : stretchFactor === 1 ? `(frame - ${startFrame2})`
      : `(frame - ${startFrame2}) / ${stretchFactor}`;

    const innerIndent = indent + "  ";

    const hasVis = needsVisGate;
    if (hasVis) {
      lines.push(`${indent}{frame >= ${inF} && frame < ${outF} && (`);
    }

    lines.push(`${hasVis ? innerIndent : indent}<SplitMatte`);
    lines.push(`${hasVis ? innerIndent : indent}  frame={frame}`);
    lines.push(`${hasVis ? innerIndent : indent}  startFrame={${startFrame}}`);
    lines.push(`${hasVis ? innerIndent : indent}  endFrame={${endFrame}}`);
    lines.push(`${hasVis ? innerIndent : indent}  topStartY={${topStartY}}`);
    lines.push(`${hasVis ? innerIndent : indent}  bottomStartY={${botStartY}}`);
    lines.push(`${hasVis ? innerIndent : indent}  topEase={${topEaseStr}}`);
    lines.push(`${hasVis ? innerIndent : indent}  botEase={${botEaseStr}}`);
    lines.push(`${hasVis ? innerIndent : indent}>`);
    lines.push(`${hasVis ? innerIndent : indent}  <${childFnName} parentFrame={${frameExpr}} />`);
    lines.push(`${hasVis ? innerIndent : indent}</SplitMatte>`);

    if (hasVis) {
      lines.push(`${indent})}`);
    }
    return;
  }

  // ── Normal layer rendering ──

  if (needsVisGate && !isCommentOnly) {
    lines.push(`${indent}{frame >= ${inF} && frame < ${outF} && (`);
  }

  const innerIndent = needsVisGate && !isCommentOnly ? indent + "  " : indent;

  switch (layer.type) {
    case "camera":
      lines.push(`${indent}{/* camera layer "${layer.name}" — handled in Task 4 */}`);
      break;

    case "precomp": {
      const childComp = data.comps[String(layer.sourceCompId)];
      const childFnName = childComp
        ? `Comp_${safeName(childComp.name)}`
        : `Comp_UNKNOWN_${layer.sourceCompId}`;
      const startFrame = layer.startFrame ?? 0;
      const stretch = layer.stretch ?? 100;
      const stretchFactor = stretch / 100;
      const frameExpr =
        startFrame === 0 && stretchFactor === 1
          ? `frame`
          : startFrame === 0
          ? `frame / ${stretchFactor}`
          : stretchFactor === 1
          ? `(frame - ${startFrame})`
          : `(frame - ${startFrame}) / ${stretchFactor}`;

      const anim = layerAnimMap.get(layer);
      const hasAnim = anim && (anim.styleOverrides && Object.keys(anim.styleOverrides).length > 0 || anim.transformParts && anim.transformParts.length > 0);

      // ── Task 6: PlaceholderImage for placeholder comps ──
      if (childComp && (isPhotoVideoComp(childComp.name) || isPlaceholderComp(childComp.name))) {
        // Render as PlaceholderImage instead of child comp
        if (inCameraComp && layer.name === "PLACEHOLDER_02") {
          // Z-scaled placeholder
          const isCircle = layer.index === 7; // circle-clipped version
          lines.push(`${innerIndent}<PlaceholderImage scale={${isCircle ? "1.16 * placeZScale" : "1.16"}} clipCircle={${isCircle}} />`);
        } else {
          lines.push(`${innerIndent}<PlaceholderImage />`);
        }
        break;
      }

      if (hasAnim) {
        const styleParts = [];
        styleParts.push(`position: "absolute"`);

        if (anim.styleOverrides.left !== undefined) {
          styleParts.push(`left: ${anim.styleOverrides.left}`);
        }
        if (anim.styleOverrides.top !== undefined) {
          styleParts.push(`top: ${anim.styleOverrides.top}`);
        }
        if (anim.styleOverrides.opacity !== undefined) {
          styleParts.push(`opacity: ${anim.styleOverrides.opacity}`);
        }

        let transformStr = "";
        if (inCameraComp && layer.name === "PLACEHOLDER_02") {
          transformStr = `\`scale(\${placeZScale})\``;
        } else if (anim.transformParts && anim.transformParts.length > 0) {
          transformStr = `\`${anim.transformParts.join(" ")}\``;
        }
        if (transformStr) {
          styleParts.push(`transform: ${transformStr}`);
        }

        lines.push(`${innerIndent}<div style={{ ${styleParts.join(", ")} }}>`);
        lines.push(`${innerIndent}  <${childFnName} parentFrame={${frameExpr}} />`);
        lines.push(`${innerIndent}</div>`);
      } else {
        lines.push(`${innerIndent}<${childFnName} parentFrame={${frameExpr}} />`);
      }
      break;
    }

    case "solid": {
      if (isControlLayer(layer)) {
        lines.push(`${indent}{/* solid "${layer.name}" — control/matte layer, skipped */}`);
        break;
      }
      const hex = solidColorToHex(layer.solidColor);
      if (!hex) {
        lines.push(`${indent}{/* solid "${layer.name}" — no color data, skipped */}`);
        break;
      }

      // ── Task 5: Alpha Inverted (5014) solids — render as overlay ──
      if (layer.trackMatteType === 5014) {
        // This is an alpha-inverted solid: renders on top, masking by covering
        const anim = layerAnimMap.get(layer);
        const hasAnim = anim && anim.styleOverrides && Object.keys(anim.styleOverrides).length > 0;
        const styleParts = [`position: "absolute"`, `backgroundColor: "${hex}"`];
        const w = layer.solidWidth || mainComp.width;
        const h = layer.solidHeight || mainComp.height;
        styleParts.push(`width: ${w}`, `height: ${h}`);
        if (hasAnim && anim.styleOverrides.left !== undefined) styleParts.push(`left: ${anim.styleOverrides.left}`);
        if (hasAnim && anim.styleOverrides.top !== undefined) styleParts.push(`top: ${anim.styleOverrides.top}`);
        lines.push(`${innerIndent}<div style={{ ${styleParts.join(", ")} }} />`);
        break;
      }

      const anim = layerAnimMap.get(layer);
      const hasAnim = anim && (anim.styleOverrides && Object.keys(anim.styleOverrides).length > 0 || anim.transformParts && anim.transformParts.length > 0);

      if (hasAnim) {
        const styleParts = [`position: "absolute"`, `backgroundColor: "${hex}"`];
        if (anim.styleOverrides.left !== undefined) styleParts.push(`left: ${anim.styleOverrides.left}`);
        if (anim.styleOverrides.top !== undefined) styleParts.push(`top: ${anim.styleOverrides.top}`);
        if (anim.styleOverrides.opacity !== undefined) styleParts.push(`opacity: ${anim.styleOverrides.opacity}`);
        if (anim.transformParts && anim.transformParts.length > 0) {
          styleParts.push(`transform: \`${anim.transformParts.join(" ")}\``);
        }
        lines.push(`${innerIndent}<div style={{ ${styleParts.join(", ")} }} />`);
      } else {
        lines.push(
          `${innerIndent}<div style={{ position: "absolute", inset: 0, backgroundColor: "${hex}" }} />`
        );
      }
      break;
    }

    case "text": {
      // ── Task 6: Skip empty text layers ──
      const rawText = layer.textContent || layer.name || "";
      // Skip layers with clearly empty/placeholder names (empty text layer)
      if (!rawText || rawText === "<empty text layer>" || rawText.trim() === "") {
        lines.push(`${indent}{/* text layer "${layer.name}" — empty, skipped */}`);
        break;
      }

      // ── Task 6: Text style lookup ──
      const textKey = rawText.toLowerCase().trim();
      const layerNameKey = (layer.name || "").toLowerCase().trim();
      const styleOverride = TEXT_STYLE_MAP[textKey] || TEXT_STYLE_MAP[layerNameKey];

      const fontSize = styleOverride ? styleOverride.fontSize : (layer.fontSize || 48);
      const color = styleOverride ? styleOverride.color : "#ffffff";
      const letterSpacing = styleOverride ? styleOverride.letterSpacing : undefined;
      const mixBlendMode = styleOverride ? styleOverride.mixBlendMode : undefined;

      const anim = layerAnimMap.get(layer);
      const hasAnim = anim && (anim.styleOverrides && Object.keys(anim.styleOverrides).length > 0);

      const baseStyle = [
        `position: "absolute"`,
        `inset: 0`,
        `display: "flex"`,
        `alignItems: "center"`,
        `justifyContent: "center"`,
        `fontFamily: FONT`,
        `fontSize: ${fontSize}`,
        `color: "${color}"`,
        `fontWeight: 800`,
        `textTransform: "uppercase"`,
        `whiteSpace: "nowrap"`,
        `userSelect: "none"`,
      ];

      if (letterSpacing) baseStyle.push(`letterSpacing: "${letterSpacing}"`);
      if (mixBlendMode) baseStyle.push(`mixBlendMode: "${mixBlendMode}"`);

      if (hasAnim) {
        if (anim.styleOverrides.opacity !== undefined) baseStyle.push(`opacity: ${anim.styleOverrides.opacity}`);
      }

      lines.push(`${innerIndent}<div style={{`);
      for (const part of baseStyle) {
        lines.push(`${innerIndent}  ${part},`);
      }
      lines.push(`${innerIndent}}}>`);
      lines.push(`${innerIndent}  {${JSON.stringify(rawText)}}`);
      lines.push(`${innerIndent}</div>`);
      break;
    }

    case "shape": {
      // ── Task 6: Render enabled shape layers as FrameRect ──
      if (layer.enabled !== false) {
        lines.push(`${innerIndent}<FrameRect />`);
      } else {
        lines.push(`${innerIndent}{/* shape matte "${layer.name}" — disabled, skipped */}`);
      }
      break;
    }

    default:
      lines.push(`${innerIndent}{/* unknown layer type "${layer.type}" — skipped */}`);
  }

  if (needsVisGate && !isCommentOnly) {
    lines.push(`${indent})}`);
  }
}

// Main export — references the main comp component
const mainFnName = `Comp_${safeName(mainComp.name)}`;
lines.push(`// ── Main export ──`);
lines.push(`export const AETitleGenerated = () => {`);
lines.push(`  const frame = useCurrentFrame();`);
lines.push(`  return <${mainFnName} parentFrame={frame} />;`);
lines.push(`};`);
lines.push(``);

// Write output
const output = lines.join("\n");
mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, output, "utf8");
console.log(`\nWrote ${lines.length} lines to: ${outputPath}`);

// Quick verification
const compFnCount = (output.match(/^const Comp_/gm) || []).length;
console.log(`Comp functions generated: ${compFnCount} (expected: ${orderedComps.length})`);
console.log(`Main export present: ${output.includes("export const AETitleGenerated")}`);
const interpolateCount = (output.match(/interpolate\(/g) || []).length;
console.log(`interpolate() calls: ${interpolateCount}`);
console.log(`Camera perspective present: ${output.includes("camScale")}`);
console.log(`SplitMatte present: ${output.includes("SplitMatte")}`);
console.log(`PlaceholderImage present: ${output.includes("PlaceholderImage")}`);
console.log(`FrameRect present: ${output.includes("FrameRect")}`);
