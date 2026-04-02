import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";

// ====================================================================
// AE → Remotion 精确翻译
// 数据源: ae_full_export.json + 测试特效转JS.json (Lottie)
// 原始: "Title_01 (fast typography)" 1920x1080, 29.97fps, 150帧(5s)
// ====================================================================

// AE influence → Remotion bezier 的近似转换
// AE 的 speed=0 + influence 决定缓动曲线的"松紧"
// influence 越大，缓动越极端（接近 ease-in 或 ease-out）
const bez = (x1, y1, x2, y2) => Easing.bezier(
  Math.max(0, Math.min(1, x1)),
  Math.max(-2, Math.min(2, y1)),
  Math.max(0, Math.min(1, x2)),
  Math.max(-2, Math.min(2, y2))
);

// 常用缓动（从 Lottie JSON 的 bezier 参数）
const EASE = {
  // unit_01 分屏: i(0.097,1) o(0.386,0) / i(0.082,1) o(0.386,0)
  splitTop: bez(0.386, 0, 0.097, 1),
  splitBot: bez(0.386, 0, 0.082, 1),
  // unit_02 分屏: i(0.107,1) o(0.529,0)
  split2: bez(0.529, 0, 0.107, 1),
  // 3D 相机 push: i(0.295,1) o(0.375,0)
  camPush: bez(0.375, 0, 0.295, 1),
  // 3D 相机 settle: i(0.481,1) o(0.735,0)
  camSettle: bez(0.735, 0, 0.481, 1),
  // TEXT_02 滑下: i(0.311,1) o(0.524,0)
  textSlide: bez(0.524, 0, 0.311, 1),
  // TEXT_02 第二段: i(0.471,1) o(0.5,0)
  textSlide2: bez(0.5, 0, 0.471, 1),
  // TEXT_04 弹入: i(0.081,1) o(0.333,0)
  textPop: bez(0.333, 0, 0.081, 1),
  // TEXT_05 滑入: i(0.716,1) o(0.259,1)
  text5Slide: bez(0.259, 1, 0.716, 1),
  // White solid 擦入: i(0.168,1) o(0.333,0)
  wipeIn: bez(0.333, 0, 0.168, 1),
  // Placeholder Z: i(0.369,1) o(0.597,0)
  placeZ: bez(0.597, 0, 0.369, 1),
  // from Mixkit 文字: i(0.578,1) o(0.243,1)
  mixkitText: bez(0.243, 1, 0.578, 1),
};

// 文字内容（从 Lottie JSON chars + 结构文件）
const TEXTS = {
  clean: "CLEAN",       // unit_01, fontSize=587
  fresh: "FRESH",       // TEXT_02, fontSize=120
  smart: "&SMART",      // TEXT_03, fontSize=120
  titles: "TITLES",     // TEXT_04, fontSize=120
  mixkit: "from Mixkit", // TEXT_05, fontSize=120
};

// 颜色
const COLORS = {
  bg: "#ffffff",
  textLight: "#fcf9f9",  // 近白色
  textDark: "#101010",    // 深灰
  placeholder: "#009a5a", // 绿色占位
};

const FONT = "Open Sans, Arial Black, Arial";

// ── Track Matte 分屏组件 ──
// AE 的 Matte 层定义了裁剪区域
// unit_01: 上半 Matte pos=[960,0.062] anchor=[960,540] → 裁剪上半屏
//          下半 Matte pos=[960,1079.75] anchor=[960,540] → 裁剪下半屏
const SplitMatte = ({ children, frame, startFrame, duration, topStartY, bottomStartY, easeTop, easeBot }) => {
  const t = interpolate(frame, [startFrame, startFrame + duration], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // 上半内容 Y 偏移
  const topOffset = interpolate(t, [0, 1], [topStartY - 540, 0], { easing: easeTop });
  // 下半内容 Y 偏移
  const botOffset = interpolate(t, [0, 1], [bottomStartY - 540, 0], { easing: easeBot });

  return (
    <>
      {/* 上半遮罩 — Matte at y=0.062, 覆盖顶部 540px */}
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 540, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: topOffset, width: 1920, height: 1080 }}>
          {children}
        </div>
      </div>
      {/* 下半遮罩 — Matte at y=1079.75, 覆盖底部 540px */}
      <div style={{ position: "absolute", left: 0, top: 540, width: 1920, height: 540, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: botOffset - 540, width: 1920, height: 1080 }}>
          {children}
        </div>
      </div>
    </>
  );
};

// ── 占位图组件 (绿色圆形 + PLACEHOLDER 文字) ──
const PlaceholderImage = ({ scale = 1, clipCircle = false, opacity = 1 }) => (
  <div style={{
    position: "absolute", left: "50%", top: "50%",
    transform: `translate(-50%, -50%) scale(${scale})`,
    width: 1920, height: 1080, opacity,
    ...(clipCircle ? {
      clipPath: "ellipse(578px 578px at 960px 540px)",
    } : {}),
  }}>
    {/* 绿色底 */}
    <div style={{
      position: "absolute", inset: 0,
      backgroundColor: COLORS.placeholder,
    }} />
    {/* PLACEHOLDER 文字已移除 — 以后替换为实际图片/视频 */}
  </div>
);

// ── 矩形框 (Shape layer "frame") ──
// AE: scale=58%, 顶点 [-652.83,-203.774] to [660.377,200], stroke=18px
const FrameRect = ({ scaleX = 58, scaleY = 58, strokeWidth = 18, color = COLORS.textLight, opacity = 1, widthFactor = 1 }) => {
  const w = (652.83 + 660.377) * (scaleX / 100) * widthFactor;
  const h = (203.774 + 200) * (scaleY / 100);
  return (
    <div style={{
      position: "absolute", left: "50%", top: "50%",
      transform: "translate(-50%, -50%)",
      width: w, height: h,
      border: `${strokeWidth * (scaleX / 100)}px solid ${color}`,
      boxSizing: "border-box",
      opacity,
    }} />
  );
};

// ══════════════════════════════════════════
// 主组件
// ══════════════════════════════════════════
export const AETitle = () => {
  const frame = useCurrentFrame();

  // ── 时间轴 ──
  // Title_01_Main: unit_01 f0-f60, unit_02 f15-f139 (stretch 104.2%)
  // 主合成 Title_01 播放 Title_01_Main 时 stretch=111.11% (sr=1.111)
  // 所以主合成帧 → Title_01_Main 帧: f_main = frame / 1.111
  const mainF = frame / 1.11111;

  // unit_01: f0-f60 in Title_01_Main
  const u1Active = mainF >= 0 && mainF < 60;
  const u1F = mainF;

  // unit_02: f15-f139 in Title_01_Main, stretch 104.2%
  const u2Active = mainF >= 15;
  const u2StartInMain = 15;
  const u2F = (mainF - u2StartInMain) / 1.04202; // local frame in unit_02

  // Scene_02_main local frame
  const s2F = u2F;

  // TEXT_02_comp 在 Scene_02_main 中 f0-f120, z=-500, scale=50%
  const tcF = s2F;

  // ── 3D 相机 Z 轴 ──
  // Camera position: f17→z801, f35→z-253, f45→z452
  const camZ = s2F < 17 ? 801
    : s2F < 35 ? interpolate(s2F, [17, 35], [801, -253], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.camPush })
    : s2F < 45 ? interpolate(s2F, [35, 45], [-253, 452], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.camSettle })
    : 452;

  // Camera → 缩放 (perspective = zoom = 1866.667)
  const zoom = 1866.667;
  const camScale = zoom / (zoom - camZ);

  // ── TEXT_02 "FRESH" Y 位置 ──
  const freshY = tcF < 39 ? 540
    : tcF < 49 ? interpolate(tcF, [39, 49], [540, 754], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.textSlide })
    : tcF < 56 ? 754
    : tcF < 63 ? interpolate(tcF, [56, 63], [754, 925], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.textSlide2 })
    : 925;

  // TEXT_03 "&SMART": f27-f74, parent=TEXT_02, pos=[960,324], anchor=[960,540]
  // 相对于 TEXT_02: y偏移 = 324 - 540 = -216
  const showSmart = tcF >= 27 && tcF < 74;
  const smartY = freshY - 216;

  // TEXT_04 "TITLES": f59-f68
  const showTitles = tcF >= 59 && tcF < 74;
  const titlesY = tcF < 59 ? 393
    : tcF < 68 ? interpolate(tcF, [59, 68], [393, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.textPop })
    : 540;

  // 文字框可见 f0-f74
  const showFramedText = tcF >= 0 && tcF < 74;

  // ── TEXT_05 "from Mixkit" (f74-f120) ──
  const showMixkit = s2F >= 74;
  const mixkitCompX = s2F < 74 ? 824
    : s2F < 89 ? interpolate(s2F, [74, 89], [824, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.text5Slide })
    : 960;
  // "from Mixkit" 文字内部位移 (parent=Position, local f0-f20)
  const mixkitLocalF = Math.max(0, s2F - 74);
  const mixkitTextX = mixkitLocalF < 20
    ? interpolate(mixkitLocalF, [0, 20], [-80, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.mixkitText })
    : 0;

  // TEXT_05 框架 frame: shape path 从满宽收缩到 0 (f76-f89 in TEXT_05 local)
  const frameCollapseT = mixkitLocalF < 2 ? 1
    : mixkitLocalF < 15 ? interpolate(mixkitLocalF, [2, 15], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.167, 0.167, 0.667, 1) })
    : 0;

  // ── White Solid 背景滑入 (f71-f77) ──
  const showWhiteBg = s2F >= 71;
  const whiteX = s2F < 71 ? 2658.78
    : s2F < 77 ? interpolate(s2F, [71, 77], [2658.78, 1160.761], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.wipeIn })
    : 1160.761;

  // ── Placeholder Z ──
  const placeZ = s2F < 17 ? -500
    : s2F < 35 ? interpolate(s2F, [17, 35], [-500, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.placeZ })
    : 0;
  const placeZScale = zoom / (zoom - placeZ);

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, overflow: "hidden" }}>

      {/* ══════ Unit 01: "CLEAN" 分屏滑入 (主合成 f0-f60) ══════ */}
      {u1Active && (
        <SplitMatte
          frame={u1F}
          startFrame={0}
          duration={15}
          topStartY={799}    // matte[3] Y≈0 (TOP region) → content[4] starts at y=799
          bottomStartY={273} // matte[1] Y≈1080 (BOTTOM region) → content[2] starts at y=273
          easeTop={EASE.splitBot}
          easeBot={EASE.splitTop}
        >
          {/* TEXT_01_comp: PLACEHOLDER_01 + BG(白色) alpha-inverted by TEXT_01 */}
          {/* 效果：白色覆盖全屏，文字形状处挖空露出绿色占位图 */}
          <AbsoluteFill>
            {/* 底层：绿色占位图 */}
            <PlaceholderImage />
            {/* 上层：白色 BG，文字区域用 SVG mask 挖空 */}
            <svg width="1920" height="1080" style={{ position: "absolute", inset: 0 }}>
              <defs>
                <mask id="cleanTextMask">
                  {/* 白色 = 可见区域 */}
                  <rect width="1920" height="1080" fill="white" />
                  {/* 黑色文字 = 挖空区域 */}
                  <text
                    x="960" y="540"
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontFamily={FONT}
                    fontWeight="800"
                    fontSize="340"
                    letterSpacing="-0.07em"
                    fill="black"
                  >
                    {TEXTS.clean}
                  </text>
                </mask>
              </defs>
              <rect width="1920" height="1080" fill={COLORS.bg} mask="url(#cleanTextMask)" />
            </svg>
          </AbsoluteFill>
        </SplitMatte>
      )}

      {/* ══════ Unit 02: Scene_02 分屏滑入 (主合成 f15+) ══════ */}
      {u2Active && (
        <SplitMatte
          frame={u2F}
          startFrame={0}
          duration={19}
          topStartY={1083}   // matte[1] Y≈0 (TOP region) → content[2] starts at y=1083
          bottomStartY={-5}  // matte[3] Y≈1080 (BOTTOM region) → content[4] starts at y=-5
          easeTop={EASE.split2}
          easeBot={EASE.split2}
        >
          <AbsoluteFill>
            {/* ── 3D 相机容器 ── */}
            <div style={{
              position: "absolute", left: "50%", top: "50%",
              transform: `translate(-50%, -50%) scale(${camScale})`,
              width: 1920, height: 1080,
            }}>

              {/* ── PLACEHOLDER_02 (背后, z 动画) ── */}
              {/* 层8: 无遮罩, scale=116% */}
              <PlaceholderImage scale={1.16 * (zoom / (zoom - 0))} />
              {/* 层7: 圆形遮罩, z 动画 */}
              <PlaceholderImage scale={1.16 * placeZScale} clipCircle />

              {/* ── TEXT_02_comp (z=-500, scale=50%) ── */}
              {/* 3D 透视必须动态算: 0.5 * zoom/(zoom-500-camPosZ) / camScale */}
              {/* camPosZ 来自 Camera position 的 Z，camScale = zoom/(zoom-camPosZ) */}
              {/* 简化: 0.5 * (zoom-camPosZ)/(zoom-500-camPosZ) ，其中 camPosZ 对应变量里的 camZ 来源 */}
              {showFramedText && (
                <div style={{
                  position: "absolute", left: "50%", top: "50%",
                  transform: `translate(-50%, -50%) scale(${0.5 * (zoom - camZ) / (zoom - 500 - camZ)})`,
                  width: 1920, height: 1080,
                }}>
                  {/* frame: 矩形框 scale=58%, 原始顶点 [-652.83,-203.774] to [660.377,200] */}
                  <FrameRect scaleX={58} scaleY={58} color={COLORS.textLight} />

                  {/* 文字裁剪容器 — 与 FrameRect 同尺寸，文字只在框内可见 */}
                  <div style={{
                    position: "absolute", left: "50%", top: "50%",
                    transform: "translate(-50%, -50%)",
                    width: (652.83 + 660.377) * 0.58,
                    height: (203.774 + 200) * 0.58,
                    overflow: "hidden",
                  }}>
                    {/* TEXT_02 "FRESH" — 相对于裁剪框定位 */}
                    <div style={{
                      position: "absolute",
                      left: -(1920 - (652.83 + 660.377) * 0.58) / 2,
                      top: freshY - 540 - (540 - (203.774 + 200) * 0.58 / 2),
                      width: 1920, height: 1080,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <div style={{
                        fontFamily: FONT, fontWeight: 800,
                        fontSize: 120,
                        color: COLORS.textLight,
                        letterSpacing: "-0.07em",
                        textTransform: "uppercase",
                      }}>
                        {TEXTS.fresh}
                      </div>
                    </div>

                    {/* TEXT_03 "&SMART" */}
                    {showSmart && (
                      <div style={{
                        position: "absolute",
                        left: -(1920 - (652.83 + 660.377) * 0.58) / 2,
                        top: smartY - 540 - (540 - (203.774 + 200) * 0.58 / 2),
                        width: 1920, height: 1080,
                        display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        <div style={{
                          fontFamily: FONT, fontWeight: 800,
                          fontSize: 120,
                          color: COLORS.textLight,
                          letterSpacing: "-0.07em",
                          textTransform: "uppercase",
                        }}>
                          {TEXTS.smart}
                        </div>
                      </div>
                    )}

                    {/* TEXT_04 "TITLES" */}
                    {showTitles && (
                      <div style={{
                        position: "absolute",
                        left: -(1920 - (652.83 + 660.377) * 0.58) / 2,
                        top: titlesY - 540 - (540 - (203.774 + 200) * 0.58 / 2),
                        width: 1920, height: 1080,
                        display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        <div style={{
                          fontFamily: FONT, fontWeight: 800,
                          fontSize: 120,
                          color: COLORS.textLight,
                          letterSpacing: "-0.07em",
                          textTransform: "uppercase",
                        }}>
                          {TEXTS.titles}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── White Solid 背景滑入 (f71+) ── */}
              {/* TEXT_05 用它做 Alpha Inverted Matte (trackMatteType=5014) */}
              {showWhiteBg && (
                <div style={{
                  position: "absolute",
                  left: whiteX - 960, top: 555.776 - 540,
                  width: 1920, height: 1080,
                  backgroundColor: COLORS.bg,
                }} />
              )}

              {/* ── TEXT_05 "from Mixkit" (f74+) ── */}
              {showMixkit && (
                <div style={{
                  position: "absolute",
                  left: mixkitCompX - 960,
                  top: 0,
                  width: 1920, height: 1080,
                  // scale = 81%
                  transform: `scale(0.81)`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {/* 框架 (scale=58%, scaleX=140%) — 收缩动画 */}
                  {frameCollapseT > 0.01 && (
                    <FrameRect
                      scaleX={58 * 1.4 * frameCollapseT}
                      scaleY={58}
                      color={COLORS.textLight}
                      strokeWidth={18}
                    />
                  )}

                  {/* "from Mixkit" 文字 — 深色 */}
                  <div style={{
                    fontFamily: FONT, fontWeight: 800,
                    fontSize: 120, // AE 原始大小，外层 scale(0.81) 会缩放
                    color: COLORS.textDark,
                    letterSpacing: "-0.07em",
                    whiteSpace: "nowrap",
                    transform: `translateX(${mixkitTextX}px)`,
                  }}>
                    {TEXTS.mixkit}
                  </div>
                </div>
              )}
            </div>
          </AbsoluteFill>
        </SplitMatte>
      )}
    </AbsoluteFill>
  );
};
