import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";

// === 全部参数由 OpenCV 测量 + Gemini 语义分析得出 ===

const SCENE_TRANSITION = 119; // 三卡→单卡精确转场帧
const BG_COLOR = "#ffffff";

// 三卡布局 (OpenCV 测量, 归一化)
const THREE_CARD = {
  left:   { x: 0.208, y: 0.500, w: 0.279, h: 0.869 },
  center: { x: 0.500, y: 0.500, w: 0.281, h: 0.873 },
  right:  { x: 0.791, y: 0.500, w: 0.280, h: 0.871 },
};
const SINGLE_CARD = { x: 0.500, y: 0.500, w: 0.287, h: 0.870 };

// 颜色时间轴 (OpenCV 逐帧测量)
const COLOR_TIMELINE = {
  left: [
    { f: 0, c: "#438caf" }, { f: 8, c: "#438daf" }, { f: 16, c: "#4f90af" },
    { f: 25, c: "#4f8faf" }, { f: 33, c: "#c0917a" }, { f: 41, c: "#c99b84" },
    { f: 49, c: "#c79a82" }, { f: 57, c: "#c89982" }, { f: 65, c: "#ecc1b2" },
    { f: 74, c: "#e2b19e" }, { f: 82, c: "#eab29f" }, { f: 90, c: "#eab29f" },
    { f: 98, c: "#5f7f97" }, { f: 106, c: "#842425" }, { f: 115, c: "#c28447" },
  ],
  center: [
    { f: 0, c: "#d69f36" }, { f: 8, c: "#d6a038" }, { f: 16, c: "#beab91" },
    { f: 25, c: "#4d1324" }, { f: 33, c: "#4d2f1a" }, { f: 41, c: "#4c321e" },
    { f: 49, c: "#413729" }, { f: 57, c: "#413729" }, { f: 65, c: "#478f91" },
    { f: 74, c: "#418482" }, { f: 82, c: "#3a516b" }, { f: 90, c: "#3a516b" },
    { f: 98, c: "#141517" }, { f: 106, c: "#131517" }, { f: 115, c: "#ffffff" },
  ],
  right: [
    { f: 0, c: "#fdfdfd" }, { f: 8, c: "#fdfdfd" }, { f: 16, c: "#bdc3bc" },
    { f: 25, c: "#bdc3bc" }, { f: 33, c: "#b0aa98" }, { f: 41, c: "#c0bfb3" },
    { f: 49, c: "#dcd7cb" }, { f: 57, c: "#ddd7cb" }, { f: 65, c: "#cec0b8" },
    { f: 74, c: "#c6b8b0" }, { f: 82, c: "#ddc9c1" }, { f: 90, c: "#ddc9c1" },
    { f: 98, c: "#6d7e6c" }, { f: 106, c: "#556c55" }, { f: 115, c: "#cf600b" },
  ],
  single: [
    { f: 119, c: "#d69f36" }, { f: 123, c: "#d69f36" }, { f: 131, c: "#bfae9a" },
    { f: 139, c: "#7b7268" }, { f: 147, c: "#151519" }, { f: 155, c: "#131517" },
    { f: 164, c: "#7b7268" }, { f: 172, c: "#fdfdfd" }, { f: 180, c: "#bac1b9" },
    { f: 188, c: "#bec3bc" }, { f: 196, c: "#bec3bc" }, { f: 205, c: "#bec3bc" },
    { f: 213, c: "#bec3bc" }, { f: 221, c: "#bec3bc" }, { f: 237, c: "#bec3bc" },
    { f: 254, c: "#bec4bd" }, { f: 262, c: "#bec3bc" },
  ],
};

// 场景组定义 (Gemini 语义分析)
// A(f0-7): 纯色  B(f8-48): 内容+dot_grid  C(f49-57): 纯色闪切  D(f58-119): 第二套内容
// E(f119-123): 过渡  F(f124-171): 深色单卡  G(f172): 白闪  H(f173-270): 绿灰卡
const CONTENT_SCENES = {
  threeCard: [
    { start: 0, end: 7, content: false, deco: "none" },
    { start: 8, end: 48, content: true, deco: "dot_grid" },
    { start: 49, end: 57, content: false, deco: "none" },
    { start: 58, end: 119, content: true, deco: "mixed" },
  ],
  singleCard: [
    { start: 119, end: 123, content: false, deco: "none", productIdx: 1 },
    { start: 124, end: 171, content: true, deco: "mixed", productIdx: 1 },
    { start: 172, end: 172, content: false, deco: "none", productIdx: 2 },
    { start: 173, end: 270, content: true, deco: "chevron", productIdx: 2 },
  ],
};

// 产品数据
const PRODUCTS = [
  {
    name: "ANUA Toner\nK-Beauty",
    subtitle: "Heartleaf 77% Soothing Toner\nCalm and Hydrate.",
    tagline: "Try It. Love It.",
    price: 25, salePrice: 18,
    img: staticFile("anua-cards/anua-toner.png"),
    accent: "#333333",
  },
  {
    name: "Soothing\nAmpoule",
    subtitle: "Repair and soothe\nyour skin barrier.",
    tagline: "Absolutely new product.\nAvailable now!",
    price: 22, salePrice: null,
    img: staticFile("anua-cards/anua-ampoule.png"),
    accent: "#FF3E3E",
  },
  {
    name: "Dark Spot\nCorrecting\nSerum",
    subtitle: "By Motion Canyon",
    tagline: "NEW\nNEW\nNEW",
    price: 24, salePrice: null,
    img: staticFile("anua-cards/anua-serum.png"),
    accent: "#333333",
  },
];

// === 工具函数 ===

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function rgbToHex(r, g, b) {
  return "#" + [r, g, b].map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
}

function lerpColor(frame, keyframes) {
  if (!keyframes.length) return "#000000";
  if (frame <= keyframes[0].f) return keyframes[0].c;
  if (frame >= keyframes[keyframes.length - 1].f) return keyframes[keyframes.length - 1].c;
  for (let i = 0; i < keyframes.length - 1; i++) {
    if (frame >= keyframes[i].f && frame <= keyframes[i + 1].f) {
      const t = (frame - keyframes[i].f) / (keyframes[i + 1].f - keyframes[i].f);
      const [r1, g1, b1] = hexToRgb(keyframes[i].c);
      const [r2, g2, b2] = hexToRgb(keyframes[i + 1].c);
      return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
    }
  }
  return keyframes[keyframes.length - 1].c;
}

function getCurrentScene(frame, scenes) {
  for (const s of scenes) {
    if (frame >= s.start && frame <= s.end) return s;
  }
  return scenes[scenes.length - 1];
}

// === 主组件 ===
export const AnuaPromo = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const isThreeCard = frame < SCENE_TRANSITION;
  const transT = interpolate(frame, [SCENE_TRANSITION - 4, SCENE_TRANSITION + 4], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: BG_COLOR }}>
      {/* 三卡 */}
      {frame < SCENE_TRANSITION + 8 &&
        ["left", "center", "right"].map((pos, i) => (
          <Card3
            key={pos}
            pos={pos}
            index={i}
            frame={frame}
            w={width}
            h={height}
            fadeOut={isThreeCard ? 0 : transT}
          />
        ))}

      {/* 单卡 */}
      {frame >= SCENE_TRANSITION - 4 && (
        <Card1
          frame={frame}
          w={width}
          h={height}
          fadeIn={transT}
        />
      )}
    </AbsoluteFill>
  );
};

// === 三卡模式 ===
const Card3 = ({ pos, index, frame, w, h, fadeOut }) => {
  const layout = THREE_CARD[pos];
  const cW = layout.w * w;
  const cH = layout.h * h;
  const cX = layout.x * w - cW / 2;
  const cY = layout.y * h - cH / 2;

  const bgColor = lerpColor(frame, COLOR_TIMELINE[pos]);
  const scene = getCurrentScene(frame, CONTENT_SCENES.threeCard);
  const showContent = scene.content;
  const decoType = scene.deco;
  const product = PRODUCTS[index];

  // 内容出现/消失过渡
  const contentFadeIn = showContent
    ? interpolate(frame, [scene.start, scene.start + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0; // 无内容场景直接隐藏

  const floatY = Math.sin(frame / 20 + index * 2) * 4;
  const productRot = Math.sin(frame / 25 + index) * 3;

  return (
    <div
      style={{
        position: "absolute",
        left: cX,
        top: cY + floatY,
        width: cW,
        height: cH,
        borderRadius: 10,
        backgroundColor: bgColor,
        overflow: "hidden",
        opacity: 1 - fadeOut,
        boxShadow: "0 6px 25px rgba(0,0,0,0.12)",
        border: "1px solid rgba(0,0,0,0.08)",
      }}
    >
      <Deco type={decoType} frame={frame} index={index} accent={product.accent} cW={cW} />

      <div style={{ opacity: contentFadeIn, position: "relative", width: "100%", height: "100%" }}>
        <PriceTag product={product} cW={cW} frame={frame} />

        <div style={{ position: "absolute", top: "12%", left: "5%", right: "5%", color: index === 1 ? "#ccc" : "#333", fontFamily: "Arial", fontSize: cW * 0.035, fontWeight: 600, fontStyle: "italic", whiteSpace: "pre-line" }}>
          {product.tagline}
        </div>

        <div style={{ position: "absolute", top: "28%", left: "50%", transform: `translateX(-50%) rotate(${productRot}deg)`, zIndex: 5 }}>
          <Img src={product.img} style={{ width: cW * 0.55, height: cW * 0.55, objectFit: "contain", filter: "drop-shadow(0 5px 12px rgba(0,0,0,0.12))" }} />
        </div>

        <div style={{ position: "absolute", bottom: "14%", left: "5%", right: "5%", color: index === 1 ? "#fff" : "#1a1a1a", fontFamily: "Arial Black, Arial", fontSize: cW * 0.06, fontWeight: 900, lineHeight: 1.1, whiteSpace: "pre-line" }}>
          {product.name}
        </div>

        <div style={{ position: "absolute", bottom: "4%", left: "5%", right: "5%", color: index === 1 ? "#aaa" : "#555", fontFamily: "Arial", fontSize: cW * 0.028, lineHeight: 1.3, whiteSpace: "pre-line" }}>
          {product.subtitle}
        </div>

        {index === 1 && (
          <div style={{ position: "absolute", bottom: "2%", width: "100%", textAlign: "center", color: "#fff", fontFamily: "Georgia", fontSize: cW * 0.055, fontWeight: 700, fontStyle: "italic" }}>
            Swipe Up
          </div>
        )}
      </div>
    </div>
  );
};

// === 单卡模式 ===
const Card1 = ({ frame, w, h, fadeIn }) => {
  const cW = SINGLE_CARD.w * w;
  const cH = SINGLE_CARD.h * h;
  const cX = SINGLE_CARD.x * w - cW / 2;
  const cY = SINGLE_CARD.y * h - cH / 2;

  const bgColor = lerpColor(frame, COLOR_TIMELINE.single);
  const scene = getCurrentScene(frame, CONTENT_SCENES.singleCard);
  const showContent = scene.content;
  const decoType = scene.deco;
  const productIdx = scene.productIdx || 1;
  const product = PRODUCTS[productIdx];

  const contentFadeIn = showContent
    ? interpolate(frame, [scene.start, scene.start + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;

  const floatY = Math.sin(frame / 15) * 5;
  const productRot = Math.sin(frame / 20) * 4;

  return (
    <div
      style={{
        position: "absolute",
        left: cX,
        top: cY,
        width: cW,
        height: cH,
        borderRadius: 10,
        backgroundColor: bgColor,
        overflow: "hidden",
        opacity: fadeIn,
        boxShadow: "0 8px 35px rgba(0,0,0,0.18)",
      }}
    >
      <Deco type={decoType} frame={frame} index={productIdx} accent={product.accent} cW={cW} />

      <div style={{ opacity: contentFadeIn, position: "relative", width: "100%", height: "100%" }}>
        <PriceTag product={product} cW={cW} frame={frame} />

        <div style={{ position: "absolute", top: "10%", left: "5%", right: "30%", color: productIdx === 1 ? "#ccc" : "#333", fontFamily: "Arial", fontSize: cW * 0.04, fontWeight: 600, fontStyle: "italic", whiteSpace: "pre-line" }}>
          {product.tagline}
        </div>

        <div style={{ position: "absolute", top: "28%", left: "50%", transform: `translateX(-50%) translateY(${floatY}px) rotate(${productRot}deg)`, zIndex: 5 }}>
          <Img src={product.img} style={{ width: cW * 0.58, height: cW * 0.58, objectFit: "contain", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.18))" }} />
        </div>

        <div style={{ position: "absolute", bottom: "14%", left: "5%", right: "5%", color: productIdx === 1 ? "#fff" : "#1a1a1a", fontFamily: "Arial Black, Arial", fontSize: cW * 0.07, fontWeight: 900, lineHeight: 1.1, whiteSpace: "pre-line" }}>
          {product.name}
        </div>

        <div style={{ position: "absolute", bottom: "4%", left: "5%", right: "5%", color: productIdx === 1 ? "#aaa" : "#555", fontFamily: "Arial", fontSize: cW * 0.033, whiteSpace: "pre-line" }}>
          {product.subtitle}
        </div>

        {productIdx === 1 && (
          <div style={{ position: "absolute", bottom: "2%", width: "100%", textAlign: "center", color: "#fff", fontFamily: "Georgia", fontSize: cW * 0.06, fontWeight: 700, fontStyle: "italic" }}>
            Swipe Up
          </div>
        )}
      </div>
    </div>
  );
};

// === 价格标签 ===
const PriceTag = ({ product, cW, frame }) => (
  <div style={{ position: "absolute", top: "3%", right: "4%", background: product.accent, color: "#fff", padding: "4px 12px", borderRadius: 6, fontFamily: "Arial", fontWeight: 900, fontSize: cW * 0.06, zIndex: 10 }}>
    {product.price}$
    {product.salePrice && (
      <div style={{ fontSize: cW * 0.03, opacity: 0.8 }}>
        <span style={{ textDecoration: "line-through" }}>{product.salePrice}$</span> sale
      </div>
    )}
  </div>
);

// === 装饰层 ===
const Deco = ({ type, frame, index, accent, cW }) => {
  if (type === "none") return null;

  if (type === "dot_grid") {
    return (
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `radial-gradient(${accent}20 2px, transparent 0)`,
        backgroundSize: "14px 14px",
        backgroundPosition: `${frame * 0.5}px ${frame * 0.3}px`,
        opacity: 0.5,
      }} />
    );
  }

  if (type === "chevron") {
    return (
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `
          linear-gradient(135deg, ${accent}12 25%, transparent 25%),
          linear-gradient(225deg, ${accent}12 25%, transparent 25%),
          linear-gradient(315deg, ${accent}12 25%, transparent 25%),
          linear-gradient(45deg, ${accent}12 25%, transparent 25%)
        `,
        backgroundSize: "20px 20px",
        backgroundPosition: `0 0, 0 10px, 10px -10px, -10px 0`,
        opacity: 0.4,
        transform: `translateY(${frame * 0.4}px)`,
      }} />
    );
  }

  // "mixed" = stripes + dots
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{
          position: "absolute",
          top: `${2 + i * 3}%`,
          [index % 2 === 0 ? "right" : "left"]: "-1%",
          width: cW * 0.12,
          height: 3,
          backgroundColor: accent,
          transform: `rotate(-25deg) translateX(${Math.sin((frame + i * 15) / 12) * 5}px)`,
          borderRadius: 2,
          opacity: 0.7,
        }} />
      ))}
      <div style={{
        position: "absolute",
        bottom: 0, right: 0,
        width: "40%", height: "25%",
        backgroundImage: `radial-gradient(${accent}18 1.5px, transparent 0)`,
        backgroundSize: "10px 10px",
        backgroundPosition: `${frame * 0.3}px ${frame * 0.2}px`,
        opacity: 0.4,
      }} />
    </>
  );
};
