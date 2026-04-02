# AE Full Export 2.0 JSON 格式

> 由 `export_ae_full.jsx` 导出，包含 AE 项目完整结构

## 顶层结构

```json
{
  "version": "2.0",
  "project": { "name": "...", "fps": 29.97, "width": 1920, "height": 1080 },
  "comps": {
    "<compId>": {
      "name": "Title_01",
      "width": 1920, "height": 1080,
      "fps": 29.97, "duration": 5.0,
      "layers": [ ... ]
    }
  }
}
```

## Layer 结构

```json
{
  "name": "Scene_02_main",
  "type": "precomp | solid | text | shape | camera | null",
  "index": 2,
  "inPoint": 0, "outPoint": 5.0,
  "stretch": 100,
  "threeDLayer": true,
  "isTrackMatte": false,
  "trackMatteType": null | 5013 | 5014,
  "transform": { ... },
  "text": { ... },
  "shapes": [ ... ]
}
```

## Transform 属性

每个属性可以是静态值或动画：

```json
{
  "Position": { "value": [960, 540, 0], "animated": false },
  "Scale": { "value": [100, 100, 100], "animated": false },
  "Rotation": { "value": 0, "animated": false },
  "Opacity": { "value": 100, "animated": false },
  "Anchor Point": { "value": [960, 540, 0], "animated": false }
}
```

动画属性：

```json
{
  "Position": {
    "animated": true,
    "keyframes": [
      {
        "time": 0,
        "value": [960, 1083, 0],
        "cubicBezier": [0.529, 0.529, 0.107, 0.107]
      },
      {
        "time": 0.634,
        "value": [960, 540, 0]
      }
    ]
  }
}
```

## Track Matte 类型

| 值 | 含义 | CSS 等价 |
|----|------|---------|
| `5013` | Alpha Matte | 内容只在 matte 不透明处可见 |
| `5014` | Alpha Inverted Matte | 内容只在 matte 透明处可见 |

**配对规则**：IS_MATTE 层总是在 content 层的上方（index 更小）

## cubicBezier 格式

导出格式：`[outX, outX, inX, inX]`（speed=0 时的 influence 值）

转换为 CSS Easing.bezier：`bez(outX, 0, inX, 1)`

## Camera 层

```json
{
  "type": "camera",
  "cameraZoom": 1866.667,
  "transform": {
    "Position": { "animated": true, "keyframes": [...] }
  }
}
```

3D 层的视觉缩放公式：`zoom / (zoom + layerZ - cameraPosZ)`

## Precomp 层

`type: "precomp"` 的层引用另一个 comp。Precomp 有固定尺寸边界，内部内容不会超出。

关键属性：
- `stretch`: 时间拉伸百分比（100 = 正常速度）
- `inPoint` / `outPoint`: 在父 comp 中的可见时间范围
