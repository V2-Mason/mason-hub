---
name: video-replication
description: Use when replicating AE video templates to Remotion — AE export, JSON translation, frame-by-frame verification with autoresearch iteration loop
---

# AE → Remotion 视频特效复刻

## Overview

将 After Effects 模板精确复刻为 Remotion 代码。核心方法：AE 导出结构化 JSON → 逐层翻译为 JSX → 以 AE 原片为 ground truth 自动迭代至视觉一致。

## When to Use

- Mason 说"复刻视频"、"replicate video"、"视频模板"、"remotion 复刻"
- 需要将 AE 模板转为可编程、可参数化的 Remotion 组件
- 有 AE 原片 MP4 作为参考目标

**不适用：** 从零创作动画（不需要 AE 参考）、纯剪辑拼接（用 ffmpeg）

## Core Pattern

```
AE 模板 → export_ae_full.jsx → JSON → 翻译(手写/codegen) → Remotion 渲染
                                                                    ↓
                                                          autoresearch 循环
                                                          (对比参考帧 → 修代码 → 重渲染)
```

## 流程

### Phase 1: AE 导出

1. AE 中 **File → Scripts → Run Script File** → `export_ae_full.jsx`
2. 输出 `ae_full_export.json` 到桌面
3. 复制到项目目录

> `export_ae_full.jsx` 位置：`C:/Users/hangn/OneDrive/Desktop/export_ae_full.jsx`
> 输出格式：AE Full Export 2.0（含 baked expressions、cubicBezier、FOV）

### Phase 2: 分析 JSON

```bash
python "${CLAUDE_SKILL_DIR}/scripts/ae-summary.py" ae_full_export.json
```

逐 comp 检查：animated layers、Track Matte、3D camera、时间拉伸

### Phase 3: 翻译

| 方式 | 适用场景 |
|------|---------|
| 手写 | 复杂/需微调的模板 |
| codegen | 结构清晰的模板（`node tools/ae-to-remotion.mjs input.json output.jsx`） |

### Phase 4: 渲染

```bash
npx remotion render src/index.jsx <CompositionId> --output=output/result.mp4
```

### Phase 5: 自动迭代验证（autoresearch）

用 AE 原片作为 ground truth，自动循环修复：

```bash
# 1. 提取参考帧
python "${CLAUDE_SKILL_DIR}/scripts/extract-frames.py" reference.mp4 --out ref-frames/ --fps 29.97

# 2. 提取 Remotion 渲染帧
python "${CLAUDE_SKILL_DIR}/scripts/extract-frames.py" output/result.mp4 --out render-frames/ --fps 29.97

# 3. 逐帧对比，输出差异最大的帧
python "${CLAUDE_SKILL_DIR}/scripts/compare-frames.py" ref-frames/ render-frames/
```

**autoresearch 配置：**
- **Metric**: 逐帧 SSIM 均值（目标 > 0.95）
- **Verify**: 渲染 → 提取帧 → SSIM 对比
- **Modify**: 读 AE JSON 定位差异帧的层/属性 → 修改 JSX
- **Direction**: maximize SSIM

手动验证退回条件：SSIM > 0.95 但视觉上仍有违和感（缓动曲线、微妙时序）

## Quick Reference — 翻译检查清单

| # | 检查项 | 规则 |
|---|--------|------|
| 1 | Track Matte 配对 | matte 层 Position.Y 决定区域（Y<540=上半），不看 content 的 Y |
| 2 | 3D 透视 | Z 偏移 + 移动 camera = `zoom/(zoom+layerZ-camPosZ)` |
| 3 | 缩放链 | scale 只在一处应用，CSS transform 传递给子元素，不在 fontSize 重复 |
| 4 | frame matte 裁剪 | 被 shape matte 裁剪的文字 → `overflow:hidden` 容器 |
| 5 | Alpha Inverted | SVG mask 在 Remotion 不可靠，用直接着色或 Canvas |
| 6 | Precomp 硬边界 | precomp wrapper div 必须 `clipPath: "inset(0)"`，模拟 AE 固定尺寸裁剪 |
| 7 | SplitMatte 完成后 | t>=1 时用 `position: absolute` 包裹，不能返回裸 fragment |

## Common Mistakes

| 问题 | 根因 | 修法 |
|------|------|------|
| 绿色/内容铺满整屏 | 缺少 precomp 硬边界，camScale 溢出 | wrapper div 加 `clipPath: "inset(0)"` |
| 分屏完成后画面跳动 | SplitMatte 返回裸 fragment 进入 flex flow | t>=1 时 `position: absolute` 包裹 |
| 文字大小不对 | CSS transform scale 传递 + fontSize 重复缩放 | scale 只在一处应用 |
| overflow:hidden 不裁剪 | Chromium 不裁剪 transform:scale 子元素 | 用 `clipPath: "inset(0)"` 替代 |
| SVG mask 渲染空白 | Remotion headless 不支持 SVG mask/mask-image | 直接着色或 Canvas |
| bezier 缓动不对 | cubicBezier `[x,x,y,y]` 不是 CSS 格式 | speed=0 时转 `bez(outX, 0, inX, 1)` |

## 文件说明

| 路径 | 用途 |
|------|------|
| `scripts/ae-summary.py` | 解析 AE JSON，输出 comp 树 + 层级 + matte/camera/动画标记 |
| `scripts/extract-frames.py` | ffmpeg 提取视频帧到目录 |
| `scripts/compare-frames.py` | SSIM 逐帧对比，输出差异报告 |
| `reference/ae-json-format.md` | AE Full Export 2.0 JSON 格式文档 |
