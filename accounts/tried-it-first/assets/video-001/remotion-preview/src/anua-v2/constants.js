import { staticFile, Easing } from "remotion";

// === 全部参数由 OpenCV 测量 + Gemini 语义分析 + Gemini 视频对比反馈得出 ===

export const BG_COLOR = "#ffffff";

// 3D 翻转过渡：三卡同时绕 Y 轴翻转换内容（原片核心过渡）
// 翻转发生在 FLIP_START ~ FLIP_END，持续约 15 帧
export const FLIP_START = 119;
export const FLIP_END = 134;

// 三卡布局 (OpenCV, 归一化坐标) — 全程保持
export const THREE_CARD = {
  left:   { x: 0.208, y: 0.500, w: 0.279, h: 0.869 },
  center: { x: 0.500, y: 0.500, w: 0.281, h: 0.873 },
  right:  { x: 0.791, y: 0.500, w: 0.280, h: 0.871 },
};

// 颜色时间轴 (OpenCV 逐帧测量)
// Scene 1: f0-f119, Scene 2: f134-f270 (翻转后新颜色)
export const COLOR_TIMELINE = {
  left: {
    scene1: [
      { f: 0, c: "#438caf" }, { f: 8, c: "#438daf" }, { f: 16, c: "#4f90af" },
      { f: 25, c: "#4f8faf" }, { f: 33, c: "#c0917a" }, { f: 41, c: "#c99b84" },
      { f: 49, c: "#c79a82" }, { f: 57, c: "#c89982" }, { f: 65, c: "#ecc1b2" },
      { f: 74, c: "#e2b19e" }, { f: 82, c: "#eab29f" }, { f: 90, c: "#eab29f" },
      { f: 98, c: "#5f7f97" }, { f: 106, c: "#842425" }, { f: 115, c: "#c28447" },
    ],
    // 翻转后新颜色：从参考帧 14-15 提取（红/棕/暖色）
    scene2: [
      { f: 134, c: "#842425" }, { f: 150, c: "#c28447" }, { f: 180, c: "#c99b84" },
      { f: 210, c: "#ecc1b2" }, { f: 240, c: "#e2b19e" }, { f: 260, c: "#e2b19e" },
    ],
  },
  center: {
    scene1: [
      { f: 0, c: "#d69f36" }, { f: 8, c: "#d6a038" }, { f: 16, c: "#beab91" },
      { f: 25, c: "#4d1324" }, { f: 33, c: "#4d2f1a" }, { f: 41, c: "#4c321e" },
      { f: 49, c: "#413729" }, { f: 57, c: "#413729" }, { f: 65, c: "#478f91" },
      { f: 74, c: "#418482" }, { f: 82, c: "#3a516b" }, { f: 90, c: "#3a516b" },
      { f: 98, c: "#141517" }, { f: 106, c: "#131517" }, { f: 115, c: "#ffffff" },
    ],
    // 翻转后：白色/浅色调
    scene2: [
      { f: 134, c: "#ffffff" }, { f: 150, c: "#fdfdfd" }, { f: 180, c: "#fdfdfd" },
      { f: 210, c: "#ffffff" }, { f: 240, c: "#fdfdfd" }, { f: 260, c: "#fdfdfd" },
    ],
  },
  right: {
    scene1: [
      { f: 0, c: "#fdfdfd" }, { f: 8, c: "#fdfdfd" }, { f: 16, c: "#bdc3bc" },
      { f: 25, c: "#bdc3bc" }, { f: 33, c: "#b0aa98" }, { f: 41, c: "#c0bfb3" },
      { f: 49, c: "#dcd7cb" }, { f: 57, c: "#ddd7cb" }, { f: 65, c: "#cec0b8" },
      { f: 74, c: "#c6b8b0" }, { f: 82, c: "#ddc9c1" }, { f: 90, c: "#ddc9c1" },
      { f: 98, c: "#6d7e6c" }, { f: 106, c: "#556c55" }, { f: 115, c: "#cf600b" },
    ],
    // 翻转后：橙色调
    scene2: [
      { f: 134, c: "#cf600b" }, { f: 150, c: "#d6842a" }, { f: 180, c: "#d6842a" },
      { f: 210, c: "#cf600b" }, { f: 240, c: "#d6842a" }, { f: 260, c: "#d6842a" },
    ],
  },
};

// 场景组 — 全程三卡，两组内容，3D 翻转过渡
export const CONTENT_SCENES = {
  // Scene 1: 入场 → 内容展示
  scene1: [
    { start: 0, end: 7, content: false, deco: "none" },
    { start: 8, end: 48, content: true, deco: "dot_grid" },
    { start: 49, end: 57, content: false, deco: "none" },
    { start: 58, end: FLIP_START - 1, content: true, deco: "mixed" },
  ],
  // Scene 2: 翻转后新内容
  scene2: [
    { start: FLIP_END, end: FLIP_END + 5, content: false, deco: "none" },
    { start: FLIP_END + 6, end: 270, content: true, deco: "mixed" },
  ],
};

// 产品数据 — Scene 1 用 index 0/1/2, Scene 2 用 index 换序或新产品
export const PRODUCTS_SCENE1 = [
  { name: "ANUA Toner\nK-Beauty", subtitle: "Heartleaf 77% Soothing Toner\nCalm and Hydrate.", tagline: "Try It. Love It.", price: 25, salePrice: 18, img: staticFile("anua-cards/anua-toner.png"), accent: "#333333" },
  { name: "Soothing\nAmpoule", subtitle: "Repair and soothe\nyour skin barrier.", tagline: "Absolutely new product.\nAvailable now!", price: 22, salePrice: null, img: staticFile("anua-cards/anua-ampoule.png"), accent: "#FF3E3E" },
  { name: "Dark Spot\nCorrecting\nSerum", subtitle: "By Motion Canyon", tagline: "NEW\nNEW\nNEW", price: 24, salePrice: null, img: staticFile("anua-cards/anua-serum.png"), accent: "#333333" },
];

// Scene 2: 翻转后换序展示（模拟原片第二组运动鞋）
export const PRODUCTS_SCENE2 = [
  { name: "Dark Spot\nCorrecting\nSerum", subtitle: "Advanced dark spot\ncorrection formula.", tagline: "Best Seller!", price: 24, salePrice: 19, img: staticFile("anua-cards/anua-serum.png"), accent: "#333333" },
  { name: "ANUA Toner\nK-Beauty", subtitle: "Heartleaf 77% Soothing Toner\nCalm and Hydrate.", tagline: "Swipe Up", price: 25, salePrice: null, img: staticFile("anua-cards/anua-toner.png"), accent: "#333333" },
  { name: "Soothing\nAmpoule", subtitle: "Repair and soothe\nyour skin barrier.", tagline: "Swipe Up", price: 22, salePrice: null, img: staticFile("anua-cards/anua-ampoule.png"), accent: "#FF3E3E" },
];

// 向后兼容
export const PRODUCTS = PRODUCTS_SCENE1;

// Easing
export const OVERSHOOT = Easing.bezier(0.175, 0.885, 0.32, 1.275);

// 卡片位置名
export const CARD_POSITIONS = ["left", "center", "right"];
