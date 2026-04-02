---
name: video-replication
description: AE/视频模板复刻到 Remotion 的标准化流程。触发词：'复刻视频'、'replicate video'、'视频模板'、'remotion 复刻'
---

# 视频特效复刻工作流（路线 C）

> AE 导出 JSON → 逐层翻译 → Remotion 渲染

## 流程

### Phase 1: AE 导出

1. 在 AE 中打开模板项目
2. **File → Scripts → Run Script File** → 选择 `export_ae_full.jsx`（桌面）
3. 脚本自动导出 `ae_full_export.json` 到桌面
4. 把 JSON 复制到项目目录备用

> `export_ae_full.jsx` 位置：`C:/Users/hangn/OneDrive/Desktop/export_ae_full.jsx`
> 输出格式：AE Full Export 2.0（含 baked expressions、cubicBezier、FOV）

### Phase 2: 分析 JSON 结构

```bash
# 查看 comp 树和层级
python -c "
import json
with open('ae_full_export.json') as f:
    d = json.load(f)
for cid, comp in d['comps'].items():
    print(f'{comp[\"name\"]}: {len(comp[\"layers\"])} layers')
"
```

逐 comp 检查：
- 哪些层有动画（`animated: true`）
- 哪些层有 Track Matte（`trackMatteType`）
- 有没有 3D camera（`type: "camera"`）
- 有没有时间拉伸（`stretch != 100`）

### Phase 3: 翻译

两种方式：
- **手写翻译**：逐层读 JSON，手写 Remotion 代码（适合复杂/需要微调的模板）
- **代码生成器**：`node tools/ae-to-remotion.mjs input.json output.jsx`（适合结构清晰的模板）

> 代码生成器位置：`accounts/tried-it-first/assets/video-001/remotion-preview/tools/ae-to-remotion.mjs`

### Phase 4: 渲染 + 对比

```bash
cd accounts/tried-it-first/assets/video-001/remotion-preview
npx remotion render src/index.jsx <CompositionId> --output=output/result.mp4
```

### Phase 5: 逐帧验证

按优先级检查：
1. **时序** — 每个元素出现/消失的帧数
2. **方向** — 动画方向（上下/左右/缩放）
3. **比例** — 文字/框架/图片的相对大小
4. **缓动** — 运动曲线是否接近

渲染单帧对比：
```bash
npx remotion still src/index.jsx <CompositionId> --frame=17 --output=output/frames/f17.png
```

## 翻译检查清单

每次翻译时必须逐项检查：

| # | 检查项 | 规则 |
|---|--------|------|
| 1 | Track Matte 配对 | 用 matte 层的 Position.Y 决定显示区域（Y<540=上半），不看 content 的 Y |
| 2 | 3D 透视 | 有 Z 偏移的层 + 移动 camera = 动态公式 `zoom/(zoom+layerZ-camPosZ)` |
| 3 | 缩放链 | 每个 scale 只在一处应用。外层 CSS transform 会传递给子元素，不要在 fontSize 上重复 |
| 4 | frame matte 裁剪 | 被 shape matte 裁剪的文字层必须套 overflow:hidden 容器 |
| 5 | Alpha Inverted | SVG mask 在 Remotion 不可靠，用替代方案（直接着色或 Canvas） |
| 6 | Precomp 硬边界 | 每个代表 AE precomp 的 wrapper div 必须加 `clipPath: "inset(0)"`，模拟 precomp 固定尺寸裁剪。详见 [[ae-track-matte-precomp-bounds]] |
| 7 | SplitMatte 完成后定位 | t >= 1 时不能返回裸 fragment，必须用 `position: absolute` 容器包裹，否则掉入 flex flow 失去 z-stacking |

## 已知限制

- `overflow: hidden` 无法裁剪 `transform: scale()` 放大后的 absolute 子元素（Chromium 行为）
- cubicBezier 导出格式 `[x,x,y,y]` 不是直接的 CSS bezier，speed=0 时转为 `bez(outX, 0, inX, 1)`
- SVG `<mask>` 和 CSS `mask-image` 在 Remotion headless 渲染中不工作
