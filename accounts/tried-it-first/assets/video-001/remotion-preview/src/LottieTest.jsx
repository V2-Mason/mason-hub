import React, { useEffect, useRef } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import lottie from "lottie-web";

const animationData = require("../public/lottie-test.json");

export const LottieTest = () => {
  const frame = useCurrentFrame();
  const containerRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || animRef.current) return;

    animRef.current = lottie.loadAnimation({
      container: containerRef.current,
      renderer: "svg",
      loop: false,
      autoplay: false,
      animationData,
    });
  }, []);

  useEffect(() => {
    if (!animRef.current) return;
    const totalLottieFrames = animRef.current.totalFrames;
    const lottieFrame = (frame / 150) * totalLottieFrames;
    animRef.current.goToAndStop(lottieFrame, true);
  }, [frame]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </AbsoluteFill>
  );
};
