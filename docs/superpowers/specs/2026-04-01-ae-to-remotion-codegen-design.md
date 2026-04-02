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
  "stretch": number,  // percentage, 100 = normal
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
    "cubicBezier": [[x1, x1, x2, x2]],  // per-dimension
    "interpIn": "bezier" | "linear" | "hold",
    "interpOut": "bezier" | "linear" | "hold"
  }]
}
```

## 生成策略

### 1. Comp → React 组件

每个 comp 生成一个函数组件：

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

找到 Camera layer，提取 Position.Z 关键帧，生成透视缩放：

```jsx
const camZ = interpolate(frame, [...], [...], {...});
const zoom = 1866.667;  // from comp FOV or Camera zoom
const camScale = zoom / (zoom - camZ);
// 包裹所有 3D layers
<div style={{ transform: `scale(${camScale})` }}>
```

### 6. Track Matte

`trackMatteType: 5013` (Alpha) — 当前层被上一层的形状裁剪
`trackMatteType: 5014` (Alpha Inverted) — 反向裁剪

生成策略：matte 层转为 CSS `clipPath` 或 `overflow: hidden` 容器包裹被遮罩层。

对 Title_01 的具体情况：
- unit_01 的分屏 matte → 两个 `overflow: hidden` 的 div (上半/下半)
- TEXT_02_comp 的 frame matte → `overflow: hidden` 矩形容器
- White Solid 的 Alpha Inverted → 白色 div 叠在上面

### 7. 文字层

读 `textContent`，生成 `<div>` + font style。字号从 effects 或 textDocument 提取。

### 8. 固态层

`type: "solid"` → `<div>` + `backgroundColor`。

## V1 不处理

- Effects（颜色控制、阴影等）— 大部分是视觉微调
- Shape layer 的复杂路径（frame 矩形用硬编码近似）
- Masks
- 混合模式 (blendMode)
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
3. 渲染结果与手写 `AETitle.jsx` 目测一致（分屏动画、文字出现时序、3D 推进、收尾动画）
4. 生成的代码可读 — 有注释标注每个 comp/layer 名称
