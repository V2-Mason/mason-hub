# 确定性评分系统设计 — Remotion 视频复刻

> 日期：2026-03-31
> 状态：已批准
> 上下文：替换基于 Gemini 主观打分的评分系统，改用 OpenCV 属性提取 + 数值对比

## 问题

现有系统用 Gemini Vision 对比渲染帧和参考帧，打 0-100 分。波动 ±15-20 分，导致好的改动被错误丢弃、坏的改动被错误保留。根因：Gemini 既是分析师又是裁判，5 个主观维度 + LLM 自算加权 = 不可控。

## 解决方案

参考帧本身就是标准。用 OpenCV 从两边提取相同属性，数值对比，零波动。

## 架构

```
参考帧 ──→ Gemini(一次性) ──→ 元素粗定位 JSON
                                    ↓
参考帧 ──→ OpenCV ──→ 精确属性值 ──→ ground_truth.json (基准)
                                    
渲染帧 ──→ OpenCV ──→ 精确属性值 ──→ 对比 ground_truth ──→ 偏差报告 JSON
                                                            ↓
                                                       autoresearch
                                                            ↓
                                                    改代码 → 渲染 → 重测
```

## 两阶段流程

### 阶段 1：基准建立（一次性）

1. Gemini 分析 33 张参考帧 → 识别每帧卡片数量、每张卡的大致区域和颜色语义
2. OpenCV 对每帧精确测量 → 卡片包围盒坐标、背景主色、卡片主色、卡片尺寸、是否可见
3. 输出 `ground_truth.json` — 33 帧 × 5 属性 = 属性时间线

### 阶段 2：迭代优化（循环）

1. Remotion 渲染对应帧
2. OpenCV 用同样方法测量渲染帧属性
3. Python 计算偏差 → 输出偏差报告（位置差 px、色差 ΔE、尺寸差 %）
4. Autoresearch 读偏差报告 → 修改代码 → 渲染 → 重测 → keep/discard

## 提取属性（P0+P1）

| 属性 | 测量方法 | 偏差单位 |
|------|---------|---------|
| 卡片位置 (x, y) | 轮廓检测 → 包围盒中心 | px |
| 卡片大小 (w, h) | 包围盒宽高 | % |
| 卡片背景色 | 包围盒内区域 K-means 主色 | ΔE 色差 |
| 背景色 | 四角取样平均 | ΔE 色差 |
| 元素可见性 | 卡片是否被检测到 | 0/1 布尔 |

## 综合偏差分数

```python
score = 100 - (
    position_penalty * 0.30 +   # 位置偏差
    size_penalty * 0.20 +       # 大小偏差
    color_penalty * 0.30 +      # 颜色偏差
    bg_penalty * 0.10 +         # 背景色偏差
    visibility_penalty * 0.10   # 可见性偏差
)
```

每个 penalty 归一化到 0-100。分数完全确定性。

## 文件结构

```
scoring/
  extract_properties.py      # OpenCV 属性提取（通用）
  build_ground_truth.py       # 阶段1: Gemini粗定位 + OpenCV精测
  ground_truth.json           # 33帧属性基准
  score_frames.py             # 重写: 对比 ground_truth vs 渲染帧
  render_keyframes.sh         # 不变
  frame_map.json              # 保留
```

## Autoresearch 集成

Verify 命令不变：
```bash
cd remotion-preview && bash scoring/render_keyframes.sh >/dev/null 2>&1 && python scoring/score_frames.py
```

输出 stdout 一个 0-100 数字，内部从 Gemini 打分变为 OpenCV 数值对比。

## Gemini 角色变化

| | 旧 | 新 |
|---|---|---|
| 用途 | 每次迭代当裁判 | 一次性做属性粗定位 |
| 调用频率 | 每轮迭代 1 次 | 总共 1 次 |
| 输出 | 主观分数 | 结构化坐标/颜色数据 |

## 依赖

- Python: opencv-python, numpy, scikit-learn (K-means)
- google-genai (已安装)

## 未来扩展（P2）

如果 P0+P1 验证有效，可追加：
- 装饰元素颜色检测
- 文字区域位置检测
- 动画曲线对比（多帧属性变化率）
