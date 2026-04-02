// === 颜色插值工具 ===

export function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

export function rgbToHex(r, g, b) {
  return "#" + [r, g, b].map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
}

export function lerpColor(frame, kfs) {
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

// === 场景查找 ===

export function getScene(frame, scenes) {
  for (const s of scenes) {
    if (frame >= s.start && frame <= s.end) return s;
  }
  return scenes[scenes.length - 1];
}
