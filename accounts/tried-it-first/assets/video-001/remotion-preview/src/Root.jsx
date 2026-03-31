import { Composition } from "remotion";
import { Video001 } from "./Video001.jsx";
import { Video002 } from "./Video002.jsx";
import { ScrollingWallDemo } from "./ScrollingWallDemo.jsx";
import { OrbitDemo } from "./OrbitDemo.jsx";

export const RemotionRoot = () => {
  return (
    <>
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
