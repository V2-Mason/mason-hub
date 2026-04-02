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

  const l6_TEXT_02_posX =
    frame < 49
    ? interpolate(frame, [39, 49], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.524, 0.524, 0.311, 0.311) })
    :
    frame < 56
    ? interpolate(frame, [49, 56], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.333, 0.333, 0.311, 0.311) })
    :
    interpolate(frame, [56, 63], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.5, 0.5, 0.471, 0.471) });
  const l6_TEXT_02_posY =
    frame < 49
    ? interpolate(frame, [39, 49], [540, 754], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    :
    frame < 56
    ? interpolate(frame, [49, 56], [754, 754], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    :
    interpolate(frame, [56, 63], [754, 925], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l6_TEXT_02_posZ =
    frame < 49
    ? interpolate(frame, [39, 49], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    :
    frame < 56
    ? interpolate(frame, [49, 56], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    :
    interpolate(frame, [56, 63], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_TEXT_04_posX = interpolate(frame, [59, 68], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.333, 0.333, 0.081, 0.081) });
  const l2_TEXT_04_posY = interpolate(frame, [59, 68], [393, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_TEXT_04_posZ = interpolate(frame, [59, 68], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {/* [7] frame (shape) f0-74 */}
      {/* shape layer — TODO */}
      {/* [6] TEXT_02 (precomp) f0-74 */}
      {frame >= 0 && frame < 74 && (
        <div style={{ position: "absolute", left: l6_TEXT_02_posX - 960, top: l6_TEXT_02_posY - 540 }}>
          <Comp_TEXT_02 parentFrame={frame} />
        </div>
      )}
      {/* [4] TEXT_03 (precomp) f27-74 */}
      {frame >= 27 && frame < 74 && (
        <Comp_TEXT_03 parentFrame={(frame - 27)} />
      )}
      {/* [2] TEXT_04 (precomp) f59-74 */}
      {frame >= 59 && frame < 74 && (
        <div style={{ position: "absolute", left: l2_TEXT_04_posX - 960, top: l2_TEXT_04_posY - 540 }}>
          <Comp_TEXT_04 parentFrame={(frame - 59)} />
        </div>
      )}
    </AbsoluteFill>
  );
};

// ── TEXT_05 (300 frames, 1920x1080) ──
const Comp_TEXT_05 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  const l2_from_Mixkit_posX = interpolate(frame, [0, 20], [-80, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.813, 0.813, 0.578, 0.578) });
  const l2_from_Mixkit_posY = interpolate(frame, [0, 20], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_from_Mixkit_posZ = interpolate(frame, [0, 20], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

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

  // Task 4: 3D camera perspective
  const zoom = 1866.667;
  const camZ =
    frame < 35
    ? interpolate(frame, [17, 35], [801, -253], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    :
    interpolate(frame, [35, 45], [-253, 452], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const camScale = zoom / (zoom - camZ);

  const placeZ = interpolate(frame, [17, 35], [-500, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const placeZScale = zoom / (zoom - placeZ);

  const l7_PLACEHOLDER_02_posX = interpolate(frame, [17, 35], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.597, 0.597, 0.369, 0.369) });
  const l7_PLACEHOLDER_02_posY = interpolate(frame, [17, 35], [540, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l7_PLACEHOLDER_02_posZ = interpolate(frame, [17, 35], [-500, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l6_White_Solid_posX = interpolate(frame, [71, 77], [2658.78, 1160.7608], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.333, 0.333, 0.168, 0.168) });
  const l6_White_Solid_posY = interpolate(frame, [71, 77], [555.775890063996, 555.775890063996], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l6_White_Solid_posZ = interpolate(frame, [71, 77], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {/* Camera perspective wrapper */}
      <div style={{ position: "absolute", left: "50%", top: "50%", transform: `translate(-50%,-50%) scale(${camScale})`, width: 1920, height: 1080 }}>
        {/* [8] PLACEHOLDER_02 (precomp) f0-120 */}
        <Comp_PLACEHOLDER_02 parentFrame={frame} />
        {/* [7] PLACEHOLDER_02 (precomp) f0-120 */}
        <div style={{ position: "absolute", left: l7_PLACEHOLDER_02_posX - 960, top: l7_PLACEHOLDER_02_posY - 540, transform: `scale(${placeZScale})` }}>
          <Comp_PLACEHOLDER_02 parentFrame={frame} />
        </div>
        {/* [6] White Solid  (solid) f71-120 */}
        {frame >= 71 && frame < 120 && (
          <div style={{ position: "absolute", backgroundColor: "#ffffff", left: l6_White_Solid_posX - 960, top: l6_White_Solid_posY - 540 }} />
        )}
        {/* [4] TEXT_02_comp (precomp) f0-120 */}
        <Comp_TEXT_02_comp parentFrame={frame} />
        {/* [3] Scale_Text (solid) f0-120 */}
        {/* solid "Scale_Text" — control/matte layer, skipped */}
        {/* [2] Camera 1 (camera) f0-120 */}
        {/* camera layer "Camera 1" — handled in Task 4 */}
        {/* [1] Camera position (solid) f0-120 */}
        {/* solid "Camera position" — control/matte layer, skipped */}
      </div>
    </AbsoluteFill>
  );
};

// ── unit_02 (120 frames, 1920x1080) ──
const Comp_unit_02 = ({ parentFrame = 0 }) => {
  const frame = parentFrame;

  const l4_Scene_02_main_posX = interpolate(frame, [0, 19], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.529, 0.529, 0.107, 0.107) });
  const l4_Scene_02_main_posY = interpolate(frame, [0, 19], [-5, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l4_Scene_02_main_posZ = interpolate(frame, [0, 19], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_Scene_02_main_posX = interpolate(frame, [0, 19], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.529, 0.529, 0.107, 0.107) });
  const l2_Scene_02_main_posY = interpolate(frame, [0, 19], [1083, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_Scene_02_main_posZ = interpolate(frame, [0, 19], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {/* [4] Scene_02_main (precomp) f0-120 */}
      <div style={{ position: "absolute", left: l4_Scene_02_main_posX - 960, top: l4_Scene_02_main_posY - 540 }}>
        <Comp_Scene_02_main parentFrame={frame} />
      </div>
      {/* [2] Scene_02_main (precomp) f0-120 */}
      <div style={{ position: "absolute", left: l2_Scene_02_main_posX - 960, top: l2_Scene_02_main_posY - 540 }}>
        <Comp_Scene_02_main parentFrame={frame} />
      </div>
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

  const l4_TEXT_01_comp_posX = interpolate(frame, [0, 15], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.386, 0.386, 0.082, 0.082) });
  const l4_TEXT_01_comp_posY = interpolate(frame, [0, 15], [799, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l4_TEXT_01_comp_posZ = interpolate(frame, [0, 15], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_TEXT_01_comp_posX = interpolate(frame, [0, 15], [960, 960], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: bez(0.386, 0.386, 0.097, 0.097) });
  const l2_TEXT_01_comp_posY = interpolate(frame, [0, 15], [273, 540], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const l2_TEXT_01_comp_posZ = interpolate(frame, [0, 15], [0, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {/* [4] TEXT_01_comp (precomp) f0-60 */}
      <div style={{ position: "absolute", left: l4_TEXT_01_comp_posX - 960, top: l4_TEXT_01_comp_posY - 540 }}>
        <Comp_TEXT_01_comp parentFrame={frame} />
      </div>
      {/* [2] TEXT_01_comp (precomp) f0-60 */}
      <div style={{ position: "absolute", left: l2_TEXT_01_comp_posX - 960, top: l2_TEXT_01_comp_posY - 540 }}>
        <Comp_TEXT_01_comp parentFrame={frame} />
      </div>
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
