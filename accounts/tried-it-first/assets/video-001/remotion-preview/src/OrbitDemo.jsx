import { Lottie } from "@remotion/lottie";
import { useEffect, useState } from "react";
import { AbsoluteFill, staticFile, continueRender, delayRender } from "remotion";

export const OrbitDemo = () => {
  const [animationData, setAnimationData] = useState(null);
  const [handle] = useState(() => delayRender("Loading Lottie"));

  useEffect(() => {
    fetch(staticFile("orbit.json"))
      .then((r) => r.json())
      .then((data) => {
        setAnimationData(data);
        continueRender(handle);
      })
      .catch((err) => {
        console.error(err);
        continueRender(handle);
      });
  }, [handle]);

  if (!animationData) return null;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Lottie
        animationData={animationData}
        style={{ width: "100%", height: "100%" }}
      />
    </AbsoluteFill>
  );
};
