import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "./layers/L0-Background";
import { CardShells } from "./layers/L1-CardShells";
import { CardColors } from "./layers/L2-CardColors";
import { CardEntry } from "./layers/L3-CardEntry";
import { ContentStatic } from "./layers/L4-ContentStatic";
import { ContentAnim } from "./layers/L5-ContentAnim";
import { Decorations } from "./layers/L6-Decorations";
import { Transitions } from "./layers/L7-Transitions";
import { MicroMotion } from "./layers/L8-MicroMotion";

// layerMask: 只渲染 <= mask 的层，用于逐层验证
export const AnuaV2 = ({ layerMask = 8 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const ctx = { frame, fps, width, height, layerMask };

  return (
    <AbsoluteFill>
      {layerMask >= 0 && <Background {...ctx} />}
      {layerMask >= 1 && <CardShells {...ctx} />}
      {layerMask >= 2 && <CardColors {...ctx} />}
      {layerMask >= 3 && <CardEntry {...ctx} />}
      {layerMask >= 4 && <ContentStatic {...ctx} />}
      {layerMask >= 5 && <ContentAnim {...ctx} />}
      {layerMask >= 6 && <Decorations {...ctx} />}
      {layerMask >= 7 && <Transitions {...ctx} />}
      {layerMask >= 8 && <MicroMotion {...ctx} />}
    </AbsoluteFill>
  );
};
