import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";

/**
 * 1:1 复刻 Jitter "Animated Web Screens" — v7
 * 基于源文件 Scene.mp4 (960×720, 7s, 30fps) 精确分析
 *
 * 运动：zoom in (0-1s) → zoom out (1-3s) → scroll up (3-7s)
 * 背景：纯黑（卡片间距=黑色）
 * 装饰：矩形拼图（不是阶梯）
 */

const C = {
  teal: "#1B4332",
  yellow: "#C8E64C",
  sage: "#C8D8C8",
  black: "#000000",
  white: "#F8F8F4",
};

// ─── 矩形拼图装饰（原版核心视觉元素）───
// 由多个 teal + yellow 矩形拼成的抽象图形
const BlockPattern = ({ variant = "A", scale = 1 }) => {
  const s = scale;
  const patterns = {
    // 大 teal 块 + yellow 填充 — 最常见的样式
    A: (
      <>
        <div style={{ position: "absolute", left: 0, top: 0, width: 160*s, height: 200*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", left: 160*s, top: 0, width: 80*s, height: 120*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", left: 0, top: 200*s, width: 80*s, height: 60*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", left: 80*s, top: 160*s, width: 80*s, height: 80*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", left: 160*s, top: 120*s, width: 80*s, height: 60*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", left: 0, top: 200*s, width: 60*s, height: 60*s, backgroundColor: C.yellow }} />
      </>
    ),
    // yellow 为主 + teal 填充
    B: (
      <>
        <div style={{ position: "absolute", right: 0, bottom: 0, width: 180*s, height: 160*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", right: 0, bottom: 160*s, width: 100*s, height: 80*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", right: 180*s, bottom: 0, width: 80*s, height: 80*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", right: 100*s, bottom: 160*s, width: 80*s, height: 60*s, backgroundColor: C.yellow }} />
      </>
    ),
    // 左上角变体
    C: (
      <>
        <div style={{ position: "absolute", left: 0, top: 0, width: 120*s, height: 160*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", left: 120*s, top: 0, width: 60*s, height: 80*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", left: 0, top: 160*s, width: 60*s, height: 60*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", left: 120*s, top: 80*s, width: 60*s, height: 80*s, backgroundColor: C.teal }} />
      </>
    ),
    // 右上角大块
    D: (
      <>
        <div style={{ position: "absolute", right: 0, top: 0, width: 200*s, height: 180*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", right: 0, top: 180*s, width: 120*s, height: 80*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", right: 200*s, top: 0, width: 60*s, height: 100*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", right: 120*s, top: 180*s, width: 80*s, height: 60*s, backgroundColor: C.yellow }} />
      </>
    ),
    // 全teal大面积
    E: (
      <>
        <div style={{ position: "absolute", left: 0, top: 0, width: 200*s, height: 240*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", left: 200*s, top: 0, width: 100*s, height: 140*s, backgroundColor: C.yellow }} />
        <div style={{ position: "absolute", left: 200*s, top: 140*s, width: 60*s, height: 80*s, backgroundColor: C.teal }} />
        <div style={{ position: "absolute", left: 0, top: 240*s, width: 120*s, height: 60*s, backgroundColor: C.yellow }} />
      </>
    ),
  };
  return <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>{patterns[variant]}</div>;
};

// Logo — 原版是折叠箭头形状
const Logo = ({ dark = false }) => (
  <div style={{
    position: "absolute", top: 16, left: dark ? undefined : 16, right: dark ? 16 : undefined, zIndex: 5,
    color: C.teal, fontSize: 18, fontWeight: 900, fontFamily: "system-ui",
    letterSpacing: -1,
  }}>
    ⟫
  </div>
);

// 按钮组 — Mobile / Desktop(filled) / UI/UX
const Buttons = () => (
  <div style={{ position: "absolute", bottom: 20, left: "50%", transform: "translateX(-50%)", display: "flex", gap: 8, zIndex: 5 }}>
    <div style={{ border: "1.5px solid rgba(0,0,0,0.15)", color: "rgba(0,0,0,0.5)", fontSize: 12, padding: "6px 16px", borderRadius: 20, fontFamily: "system-ui", backgroundColor: "transparent" }}>Mobile</div>
    <div style={{ backgroundColor: C.teal, color: "#fff", fontSize: 12, fontWeight: 600, padding: "6px 16px", borderRadius: 20, fontFamily: "system-ui" }}>Desktop</div>
    <div style={{ border: "1.5px solid rgba(0,0,0,0.15)", color: "rgba(0,0,0,0.5)", fontSize: 12, padding: "6px 16px", borderRadius: 20, fontFamily: "system-ui", backgroundColor: "transparent" }}>UI / UX</div>
  </div>
);

// 尺寸文字
const Size = ({ text, dark = false }) => (
  <div style={{
    position: "absolute", top: "45%", left: "55%", transform: "translate(-50%,-50%)", zIndex: 3,
    color: dark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.3)",
    fontSize: 48, fontWeight: 200, fontFamily: "Inter, system-ui",
    letterSpacing: -2, whiteSpace: "nowrap",
  }}>
    {text}
  </div>
);

// 照片
const Photo = ({ type }) => {
  const g = {
    curtains: "linear-gradient(90deg, #c8b428 0%, #e6dc50 25%, #b4a014 55%, #d2c23c 80%, #aa9610 100%), repeating-linear-gradient(0deg, transparent, transparent 6px, rgba(255,255,255,0.08) 6px, rgba(255,255,255,0.08) 7px)",
    conference: "linear-gradient(180deg, #a0966e 0%, #c8b864 30%, #8c8246 70%, #645a28 100%), radial-gradient(at 55% 35%, rgba(255,240,180,0.3), transparent 50%)",
    silhouette: "linear-gradient(160deg, #b8c0a8 0%, #3c4630 25%, #0a0f00 50%, #000 100%)",
    laptop: "linear-gradient(180deg, #d8d8d0 0%, #b8b8b0 40%, #909088 70%, #585850 100%), radial-gradient(at 50% 55%, rgba(200,200,195,0.4), transparent 45%)",
    speaker: "linear-gradient(180deg, #c8c8c0 0%, #a8a8a0 30%, #888880 60%, #686860 100%), radial-gradient(at 50% 50%, rgba(180,180,175,0.5), transparent 40%)",
  };
  return <div style={{ position: "absolute", inset: 0, backgroundImage: g[type], zIndex: 0 }} />;
};

// 卡片
const Card = ({ x, y, w, h, bg, children }) => (
  <div style={{
    position: "absolute", left: x, top: y, width: w, height: h,
    backgroundColor: bg, borderRadius: 16, overflow: "hidden",
  }}>
    {children}
  </div>
);

// ═══ 布局 ═══
// 画布 960×720 → 按 2x 输出 1920×1080
// 原版3列，间距黑色 ~8px
const W = 1920;
const H = 1080;
const CW = 590; // 列宽
const G = 10;   // 间距（黑色）
const X = [-120, (W - CW) / 2 - CW/2 - G/2 + 30, (W - CW) / 2 + CW/2 + G/2 + 30]; // 左(裁切) / 中偏左 / 中偏右
// 简化：3列均分 + 左右溢出
const X0 = -80;
const X1 = X0 + CW + G;  // 520
const X2 = X1 + CW + G;  // 1120

const RH = [320, 380, 320, 380, 320, 380, 320, 380, 320]; // 交替行高
const buildRows = () => {
  const ys = [];
  let y = 0;
  for (const h of RH) { ys.push(y); y += h + G; }
  return ys;
};
const Y = buildRows();

const CARDS = [
  // Row 0
  { id: "00", x: X0, y: Y[0], w: CW, h: RH[0], bg: C.sage, c: () => <><Photo type="curtains" /><Logo /><Size text="1440 × 900" /><Buttons /></> },
  { id: "01", x: X1, y: Y[0], w: CW, h: RH[0], bg: C.sage, c: () => <><Photo type="conference" /><Logo /></> },
  { id: "02", x: X2, y: Y[0], w: CW + 100, h: RH[0], bg: C.sage, c: () => <><BlockPattern variant="D" scale={0.9} /><Logo dark /></> },

  // Row 1
  { id: "10", x: X0, y: Y[1], w: CW, h: RH[1], bg: C.teal, c: () => <><BlockPattern variant="C" scale={1} /><Logo /></> },
  { id: "11", x: X1, y: Y[1], w: CW, h: RH[1], bg: C.white, c: () => <><BlockPattern variant="A" scale={0.85} /><Logo dark /><Size text="1440 × 900" /><Buttons /></> },
  { id: "12", x: X2, y: Y[1], w: CW + 100, h: RH[1], bg: C.yellow, c: () => <><Size text="1440 × 960" /><BlockPattern variant="B" scale={0.9} /><Logo /><Buttons /></> },

  // Row 2
  { id: "20", x: X0, y: Y[2], w: CW, h: RH[2], bg: C.white, c: () => <><Size text="1440 × 960" /><Logo /><Buttons /></> },
  { id: "21", x: X1, y: Y[2], w: CW, h: RH[2], bg: C.sage, c: () => <><BlockPattern variant="E" scale={0.8} /><Logo /></> },
  { id: "22", x: X2, y: Y[2], w: CW + 100, h: RH[2], bg: C.white, c: () => <><Photo type="laptop" /><Logo dark /></> },

  // Row 3
  { id: "30", x: X0, y: Y[3], w: CW, h: RH[3], bg: C.black, c: () => <><Photo type="silhouette" /></> },
  { id: "31", x: X1, y: Y[3], w: CW, h: RH[3], bg: C.white, c: () => <><BlockPattern variant="A" scale={0.9} /><Logo dark /><Size text="1440 × 900" /><Buttons /></> },
  { id: "32", x: X2, y: Y[3], w: CW + 100, h: RH[3], bg: C.yellow, c: () => <><BlockPattern variant="C" scale={1} /><Logo /></> },

  // Row 4
  { id: "40", x: X0, y: Y[4], w: CW, h: RH[4], bg: C.yellow, c: () => <><Size text="1440 × 900" /><BlockPattern variant="B" scale={0.7} /><Logo /><Buttons /></> },
  { id: "41", x: X1, y: Y[4], w: CW, h: RH[4], bg: C.white, c: () => <><Photo type="speaker" /><Logo dark /></> },
  { id: "42", x: X2, y: Y[4], w: CW + 100, h: RH[4], bg: C.teal, c: () => <><BlockPattern variant="D" scale={0.85} /></> },

  // Row 5
  { id: "50", x: X0, y: Y[5], w: CW, h: RH[5], bg: C.sage, c: () => <><Logo /><Size text="1440 × 900" /><BlockPattern variant="C" scale={0.8} /><Buttons /></> },
  { id: "51", x: X1, y: Y[5], w: CW, h: RH[5], bg: C.yellow, c: () => <><Size text="1440 × 900" /><BlockPattern variant="E" scale={0.75} /><Logo /><Buttons /></> },
  { id: "52", x: X2, y: Y[5], w: CW + 100, h: RH[5], bg: C.teal, c: () => <><BlockPattern variant="A" scale={0.9} /><Logo /></> },

  // Row 6
  { id: "60", x: X0, y: Y[6], w: CW, h: RH[6], bg: C.white, c: () => <><Photo type="conference" /><Logo dark /></> },
  { id: "61", x: X1, y: Y[6], w: CW, h: RH[6], bg: C.sage, c: () => <><Size text="1440 × 900" /><Logo /><Buttons /></> },
  { id: "62", x: X2, y: Y[6], w: CW + 100, h: RH[6], bg: C.yellow, c: () => <><BlockPattern variant="B" scale={0.85} /><Logo /></> },

  // Row 7
  { id: "70", x: X0, y: Y[7], w: CW, h: RH[7], bg: C.yellow, c: () => <><Size text="1440 × 900" /><Logo /><BlockPattern variant="C" scale={0.9} /><Buttons /></> },
  { id: "71", x: X1, y: Y[7], w: CW, h: RH[7], bg: C.white, c: () => <><BlockPattern variant="A" scale={0.85} /><Logo dark /><Size text="1440 × 900" /><Buttons /></> },
  { id: "72", x: X2, y: Y[7], w: CW + 100, h: RH[7], bg: C.sage, c: () => <><Photo type="curtains" /><Logo /></> },

  // Row 8
  { id: "80", x: X0, y: Y[8], w: CW, h: RH[8], bg: C.sage, c: () => <><Photo type="laptop" /><Logo /></> },
  { id: "81", x: X1, y: Y[8], w: CW, h: RH[8], bg: C.teal, c: () => <><BlockPattern variant="D" scale={0.8} /></> },
  { id: "82", x: X2, y: Y[8], w: CW + 100, h: RH[8], bg: C.white, c: () => <><Size text="1440 × 900" /><Logo dark /><Buttons /></> },
];

// ─── Gemini 分析的精确关键帧 ───
// 运动模型：相机推拉（Zoom + Pan），不是滚动
// 所有卡片在同一平面，"相机"向右下角某张卡片推进
// 总缩放：1x → 3x，ease-out 长阻尼
const KEYFRAMES = [
  { time: 0.0, x: 0,    y: 0,    scale: 1.00 },
  { time: 0.5, x: -10,  y: -15,  scale: 1.05 },
  { time: 1.0, x: -30,  y: -45,  scale: 1.15 },
  { time: 1.5, x: -80,  y: -110, scale: 1.35 },
  { time: 2.0, x: -160, y: -220, scale: 1.65 },
  { time: 2.5, x: -280, y: -380, scale: 2.00 },
  { time: 3.0, x: -420, y: -560, scale: 2.35 },
  { time: 4.0, x: -640, y: -840, scale: 2.80 },
  { time: 5.0, x: -710, y: -940, scale: 2.95 },
  { time: 7.0, x: -740, y: -980, scale: 3.00 },
];

const KF_TIMES = KEYFRAMES.map(k => k.time);
const KF_X = KEYFRAMES.map(k => k.x);
const KF_Y = KEYFRAMES.map(k => k.y);
const KF_SCALE = KEYFRAMES.map(k => k.scale);

export const ScrollingWallDemo = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps; // 秒

  const scale = interpolate(time, KF_TIMES, KF_SCALE, { extrapolateRight: "clamp" });
  const tx = interpolate(time, KF_TIMES, KF_X, { extrapolateRight: "clamp" });
  const ty = interpolate(time, KF_TIMES, KF_Y, { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: C.black, overflow: "hidden" }}>
      <div style={{
        position: "relative", width: 1920, height: 5000,
        transform: `scale(${scale}) translate(${tx}px, ${ty}px)`,
        transformOrigin: "0% 0%",
      }}>
        {CARDS.map((card) => (
          <Card key={card.id} x={card.x} y={card.y} w={card.w} h={card.h} bg={card.bg}>
            {card.c()}
          </Card>
        ))}
      </div>
    </AbsoluteFill>
  );
};
