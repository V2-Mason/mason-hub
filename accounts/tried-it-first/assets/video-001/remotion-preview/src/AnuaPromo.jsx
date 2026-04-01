import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Easing,
} from "remotion";

// === 全部参数由 OpenCV 测量 + Gemini 语义分析 + Gemini 动效逆向得出 ===

const SCENE_TRANSITION = 119;
const BG_COLOR = "#ffffff";

// 三卡布局 (OpenCV, 归一化)
const THREE_CARD = {
  left:   { x: 0.208, y: 0.500, w: 0.279, h: 0.869 },
  center: { x: 0.500, y: 0.500, w: 0.281, h: 0.873 },
  right:  { x: 0.791, y: 0.500, w: 0.280, h: 0.871 },
};
const SINGLE_CARD = { x: 0.500, y: 0.500, w: 0.287, h: 0.870 };

// 颜色时间轴 (OpenCV)
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
    { f: 245, c: "#bec4bd" }, { f: 254, c: "#bec3bc" }, { f: 260, c: "#bec3bc" }, { f: 262, c: "#bec3bc" },
  ],
};

// 场景组 (Gemini 语义)
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

const PRODUCTS = [
  { name: "ANUA Toner\nK-Beauty", subtitle: "Heartleaf 77% Soothing Toner\nCalm and Hydrate.", tagline: "Try It. Love It.", price: 25, salePrice: 18, img: staticFile("anua-cards/anua-toner.png"), accent: "#333333" },
  { name: "Soothing\nAmpoule", subtitle: "Repair and soothe\nyour skin barrier.", tagline: "Absolutely new product.\nAvailable now!", price: 22, salePrice: null, img: staticFile("anua-cards/anua-ampoule.png"), accent: "#FF3E3E" },
  { name: "Dark Spot\nCorrecting\nSerum", subtitle: "By Motion Canyon", tagline: "NEW\nNEW\nNEW", price: 24, salePrice: null, img: staticFile("anua-cards/anua-serum.png"), accent: "#333333" },
];

// === Easing: overshoot bounce ===
const OVERSHOOT = Easing.bezier(0.175, 0.885, 0.32, 1.275);

// === 工具函数 ===
function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function rgbToHex(r, g, b) {
  return "#" + [r, g, b].map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
}
function lerpColor(frame, kfs) {
  if (!kfs.length) return "#000";
  if (frame <= kfs[0].f) return kfs[0].c;
  if (frame >= kfs[kfs.length - 1].f) return kfs[kfs.length - 1].c;
  for (let i = 0; i < kfs.length - 1; i++) {
    if (frame >= kfs[i].f && frame <= kfs[i + 1].f) {
      const t = (frame - kfs[i].f) / (kfs[i + 1].f - kfs[i].f);
      const [r1, g1, b1] = hexToRgb(kfs[i].c);
      const [r2, g2, b2] = hexToRgb(kfs[i + 1].c);
      return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
    }
  }
  return kfs[kfs.length - 1].c;
}
function getScene(frame, scenes) {
  for (const s of scenes) { if (frame >= s.start && frame <= s.end) return s; }
  return scenes[scenes.length - 1];
}

// === 主组件 ===
export const AnuaPromo = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const isThreeCard = frame < SCENE_TRANSITION;
  const transT = interpolate(frame, [SCENE_TRANSITION - 4, SCENE_TRANSITION + 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: BG_COLOR }}>
      {frame < SCENE_TRANSITION + 8 &&
        ["left", "center", "right"].map((pos, i) => (
          <Card3 key={pos} pos={pos} index={i} frame={frame} fps={fps} w={width} h={height} fadeOut={isThreeCard ? 0 : transT} />
        ))}
      {frame >= SCENE_TRANSITION - 4 && (
        <Card1 frame={frame} fps={fps} w={width} h={height} fadeIn={transT} />
      )}
    </AbsoluteFill>
  );
};

// === 三卡 ===
const Card3 = ({ pos, index, frame, fps, w, h, fadeOut }) => {
  const layout = THREE_CARD[pos];
  const cW = layout.w * w;
  const cH = layout.h * h;

  // FIX #1: 卡片入场 — overshoot 弹跳，从 0.9 到 1.02 再到 1.0, 400ms=12帧
  const cardScale = interpolate(frame, [0, 6, 12], [0.9, 1.02, 1.0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: OVERSHOOT,
  });

  const cX = layout.x * w - (cW * cardScale) / 2;
  const cY = layout.y * h - (cH * cardScale) / 2;

  const bgColor = lerpColor(frame, COLOR_TIMELINE[pos]);
  const scene = getScene(frame, CONTENT_SCENES.threeCard);
  const product = PRODUCTS[index];

  // 内容出现带 overshoot 弹性
  const contentProgress = scene.content
    ? interpolate(frame, [scene.start, scene.start + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;

  // FIX #2: 产品图入场 — 从左上滑入 + 旋转 + 弹跳缩放
  const prodSlideX = scene.content
    ? interpolate(contentProgress, [0, 1], [-20, 0], { easing: OVERSHOOT })
    : -20;
  const prodSlideY = scene.content
    ? interpolate(contentProgress, [0, 1], [-15, 0], { easing: OVERSHOOT })
    : -15;
  const prodRotEntry = scene.content
    ? interpolate(contentProgress, [0, 1], [12, 0])
    : 12;
  const prodScaleEntry = scene.content
    ? interpolate(contentProgress, [0, 0.7, 1], [0.7, 1.08, 1.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0.7;

  // 持续微动
  const floatY = Math.sin(frame / 20 + index * 2) * 3;
  const microRot = Math.sin(frame / 25 + index) * 2;

  return (
    <div style={{
      position: "absolute", left: cX, top: cY + floatY,
      width: cW * cardScale, height: cH * cardScale,
      borderRadius: 10, backgroundColor: bgColor, overflow: "hidden",
      opacity: 1 - fadeOut,
      boxShadow: "0 6px 25px rgba(0,0,0,0.12)",
      border: "1px solid rgba(0,0,0,0.08)",
    }}>
      <Deco type={scene.deco} frame={frame} index={index} accent={product.accent} cW={cW} contentProgress={contentProgress} />

      <div style={{ opacity: contentProgress, position: "relative", width: "100%", height: "100%" }}>
        {/* FIX #5: 价格标签 — 从右侧滑入 */}
        <PriceTag product={product} cW={cW} frame={frame} slideProgress={contentProgress} />

        {/* FIX #3: Tagline + 箭头 */}
        <Tagline product={product} index={index} cW={cW} frame={frame} progress={contentProgress} />

        {/* FIX #2: 产品图 — 滑入+旋转+弹跳 */}
        <div style={{
          position: "absolute", top: "28%", left: "50%",
          transform: `translateX(calc(-50% + ${prodSlideX}%)) translateY(${prodSlideY}%) rotate(${prodRotEntry + microRot}deg) scale(${prodScaleEntry})`,
          zIndex: 5, opacity: contentProgress,
        }}>
          <Img src={product.img} style={{ width: cW * 0.55, height: cW * 0.55, objectFit: "contain", filter: "drop-shadow(0 5px 12px rgba(0,0,0,0.12))" }} />
        </div>

        {/* FIX #4: 标题 — 逐行弹出 */}
        <TitleText product={product} index={index} cW={cW} frame={frame} sceneStart={scene.start} />

        <div style={{ position: "absolute", bottom: "4%", left: "5%", right: "5%", color: index === 1 ? "#aaa" : "#555", fontFamily: "Arial", fontSize: cW * 0.028, lineHeight: 1.3, whiteSpace: "pre-line", opacity: contentProgress }}>
          {product.subtitle}
        </div>

        {/* FIX #7: Swipe Up + 箭头浮动 */}
        {index === 1 && <SwipeUp cW={cW} frame={frame} progress={contentProgress} />}
      </div>
    </div>
  );
};

// === 单卡 ===
const Card1 = ({ frame, fps, w, h, fadeIn }) => {
  const cW = SINGLE_CARD.w * w;
  const cH = SINGLE_CARD.h * h;
  const cX = SINGLE_CARD.x * w - cW / 2;
  const cY = SINGLE_CARD.y * h - cH / 2;

  const bgColor = lerpColor(frame, COLOR_TIMELINE.single);
  const scene = getScene(frame, CONTENT_SCENES.singleCard);
  const productIdx = scene.productIdx || 1;
  const product = PRODUCTS[productIdx];

  // FIX #9: 内容切换 — 产品旋转缩放进出
  const contentProgress = scene.content
    ? interpolate(frame, [scene.start, scene.start + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;

  const prodScale = scene.content
    ? interpolate(contentProgress, [0, 0.7, 1], [0.5, 1.1, 1.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0.5;
  const prodRot = scene.content
    ? interpolate(contentProgress, [0, 1], [-30, 0])
    : -30;

  const floatY = Math.sin(frame / 15) * 5;
  const microRot = Math.sin(frame / 20) * 3;

  return (
    <div style={{
      position: "absolute", left: cX, top: cY,
      width: cW, height: cH, borderRadius: 10,
      backgroundColor: bgColor, overflow: "hidden",
      opacity: fadeIn, boxShadow: "0 8px 35px rgba(0,0,0,0.18)",
    }}>
      <Deco type={scene.deco} frame={frame} index={productIdx} accent={product.accent} cW={cW} contentProgress={contentProgress} />

      <div style={{ opacity: contentProgress, position: "relative", width: "100%", height: "100%" }}>
        <PriceTag product={product} cW={cW} frame={frame} slideProgress={contentProgress} />
        <Tagline product={product} index={productIdx} cW={cW} frame={frame} progress={contentProgress} />

        {/* FIX #9: 产品图 — 旋转+缩放弹入 */}
        <div style={{
          position: "absolute", top: "28%", left: "50%",
          transform: `translateX(-50%) translateY(${floatY}px) rotate(${prodRot + microRot}deg) scale(${prodScale})`,
          zIndex: 5, opacity: contentProgress,
        }}>
          <Img src={product.img} style={{ width: cW * 0.58, height: cW * 0.58, objectFit: "contain", filter: "drop-shadow(0 6px 18px rgba(0,0,0,0.18))" }} />
        </div>

        <TitleText product={product} index={productIdx} cW={cW} frame={frame} sceneStart={scene.start} />

        <div style={{ position: "absolute", bottom: "4%", left: "5%", right: "5%", color: productIdx === 1 ? "#aaa" : "#555", fontFamily: "Arial", fontSize: cW * 0.033, whiteSpace: "pre-line", opacity: contentProgress }}>
          {product.subtitle}
        </div>

        {productIdx === 1 && <SwipeUp cW={cW} frame={frame} progress={contentProgress} />}
      </div>
    </div>
  );
};

// === FIX #4: 标题逐行弹出 ===
const TitleText = ({ product, index, cW, frame, sceneStart }) => {
  const lines = product.name.split("\n");
  return (
    <div style={{ position: "absolute", bottom: "14%", left: "5%", right: "5%" }}>
      {lines.map((line, li) => {
        const lineDelay = sceneStart + 6 + li * 2; // stagger 2帧 ≈ 66ms
        const lineT = interpolate(frame, [lineDelay, lineDelay + 9], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });
        const slideY = interpolate(lineT, [0, 0.7, 1], [30, -3, 0]); // bounce
        return (
          <div key={li} style={{
            color: index === 1 ? "#fff" : "#1a1a1a",
            fontFamily: "Arial Black, Arial", fontSize: cW * 0.06, fontWeight: 900, lineHeight: 1.1,
            opacity: lineT,
            transform: `translateY(${slideY}px)`,
          }}>
            {line}
          </div>
        );
      })}
    </div>
  );
};

// === FIX #3: Tagline + 向下箭头 ===
const Tagline = ({ product, index, cW, frame, progress }) => {
  const arrowBounce = Math.sin(frame / 8) * 4; // 持续脉冲
  return (
    <div style={{
      position: "absolute", top: "12%", left: "5%", right: "5%",
      opacity: progress,
      transform: `translateY(${interpolate(progress, [0, 1], [15, 0])}px)`,
    }}>
      <div style={{ color: index === 1 ? "#ccc" : "#333", fontFamily: "Arial", fontSize: cW * 0.035, fontWeight: 600, fontStyle: "italic", whiteSpace: "pre-line" }}>
        {product.tagline}
      </div>
      {/* 箭头 */}
      <div style={{
        marginTop: 4,
        transform: `translateY(${arrowBounce}px)`,
        color: index === 1 ? "#ccc" : "#333",
        fontSize: cW * 0.04,
      }}>
        ↓
      </div>
    </div>
  );
};

// === FIX #5: 价格标签 — 从右滑入 + 删除线动画 ===
const PriceTag = ({ product, cW, frame, slideProgress }) => {
  const slideX = interpolate(slideProgress, [0, 1], [30, 0], { easing: OVERSHOOT });
  // 删除线宽度动画
  const strikeWidth = product.salePrice
    ? interpolate(slideProgress, [0.6, 0.8], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;

  return (
    <div style={{
      position: "absolute", top: "3%", right: "4%",
      transform: `translateX(${slideX}%)`,
      opacity: slideProgress, zIndex: 10,
    }}>
      <div style={{ background: product.accent, color: "#fff", padding: "4px 12px", borderRadius: 6, fontFamily: "Arial", fontWeight: 900, fontSize: cW * 0.06, textAlign: "center" }}>
        {product.price}$
      </div>
      {product.salePrice && (
        <div style={{ background: "#222", color: "#fff", padding: "2px 8px", borderRadius: 4, fontFamily: "Arial", fontWeight: 700, fontSize: cW * 0.03, marginTop: 3, textAlign: "center", position: "relative" }}>
          <span>{product.salePrice}$</span>
          {/* 动画删除线 */}
          <div style={{
            position: "absolute", top: "50%", left: 4,
            width: `${strikeWidth}%`, height: 2,
            backgroundColor: "#ff4444",
            transform: "translateY(-50%)",
          }} />
          <span style={{ marginLeft: 4, fontSize: cW * 0.025 }}>sale</span>
        </div>
      )}
    </div>
  );
};

// === FIX #7: Swipe Up + 浮动箭头 ===
const SwipeUp = ({ cW, frame, progress }) => {
  const arrowFloat = Math.sin(frame / 10) * 5;
  const scaleIn = interpolate(progress, [0, 1], [0.9, 1]);
  return (
    <div style={{
      position: "absolute", bottom: "2%", width: "100%", textAlign: "center",
      opacity: progress, transform: `scale(${scaleIn})`,
    }}>
      <div style={{
        color: "#fff", fontSize: cW * 0.04,
        transform: `translateY(${arrowFloat}px)`,
        marginBottom: 2,
      }}>
        ↑
      </div>
      <div style={{ color: "#fff", fontFamily: "Georgia", fontSize: cW * 0.055, fontWeight: 700, fontStyle: "italic" }}>
        Swipe Up
      </div>
    </div>
  );
};

// === FIX #6/#8: 装饰层 — 波纹/网格/条纹 + 淡入动画 ===
const Deco = ({ type, frame, index, accent, cW, contentProgress = 1 }) => {
  if (type === "none") return null;

  // 装饰淡入
  const decoOpacity = interpolate(contentProgress, [0, 0.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  if (type === "dot_grid") {
    return (
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `radial-gradient(${accent}25 2px, transparent 0)`,
        backgroundSize: "14px 14px",
        backgroundPosition: `${frame * 0.5}px ${frame * 0.3}px`,
        opacity: decoOpacity * 0.6,
        transform: `scale(${interpolate(contentProgress, [0, 1], [0.9, 1])})`,
      }} />
    );
  }

  if (type === "chevron") {
    return (
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `
          linear-gradient(135deg, ${accent}15 25%, transparent 25%),
          linear-gradient(225deg, ${accent}15 25%, transparent 25%),
          linear-gradient(315deg, ${accent}15 25%, transparent 25%),
          linear-gradient(45deg, ${accent}15 25%, transparent 25%)
        `,
        backgroundSize: "20px 20px",
        backgroundPosition: `0 0, 0 10px, 10px -10px, -10px 0`,
        opacity: decoOpacity * 0.5,
        transform: `translateY(${frame * 0.4}px)`,
      }} />
    );
  }

  // "mixed" = 对角线条纹(从两侧滑入) + 底部点阵 + 波纹框
  return (
    <>
      {/* FIX #10: 对角线条纹从两侧滑入 */}
      {[0, 1, 2, 3].map((i) => {
        const slideIn = interpolate(contentProgress, [0.1 + i * 0.05, 0.3 + i * 0.05], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={`s${i}`} style={{
            position: "absolute",
            top: `${2 + i * 3}%`,
            [index % 2 === 0 ? "right" : "left"]: `${interpolate(slideIn, [0, 1], [-15, -1])}%`,
            width: cW * 0.14,
            height: 3,
            backgroundColor: accent,
            transform: `rotate(-25deg) translateX(${Math.sin((frame + i * 15) / 12) * 5}px)`,
            borderRadius: 2,
            opacity: slideIn * 0.8,
          }} />
        );
      })}
      {/* 底部点阵 — 带缩放淡入 */}
      <div style={{
        position: "absolute", bottom: 0, right: 0,
        width: "45%", height: "28%",
        backgroundImage: `radial-gradient(${accent}20 1.5px, transparent 0)`,
        backgroundSize: "10px 10px",
        backgroundPosition: `${frame * 0.3}px ${frame * 0.2}px`,
        opacity: decoOpacity * 0.5,
        transform: `scale(${interpolate(contentProgress, [0, 1], [0.8, 1])})`,
        transformOrigin: "bottom right",
      }} />
      {/* FIX #6: 波纹方框（仅中间卡） */}
      {index === 1 && (
        <WaveFrame frame={frame} cW={cW} accent={accent} progress={contentProgress} />
      )}
    </>
  );
};

// === FIX #6: 波纹方框 — 逐边描绘 ===
const WaveFrame = ({ frame, cW, accent, progress }) => {
  // 4条边依次绘制
  const borderTop = interpolate(progress, [0.2, 0.35], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const borderRight = interpolate(progress, [0.35, 0.5], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const borderBottom = interpolate(progress, [0.5, 0.65], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const borderLeft = interpolate(progress, [0.65, 0.8], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const boxSize = cW * 0.7;
  const boxX = (cW - boxSize) / 2;
  const boxY = cW * 0.15;

  return (
    <div style={{ position: "absolute", left: boxX, top: boxY, width: boxSize, height: boxSize, pointerEvents: "none" }}>
      {/* Top */}
      <div style={{ position: "absolute", top: 0, left: 0, width: `${borderTop}%`, height: 2, backgroundColor: accent, opacity: 0.6 }} />
      {/* Right */}
      <div style={{ position: "absolute", top: 0, right: 0, width: 2, height: `${borderRight}%`, backgroundColor: accent, opacity: 0.6 }} />
      {/* Bottom */}
      <div style={{ position: "absolute", bottom: 0, right: 0, width: `${borderBottom}%`, height: 2, backgroundColor: accent, opacity: 0.6 }} />
      {/* Left */}
      <div style={{ position: "absolute", bottom: 0, left: 0, width: 2, height: `${borderLeft}%`, backgroundColor: accent, opacity: 0.6 }} />
    </div>
  );
};
