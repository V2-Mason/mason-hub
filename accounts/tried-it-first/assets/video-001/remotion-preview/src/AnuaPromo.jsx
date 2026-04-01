import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";

// === 从 animation_params.json 提取的精确参数 ===
// 所有数值由 OpenCV 从 33 张参考帧测量得出，非手调

const SCENE_CHANGE = 119; // 三卡→单卡转场帧 (精确测量)
const BG_COLOR = "#ffffff";

// 三卡阶段：每张卡的颜色关键帧 (从参考帧测量)
const CARD_COLOR_KEYFRAMES = {
  left: [
    { f: 0, color: "#438caf" },
    { f: 25, color: "#4f8faf" },
    { f: 41, color: "#448eaf" },
    { f: 65, color: "#c0917a" },
    { f: 82, color: "#eab29f" },
    { f: 98, color: "#dca48b" },
    { f: 115, color: "#c28447" },
  ],
  center: [
    { f: 0, color: "#d69f36" },
    { f: 25, color: "#4d1324" },
    { f: 49, color: "#413729" },
    { f: 65, color: "#3a516b" },
    { f: 82, color: "#3a516b" },
    { f: 98, color: "#b8752a" },
    { f: 115, color: "#ffffff" },
  ],
  right: [
    { f: 0, color: "#fdfdfd" },
    { f: 25, color: "#bdc3bc" },
    { f: 49, color: "#737f74" },
    { f: 65, color: "#ddc9c1" },
    { f: 82, color: "#ddc9c1" },
    { f: 98, color: "#8e9a89" },
    { f: 115, color: "#cf600b" },
  ],
};

// 单卡阶段颜色关键帧
const SINGLE_CARD_COLORS = [
  { f: 123, color: "#d69f36" },
  { f: 139, color: "#151519" },
  { f: 155, color: "#131517" },
  { f: 180, color: "#b5b08f" },
  { f: 205, color: "#bec3bc" },
  { f: 237, color: "#bdc2bc" },
  { f: 262, color: "#bec3bc" },
];

// 卡片布局参数 (归一化到画面比例)
const CARD_LAYOUT = {
  left:   { x: 0.208, y: 0.500, w: 0.279, h: 0.869 },
  center: { x: 0.500, y: 0.500, w: 0.281, h: 0.873 },
  right:  { x: 0.791, y: 0.500, w: 0.280, h: 0.871 },
  single: { x: 0.500, y: 0.500, w: 0.281, h: 0.870 },
};

// 产品数据
const PRODUCTS = [
  {
    name: "ANUA Toner\nK-Beauty",
    subtitle: "Heartleaf 77% Soothing Toner\nCalm and Hydrate.",
    tagline: "Try It. Love It.",
    price: 25,
    salePrice: 18,
    img: staticFile("anua-cards/anua-toner.png"),
    accent: "#333333",
  },
  {
    name: "Soothing\nAmpoule",
    subtitle: "Repair and soothe\nyour skin barrier.",
    tagline: "Absolutely new product.\nAvailable now!",
    price: 22,
    salePrice: null,
    img: staticFile("anua-cards/anua-ampoule.png"),
    accent: "#FF3E3E",
  },
  {
    name: "Dark Spot\nCorrecting\nSerum",
    subtitle: "By Motion Canyon",
    tagline: "NEW\nNEW\nNEW",
    price: 24,
    salePrice: null,
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

function interpolateColor(frame, keyframes) {
  if (keyframes.length === 0) return "#000000";
  if (frame <= keyframes[0].f) return keyframes[0].color;
  if (frame >= keyframes[keyframes.length - 1].f) return keyframes[keyframes.length - 1].color;

  for (let i = 0; i < keyframes.length - 1; i++) {
    if (frame >= keyframes[i].f && frame <= keyframes[i + 1].f) {
      const t = (frame - keyframes[i].f) / (keyframes[i + 1].f - keyframes[i].f);
      const [r1, g1, b1] = hexToRgb(keyframes[i].color);
      const [r2, g2, b2] = hexToRgb(keyframes[i + 1].color);
      return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
    }
  }
  return keyframes[keyframes.length - 1].color;
}

// === 主组件 ===
export const AnuaPromo = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const isThreeCard = frame < SCENE_CHANGE;

  // 转场过渡 (10帧过渡)
  const transitionT = interpolate(
    frame,
    [SCENE_CHANGE - 5, SCENE_CHANGE + 5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ background: BG_COLOR }}>
      {/* 三卡模式 */}
      {frame < SCENE_CHANGE + 10 &&
        ["left", "center", "right"].map((pos, i) => (
          <ThreeCardItem
            key={pos}
            position={pos}
            product={PRODUCTS[i]}
            index={i}
            frame={frame}
            width={width}
            height={height}
            fadeOut={transitionT}
            isTransitioning={!isThreeCard}
          />
        ))}

      {/* 单卡模式 */}
      {frame >= SCENE_CHANGE - 5 && (
        <SingleCardItem
          frame={frame}
          width={width}
          height={height}
          fadeIn={transitionT}
          products={PRODUCTS}
        />
      )}
    </AbsoluteFill>
  );
};

// === 三卡阶段的单张卡 ===
const ThreeCardItem = ({ position, product, index, frame, width, height, fadeOut, isTransitioning }) => {
  const layout = CARD_LAYOUT[position];
  const colorKfs = CARD_COLOR_KEYFRAMES[position];

  const cardW = layout.w * width;
  const cardH = layout.h * height;
  const cardX = layout.x * width - cardW / 2;
  const cardY = layout.y * height - cardH / 2;

  const bgColor = interpolateColor(frame, colorKfs);

  // 内容在 frame 5 后逐渐出现
  const contentOpacity = interpolate(frame, [3, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 微悬浮
  const floatY = Math.sin(frame / 20 + index * 2) * 5;

  // 产品图微旋转
  const productRotation = Math.sin(frame / 25 + index) * 3;

  return (
    <div
      style={{
        position: "absolute",
        left: cardX,
        top: cardY + floatY,
        width: cardW,
        height: cardH,
        borderRadius: 12,
        backgroundColor: bgColor,
        overflow: "hidden",
        opacity: isTransitioning ? 1 - fadeOut : 1,
        boxShadow: "0 8px 30px rgba(0,0,0,0.15)",
      }}
    >
      {/* 装饰条纹 */}
      <DecoStripes index={index} frame={frame} accent={product.accent} cardW={cardW} />

      {/* 内容层 — frame 5 后出现 */}
      <div style={{ opacity: contentOpacity, position: "relative", width: "100%", height: "100%" }}>
        {/* 价格标签 */}
        <div
          style={{
            position: "absolute",
            top: "3%",
            right: "4%",
            background: product.accent,
            color: "white",
            padding: "4px 12px",
            borderRadius: 6,
            fontFamily: "Arial, sans-serif",
            fontWeight: 900,
            fontSize: cardW * 0.065,
            zIndex: 10,
          }}
        >
          {product.price}$
          {product.salePrice && (
            <div style={{ fontSize: cardW * 0.035, opacity: 0.8 }}>
              <span style={{ textDecoration: "line-through" }}>{product.salePrice}$</span> sale
            </div>
          )}
        </div>

        {/* Tagline */}
        <div
          style={{
            position: "absolute",
            top: "12%",
            left: "5%",
            right: "5%",
            color: index === 1 ? "#ccc" : "#333",
            fontFamily: "Arial, sans-serif",
            fontSize: cardW * 0.035,
            fontWeight: 600,
            fontStyle: "italic",
            whiteSpace: "pre-line",
          }}
        >
          {product.tagline}
        </div>

        {/* 产品图 */}
        <div
          style={{
            position: "absolute",
            top: "28%",
            left: "50%",
            transform: `translateX(-50%) rotate(${productRotation}deg)`,
            zIndex: 5,
          }}
        >
          <Img
            src={product.img}
            style={{
              width: cardW * 0.55,
              height: cardW * 0.55,
              objectFit: "contain",
              filter: "drop-shadow(0 6px 15px rgba(0,0,0,0.15))",
            }}
          />
        </div>

        {/* 产品名称 */}
        <div
          style={{
            position: "absolute",
            bottom: "15%",
            left: "5%",
            right: "5%",
            color: index === 1 ? "white" : "#1a1a1a",
            fontFamily: "Arial Black, Arial, sans-serif",
            fontSize: cardW * 0.065,
            fontWeight: 900,
            lineHeight: 1.1,
            whiteSpace: "pre-line",
          }}
        >
          {product.name}
        </div>

        {/* 副标题 */}
        <div
          style={{
            position: "absolute",
            bottom: "4%",
            left: "5%",
            right: "5%",
            color: index === 1 ? "#aaa" : "#555",
            fontFamily: "Arial, sans-serif",
            fontSize: cardW * 0.03,
            lineHeight: 1.4,
            whiteSpace: "pre-line",
          }}
        >
          {product.subtitle}
        </div>

        {/* 中间卡底部 CTA */}
        {index === 1 && (
          <div
            style={{
              position: "absolute",
              bottom: "3%",
              left: 0,
              right: 0,
              textAlign: "center",
              color: "white",
              fontFamily: "Georgia, serif",
              fontSize: cardW * 0.06,
              fontWeight: 700,
              fontStyle: "italic",
            }}
          >
            Swipe Up
          </div>
        )}
      </div>
    </div>
  );
};

// === 单卡阶段 ===
const SingleCardItem = ({ frame, width, height, fadeIn, products }) => {
  const layout = CARD_LAYOUT.single;
  const cardW = layout.w * width;
  const cardH = layout.h * height;
  const cardX = layout.x * width - cardW / 2;
  const cardY = layout.y * height - cardH / 2;

  const bgColor = interpolateColor(frame, SINGLE_CARD_COLORS);

  // 选择显示哪个产品 (中间卡先，然后右卡)
  const productIndex = frame < 180 ? 1 : 2;
  const product = products[productIndex];

  // 产品图微动
  const floatY = Math.sin(frame / 15) * 6;
  const rotation = Math.sin(frame / 20) * 4;

  return (
    <div
      style={{
        position: "absolute",
        left: cardX,
        top: cardY,
        width: cardW,
        height: cardH,
        borderRadius: 12,
        backgroundColor: bgColor,
        overflow: "hidden",
        opacity: fadeIn,
        boxShadow: "0 10px 40px rgba(0,0,0,0.2)",
      }}
    >
      {/* 装饰 */}
      <DecoStripes index={productIndex} frame={frame} accent={product.accent} cardW={cardW} />

      {/* 价格 */}
      <div
        style={{
          position: "absolute",
          top: "3%",
          right: "4%",
          background: product.accent,
          color: "white",
          padding: "6px 16px",
          borderRadius: 8,
          fontFamily: "Arial, sans-serif",
          fontWeight: 900,
          fontSize: cardW * 0.08,
          zIndex: 10,
        }}
      >
        {product.price + Math.floor(interpolate(frame, [SCENE_CHANGE, SCENE_CHANGE + 30], [0, 8], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))}$
      </div>

      {/* Tagline */}
      <div
        style={{
          position: "absolute",
          top: "12%",
          left: "5%",
          right: "35%",
          color: productIndex === 1 ? "#ccc" : "#333",
          fontFamily: "Arial, sans-serif",
          fontSize: cardW * 0.04,
          fontWeight: 600,
          fontStyle: "italic",
          whiteSpace: "pre-line",
        }}
      >
        {product.tagline}
      </div>

      {/* 产品图 */}
      <div
        style={{
          position: "absolute",
          top: "30%",
          left: "50%",
          transform: `translateX(-50%) translateY(${floatY}px) rotate(${rotation}deg)`,
          zIndex: 5,
        }}
      >
        <Img
          src={product.img}
          style={{
            width: cardW * 0.6,
            height: cardW * 0.6,
            objectFit: "contain",
            filter: "drop-shadow(0 8px 20px rgba(0,0,0,0.2))",
          }}
        />
      </div>

      {/* 名称 */}
      <div
        style={{
          position: "absolute",
          bottom: "15%",
          left: "5%",
          right: "5%",
          color: productIndex === 1 ? "white" : "#1a1a1a",
          fontFamily: "Arial Black, Arial, sans-serif",
          fontSize: cardW * 0.075,
          fontWeight: 900,
          lineHeight: 1.1,
          whiteSpace: "pre-line",
        }}
      >
        {product.name}
      </div>

      {/* 底部 */}
      <div
        style={{
          position: "absolute",
          bottom: "3%",
          left: "5%",
          right: "5%",
          color: productIndex === 1 ? "#aaa" : "#555",
          fontFamily: "Arial, sans-serif",
          fontSize: cardW * 0.035,
          whiteSpace: "pre-line",
        }}
      >
        {product.subtitle}
      </div>

      {productIndex === 1 && (
        <div
          style={{
            position: "absolute",
            bottom: "2%",
            left: 0,
            right: 0,
            textAlign: "center",
            color: "white",
            fontFamily: "Georgia, serif",
            fontSize: cardW * 0.065,
            fontWeight: 700,
            fontStyle: "italic",
          }}
        >
          Swipe Up
        </div>
      )}
    </div>
  );
};

// === 装饰条纹 ===
const DecoStripes = ({ index, frame, accent, cardW }) => {
  const speed = 1.5;
  const offset = frame * speed;

  if (index === 0) {
    return (
      <>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: "2%" + i * 4 + "%",
              right: "-2%",
              width: cardW * 0.15,
              height: 4,
              backgroundColor: accent,
              transform: `rotate(-30deg) translateX(${Math.sin((frame + i * 20) / 15) * 6}px)`,
              opacity: 0.7,
              borderRadius: 2,
            }}
          />
        ))}
      </>
    );
  }

  if (index === 1) {
    return (
      <>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: `${2 + i * 3}%`,
              left: "-1%",
              width: cardW * 0.12,
              height: 3,
              backgroundColor: accent,
              transform: `rotate(-25deg) translateX(${Math.sin((frame + i * 15) / 12) * 5}px)`,
              borderRadius: 2,
            }}
          />
        ))}
      </>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
          linear-gradient(45deg, ${accent}15 25%, transparent 25%),
          linear-gradient(-45deg, ${accent}15 25%, transparent 25%)
        `,
        backgroundSize: "16px 16px",
        opacity: 0.4,
        transform: `translateY(${offset * 0.3}px)`,
      }}
    />
  );
};
