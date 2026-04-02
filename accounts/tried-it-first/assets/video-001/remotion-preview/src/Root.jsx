import React from "react";
import { Composition } from "remotion";
import { Video001 } from "./Video001.jsx";
import { Video002 } from "./Video002.jsx";
import { ScrollingWallDemo } from "./ScrollingWallDemo.jsx";
import { OrbitDemo } from "./OrbitDemo.jsx";
import { AnuaPromo } from "./AnuaPromo.jsx";
import { AnuaV2 } from "./anua-v2/index.jsx";
import { LottieTest } from "./LottieTest.jsx";
import { AETitle } from "./AETitle.jsx";
import { AETitleGenerated } from "./AETitleGenerated.jsx";

const V2_PROPS = { durationInFrames: 30 * 9, fps: 30, width: 1920, height: 1080 };

export const RemotionRoot = () => {
  return (
    <>
      {/* === V1 (旧版保留) === */}
      <Composition
        id="Anua-Promo-3Cards"
        component={AnuaPromo}
        durationInFrames={30 * 9}
        fps={30}
        width={1920}
        height={1080}
      />
      {/* === V2 逐层验证 === */}
      <Composition id="Anua-V2-Full" component={AnuaV2} {...V2_PROPS} />
      <Composition id="Anua-V2-L1" component={() => <AnuaV2 layerMask={1} />} {...V2_PROPS} />
      <Composition id="Anua-V2-L2" component={() => <AnuaV2 layerMask={2} />} {...V2_PROPS} />
      <Composition id="Anua-V2-L3" component={() => <AnuaV2 layerMask={3} />} {...V2_PROPS} />
      <Composition id="Anua-V2-L5" component={() => <AnuaV2 layerMask={5} />} {...V2_PROPS} />
      {/* === Lottie 测试 === */}
      <Composition id="Lottie-Test" component={LottieTest} durationInFrames={150} fps={30} width={1920} height={1080} />
      {/* === AE 精确翻译 === */}
      <Composition id="AE-Title" component={AETitle} durationInFrames={150} fps={30} width={1920} height={1080} />
      <Composition id="AE-Title-Generated" component={AETitleGenerated} durationInFrames={150} fps={30} width={1920} height={1080} />
      <Composition
        id="Orbit-Lottie"
        component={OrbitDemo}
        durationInFrames={60 * 5.3}
        fps={60}
        width={1600}
        height={1200}
      />
      <Composition
        id="ScrollingWall-Demo"
        component={ScrollingWallDemo}
        durationInFrames={30 * 7}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Video002-VibeCoding"
        component={Video002}
        durationInFrames={30 * 182}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Video001-Legacy"
        component={Video001}
        durationInFrames={30 * 285}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
