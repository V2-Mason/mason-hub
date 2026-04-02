#!/usr/bin/env node
// ae-to-remotion.mjs
// Task 1+2+3+4: AE JSON → Remotion JSX generator (static layers + keyframe animation + 3D camera)
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

// ── Task 3: Keyframe animation code generation ────────────────────────────────

/**
 * Generate a bezier easing expression from a cubicBezier array entry.
 * cubicBezier[dimIndex] = [x1, y1, x2, y2]
 * Falls back to linear (null) if not present.
 */
function bezExpr(cubicBezier, dimIndex = 0) {
  const cb = cubicBezier && cubicBezier[dimIndex];
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
  // For each segment [i, i+1], use keyframe[i].cubicBezier for easing
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
    // Z is used for camera depth, not directly as CSS (handled in Task 4 per layer)
  }

  // Scale (multi-dimensional: sx, sy)
  const scale = t["Scale"];
  if (scale && scale.animated && scale.keyframes.length >= 2) {
    // Check if baked constant (all same value) — skip if so
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

// ── Task 2+3+4: Generate .jsx ─────────────────────────────────────────────────

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

// Per comp: one React component
for (const comp of orderedComps) {
  const fnName = `Comp_${safeName(comp.name)}`;

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

    // Camera position Z keyframes
    const camPosKfs = camPosLayer.transform && camPosLayer.transform.Position && camPosLayer.transform.Position.keyframes;
    if (camPosKfs && camPosKfs.length >= 2) {
      const camZDecl = genInterpolate1D("camZ", camPosKfs, 2);
      if (camZDecl) lines.push(camZDecl);
    } else {
      lines.push(`  const camZ = 0;`);
    }
    lines.push(`  const camScale = zoom / (zoom - camZ);`);
    lines.push(``);

    // PLACEHOLDER_02 (first one with animated Z Position)
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
  // Collect unique animated layers by layerVarPrefix
  const layerAnimMap = new Map(); // layer → { varDecls, styleOverrides, transformParts }
  const enabledLayers = comp.layers.filter((l) => l.enabled !== false);
  const sortedLayers = [...enabledLayers].sort((a, b) => b.index - a.index);

  for (const layer of sortedLayers) {
    if (isControlLayer(layer) || layer.type === "camera" || layer.type === "shape") continue;
    const prefix = `l${layer.index}_${safeName(layer.name)}`;
    const anim = genLayerAnimation(layer, prefix);
    if (anim.varDecls.length > 0) {
      // Emit declarations
      for (const decl of anim.varDecls) {
        lines.push(decl);
      }
    }
    layerAnimMap.set(layer, { prefix, ...anim });
  }

  if ([...layerAnimMap.values()].some(a => a.varDecls.length > 0)) {
    lines.push(``);
  }

  lines.push(`  return (`);

  // Task 4: Wrap all non-placeholder 3D layers inside perspective div
  if (hasCamera) {
    lines.push(`    <AbsoluteFill>`);
    lines.push(`      {/* Camera perspective wrapper */}`);
    lines.push(`      <div style={{ position: "absolute", left: "50%", top: "50%", transform: \`translate(-50%,-50%) scale(\${camScale})\`, width: ${mainComp.width}, height: ${mainComp.height} }}>`);

    for (const layer of sortedLayers) {
      emitLayer(layer, comp, "        ", layerAnimMap, true);
    }

    lines.push(`      </div>`);
    lines.push(`    </AbsoluteFill>`);
  } else {
    lines.push(`    <AbsoluteFill>`);
    for (const layer of sortedLayers) {
      emitLayer(layer, comp, "      ", layerAnimMap, false);
    }
    lines.push(`    </AbsoluteFill>`);
  }

  lines.push(`  );`);
  lines.push(`};`);
  lines.push(``);
}

// ── Layer emitter (used inline above) ────────────────────────────────────────

function emitLayer(layer, comp, indent, layerAnimMap, inCameraComp) {
  const needsVisGate =
    (layer.inFrame != null && layer.inFrame > 0) ||
    (layer.outFrame != null && layer.outFrame < comp.totalFrames);

  const inF = layer.inFrame ?? 0;
  const outF = layer.outFrame ?? comp.totalFrames;

  // Comment for each layer
  lines.push(`${indent}{/* [${layer.index}] ${layer.name} (${layer.type}) f${inF}-${outF} */}`);

  const isCommentOnly = layer.type === "camera" || layer.type === "shape";

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

      // Get animation data for this precomp layer
      const anim = layerAnimMap.get(layer);
      const hasAnim = anim && (anim.styleOverrides && Object.keys(anim.styleOverrides).length > 0 || anim.transformParts && anim.transformParts.length > 0);

      if (hasAnim) {
        // Build style string for the wrapper div
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

        // PLACEHOLDER_02 special: apply per-layer Z scale
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
      const text = layer.textContent || layer.name || "";
      const fontSize = layer.fontSize || 48;

      const anim = layerAnimMap.get(layer);
      const hasAnim = anim && (anim.styleOverrides && Object.keys(anim.styleOverrides).length > 0);

      const baseStyle = [
        `position: "absolute"`,
        `inset: 0`,
        `display: "flex"`,
        `alignItems: "center"`,
        `justifyContent: "center"`,
        `fontFamily: "Arial, sans-serif"`,
        `fontSize: ${fontSize}`,
        `color: "#ffffff"`,
        `fontWeight: 800`,
        `textTransform: "uppercase"`,
        `whiteSpace: "nowrap"`,
        `userSelect: "none"`,
      ];

      if (hasAnim) {
        if (anim.styleOverrides.opacity !== undefined) baseStyle.push(`opacity: ${anim.styleOverrides.opacity}`);
      }

      lines.push(`${innerIndent}<div style={{`);
      for (const part of baseStyle) {
        lines.push(`${innerIndent}  ${part},`);
      }
      lines.push(`${innerIndent}}}>`);
      lines.push(`${innerIndent}  {${JSON.stringify(text)}}`);
      lines.push(`${innerIndent}</div>`);
      break;
    }

    case "shape":
      lines.push(`${innerIndent}{/* shape layer — TODO */}`);
      break;

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
