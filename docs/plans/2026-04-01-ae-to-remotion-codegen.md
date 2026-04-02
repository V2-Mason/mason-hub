# AE-to-Remotion Code Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Node script that reads `ae_full_export.json` and generates a working Remotion .jsx file equivalent to the hand-written `AETitle.jsx`.

**Architecture:** Single-file Node script (`ae-to-remotion.mjs`) that traverses the JSON comp tree recursively, generating one React component per comp. Each component handles its layers' transforms via Remotion's `interpolate()` + `Easing.bezier()`. Special cases (Track Matte, 3D camera, time stretch) are pattern-matched for Title_01.

**Tech Stack:** Node.js (ESM), Remotion 4.x, no external dependencies for the generator itself.

**Spec:** `docs/superpowers/specs/2026-04-01-ae-to-remotion-codegen-design.md`

**Reference files:**
- `accounts/tried-it-first/assets/video-001/remotion-preview/src/AETitle.jsx` — hand-written target to match
- `C:/Users/hangn/OneDrive/Desktop/ae_full_export.json` — input data
- `accounts/tried-it-first/assets/video-001/remotion-preview/src/Root.jsx` — Remotion entry point

---

## Task 1: Scaffold — JSON loader + comp walker

**Files:**
- Create: `accounts/tried-it-first/assets/video-001/remotion-preview/tools/ae-to-remotion.mjs`

**Step 1: Create the script with JSON loading and comp tree traversal**

```js
#!/usr/bin/env node
// ae-to-remotion.mjs — AE Full Export JSON → Remotion JSX code generator (V1)
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const [,, inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error('Usage: node ae-to-remotion.mjs <input.json> <output.jsx>');
  process.exit(1);
}

const data = JSON.parse(readFileSync(resolve(inputPath), 'utf-8'));
const comps = data.comps;

// Find main comp by name
const mainCompId = Object.keys(comps).find(id => comps[id].name === data.mainComp);
if (!mainCompId) throw new Error(`Main comp "${data.mainComp}" not found`);

// Sanitize comp name → valid JS identifier
function safeName(name) {
  return name.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
}

// Collect all reachable comps from main (DFS)
const reachableComps = new Set();
function walkComps(compId) {
  if (reachableComps.has(compId)) return;
  reachableComps.add(compId);
  const comp = comps[compId];
  for (const layer of comp.layers) {
    if (layer.type === 'precomp' && layer.sourceCompId) {
      walkComps(String(layer.sourceCompId));
    }
  }
}
walkComps(mainCompId);

console.log(`Found ${reachableComps.size} reachable comps from "${data.mainComp}":`);
for (const id of reachableComps) {
  const c = comps[id];
  console.log(`  Comp_${safeName(c.name)}: ${c.layers.length} layers`);
}

// Placeholder output
writeFileSync(resolve(outputPath), '// TODO: generated code\n');
console.log(`Output: ${outputPath}`);
```

**Step 2: Run to verify comp tree**

```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
node tools/ae-to-remotion.mjs "C:/Users/hangn/OneDrive/Desktop/ae_full_export.json" src/AETitleGenerated.jsx
```

Expected: Lists 16 comps with sanitized names.

**Step 3: Commit**

```bash
git add tools/ae-to-remotion.mjs
git commit -m "feat(codegen): scaffold ae-to-remotion with JSON loader and comp walker"
```

---

## Task 2: Generate static layers (no animation)

Build the code generation for non-animated layers: solid colors, text content, precomp references, visibility (inFrame/outFrame).

**Files:**
- Modify: `accounts/tried-it-first/assets/video-001/remotion-preview/tools/ae-to-remotion.mjs`

**Step 1: Add code generation functions**

Replace the placeholder output with a full code generator. Key functions to add:

```js
// Generate the JSX header (imports)
function genHeader(mainCompName) {
  return `// Auto-generated from ae_full_export.json — ${mainCompName}
// Do not edit directly. Regenerate with: node tools/ae-to-remotion.mjs
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";

const bez = (x1, y1, x2, y2) => Easing.bezier(
  Math.max(0, Math.min(1, x1)),
  Math.max(-2, Math.min(2, y1)),
  Math.max(0, Math.min(1, x2)),
  Math.max(-2, Math.min(2, y2))
);
`;
}

// Generate one comp as a React component
function genComp(compId) {
  const comp = comps[compId];
  const name = `Comp_${safeName(comp.name)}`;
  
  // Filter enabled layers, sort by index descending (AE render order: highest index = bottom)
  const layers = comp.layers
    .filter(l => l.enabled !== false)
    .sort((a, b) => b.index - a.index);
  
  let code = `\nconst ${name} = ({ parentFrame = 0 }) => {\n`;
  code += `  const frame = parentFrame;\n`;
  code += `  return (\n    <AbsoluteFill>\n`;
  
  for (const layer of layers) {
    code += genLayer(layer, comp);
  }
  
  code += `    </AbsoluteFill>\n  );\n};\n`;
  return code;
}

// Generate a single layer
function genLayer(layer, parentComp) {
  const indent = '      ';
  let code = `${indent}{/* [${layer.index}] ${layer.name} (${layer.type}) f${layer.inFrame}-${layer.outFrame} */}\n`;
  
  // Visibility gate
  const hasTimeRange = layer.inFrame > 0 || layer.outFrame < parentComp.totalFrames;
  if (hasTimeRange) {
    code += `${indent}{frame >= ${layer.inFrame} && frame < ${layer.outFrame} && (\n`;
  }
  
  if (layer.type === 'precomp' && layer.sourceCompId) {
    const childName = `Comp_${safeName(comps[String(layer.sourceCompId)].name)}`;
    const stretch = (layer.stretch || 100) / 100;
    const offset = layer.startFrame || 0;
    const frameExpr = stretch !== 1
      ? `{(frame - ${offset}) / ${stretch}}`
      : offset > 0 ? `{frame - ${offset}}` : '{frame}';
    code += `${indent}  <${childName} parentFrame=${frameExpr} />\n`;
  } else if (layer.type === 'solid') {
    const color = layer.solidColor || '#000000';
    code += `${indent}  <div style={{ position: "absolute", inset: 0, backgroundColor: "${color}" }} />\n`;
  } else if (layer.type === 'text') {
    const text = layer.textContent || '';
    code += `${indent}  <div style={{ position: "absolute", display: "flex", alignItems: "center", justifyContent: "center", width: "100%", height: "100%", fontFamily: "Open Sans, Arial Black, Arial", fontWeight: 800, fontSize: 100 }}>${text}</div>\n`;
  } else if (layer.type === 'shape') {
    code += `${indent}  {/* shape layer — TODO */}\n`;
  }
  
  if (hasTimeRange) {
    code += `${indent})}\n`;
  }
  
  return code;
}
```

**Step 2: Generate the export and write file**

```js
// Build output
let output = genHeader(data.mainComp);

// Generate comps bottom-up (leaves first, so refs are defined before use)
const ordered = [...reachableComps].reverse();
for (const id of ordered) {
  output += genComp(id);
}

// Export main comp
const mainName = `Comp_${safeName(comps[mainCompId].name)}`;
output += `\nexport const AETitleGenerated = () => {\n`;
output += `  const frame = useCurrentFrame();\n`;
output += `  return <${mainName} parentFrame={frame} />;\n`;
output += `};\n`;

writeFileSync(resolve(outputPath), output);
console.log(`Generated ${outputPath}`);
```

**Step 3: Run and inspect output**

```bash
node tools/ae-to-remotion.mjs "C:/Users/hangn/OneDrive/Desktop/ae_full_export.json" src/AETitleGenerated.jsx
```

Verify: output has 16 component functions, precomp refs chain correctly, text content appears.

**Step 4: Commit**

```bash
git add tools/ae-to-remotion.mjs src/AETitleGenerated.jsx
git commit -m "feat(codegen): generate static layers — solid/text/precomp with time ranges"
```

---

## Task 3: Keyframe animation → interpolate()

**Files:**
- Modify: `tools/ae-to-remotion.mjs`

**Step 1: Add keyframe code generation**

```js
// Generate interpolate() call for an animated property
// Returns { varName, code } where code declares the variable
function genAnimatedProp(propName, prop, layerName, frameVar = 'frame') {
  const kfs = prop.keyframes;
  const varPrefix = safeName(layerName).toLowerCase();
  
  if (kfs.length < 2) {
    // Single keyframe = static
    return null;
  }
  
  const isMultiDim = Array.isArray(kfs[0].value);
  const dims = isMultiDim ? kfs[0].value.length : 1;
  const dimSuffixes = ['X', 'Y', 'Z'];
  const results = [];
  
  for (let dim = 0; dim < dims; dim++) {
    const varName = `${varPrefix}_${safeName(propName)}${isMultiDim ? dimSuffixes[dim] : ''}`;
    
    // For 2 keyframes: single interpolate
    // For 3+: chained ternary with per-segment interpolate
    if (kfs.length === 2) {
      const v0 = isMultiDim ? kfs[0].value[dim] : kfs[0].value;
      const v1 = isMultiDim ? kfs[1].value[dim] : kfs[1].value;
      const f0 = kfs[0].frame;
      const f1 = kfs[1].frame;
      
      // Get bezier from first keyframe's cubicBezier
      let easingStr = '';
      const cb = kfs[0].cubicBezier;
      if (cb && cb[0]) {
        // cubicBezier is [[x1,y1,x2,y2]] per-dimension or shared
        const b = cb[Math.min(dim, cb.length - 1)];
        if (b) easingStr = `, easing: bez(${b[0]}, ${b[1]}, ${b[2]}, ${b[3]})`;
      }
      
      const code = `  const ${varName} = interpolate(${frameVar}, [${f0}, ${f1}], [${v0}, ${v1}], { extrapolateLeft: "clamp", extrapolateRight: "clamp"${easingStr} });\n`;
      results.push({ varName, code, dim });
    } else {
      // Multi-segment: chained ternary
      let code = `  const ${varName} = `;
      for (let i = 0; i < kfs.length - 1; i++) {
        const v0 = isMultiDim ? kfs[i].value[dim] : kfs[i].value;
        const v1 = isMultiDim ? kfs[i + 1].value[dim] : kfs[i + 1].value;
        const f0 = kfs[i].frame;
        const f1 = kfs[i + 1].frame;
        
        let easingStr = '';
        const cb = kfs[i].cubicBezier;
        if (cb && cb[0]) {
          const b = cb[Math.min(dim, cb.length - 1)];
          if (b) easingStr = `, easing: bez(${b[0]}, ${b[1]}, ${b[2]}, ${b[3]})`;
        }
        
        const isLast = i === kfs.length - 2;
        if (i === 0) {
          code += `${frameVar} < ${f1}\n`;
        }
        code += `    ${i === 0 ? '?' : ':'} `;
        
        if (!isLast) {
          code += `${frameVar} < ${f1} ? interpolate(${frameVar}, [${f0}, ${f1}], [${v0}, ${v1}], { extrapolateLeft: "clamp", extrapolateRight: "clamp"${easingStr} })\n`;
        } else {
          code += `interpolate(${frameVar}, [${f0}, ${f1}], [${v0}, ${v1}], { extrapolateLeft: "clamp", extrapolateRight: "clamp"${easingStr} })\n`;
        }
      }
      // Final fallback = last value
      const lastVal = isMultiDim ? kfs[kfs.length - 1].value[dim] : kfs[kfs.length - 1].value;
      code += `    : ${lastVal};\n`;
      results.push({ varName, code, dim });
    }
  }
  
  return results;
}
```

**Step 2: Integrate into genLayer — apply animated transforms to style**

In `genLayer`, before generating the JSX element, check each transform property for animation. If animated, generate the `interpolate()` variable declarations and use them in the `style` / `transform` string.

Key transform mappings:
- `Position [x,y,z]` → `left: posX - anchorX`, `top: posY - anchorY`
- `Scale [sx,sy,sz]` → `transform: scale(sx/100, sy/100)`
- `Rotation` → `transform: rotate(${rot}deg)`
- `Opacity` → `opacity: op / 100`

**Step 3: Run and verify animated layers have interpolate() calls**

```bash
node tools/ae-to-remotion.mjs "C:/Users/hangn/OneDrive/Desktop/ae_full_export.json" src/AETitleGenerated.jsx
```

Check output: `Camera position` has 3-keyframe Position.Z interpolate, `TEXT_02/fresh` has 4-keyframe Position.Y, etc.

**Step 4: Commit**

```bash
git commit -am "feat(codegen): keyframe animation via interpolate() with bezier easing"
```

---

## Task 4: 3D Camera perspective

**Files:**
- Modify: `tools/ae-to-remotion.mjs`

**Step 1: Detect camera in comp, generate camZ + camScale**

In `genComp`, when processing `Scene_02_main`:
1. Find `type: "camera"` layer → extract `camera.Zoom.value` (1866.667)
2. Find camera's parent layer (`Camera position`) → extract Position.Z keyframes
3. Generate `camZ` interpolate + `camScale = zoom / (zoom - camZ)`
4. Wrap all 3D layers in a `<div style={{ transform: scale(camScale) }}>`

Also detect layers with their own Z Position animation (like PLACEHOLDER_02) and generate separate zScale.

**Step 2: Run and verify camera section in output**

Expected: `Scene_02_main` component has `camZ` variable + scaling wrapper div.

**Step 3: Commit**

```bash
git commit -am "feat(codegen): 3D camera perspective with zoom scaling"
```

---

## Task 5: Track Matte (split-screen + alpha)

**Files:**
- Modify: `tools/ae-to-remotion.mjs`

**Step 1: Implement matte pattern matching**

In the layer list processing, when a layer has `trackMatteType`:
- The **previous layer** in the array (one index higher) is the matte layer (usually DISABLED)
- Pair them: matte layer defines the clip region, matted layer is the content

For Title_01's three patterns:

**Pattern A: Split-screen matte** (unit_01, unit_02)
- Two matte+content pairs with same content comp
- Matte layers have Position.Y near 0 (top half) and near 1080 (bottom half)
- Generate: two `<div style={{ overflow: "hidden", height: 540 }}>` containers
- Content inside each gets Y-offset animation from the matte's Position

**Pattern B: Frame matte** (TEXT_02_comp)
- Shape layer named "frame" as matte
- Generate: `<div style={{ overflow: "hidden", width/height from shape }}>` wrapping the text comp

**Pattern C: Alpha Inverted** (5014)
- White Solid or BG layer
- Generate: positioned `<div>` with backgroundColor on top

**Step 2: Run and verify matte structures**

Check: `unit_01` has split-screen divs, `TEXT_02_comp` text layers wrapped in overflow containers.

**Step 3: Commit**

```bash
git commit -am "feat(codegen): Track Matte — split-screen, frame clip, alpha inverted"
```

---

## Task 6: Text styling + hardcoded details

**Files:**
- Modify: `tools/ae-to-remotion.mjs`

**Step 1: Add text style hardcodes for Title_01**

```js
// Title_01 text style overrides (from AETitle.jsx hand-written version)
const TEXT_STYLES = {
  'clean': { fontSize: 340, color: '#fcf9f9', letterSpacing: '-0.07em', mixBlendMode: 'difference' },
  'fresh': { fontSize: 60, color: '#fcf9f9', letterSpacing: '-0.07em' },
  '&smart': { fontSize: 60, color: '#fcf9f9', letterSpacing: '-0.07em' },
  'titles': { fontSize: 60, color: '#fcf9f9', letterSpacing: '-0.07em' },
  'from Mixkit': { fontSize: 70, color: '#101010', letterSpacing: '-0.07em' },
  'placeholder ': { fontSize: 12, color: '#222', opacity: 0.15 },
};
```

Apply these in `genLayer` when `layer.type === 'text'`.

**Step 2: Add placeholder image hardcode**

The PLACEHOLDER_01/02 comps render a green (#009a5a) rectangle with "PLACEHOLDER" text. Hardcode this as a helper component in the generated output.

**Step 3: Run and verify text styling**

Check: generated code has correct font sizes, colors, mixBlendMode for "CLEAN".

**Step 4: Commit**

```bash
git commit -am "feat(codegen): text styles + placeholder image hardcodes for Title_01"
```

---

## Task 7: Register in Root.jsx + render test

**Files:**
- Modify: `accounts/tried-it-first/assets/video-001/remotion-preview/src/Root.jsx`

**Step 1: Add AETitleGenerated composition**

```jsx
import { AETitleGenerated } from "./AETitleGenerated.jsx";

// In RemotionRoot:
<Composition id="AE-Title-Generated" component={AETitleGenerated} durationInFrames={150} fps={30} width={1920} height={1080} />
```

**Step 2: Render both versions side by side**

```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
npx remotion render RemotionRoot AE-Title --output=output/ae-title-handwritten.mp4
npx remotion render RemotionRoot AE-Title-Generated --output=output/ae-title-generated.mp4
```

**Step 3: Visual comparison**

Open both mp4s and compare. Check:
- Split-screen animations timing
- Text appearance order (CLEAN → FRESH → &SMART → TITLES → from Mixkit)
- 3D camera push-in effect
- White background wipe

**Step 4: Commit**

```bash
git commit -am "feat(codegen): register AETitleGenerated + render verification"
```

---

## Task 8: Fix discrepancies

This task is for iterating on visual differences found in Task 7. Expected issues:

- Timing offsets from stretch calculation rounding
- Position offsets from anchor point handling
- Missing opacity animations
- Shape layer "frame" sizing

For each discrepancy:
1. Identify which layer/property is off by comparing with AETitle.jsx
2. Fix the generation logic in ae-to-remotion.mjs
3. Regenerate + re-render
4. Commit fix

---

## Summary

| Task | What | Est. complexity |
|------|------|----------------|
| 1 | Scaffold: JSON loader + comp walker | Low |
| 2 | Static layers: solid/text/precomp | Medium |
| 3 | Keyframe animation → interpolate() | Medium-High |
| 4 | 3D camera perspective | Medium |
| 5 | Track Matte patterns | High |
| 6 | Text styling hardcodes | Low |
| 7 | Register + render test | Low |
| 8 | Fix discrepancies | Variable |
