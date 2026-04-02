// Auto-generated from ae_full_export.json
// Source: "Title_01 (fast typography)" — 1920x1080 @ 29.9700012207031fps, 150 frames
// DO NOT EDIT by hand — regenerate with ae-to-remotion.mjs

import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";

const bez = (x1, y1, x2, y2) => Easing.bezier(
  Math.max(0, Math.min(1, x1)),
  Math.max(-2, Math.min(2, y1)),
  Math.max(0, Math.min(1, x2)),
  Math.max(-2, Math.min(2, y2))
);

// ── TEXT_04 (300 frames, 1920x1080) ──
const Comp_TEXT_04 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] titles (text) f0-300 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"titles"}
      </div>
    </AbsoluteFill>
  );
};

// ── TEXT_03 (300 frames, 1920x1080) ──
const Comp_TEXT_03 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] &smart (text) f0-300 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"&smart"}
      </div>
    </AbsoluteFill>
  );
};

// ── TEXT_02 (300 frames, 1920x1080) ──
const Comp_TEXT_02 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] fresh (text) f0-300 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"fresh"}
      </div>
    </AbsoluteFill>
  );
};

// ── TEXT_02_comp (300 frames, 1920x1080) ──
const Comp_TEXT_02_comp = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [7] frame (shape) f0-74 */}
      {/* shape layer — TODO */}
      {/* [6] TEXT_02 (precomp) f0-74 */}
      {frame >= 0 && frame < 74 && (
        <Comp_TEXT_02 parentFrame={frame} />
      )}
      {/* [4] TEXT_03 (precomp) f27-74 */}
      {frame >= 27 && frame < 74 && (
        <Comp_TEXT_03 parentFrame={(frame - 27)} />
      )}
      {/* [2] TEXT_04 (precomp) f59-74 */}
      {frame >= 59 && frame < 74 && (
        <Comp_TEXT_04 parentFrame={(frame - 59)} />
      )}
    </AbsoluteFill>
  );
};

// ── TEXT_05 (300 frames, 1920x1080) ──
const Comp_TEXT_05 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [3] frame (shape) f0-300 */}
      {/* shape layer — TODO */}
      {/* [2] from Mixkit (text) f0-300 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"from Mixkit"}
      </div>
      {/* [1] Position (solid) f0-300 */}
      {/* solid "Position" — control/matte layer, skipped */}
    </AbsoluteFill>
  );
};

// ── Placeholder _Text (300 frames, 1920x1080) ──
const Comp_Placeholder_Text = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] placeholder  (text) f0-300 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"placeholder "}
      </div>
    </AbsoluteFill>
  );
};

// ── Photo/Video (300 frames, 1920x1080) ──
const Comp_Photo_Video = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [2] Placeholder (solid) f0-300 */}
      <div style={{ position: "absolute", inset: 0, backgroundColor: "#009a5a" }} />
      {/* [1] Placeholder _Text (precomp) f0-300 */}
      <Comp_Placeholder_Text parentFrame={frame} />
    </AbsoluteFill>
  );
};

// ── PLACEHOLDER_02 (1798 frames, 1920x1080) ──
const Comp_PLACEHOLDER_02 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] Photo/Video (precomp) f0-300 */}
      {frame >= 0 && frame < 300 && (
        <Comp_Photo_Video parentFrame={frame} />
      )}
    </AbsoluteFill>
  );
};

// ── Scene_02_main (120 frames, 1920x1080) ──
const Comp_Scene_02_main = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [8] PLACEHOLDER_02 (precomp) f0-120 */}
      <Comp_PLACEHOLDER_02 parentFrame={frame} />
      {/* [7] PLACEHOLDER_02 (precomp) f0-120 */}
      <Comp_PLACEHOLDER_02 parentFrame={frame} />
      {/* [6] White Solid  (solid) f71-120 */}
      {frame >= 71 && frame < 120 && (
        <div style={{ position: "absolute", inset: 0, backgroundColor: "#ffffff" }} />
      )}
      {/* [4] TEXT_02_comp (precomp) f0-120 */}
      <Comp_TEXT_02_comp parentFrame={frame} />
      {/* [3] Scale_Text (solid) f0-120 */}
      {/* solid "Scale_Text" — control/matte layer, skipped */}
      {/* [2] Camera 1 (camera) f0-120 */}
      {/* camera layer "Camera 1" — skipped (handled in Task 4) */}
      {/* [1] Camera position (solid) f0-120 */}
      {/* solid "Camera position" — control/matte layer, skipped */}
    </AbsoluteFill>
  );
};

// ── unit_02 (120 frames, 1920x1080) ──
const Comp_unit_02 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [4] Scene_02_main (precomp) f0-120 */}
      <Comp_Scene_02_main parentFrame={frame} />
      {/* [2] Scene_02_main (precomp) f0-120 */}
      <Comp_Scene_02_main parentFrame={frame} />
    </AbsoluteFill>
  );
};

// ── TEXT_01 (300 frames, 1920x1080) ──
const Comp_TEXT_01 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] clean (text) f0-300 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"clean"}
      </div>
    </AbsoluteFill>
  );
};

// ── PLACEHOLDER_01 (300 frames, 1920x1080) ──
const Comp_PLACEHOLDER_01 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [1] Photo/Video (precomp) f0-300 */}
      <Comp_Photo_Video parentFrame={frame} />
    </AbsoluteFill>
  );
};

// ── TEXT_01_comp (60 frames, 1920x1080) ──
const Comp_TEXT_01_comp = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [3] PLACEHOLDER_01 (precomp) f0-60 */}
      <Comp_PLACEHOLDER_01 parentFrame={frame} />
      {/* [2] BG (solid) f0-60 */}
      <div style={{ position: "absolute", inset: 0, backgroundColor: "#ffffff" }} />
    </AbsoluteFill>
  );
};

// ── unit_01 (60 frames, 1920x1080) ──
const Comp_unit_01 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [4] TEXT_01_comp (precomp) f0-60 */}
      <Comp_TEXT_01_comp parentFrame={frame} />
      {/* [2] TEXT_01_comp (precomp) f0-60 */}
      <Comp_TEXT_01_comp parentFrame={frame} />
    </AbsoluteFill>
  );
};

// ── Title_01_Main (135 frames, 1920x1080) ──
const Comp_Title_01_Main = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [2] unit_01 (precomp) f0-60 */}
      {frame >= 0 && frame < 60 && (
        <Comp_unit_01 parentFrame={frame} />
      )}
      {/* [1] unit_02 (precomp) f15-139 */}
      {frame >= 15 && frame < 139 && (
        <Comp_unit_02 parentFrame={(frame - 15) / 1.04201680672269} />
      )}
    </AbsoluteFill>
  );
};

// ── Title_01 (fast typography) (150 frames, 1920x1080) ──
const Comp_Title_01_fast_typography = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  return (
    <AbsoluteFill>
      {/* [3] Title_01_Main (precomp) f0-150 */}
      <Comp_Title_01_Main parentFrame={frame / 1.11111111111111} />
      {/* [2] Controls (solid) f0-150 */}
      {/* solid "Controls" — control/matte layer, skipped */}
      {/* [1] <empty text layer> (text) f0-150 */}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Arial, sans-serif",
        fontSize: 48,
        color: "#ffffff",
        fontWeight: 800,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        userSelect: "none",
      }}>
        {"<empty text layer>"}
      </div>
    </AbsoluteFill>
  );
};

// ── Main export ──
export const AETitleGenerated = () => {
  const frame = useCurrentFrame();
  return <Comp_Title_01_fast_typography parentFrame={frame} />;
};
