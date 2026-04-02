import React from "react";
import { Img, interpolate } from "remotion";
import {
  THREE_CARD, FLIP_START, FLIP_END,
  COLOR_TIMELINE, CONTENT_SCENES,
  PRODUCTS_SCENE1, PRODUCTS_SCENE2,
  CARD_POSITIONS, OVERSHOOT,
} from "../constants";
import { lerpColor, getScene } from "../utils";

// ── 子组件：价格标签 ──
const PriceTag = ({ product, cW, slideProgress }) => {
  const slideX = interpolate(slideProgress, [0, 1], [30, 0], { easing: OVERSHOOT });
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
          <div style={{ position: "absolute", top: "50%", left: 4, width: `${strikeWidth}%`, height: 2, backgroundColor: "#ff4444", transform: "translateY(-50%)" }} />
          <span style={{ marginLeft: 4, fontSize: cW * 0.025 }}>sale</span>
        </div>
      )}
    </div>
  );
};

// ── 子组件：Tagline + 箭头 ──
const Tagline = ({ product, index, cW, frame, progress }) => {
  const arrowBounce = Math.sin(frame / 8) * 4;
  return (
    <div style={{
      position: "absolute", top: "12%", left: "5%", right: "5%",
      opacity: progress,
      transform: `translateY(${interpolate(progress, [0, 1], [15, 0])}px)`,
    }}>
      <div style={{ color: index === 1 ? "#ccc" : "#333", fontFamily: "Arial", fontSize: cW * 0.035, fontWeight: 600, fontStyle: "italic", whiteSpace: "pre-line" }}>
        {product.tagline}
      </div>
      <div style={{ marginTop: 4, transform: `translateY(${arrowBounce}px)`, color: index === 1 ? "#ccc" : "#333", fontSize: cW * 0.04 }}>
        ↓
      </div>
    </div>
  );
};

// ── P2 修复：产品图入场 — 更强的旋转/弹跳/透视 ──
const ProductImage = ({ product, cW, frame, contentProgress, animated, microRot, isSingle }) => {
  // P2: 更大的旋转角度、更明显的弹跳
  const prodSlideX = animated ? interpolate(contentProgress, [0, 1], [-30, 0], { easing: OVERSHOOT }) : 0;
  const prodSlideY = animated ? interpolate(contentProgress, [0, 1], [-25, 0], { easing: OVERSHOOT }) : 0;
  const prodRotEntry = animated ? interpolate(contentProgress, [0, 1], [18, 0]) : 0;
  const prodScaleEntry = animated
    ? interpolate(contentProgress, [0, 0.5, 0.8, 1], [0.4, 1.15, 0.95, 1.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;
  const imgSize = cW * (isSingle ? 0.58 : 0.55);

  return (
    <div style={{
      position: "absolute", top: "28%", left: "50%",
      transform: `translateX(calc(-50% + ${prodSlideX}%)) translateY(${prodSlideY}%) rotate(${prodRotEntry + microRot}deg) scale(${prodScaleEntry})`,
      zIndex: 5, opacity: animated ? contentProgress : 1,
      // P2: 加透视变换
      perspective: "500px",
    }}>
      <Img src={product.img} style={{
        width: imgSize, height: imgSize, objectFit: "contain",
        filter: "drop-shadow(0 5px 12px rgba(0,0,0,0.12))",
        // P2: 入场时轻微 3D 倾斜
        transform: animated ? `rotateY(${interpolate(contentProgress, [0, 1], [15, 0])}deg)` : undefined,
      }} />
    </div>
  );
};

// ── P4 修复：标题逐行弹出 + 更弹性的 easing ──
const TitleText = ({ product, index, cW, frame, sceneStart, animated }) => {
  const lines = product.name.split("\n");
  return (
    <div style={{ position: "absolute", bottom: "14%", left: "5%", right: "5%" }}>
      {lines.map((line, li) => {
        let lineT = 1;
        if (animated) {
          // P4: 更大的交错间隔
          const lineDelay = sceneStart + 4 + li * 3;
          lineT = interpolate(frame, [lineDelay, lineDelay + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        }
        // P6: 更 snappy 的弹跳
        const slideY = animated ? interpolate(lineT, [0, 0.6, 0.85, 1], [40, -6, 2, 0]) : 0;
        const scaleT = animated ? interpolate(lineT, [0, 0.6, 0.85, 1], [0.8, 1.05, 0.98, 1]) : 1;
        return (
          <div key={li} style={{
            color: index === 1 ? "#fff" : "#1a1a1a",
            fontFamily: "Arial Black, Arial", fontSize: cW * 0.06, fontWeight: 900, lineHeight: 1.1,
            opacity: lineT,
            transform: `translateY(${slideY}px) scale(${scaleT})`,
            transformOrigin: "left bottom",
          }}>
            {line}
          </div>
        );
      })}
    </div>
  );
};

// ── P5 修复：Swipe Up + 持续弹跳箭头 ──
const SwipeUp = ({ cW, frame, progress }) => {
  // P5: 更明显的持续弹跳
  const arrowFloat = Math.sin(frame / 6) * 8 + Math.sin(frame / 13) * 3;
  const scaleIn = interpolate(progress, [0, 0.5, 0.8, 1], [0.5, 1.1, 0.95, 1]);
  return (
    <div style={{ position: "absolute", bottom: "2%", width: "100%", textAlign: "center", opacity: progress, transform: `scale(${scaleIn})` }}>
      <div style={{ color: "#fff", fontSize: cW * 0.04, transform: `translateY(${arrowFloat}px)`, marginBottom: 2 }}>↑</div>
      <div style={{ color: "#fff", fontFamily: "Georgia", fontSize: cW * 0.055, fontWeight: 700, fontStyle: "italic" }}>Swipe Up</div>
    </div>
  );
};

// ── P3 修复：装饰层 — 改进波纹框为更像 swirly 风格 ──
const Deco = ({ type, frame, index, accent, cW, contentProgress = 1 }) => {
  if (type === "none") return null;
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
        backgroundImage: `linear-gradient(135deg, ${accent}15 25%, transparent 25%), linear-gradient(225deg, ${accent}15 25%, transparent 25%), linear-gradient(315deg, ${accent}15 25%, transparent 25%), linear-gradient(45deg, ${accent}15 25%, transparent 25%)`,
        backgroundSize: "20px 20px",
        backgroundPosition: "0 0, 0 10px, 10px -10px, -10px 0",
        opacity: decoOpacity * 0.5,
        transform: `translateY(${frame * 0.4}px)`,
      }} />
    );
  }

  // "mixed"
  return (
    <>
      {[0, 1, 2, 3].map((i) => {
        const slideIn = interpolate(contentProgress, [0.1 + i * 0.05, 0.3 + i * 0.05], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={`s${i}`} style={{
            position: "absolute", top: `${2 + i * 3}%`,
            [index % 2 === 0 ? "right" : "left"]: `${interpolate(slideIn, [0, 1], [-15, -1])}%`,
            width: cW * 0.14, height: 3, backgroundColor: accent,
            transform: `rotate(-25deg) translateX(${Math.sin((frame + i * 15) / 12) * 5}px)`,
            borderRadius: 2, opacity: slideIn * 0.8,
          }} />
        );
      })}
      <div style={{
        position: "absolute", bottom: 0, right: 0, width: "45%", height: "28%",
        backgroundImage: `radial-gradient(${accent}20 1.5px, transparent 0)`,
        backgroundSize: "10px 10px",
        backgroundPosition: `${frame * 0.3}px ${frame * 0.2}px`,
        opacity: decoOpacity * 0.5,
        transform: `scale(${interpolate(contentProgress, [0, 1], [0.8, 1])})`,
        transformOrigin: "bottom right",
      }} />
      {/* P3: 改进波纹框 — SVG 路径实现 swirly 风格 */}
      {index === 1 && <WaveFrame frame={frame} cW={cW} accent={accent} progress={contentProgress} />}
    </>
  );
};

// ── P3: 波纹方框 ──
const WaveFrame = ({ frame, cW, accent, progress }) => {
  const borderTop = interpolate(progress, [0.2, 0.35], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const borderRight = interpolate(progress, [0.35, 0.5], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const borderBottom = interpolate(progress, [0.5, 0.65], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const borderLeft = interpolate(progress, [0.65, 0.8], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const boxSize = cW * 0.7;
  const boxX = (cW - boxSize) / 2;
  const boxY = cW * 0.15;

  return (
    <div style={{ position: "absolute", left: boxX, top: boxY, width: boxSize, height: boxSize, pointerEvents: "none" }}>
      <div style={{ position: "absolute", top: 0, left: 0, width: `${borderTop}%`, height: 2, backgroundColor: accent, opacity: 0.6 }} />
      <div style={{ position: "absolute", top: 0, right: 0, width: 2, height: `${borderRight}%`, backgroundColor: accent, opacity: 0.6 }} />
      <div style={{ position: "absolute", bottom: 0, right: 0, width: `${borderBottom}%`, height: 2, backgroundColor: accent, opacity: 0.6 }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, width: 2, height: `${borderLeft}%`, backgroundColor: accent, opacity: 0.6 }} />
    </div>
  );
};

// ── 卡片内容面 ──
const CardFace = ({ product, index, cW, frame, scene, layerMask, backfaceHidden, style }) => {
  const hasContent = layerMask >= 4;
  const hasAnim = layerMask >= 5;
  const hasDeco = layerMask >= 6;
  const hasMicro = layerMask >= 8;

  const microRot = hasMicro ? Math.sin(frame / 25 + index) * 2 : 0;

  const contentProgress = (hasAnim && scene && scene.content)
    ? interpolate(frame, [scene.start, scene.start + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : (hasContent && scene && scene.content) ? 1 : 0;

  return (
    <div style={{
      position: "absolute", inset: 0,
      backfaceVisibility: backfaceHidden ? "hidden" : "visible",
      ...style,
    }}>
      {hasDeco && scene && <Deco type={scene.deco} frame={frame} index={index} accent={product.accent} cW={cW} contentProgress={contentProgress} />}

      {hasContent && scene && scene.content && (
        <div style={{ opacity: hasAnim ? contentProgress : 1, position: "relative", width: "100%", height: "100%" }}>
          <PriceTag product={product} cW={cW} slideProgress={hasAnim ? contentProgress : 1} />
          <Tagline product={product} index={index} cW={cW} frame={frame} progress={hasAnim ? contentProgress : 1} />
          <ProductImage product={product} cW={cW} frame={frame} contentProgress={contentProgress} animated={hasAnim} microRot={microRot} />
          <TitleText product={product} index={index} cW={cW} frame={frame} sceneStart={scene.start} animated={hasAnim} />
          <div style={{ position: "absolute", bottom: "4%", left: "5%", right: "5%", color: index === 1 ? "#aaa" : "#555", fontFamily: "Arial", fontSize: cW * 0.028, lineHeight: 1.3, whiteSpace: "pre-line", opacity: hasAnim ? contentProgress : 1 }}>
            {product.subtitle}
          </div>
          {index === 1 && <SwipeUp cW={cW} frame={frame} progress={hasAnim ? contentProgress : 1} />}
        </div>
      )}
    </div>
  );
};

// ══════════════════════════════════════════════
// 主组件：CardShells — 全程三卡 + 3D 翻转过渡
// ══════════════════════════════════════════════
export const CardShells = ({ frame, fps, width, height, layerMask }) => {
  const hasColors = layerMask >= 2;
  const hasEntry = layerMask >= 3;
  const hasMicro = layerMask >= 8;

  // 3D 翻转进度 (0 → 180 degrees)
  const flipProgress = interpolate(frame, [FLIP_START, FLIP_END], [0, 180], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const isFlipped = frame >= FLIP_START;
  const isScene2 = frame >= FLIP_END;

  // 当前场景
  const scene1 = getScene(frame, CONTENT_SCENES.scene1);
  const scene2 = isScene2 ? getScene(frame, CONTENT_SCENES.scene2) : null;

  return (
    <>
      {CARD_POSITIONS.map((pos, index) => {
        const layout = THREE_CARD[pos];
        const cW = layout.w * width;
        const cH = layout.h * height;

        // L3: 入场弹跳
        const cardScale = hasEntry
          ? interpolate(frame, [0, 6, 12], [0.9, 1.02, 1.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: OVERSHOOT })
          : 1;

        // L8: 微动
        const floatY = hasMicro ? Math.sin(frame / 20 + index * 2) * 3 : 0;

        const cX = layout.x * width - (cW * cardScale) / 2;
        const cY = layout.y * height - (cH * cardScale) / 2;

        // 颜色：翻转前用 scene1，翻转后用 scene2
        let bgColor = "#d0d0d0";
        if (hasColors) {
          const colorData = COLOR_TIMELINE[pos];
          if (isScene2) {
            bgColor = lerpColor(frame, colorData.scene2);
          } else {
            bgColor = lerpColor(frame, colorData.scene1);
          }
        }

        // 翻转后的背面颜色
        let bgColorBack = "#d0d0d0";
        if (hasColors) {
          bgColorBack = lerpColor(Math.max(frame, FLIP_END), COLOR_TIMELINE[pos].scene2);
        }

        const product1 = PRODUCTS_SCENE1[index];
        const product2 = PRODUCTS_SCENE2[index];

        return (
          <div key={pos} style={{
            position: "absolute",
            left: cX,
            top: cY + floatY,
            width: cW * cardScale,
            height: cH * cardScale,
            // P1: 3D 翻转需要 perspective
            perspective: "1200px",
          }}>
            {/* 3D 翻转容器 */}
            <div style={{
              position: "relative",
              width: "100%",
              height: "100%",
              transformStyle: "preserve-3d",
              transform: `rotateY(${flipProgress}deg)`,
              transition: "none",
            }}>
              {/* 正面 (Scene 1) */}
              <div style={{
                position: "absolute", inset: 0,
                borderRadius: 10,
                backgroundColor: bgColor,
                overflow: "hidden",
                boxShadow: "0 6px 25px rgba(0,0,0,0.12)",
                border: "1px solid rgba(0,0,0,0.08)",
                backfaceVisibility: "hidden",
              }}>
                <CardFace
                  product={product1}
                  index={index}
                  cW={cW}
                  frame={frame}
                  scene={scene1}
                  layerMask={layerMask}
                  backfaceHidden={false}
                />
              </div>

              {/* 背面 (Scene 2) — 预先旋转 180 度 */}
              <div style={{
                position: "absolute", inset: 0,
                borderRadius: 10,
                backgroundColor: bgColorBack,
                overflow: "hidden",
                boxShadow: "0 6px 25px rgba(0,0,0,0.12)",
                border: "1px solid rgba(0,0,0,0.08)",
                backfaceVisibility: "hidden",
                transform: "rotateY(180deg)",
              }}>
                <CardFace
                  product={product2}
                  index={index}
                  cW={cW}
                  frame={frame}
                  scene={scene2}
                  layerMask={layerMask}
                  backfaceHidden={false}
                />
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
};
