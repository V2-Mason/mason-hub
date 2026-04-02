import React from "react";
import { AbsoluteFill } from "remotion";
import { BG_COLOR } from "../constants";

export const Background = () => {
  return <AbsoluteFill style={{ backgroundColor: BG_COLOR }} />;
};
