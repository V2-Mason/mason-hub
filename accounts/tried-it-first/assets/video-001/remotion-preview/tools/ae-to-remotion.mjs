#!/usr/bin/env node
// ae-to-remotion.mjs
// Task 1+2: AE JSON → Remotion JSX generator (static layers, no animation)
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

// ── Task 2: Generate .jsx ─────────────────────────────────────────────────────

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

  lines.push(`// ── ${comp.name} (${comp.totalFrames} frames, ${comp.width || mainComp.width}x${comp.height || mainComp.height}) ──`);
  lines.push(`const ${fnName} = ({ parentFrame = 0 }) => {`);
  lines.push(`  const frame = parentFrame;`);
  lines.push(``);
  lines.push(`  return (`);
  lines.push(`    <AbsoluteFill>`);

  // Filter out disabled layers
  const enabledLayers = comp.layers.filter((l) => l.enabled !== false);

  // Sort by index DESCENDING (AE bottom layer = highest index = rendered first in DOM)
  const sortedLayers = [...enabledLayers].sort((a, b) => b.index - a.index);

  for (const layer of sortedLayers) {
    const needsVisGate =
      (layer.inFrame != null && layer.inFrame > 0) ||
      (layer.outFrame != null && layer.outFrame < comp.totalFrames);

    const inF = layer.inFrame ?? 0;
    const outF = layer.outFrame ?? comp.totalFrames;

    // Comment for each layer
    lines.push(`      {/* [${layer.index}] ${layer.name} (${layer.type}) f${inF}-${outF} */}`);

    // Layers that render as comments only — skip visibility gate (comments aren't JSX expressions)
    const isCommentOnly = layer.type === "camera" || layer.type === "shape";

    // Visibility gate opener (only for renderable layers)
    if (needsVisGate && !isCommentOnly) {
      lines.push(`      {frame >= ${inF} && frame < ${outF} && (`);
    }

    const indent = needsVisGate && !isCommentOnly ? "        " : "      ";

    switch (layer.type) {
      case "camera":
        // Skip cameras — handled later in Task 4
        lines.push(`      {/* camera layer "${layer.name}" — skipped (handled in Task 4) */}`);
        break;

      case "precomp": {
        const childComp = data.comps[String(layer.sourceCompId)];
        const childFnName = childComp
          ? `Comp_${safeName(childComp.name)}`
          : `Comp_UNKNOWN_${layer.sourceCompId}`;
        const startFrame = layer.startFrame ?? 0;
        const stretch = layer.stretch ?? 100;
        // parentFrame for child = (frame - startFrame) / (stretch/100)
        const stretchFactor = stretch / 100;
        const frameExpr =
          startFrame === 0 && stretchFactor === 1
            ? `frame`
            : startFrame === 0
            ? `frame / ${stretchFactor}`
            : stretchFactor === 1
            ? `(frame - ${startFrame})`
            : `(frame - ${startFrame}) / ${stretchFactor}`;
        lines.push(`${indent}<${childFnName} parentFrame={${frameExpr}} />`);
        break;
      }

      case "solid": {
        // Skip control/matte layers
        if (isControlLayer(layer)) {
          lines.push(`      {/* solid "${layer.name}" — control/matte layer, skipped */}`);
          break;
        }
        const hex = solidColorToHex(layer.solidColor);
        if (!hex) {
          lines.push(`      {/* solid "${layer.name}" — no color data, skipped */}`);
          break;
        }
        lines.push(
          `${indent}<div style={{ position: "absolute", inset: 0, backgroundColor: "${hex}" }} />`
        );
        break;
      }

      case "text": {
        const text = layer.textContent || layer.name || "";
        const fontSize = layer.fontSize || 48;
        lines.push(`${indent}<div style={{`);
        lines.push(`${indent}  position: "absolute",`);
        lines.push(`${indent}  inset: 0,`);
        lines.push(`${indent}  display: "flex",`);
        lines.push(`${indent}  alignItems: "center",`);
        lines.push(`${indent}  justifyContent: "center",`);
        lines.push(`${indent}  fontFamily: "Arial, sans-serif",`);
        lines.push(`${indent}  fontSize: ${fontSize},`);
        lines.push(`${indent}  color: "#ffffff",`);
        lines.push(`${indent}  fontWeight: 800,`);
        lines.push(`${indent}  textTransform: "uppercase",`);
        lines.push(`${indent}  whiteSpace: "nowrap",`);
        lines.push(`${indent}  userSelect: "none",`);
        lines.push(`${indent}}}>`);
        lines.push(`${indent}  {${JSON.stringify(text)}}`);
        lines.push(`${indent}</div>`);
        break;
      }

      case "shape":
        lines.push(`${indent}{/* shape layer — TODO */}`);
        break;

      default:
        lines.push(`${indent}{/* unknown layer type "${layer.type}" — skipped */}`);
    }

    // Visibility gate closer (only for renderable layers)
    if (needsVisGate && !isCommentOnly) {
      lines.push(`      )}`);
    }
  }

  lines.push(`    </AbsoluteFill>`);
  lines.push(`  );`);
  lines.push(`};`);
  lines.push(``);
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
