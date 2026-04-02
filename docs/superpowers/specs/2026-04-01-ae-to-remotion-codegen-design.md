# AE-to-Remotion Code Generator (V1 - Title_01)

> 日期: 2026-04-01
> 状态: Approved
> 范围: 针对 Title_01 (fast typography) 模板的代码生成器

## 目标

写一个 Node 脚本 `ae-to-remotion.mjs`，读取 `ae_full_export.json`，自动生成一个可运行的 Remotion .jsx 文件。生成的代码结构与手写的 `AETitle.jsx` 一致，可读、可手动微调。

## 输入/输出

- **输入**: `ae_full_export.json` (AE Full Export 2.0 格式，含 baked expressions、cubicBezier、FOV)
- **输出**: `AETitleGenerated.jsx` — 完整的 Remotion 组件文件

## 数据结构

### JSON 顶层

```json
{
  "_info": "AE Full Export 2.0",
  "mainComp": "Title_01 (fast typography)",
  "comps": {
    "<id>": {
      "name": string,
      "width": number, "height": number,
      "fps": number, "totalFrames": number,
      "layers": Layer[],
      "cameras": Camera[]  // optional
    }
  }
}
```

### Layer 结构

```json
{
  "index": number,
  "name": string,
  "type": "text" | "solid" | "precomp" | "shape",
  "inFrame": number, "outFrame": number,
  "enabled": boolean,
  "threeDLayer": boolean,
  "transform": {
    "Position": Property,
    "Scale": Property,
    "Rotation": Property,
    "Opacity": Property,
    "Anchor Point": Property,
    // 3D layers also have X/Y/Z Rotation, Orientation
  },
  // precomp only:
  "sourceCompId": string,
  "stretch": number,  // percentage (111.11 means 1.1111x slower). Convert: multiplier = stretch / 100
  // matte:
  "trackMatteType": 5013 | 5014,  // Alpha | Alpha Inverted
  // text:
  "textContent": string | null,
  "effects": Effect[]
}
```

### Property 结构

```json
{
  "value": number | number[],
  "animated": boolean,
  "keyframes": [{
    "frame": number,
    "value": number | number[],
    "cubicBezier": [[x1, y1, x2, y2]],  // per-dimension, nested array (one [4] per dimension)
    "interpIn": "bezier" | "linear" | "hold",
    "interpOut": "bezier" | "linear" | "hold"
  }]
}
```

## 生成策略

### 1. Comp → React 组件

每个 comp 生成一个函数组件。命名规则：comp name 中非字母数字字符替换为 `_`，连续 `_` 合并，首字母大写。例如 `"Title_01 (fast typography)"` → `Comp_Title_01_fast_typography`。

```jsx
const Comp_unit_01 = ({ parentFrame }) => {
  const frame = parentFrame;  // 或经过 stretch/offset 映射
  return (
    <AbsoluteFill>
      {/* layers in reverse index order (AE bottom layer = first rendered) */}
    </AbsoluteFill>
  );
};
```

### 2. Keyframe 动画 → interpolate()

对每个 animated property：
- 提取所有 keyframe 的 frame 和 value
- 如果有 `cubicBezier`，在 keyframe 对之间生成 `Easing.bezier()` 分段
- 多维属性 (Position [x,y,z]) 拆成独立 interpolate 调用

```jsx
const posX = interpolate(frame, [0, 19], [960, 960], {
  extrapolateLeft: "clamp", extrapolateRight: "clamp",
  easing: Easing.bezier(0.529, 0, 0.107, 1),
});
```

### 3. Precomp 嵌套

precomp layer 生成子组件调用，传入映射后的 frame：

```jsx
// layer.inFrame = 0, layer.stretch = 111.11%
<Comp_Title_01_Main parentFrame={(frame - 0) / 1.1111} />
```

### 4. 时间拉伸

`stretch` 字段是百分比（100 = 正常），映射公式：
```
localFrame = (parentFrame - inFrame) / (stretch / 100)
```

### 5. 3D 相机透视

找到 Camera layer，提取 Position.Z 关键帧，生成透视缩放。Camera 的 camScale 作为全局透视包裹容器。

但个别 3D layer 有自己的 Z Position 动画（如 Title_01 中 PLACEHOLDER_02 的 Z 轨道），需要单独计算该层的 zScale = `zoom / (zoom - layerZ)`，与 camScale 独立。

```jsx
// 全局相机
const camZ = interpolate(frame, [...], [...], {...});
const zoom = 1866.667;  // from Camera zoom property
const camScale = zoom / (zoom - camZ);

// 有自身 Z 动画的层单独算
const placeZ = interpolate(frame, [...], [...], {...});
const placeZScale = zoom / (zoom - placeZ);

<div style={{ transform: `scale(${camScale})` }}>
  {/* 大部分 3D layers 只受 camScale */}
  {/* 有 Z 动画的层额外乘 zScale */}
  <div style={{ transform: `scale(${placeZScale})` }}>...</div>
</div>
```

### 6. Track Matte

`trackMatteType: 5013` (Alpha) — 当前层被上一层的形状裁剪
`trackMatteType: 5014` (Alpha Inverted) — 反向裁剪

V1 策略（hardcoded for Title_01）：Track Matte 的 CSS 实现方式无法从 JSON 数据自动推导，因为 matte 形状可能是任意路径。V1 对 Title_01 中出现的三种 matte 模式做 pattern matching：

1. **分屏 matte**（matte 层 Position.Y 接近 0 或 1080）→ 两个 `overflow: hidden` 的 div (上半/下半)，Y 偏移做动画
2. **矩形框 matte**（matte 层是 shape layer 且名含 "frame"）→ `overflow: hidden` 矩形容器
3. **Alpha Inverted（5014）**→ 白色 div 叠在上面

未来通用版需要用 Canvas mask 或 SVG clipPath 实现任意 matte 形状。

### 7. 文字层

读 `textContent`，生成 `<div>` + font style。

字号来源优先级：
1. `layer.textDocument.fontSize`（如果导出脚本包含）
2. 从 `AETitle.jsx` 手写版中已知的映射 hardcode（TEXT_01=587, TEXT_02/03/04=120）
3. 默认 100px fallback

V1 采用方案 2（hardcode），因为当前导出脚本的 textDocument 信息不完整。

### 8. 固态层

`type: "solid"` → `<div>` + `backgroundColor`。

## V1 不处理

- Effects（颜色控制、阴影等）— 大部分是视觉微调
- Shape layer 的复杂路径（frame 矩形用硬编码近似）
- Masks
- 混合模式 (blendMode) — 例外：`mixBlendMode: "difference"` 用于 CLEAN 文字镂空效果，在生成代码中 hardcode 此特例
- 空间贝塞尔 (spatialIn/Out) — 影响运动路径曲线，视觉差异小

## 文件位置

```
accounts/tried-it-first/assets/video-001/remotion-preview/
  tools/ae-to-remotion.mjs          # 生成脚本
  src/AETitleGenerated.jsx           # 生成输出
  src/AETitle.jsx                    # 手写版（对照参考）
```

## 使用方式

```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
node tools/ae-to-remotion.mjs path/to/ae_full_export.json src/AETitleGenerated.jsx
```

## 验收标准

1. 脚本读取 `ae_full_export.json`，无报错输出 `AETitleGenerated.jsx`
2. 生成的文件可直接被 Remotion 渲染（`npx remotion render RemotionRoot AETitleGenerated`）
3. 渲染结果与手写 `AETitle.jsx` 目测一致（分屏动画、文字出现时序、3D 推进、收尾动画）。容忍范围：动画时序和主要元素位置匹配，颜色/字号/细微视觉差异（如缺少 effects 的阴影）可接受
4. 生成的代码可读 — 有注释标注每个 comp/layer 名称
