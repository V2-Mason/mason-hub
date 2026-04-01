import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";

// === 动画参数 (autoresearch 调优区) ===
const ANIM = {
  // 入场
  staggerDelay: 8,           // 每张卡片错开帧数
  springDamping: 8,          // 弹性阻尼 (越小越弹)
  springStiffness: 160,      // 弹性刚度
  springMass: 0.6,           // 弹性质量
  entranceFromY: 900,        // 入场起始Y偏移

  // 悬浮呼吸
  floatAmplitude: 10,        // 悬浮Y振幅
  floatFreq: 18,             // 悬浮频率 (越大越慢)
  floatPhaseOffset: 2.1,     // 每张卡片相位偏移

  // 微旋转
  rotationAmplitude: 2.0,    // 旋转振幅(度)
  rotationFreq: 30,          // 旋转频率

  // 发光
  glowMin: 8,                // 最小发光半径
  glowMax: 25,               // 最大发光半径
  glowFreq: 14,              // 发光呼吸频率

  // 时间轴关键帧
  entranceEnd: 30,           // 入场完成帧
  sceneChangeFrame: 135,     // 场景切换帧 (~4.5s)
  invertStart: 195,          // 反转开始帧
  invertEnd: 240,            // 反转结束帧
  fadeStart: 250,            // 淡出开始帧
  fadeEnd: 270,              // 淡出结束帧
};

// === 产品数据 ===
const PRODUCTS = [
  {
    name: "ANUA Toner\nK-Beauty",
    subtitle: "Heartleaf 77% Soothing Toner\nCalm and Hydrate.",
    tagline: "Try It. Love It.",
    price: 25,
    salePrice: 18,
    img: staticFile("anua-cards/anua-toner.png"),
    bg: "#E88B7A",         // 珊瑚粉
    bgAlt: "#FF7D7D",      // 变色后
    accent: "#333333",
    glowColor: "rgba(255, 130, 130, 0.6)",
  },
  {
    name: "Soothing\nAmpoule",
    subtitle: "Repair and soothe\nyour skin barrier.",
    tagline: "Absolutely new product.\nAvailable now!",
    price: 22,
    salePrice: null,
    img: staticFile("anua-cards/anua-ampoule.png"),
    bg: "#111111",         // 黑
    bgAlt: "#1a1a2e",      // 变色后
    accent: "#FF3E3E",
    glowColor: "rgba(255, 200, 50, 0.6)",
  },
  {
    name: "Dark Spot\nCorrecting\nSerum",
    subtitle: "By Motion Canyon",
    tagline: "NEW\nNEW\nNEW",
    price: 24,
    salePrice: null,
    img: staticFile("anua-cards/anua-serum.png"),
    bg: "#CD3F3F",         // 红
    bgAlt: "#E4FF1A",      // 变色后 荧光绿
    accent: "#F2C94C",
    glowColor: "rgba(255, 80, 120, 0.5)",
  },
];

// === 主组件 ===
export const AnuaPromo = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 背景色相渐变
  const bgHue = interpolate(frame, [0, 270], [210, 240], {
    extrapolateRight: "clamp",
  });
  const bgHueShift = frame > ANIM.invertStart
    ? interpolate(frame, [ANIM.invertStart, ANIM.invertEnd], [0, 120], {
        extrapolateRight: "clamp",
      })
    : 0;

  // 颜色反转闪烁
  const isInverted =
    frame > ANIM.invertStart &&
    frame < ANIM.invertEnd &&
    frame % 10 < 4;

  // 淡出
  const fadeOut = interpolate(frame, [ANIM.fadeStart, ANIM.fadeEnd], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `hsl(${bgHue + bgHueShift}, 12%, 15%)`,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "row",
        gap: 30,
        filter: isInverted ? "invert(1)" : "none",
        opacity: fadeOut,
      }}
    >
      {/* 背景动态点阵 (Motion Tile) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "radial-gradient(rgba(255,255,255,0.05) 1.5px, transparent 0)",
          backgroundSize: "24px 24px",
          backgroundPosition: `${frame * 0.8}px ${frame * 1.2}px`,
          pointerEvents: "none",
        }}
      />

      {PRODUCTS.map((product, i) => (
        <CardRebuilt
          key={i}
          product={product}
          index={i}
          frame={frame}
          fps={fps}
        />
      ))}
    </AbsoluteFill>
  );
};

// === 单张卡片 (代码重建) ===
const CardRebuilt = ({ product, index, frame, fps }) => {
  // --- 入场动画 ---
  const delay = index * ANIM.staggerDelay;
  const entrance = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: {
      damping: ANIM.springDamping,
      stiffness: ANIM.springStiffness,
      mass: ANIM.springMass,
    },
  });

  const translateY = interpolate(entrance, [0, 1], [ANIM.entranceFromY, 0]);
  const scaleIn = interpolate(entrance, [0, 1], [0.4, 1]);
  const opacityIn = interpolate(entrance, [0, 1], [0, 1]);

  // --- 悬浮 ---
  const floatY =
    frame > ANIM.entranceEnd
      ? Math.sin((frame - ANIM.entranceEnd) / ANIM.floatFreq + index * ANIM.floatPhaseOffset) *
        ANIM.floatAmplitude
      : 0;

  // --- 微旋转 ---
  const rotation =
    frame > ANIM.entranceEnd
      ? Math.sin((frame - ANIM.entranceEnd) / ANIM.rotationFreq + index * 1.5) *
        ANIM.rotationAmplitude
      : 0;

  // --- 发光呼吸 ---
  const glow =
    frame > 50
      ? interpolate(
          Math.sin(frame / ANIM.glowFreq + index),
          [-1, 1],
          [ANIM.glowMin, ANIM.glowMax]
        )
      : 0;

  // --- 背景色变化 (Hue/Saturation 效果) ---
  const colorProgress =
    frame > ANIM.invertStart
      ? interpolate(frame, [ANIM.invertStart, ANIM.invertEnd], [0, 1], {
          extrapolateRight: "clamp",
        })
      : 0;

  // --- 价格数字变化 (Numbers 效果) ---
  const priceAnimated =
    frame > ANIM.sceneChangeFrame
      ? product.price + Math.floor(
          interpolate(frame, [ANIM.sceneChangeFrame, ANIM.sceneChangeFrame + 30], [0, 8], {
            extrapolateRight: "clamp",
          })
        )
      : product.price;

  const salePriceAnimated =
    product.salePrice && frame > ANIM.sceneChangeFrame
      ? product.salePrice + Math.floor(
          interpolate(frame, [ANIM.sceneChangeFrame, ANIM.sceneChangeFrame + 30], [0, 6], {
            extrapolateRight: "clamp",
          })
        )
      : product.salePrice;

  // --- 产品图悬浮 ---
  const productFloatY =
    frame > ANIM.entranceEnd
      ? Math.sin((frame - ANIM.entranceEnd) / 12 + index * 0.8) * 8
      : 0;

  const productRotation =
    frame > ANIM.entranceEnd
      ? Math.sin((frame - ANIM.entranceEnd) / 20 + index) * 5
      : 0;

  // --- 文字弹出 (逐行 stagger) ---
  const textDelay = delay + 15;
  const textEntrance = spring({
    frame: Math.max(0, frame - textDelay),
    fps,
    config: { damping: 10, stiffness: 100, mass: 0.5 },
  });
  const textY = interpolate(textEntrance, [0, 1], [60, 0]);
  const textOpacity = interpolate(textEntrance, [0, 1], [0, 1]);

  // --- 价格标签弹出 ---
  const priceDelay = delay + 22;
  const priceEntrance = spring({
    frame: Math.max(0, frame - priceDelay),
    fps,
    config: { damping: 8, stiffness: 200, mass: 0.4 },
  });
  const priceScale = interpolate(priceEntrance, [0, 1], [0, 1]);

  // 选择当前背景色
  const bgColor = colorProgress > 0.5 ? product.bgAlt : product.bg;

  return (
    <div
      style={{
        transform: [
          `translateY(${translateY + floatY}px)`,
          `rotate(${rotation}deg)`,
          `scale(${scaleIn})`,
        ].join(" "),
        opacity: opacityIn,
        filter: `drop-shadow(0 0 ${glow}px ${product.glowColor})`,
      }}
    >
      <div
        style={{
          width: 320,
          height: 580,
          borderRadius: 14,
          backgroundColor: bgColor,
          position: "relative",
          overflow: "hidden",
          boxShadow: "0 15px 40px rgba(0,0,0,0.3)",
        }}
      >
        {/* 装饰条纹 */}
        <DecoStripes index={index} frame={frame} accent={product.accent} />

        {/* 价格标签 */}
        <div
          style={{
            position: "absolute",
            top: 18,
            right: 16,
            transform: `scale(${priceScale})`,
            transformOrigin: "top right",
            zIndex: 10,
          }}
        >
          <div
            style={{
              background: product.accent,
              color: "white",
              padding: "6px 14px",
              borderRadius: 6,
              fontFamily: "Arial, sans-serif",
              fontWeight: 900,
              fontSize: 28,
              textAlign: "center",
              boxShadow: `0 0 15px ${product.accent}66`,
            }}
          >
            {priceAnimated}$
          </div>
          {salePriceAnimated && (
            <div
              style={{
                background: "#222",
                color: "white",
                padding: "3px 10px",
                borderRadius: 4,
                fontFamily: "Arial, sans-serif",
                fontWeight: 700,
                fontSize: 16,
                marginTop: 4,
                textAlign: "center",
              }}
            >
              <span style={{ textDecoration: "line-through", opacity: 0.7 }}>
                {salePriceAnimated}$
              </span>{" "}
              <span style={{ fontSize: 11 }}>sale</span>
            </div>
          )}
        </div>

        {/* Tagline */}
        <div
          style={{
            position: "absolute",
            top: index === 1 ? 70 : 90,
            left: 20,
            right: 20,
            color: index === 1 ? "#ccc" : "#333",
            fontFamily: "Arial, sans-serif",
            fontSize: 14,
            fontWeight: 600,
            fontStyle: "italic",
            whiteSpace: "pre-line",
            opacity: textOpacity,
            transform: `translateY(${textY * 0.5}px)`,
          }}
        >
          {product.tagline}
        </div>

        {/* 产品图 */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: `translate(-50%, -55%) translateY(${productFloatY}px) rotate(${productRotation}deg)`,
            zIndex: 5,
          }}
        >
          <Img
            src={product.img}
            style={{
              width: 220,
              height: 220,
              objectFit: "contain",
              filter: "drop-shadow(0 8px 20px rgba(0,0,0,0.2))",
            }}
          />
        </div>

        {/* 产品名称 */}
        <div
          style={{
            position: "absolute",
            bottom: 80,
            left: 20,
            right: 20,
            color: index === 1 ? "white" : "#1a1a1a",
            fontFamily: "Arial Black, Arial, sans-serif",
            fontSize: 26,
            fontWeight: 900,
            lineHeight: 1.1,
            whiteSpace: "pre-line",
            opacity: textOpacity,
            transform: `translateY(${textY}px)`,
          }}
        >
          {product.name}
        </div>

        {/* 副标题 */}
        <div
          style={{
            position: "absolute",
            bottom: 24,
            left: 20,
            right: 20,
            color: index === 1 ? "#aaa" : "#555",
            fontFamily: "Arial, sans-serif",
            fontSize: 12,
            lineHeight: 1.4,
            whiteSpace: "pre-line",
            opacity: textOpacity,
            transform: `translateY(${textY * 0.8}px)`,
          }}
        >
          {product.subtitle}
        </div>

        {/* 中间卡片底部 CTA */}
        {index === 1 && (
          <div
            style={{
              position: "absolute",
              bottom: 20,
              left: 0,
              right: 0,
              textAlign: "center",
              color: "white",
              fontFamily: "Georgia, serif",
              fontSize: 28,
              fontWeight: 700,
              fontStyle: "italic",
              opacity: textOpacity,
            }}
          >
            Swipe Up
          </div>
        )}
      </div>
    </div>
  );
};

// === 装饰条纹 ===
const DecoStripes = ({ index, frame, accent }) => {
  const speed = 1.5;
  const offset = frame * speed;

  if (index === 0) {
    // 左卡: 对角斜线装饰
    return (
      <>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: 10 + i * 22,
              right: -10,
              width: 60,
              height: 4,
              backgroundColor: accent,
              transform: `rotate(-30deg) translateX(${Math.sin((frame + i * 20) / 15) * 8}px)`,
              opacity: 0.7,
              borderRadius: 2,
            }}
          />
        ))}
        {/* 底部散点装饰 */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            width: 140,
            height: 120,
            backgroundImage: `radial-gradient(${accent}33 2px, transparent 0)`,
            backgroundSize: "12px 12px",
            backgroundPosition: `${offset}px ${offset * 0.5}px`,
            opacity: 0.5,
          }}
        />
      </>
    );
  }

  if (index === 1) {
    // 中卡: 红色对角线
    return (
      <>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: 6 + i * 16,
              left: -5,
              width: 50,
              height: 3,
              backgroundColor: accent,
              transform: `rotate(-25deg) translateX(${Math.sin((frame + i * 15) / 12) * 6}px)`,
              borderRadius: 2,
            }}
          />
        ))}
        {[0, 1, 2, 3].map((i) => (
          <div
            key={`r${i}`}
            style={{
              position: "absolute",
              bottom: 70 + i * 16,
              right: -5,
              width: 50,
              height: 3,
              backgroundColor: accent,
              transform: `rotate(-25deg) translateX(${Math.sin((frame + i * 15) / 12) * -6}px)`,
              borderRadius: 2,
            }}
          />
        ))}
      </>
    );
  }

  // 右卡: 点阵背景滚动
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
          linear-gradient(45deg, ${accent}22 25%, transparent 25%),
          linear-gradient(-45deg, ${accent}22 25%, transparent 25%),
          linear-gradient(45deg, transparent 75%, ${accent}22 75%),
          linear-gradient(-45deg, transparent 75%, ${accent}22 75%)
        `,
        backgroundSize: "20px 20px",
        backgroundPosition: `0 0, 0 10px, 10px -10px, -10px 0px`,
        opacity: 0.3,
        transform: `translateY(${offset * 0.5}px)`,
      }}
    />
  );
};
