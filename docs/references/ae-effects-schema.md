# Adobe After Effects — 内置效果完整参数 Schema

> 版本：AE 2024/2025 | 用途：调参/优化时的速查表
> 不含已废弃效果（Obsolete）和第三方插件

---

## 概览统计

| 分类 | 效果数量 |
|------|---------|
| 3D Channel | 7 |
| Audio | 10 |
| Blur & Sharpen | 18 |
| Channel | 12 |
| Color Correction | 30+ |
| Distort | 30+ |
| Expression Controls | 8 |
| Generate | 20+ |
| Immersive Video | 5 |
| Keying | 10+ |
| Matte | 5 |
| Noise & Grain | 10+ |
| Perspective | 5 |
| Simulation | 8 |
| Stylize | 15+ |
| Text | 2 |
| Time | 7 |
| Transition | 12+ |
| Utility | 5+ |
| **合计** | **~210+** |

---

## 参数类型说明

| Type | 说明 | 示例 |
|------|------|------|
| float | 浮点数滑块 | Opacity: 0-100 |
| int | 整数 | Segments: 1-100 |
| angle | 角度（可超360°/多圈） | Rotation: 0x+0° |
| point | 2D坐标 (x,y) | Center: (960, 540) |
| point3D | 3D坐标 (x,y,z) | Position: (0,0,0) |
| color | RGBA颜色 | Color: (255,0,0,255) |
| enum | 下拉菜单选项 | Mode: Normal/Add/... |
| boolean | 开关 | Invert: on/off |
| layer | 图层引用 | Source: None/layer |
| spline | 曲线控制点 | Curves: 0-255 mapping |

---

## 1. 3D Channel

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **3D Channel Extract** | 3D Channel | enum | Z Depth, Surface Normals, etc. | Z Depth |
| | White Point | float | 0-100 | 100 |
| | Black Point | float | 0-100 | 0 |
| | Softness | float | 0-100 | 0 |
| **Depth Matte** | Depth | float | 0-100 | 50 |
| | Feather | float | 0-100 | 0 |
| | Invert | boolean | on/off | off |
| **Depth of Field** | Focal Plane | float | 0-100 | 50 |
| | Maximum Radius | float | 0-100 | 3 |
| | Focal Plane Thickness | float | 0-100 | 0 |
| **EXtractoR** | Channel | enum | Z Depth, Object ID, UV, etc. | Z Depth |
| | White/Black Point | float | 0+ | varies |
| **Fog 3D** | Fog Start Depth | float | 0-100 | 0 |
| | Fog End Depth | float | 0-100 | 100 |
| | Fog Color | color | RGBA | white |
| | Fog Opacity | float | 0-100% | 100% |
| | Scattering Density | float | 0-100 | 0 |
| **ID Matte** | ID Selection | int | 0+ | 1 |
| | Feather | float | 0-100 | 0 |
| | Invert | boolean | on/off | off |
| **IDentifier** | (companion to EXtractoR) | — | — | — |

---

## 2. Audio

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Backwards** | Swap Channels | boolean | on/off | off |
| **Bass & Treble** | Bass | float | -100 to 100 dB | 0 |
| | Treble | float | -100 to 100 dB | 0 |
| **Delay** | Delay Time (ms) | float | 0-2000 | 500 |
| | Delay Amount | float | 0-100% | 50% |
| | Feedback | float | 0-100% | 50% |
| | Dry Out / Wet Out | float | 0-100% | 50%/50% |
| **Flange & Chorus** | Voice Separation Time (ms) | float | 0-100 | 3.5 |
| | Voices | int | 1-5 | 2 |
| | Modulation Rate (Hz) | float | 0-10 | 0.2 |
| | Modulation Depth | float | 0-100% | 50% |
| | Voice Phase Change | angle | 0-360 | 0 |
| | Invert Phase | boolean | on/off | off |
| | Stereo Voices | boolean | on/off | off |
| | Dry/Wet Mix | float | 0-100% | 50% |
| **High-Low Pass** | Filter Options | enum | Low Pass / High Pass | Low Pass |
| | Cutoff Frequency (Hz) | float | 0-22050 | 1000 |
| **Modulator** | Modulation Type | enum | Sine / Triangle | Sine |
| | Modulation Rate (Hz) | float | 0.1-100 | 1 |
| | Modulation Depth | float | 0-100% | 50% |
| | Amplitude Modulation | float | 0-100% | 0 |
| **Parametric EQ** | Band Enabled (x3) | boolean | on/off | on |
| | Frequency (Hz, x3) | float | 20-20000 | 200/1000/5000 |
| | Bandwidth (octaves, x3) | float | 0.1-5.0 | 1.0 |
| | Boost/Cut (dB, x3) | float | -20 to 20 | 0 |
| **Reverb** | Reverb Time (ms) | float | 1-3000 | 1000 |
| | Diffusion | float | 0-100% | 50% |
| | Decay | float | 0-100% | 50% |
| | Brightness | float | 0-100% | 50% |
| | Dry/Wet Mix | float | 0-100% | 50% |
| **Stereo Mixer** | Left Level | float | -100 to 100% | 100% |
| | Right Level | float | -100 to 100% | 100% |
| | Left Pan | float | -1.0 to 1.0 | -1.0 |
| | Right Pan | float | -1.0 to 1.0 | 1.0 |
| | Invert Phase | boolean | on/off | off |
| **Tone** | Frequency 1-5 (Hz) | float | 20-20000 | 440 |
| | Level 1-5 | float | 0-100% | 50% |
| | Waveform | enum | Sine/Square/Saw/Triangle | Sine |

---

## 3. Blur & Sharpen

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Bilateral Blur** | Radius | float | 0-100 | 5 |
| | Threshold | float | 0-256 | 25.5 |
| | Colorize | boolean | on/off | off |
| **Camera Lens Blur** | Blur Radius | float | 0-500 | 0 |
| | Iris Shape | enum | 4-16 blades | Hexagon (6) |
| | Iris Roundness | float | 0-100% | 0 |
| | Iris Rotation | angle | 0-360 | 0 |
| | Iris Aspect Ratio | float | 0.1-10 | 1.0 |
| | Diffraction Fringe | float | 0-500 | 0 |
| | Highlight Gain | float | 0-500% | 0 |
| | Highlight Threshold | float | 0-255 | 200 |
| | Highlight Saturation | float | 0-100% | 0 |
| | Blur Map | enum | None / Effect & Masks / layer | None |
| | Blur Focal Distance | float | 0-255 | 0 |
| | Repeat Edge Pixels | boolean | on/off | on |
| **Channel Blur** | Red Blurriness | float | 0-500 | 0 |
| | Green Blurriness | float | 0-500 | 0 |
| | Blue Blurriness | float | 0-500 | 0 |
| | Alpha Blurriness | float | 0-500 | 0 |
| | Edge Behavior | enum | Repeat / Clip | Repeat |
| | Blur Dimensions | enum | H and V / H / V | H and V |
| **Compound Blur** | Blur Layer | layer | any layer | None |
| | Maximum Blur | float | 0-500 | 20 |
| | Stretch Map to Fit | boolean | on/off | on |
| | Invert Blur | boolean | on/off | off |
| **Directional Blur** | Direction | angle | 0-360 | 0 |
| | Blur Length | float | 0-500 | 0 |
| **Fast Box Blur** | Blur Radius | float | 0-500 | 3 |
| | Iterations | int | 1-20 | 3 |
| | Blur Dimensions | enum | H and V / H / V | H and V |
| | Repeat Edge Pixels | boolean | on/off | on |
| **Gaussian Blur** | Blurriness | float | 0-30000 | 0 |
| | Blur Dimensions | enum | H and V / H / V | H and V |
| | Repeat Edge Pixels | boolean | on/off | on |
| **Radial Blur** | Amount | float | 0-100 | 10 |
| | Type | enum | Spin / Zoom | Spin |
| | Antialiasing | enum | Low / Medium / High | High |
| | Center | point | (x,y) | center |
| **Sharpen** | Sharpen Amount | float | 0-500 | 0 |
| **Smart Blur** | Radius | float | 0.1-100 | 3 |
| | Threshold | float | 0-100 | 25 |
| | Mode | enum | Normal / Edge Only / Overlay Edge | Normal |
| | Quality | enum | Low / Medium / High | High |
| **Unsharp Mask** | Amount | float | 0-500% | 100% |
| | Radius | float | 0.1-250 | 2 |
| | Threshold | float | 0-255 | 0 |
| **CC Cross Blur** | Radius | float | 0-500 | 10 |
| | Transfer Mode | enum | blend modes | Normal |
| **CC Radial Blur** | Amount | float | 0-100 | 10 |
| | Center | point | (x,y) | center |
| | Type | enum | Straight Zoom / Fading Zoom / Spin | Straight Zoom |
| **CC Radial Fast Blur** | Amount | float | 0-100 | 10 |
| | Center | point | (x,y) | center |
| | Zoom | enum | Brightest / Darkest / Standard | Standard |
| **CC Vector Blur** | Amount | float | 0-500 | 10 |
| | Angle Offset | angle | 0-360 | 0 |
| | Type | enum | Naturally-Grayed / Constant-Length | Naturally |

---

## 4. Channel

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Arithmetic** | Operator | enum | And/Or/Xor/Add/Sub/Multiply/Difference/etc. | And |
| | Value (R/G/B) | int | 0-255 | 0 |
| **Blend** | Blend With Layer | layer | any | None |
| | Mode | enum | Crossfade/Darken Only/Lighten Only/etc. | Crossfade |
| | Blend With Original | float | 0-100% | 0% |
| **Calculations** | Input Channel | enum | RGBA / R / G / B / A / Gray | RGBA |
| | Second Layer | layer | any | None |
| | Second Layer Channel | enum | RGBA / R / G / B / A / Gray | RGBA |
| | Blending Mode | enum | standard blend modes | Multiply |
| | Stretch Second Source | boolean | on/off | on |
| | Preserve Transparency | boolean | on/off | off |
| **Channel Combiner** | From | enum | RGB / Lightness / Hue / Saturation | Lightness |
| | To | enum | RGB / Lightness / Hue / Saturation | Lightness |
| | Invert | boolean | on/off | off |
| **Compound Arithmetic** | Second Source Layer | layer | any | None |
| | Operator | enum | Copy/Add/Sub/Multiply/Difference/And/Or/etc. | Copy |
| | Operate on Channels | enum | All / RGBA Ind. | All |
| | Overflow Behavior | enum | Clip / Wrap Back / Scale | Clip |
| | Stretch Second Source | boolean | on/off | on |
| **Invert** | Channel | enum | RGB/R/G/B/HLS/Hue/Lightness/Saturation/YIQ/Alpha | RGB |
| | Blend With Original | float | 0-100% | 0% |
| **Minimax** | Operation | enum | Minimum / Maximum / Min Then Max / Max Then Min | Minimum |
| | Radius | int | 1-100 | 1 |
| | Channel | enum | RGBA / R&G&B / Alpha | RGBA |
| | Direction | enum | H&V / H / V / Just R / Just G / Just B / Just A | H&V |
| **Remove Color Matting** | Background Color | color | RGBA | black |
| **Set Channels** | Take _ From (x4) | enum | Source R/G/B/A / Full On / Full Off | Source R/G/B/A |
| **Set Matte** | Take Matte From Layer | layer | any | None |
| | Use for Matte | enum | R / G / B / A / Luma / Hue / Lightness / Saturation | Alpha |
| | Invert Matte | boolean | on/off | off |
| | Stretch Matte to Fit | boolean | on/off | on |
| | Premultiply Matte Layer | boolean | on/off | on |
| **Shift Channels** | Take Red From | enum | R/G/B/A/Full On/Full Off | Red |
| | Take Green From | enum | same | Green |
| | Take Blue From | enum | same | Blue |
| | Take Alpha From | enum | same | Alpha |
| **CC Composite** | (blending controls for layered compositing) | — | — | — |

---

## 5. Color Correction

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Auto Color** | Temporal Smoothing (sec) | float | 0-10 | 0 |
| | Scene Detect | boolean | on/off | off |
| | Black Clip % | float | 0-50% | 0.10% |
| | White Clip % | float | 0-50% | 0.10% |
| | Blend With Original | float | 0-100% | 0% |
| | Snap Neutral Midtones | boolean | on/off | on |
| **Auto Contrast** | (同 Auto Color，无 Snap Neutral Midtones) | — | — | — |
| **Auto Levels** | (同 Auto Color，无 Snap Neutral Midtones) | — | — | — |
| **Black & White** | Reds | float | -200 to 300% | 40% |
| | Yellows | float | -200 to 300% | 60% |
| | Greens | float | -200 to 300% | 40% |
| | Cyans | float | -200 to 300% | 60% |
| | Blues | float | -200 to 300% | 20% |
| | Magentas | float | -200 to 300% | 80% |
| | Tint | boolean | on/off | off |
| | Tint Color | color | RGBA | sepia |
| **Brightness & Contrast** | Brightness | float | -150 to 150 | 0 |
| | Contrast | float | -100 to 100 | 0 |
| | Use Legacy | boolean | on/off | off |
| **Broadcast Colors** | Broadcast Locale | enum | NTSC / PAL | NTSC |
| | How to Make Color Safe | enum | Reduce Luminance / Reduce Saturation / Key Out Unsafe / Key Out Safe | Reduce Luminance |
| | Maximum Signal (IRE) | float | 90-120 | 110 |
| **CC Color Offset** | Red Offset | float | -200 to 200 | 0 |
| | Green Offset | float | -200 to 200 | 0 |
| | Blue Offset | float | -200 to 200 | 0 |
| **CC Toner** | Tones | enum | Duotone / Tritone / Pentone | Tritone |
| | Highlights / Midtones / Shadows | color | RGBA | varies |
| | Blend With Original | float | 0-100% | 0% |
| **Change Color** | Hue Transform | angle | -180 to 180 | 0 |
| | Lightness Transform | float | -100 to 100 | 0 |
| | Saturation Transform | float | -100 to 100 | 0 |
| | Color to Change | color | RGBA | red |
| | Matching Tolerance | float | 0-100% | 25% |
| | Matching Softness | float | 0-100% | 0% |
| | Match | enum | Color / Hue / Chroma | Color |
| | Invert Color Correction Mask | boolean | on/off | off |
| **Change to Color** | From | color | RGBA | red |
| | To | color | RGBA | red |
| | Change | enum | Hue / Hue & Lightness / Hue & Saturation / All | Hue |
| | Tolerance | float | 0-100% | 10% |
| | Softness | float | 0-100% | 0% |
| **Channel Mixer** | Red-Red / Red-Green / Red-Blue | float | -200 to 200% | 100/0/0 |
| | Green-Red / Green-Green / Green-Blue | float | -200 to 200% | 0/100/0 |
| | Blue-Red / Blue-Green / Blue-Blue | float | -200 to 200% | 0/0/100 |
| | Red/Green/Blue Const | float | -200 to 200% | 0 |
| | Monochrome | boolean | on/off | off |
| **Color Balance** | Shadow R/G/B Balance | float | -100 to 100 | 0 |
| | Midtone R/G/B Balance | float | -100 to 100 | 0 |
| | Highlight R/G/B Balance | float | -100 to 100 | 0 |
| | Preserve Luminosity | boolean | on/off | on |
| **Color Balance (HLS)** | Hue | angle | -180 to 180 | 0 |
| | Lightness | float | -100 to 100 | 0 |
| | Saturation | float | -100 to 100 | 0 |
| **Colorama** | Input Phase (Get Phase From) | enum | Intensity / Hue / Saturation / Lightness / etc. | Intensity |
| | Output Cycle | preset palette | 30+ palettes | Fire |
| | Modify | enum | All / Hue / Saturation / Lightness | All |
| | Cycle Repetitions | float | 1-100 | 1 |
| | Blend With Original | float | 0-100% | 0% |
| **Curves** | Channel | enum | RGB / Red / Green / Blue / Alpha | RGB |
| | Curve (control points) | spline | 0-255 → 0-255 | linear |
| **Equalize** | Equalize Based On | enum | RGB / Photoshop Style | Photoshop Style |
| | Amount to Equalize | float | 0-100% | 100% |
| **Exposure** | Exposure | float | -20 to 20 | 0 |
| | Offset | float | -10 to 10 | 0 |
| | Gamma Correction | float | 0.01-9.99 | 1.0 |
| | Bypass Linear Light Conversion | boolean | on/off | off |
| **Gamma/Pedestal/Gain** | Gamma (per channel) | float | 0-10 | 1.0 |
| | Pedestal (per channel) | float | -1 to 1 | 0 |
| | Gain (per channel) | float | 0-10 | 1.0 |
| **Hue/Saturation** | Channel Control | enum | Master / Reds / Yellows / Greens / Cyans / Blues / Magentas | Master |
| | Master Hue | angle | -180 to 180 | 0 |
| | Master Saturation | float | -100 to 100 | 0 |
| | Master Lightness | float | -100 to 100 | 0 |
| | Colorize | boolean | on/off | off |
| | Colorize Hue | angle | 0-360 | 0 |
| | Colorize Saturation | float | 0-100 | 25 |
| | Colorize Lightness | float | -100 to 100 | 0 |
| **Leave Color** | Amount to Decolor | float | 0-100% | 100% |
| | Color to Leave | color | RGBA | green |
| | Tolerance | float | 0-100% | 10% |
| | Edge Softness | float | 0-100% | 0% |
| | Match Colors | enum | Using RGB / Using Hue | Using RGB |
| **Levels** | Channel | enum | RGB / Red / Green / Blue / Alpha | RGB |
| | Input Black | float | 0-255 | 0 |
| | Input White | float | 0-255 | 255 |
| | Gamma | float | 0.1-10 | 1.0 |
| | Output Black | float | 0-255 | 0 |
| | Output White | float | 0-255 | 255 |
| **Levels (Individual Controls)** | (同 Levels，R/G/B/A 分离控制) | — | — | — |
| **Lumetri Color** | Temperature | float | -100 to 100 | 0 |
| | Tint | float | -100 to 100 | 0 |
| | Exposure | float | -5 to 5 | 0 |
| | Contrast | float | -100 to 100 | 0 |
| | Highlights | float | -100 to 100 | 0 |
| | Shadows | float | -100 to 100 | 0 |
| | Whites | float | -100 to 100 | 0 |
| | Blacks | float | -100 to 100 | 0 |
| | Saturation | float | 0-200 | 100 |
| | Creative: Faded Film | float | 0-100 | 0 |
| | Creative: Sharpen | float | 0-200 | 0 |
| | Creative: Vibrance | float | -100 to 100 | 0 |
| | Curves / Color Wheels / HSL Secondary / Vignette | (complex sub-panels) | — | — |
| **Photo Filter** | Filter | enum | Warming/Cooling/Color presets | Warming (85) |
| | Color | color | RGBA | orange tint |
| | Density | float | 0-100% | 25% |
| | Preserve Luminosity | boolean | on/off | on |
| **Selective Color** | Colors | enum | Reds/Yellows/Greens/Cyans/Blues/Magentas/Whites/Neutrals/Blacks | Reds |
| | Cyan/Magenta/Yellow/Black | float | -100 to 100% | 0% |
| | Method | enum | Relative / Absolute | Relative |
| **Shadow/Highlight** | Shadow Amount | float | 0-100% | 50% |
| | Shadow Tonal Width | float | 0-100% | 50% |
| | Shadow Radius | float | 0-2500 px | 30 |
| | Highlight Amount | float | 0-100% | 0% |
| | Highlight Tonal Width | float | 0-100% | 50% |
| | Highlight Radius | float | 0-2500 px | 30 |
| | Color Correction | float | -100 to 100 | +20 |
| | Midtone Contrast | float | -100 to 100 | 0 |
| | Black Clip | float | 0-50% | 0.01% |
| | White Clip | float | 0-50% | 0.01% |
| **Tint** | Map Black To | color | RGBA | black |
| | Map White To | color | RGBA | white |
| | Amount to Tint | float | 0-100% | 100% |
| **Tritone** | Highlights | color | RGBA | white |
| | Midtones | color | RGBA | gray |
| | Shadows | color | RGBA | black |
| | Blend With Original | float | 0-100% | 0% |
| **Vibrance** | Vibrance | float | -100 to 100 | 0 |
| | Saturation | float | -100 to 100 | 0 |

---

## 6. Distort

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Bezier Warp** | Top/Bottom/Left/Right vertex+tangent (12 pts) | point | (x,y) | layer corners |
| | Quality | enum | Draft / Standard / Best | Standard |
| **Bulge** | Horizontal Radius | float | 0-4000 | 100 |
| | Vertical Radius | float | 0-4000 | 100 |
| | Bulge Height | float | -4 to 4 | 1.5 |
| | Bulge Center | point | (x,y) | center |
| | Taper Radius | float | 0-100% | 0% |
| | Antialiasing | enum | Low / High | High |
| | Pin All Edges | boolean | on/off | off |
| **CC Bend It** | Start | point | (x,y) | top center |
| | End | point | (x,y) | bottom center |
| | Bend | float | -100 to 100 | 0 |
| **CC Blobylize** | Softness | float | 0-100 | 25 |
| | Cut Away | enum | Above / Below | Below |
| | Threshold | float | 0-255 | 128 |
| **CC Flo Motion** | Amount | float | 0-100 | 25 |
| **CC Griddler** | Horizontal Scale | float | 0-100% | 50% |
| | Vertical Scale | float | 0-100% | 50% |
| | Rotation | angle | 0-360 | 0 |
| **CC Lens** | Size | float | 0-500 | 100 |
| | Convergence | float | -100 to 100 | 0 |
| | Center | point | (x,y) | center |
| **CC Page Turn** | Fold Position | point | (x,y) | top-right |
| | Fold Direction | angle | 0-360 | 0 |
| | Fold Radius | float | 0-500 | 50 |
| | Paper Color | color | RGBA | white |
| | Render | enum | Front / Back / Both | Both |
| **CC Power Pin** | Upper Left/Right/Lower Left/Right | point | (x,y) | corners |
| | Perspective Correction | boolean | on/off | on |
| **CC Ripple Pulse** | Center | point | (x,y) | center |
| | Radius | float | 0-500 | 100 |
| | Amplitude | float | 0-100 | 25 |
| **CC Slant** | Slant | float | -100 to 100 | 0 |
| **CC Split** | Point A / Point B | point | (x,y) | varies |
| | Offset | float | 0-500 | 0 |
| **Corner Pin** | Upper Left/Right/Lower Left/Right | point | (x,y) | corners |
| **Displacement Map** | Displacement Map Layer | layer | any | None |
| | Use for H/V Displacement | enum | R/G/B/A/Luma/Hue/Lightness/Saturation/Full | Red/Green |
| | Max H/V Displacement | float | -32000 to 32000 | 0 |
| | Displacement Map Behavior | enum | Center Map / Stretch Map to Fit / Tile Map | Center Map |
| | Edge Behavior | enum | Wrap Pixels / Clip | Wrap |
| **Liquify** | Brush Size | float | 1-4000 | 100 |
| | Brush Pressure | float | 1-100% | 50% |
| | Turbulent Jitter | float | 0-100 | 20 |
| | Tools | enum | Warp/Twirl/Pucker/Bloat/Shift/Reflect/Turbulence/Reconstruct/Freeze/Thaw | Warp |
| **Magnify** | Shape | enum | Circle / Square | Circle |
| | Center | point | (x,y) | center |
| | Magnification | float | 0-600% | 200% |
| | Size | float | 0-5000 | 100 |
| | Feather | float | 0-100 | 0 |
| | Scaling | enum | Standard / Soft | Standard |
| **Mesh Warp** | Rows / Columns | int | 2-32 | 4/4 |
| | Elasticity | enum | Stiff / Normal / Super Fluid | Normal |
| | Quality | enum | Draft / Standard / Best | Standard |
| **Mirror** | Reflection Center | point | (x,y) | center |
| | Reflection Angle | angle | 0-360 | 0 |
| **Offset** | Shift Center To | point | (x,y) | center |
| | Blend With Original | float | 0-100% | 0% |
| **Optics Compensation** | Field of View (FOV) | float | 0-200 | 0 |
| | Reverse Lens Distortion | boolean | on/off | off |
| | FOV Orientation | enum | Horizontal / Vertical / Diagonal | Horizontal |
| | View Center | point | (x,y) | center |
| **Polar Coordinates** | Interpolation | float | 0-100% | 100% |
| | Type | enum | Rect to Polar / Polar to Rect | Rect to Polar |
| **Ripple** | Radius | float | 0-2000 | 200 |
| | Center | point | (x,y) | center |
| | Wave Speed | float | 0-10 | 1 |
| | Wave Width | float | 2-500 | 50 |
| | Wave Height | float | 0-999 | 10 |
| | Ripple Phase | angle | 0+ | 0 |
| **Spherize** | Radius | float | 0-2000 | 100 |
| | Center | point | (x,y) | center |
| **Transform** | Anchor Point | point | (x,y) | center |
| | Position | point | (x,y) | center |
| | Scale Height/Width | float | 0-500% | 100% |
| | Skew | float | -90 to 90 | 0 |
| | Rotation | angle | unlimited | 0 |
| | Opacity | float | 0-100% | 100% |
| | Shutter Angle | float | 0-720 | 0 |
| | Shutter Samples | int | 1-64 | 5 |
| **Turbulent Displace** | Displacement Type | enum | Turbulent/Bulge/Twist/etc. | Turbulent |
| | Amount | float | 0-500 | 50 |
| | Size | float | 2-1000 | 100 |
| | Offset (Turbulence) | point | (x,y) | center |
| | Complexity | float | 1-20 | 1 |
| | Evolution | angle | revolutions | 0 |
| | Cycle Evolution | boolean | on/off | off |
| | Random Seed | int | 0-30000 | 0 |
| | Pinning | enum | None / All Edges / Left & Right / Top & Bottom | None |
| **Twirl** | Angle | angle | -3600 to 3600 | 0 |
| | Twirl Radius | float | 0-4000 | 200 |
| | Twirl Center | point | (x,y) | center |
| **Warp** | Warp Style | enum | Arc/Arch/Bulge/Shell/Flag/Wave/Fish/Rise/Fisheye/Inflate/Squeeze/Twist | Arc |
| | Bend | float | -100 to 100 | 50 |
| | H/V Distortion | float | -100 to 100 | 0 |
| **Warp Stabilizer VFX** | Smoothness | float | 0-1000% | 50% |
| | Method | enum | Subspace Warp / Perspective / Pos,Scale,Rot / Position | Subspace Warp |
| | Result | enum | Smooth Motion / No Motion | Smooth Motion |
| | Framing | enum | Stabilize Only / Crop / Auto-scale / Synthesize Edges | Auto-scale |
| | Auto-scale | float | 100-200% | 110% |
| | Detailed Analysis | boolean | on/off | off |
| | Rolling Shutter Ripple | enum | Auto / Enhanced / off | off |
| **Wave Warp** | Wave Type | enum | Sine/Square/Triangle/Sawtooth/Circle/Semicircle/Noise/Smooth Noise | Sine |
| | Wave Height | float | 0-4000 | 25 |
| | Wave Width | float | 2-4000 | 200 |
| | Direction | angle | 0-360 | 0 |
| | Wave Speed | float | 0-99 | 1 |
| | Pinning | enum | None / All Edges / Left & Right / Top & Bottom | None |
| | Phase | angle | 0+ | 0 |

---

## 7. Expression Controls

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **3D Point Control** | 3D Point | point3D | (x,y,z) unlimited | (0,0,0) |
| **Angle Control** | Angle | angle | unlimited | 0 |
| **Checkbox Control** | Checkbox | boolean | on/off | on |
| **Color Control** | Color | color | RGBA | red |
| **Dropdown Menu Control** | Dropdown | enum | user-defined (max 998 items) | first item |
| **Layer Control** | Layer | layer | any comp layer | None |
| **Point Control** | Point | point | (x,y) unlimited | center |
| **Slider Control** | Slider | float | -1,000,000 to 1,000,000 | 0 |

---

## 8. Generate

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **4-Color Gradient** | Point 1/2/3/4 | point | (x,y) | corners |
| | Color 1/2/3/4 | color | RGBA | red/green/yellow/blue |
| | Blend | float | 0-100% | 50% |
| | Jitter | float | 0-100 | 0 |
| | Opacity | float | 0-100% | 100% |
| **Advanced Lightning** | Lightning Type | enum | Direction/Strike/Breaking/Omni/Bounce/etc. | Direction |
| | Segments | int | 1-100 | 5 |
| | Amplitude | float | 0-100 | 10 |
| | Branching | float | 0-100% | 50% |
| | Core Color / Glow Color | color | RGBA | white/blue |
| | Core Width / Glow Width | float | 0-100 | 3/15 |
| | Core Opacity / Glow Opacity | float | 0-100% | 100%/50% |
| | Composite On Original | boolean | on/off | on |
| **Audio Spectrum** | Audio Layer | layer | any audio layer | None |
| | Start/End Point | point | (x,y) | varies |
| | Start/End Frequency | float | 0-22050 Hz | 0/4000 |
| | Frequency Bands | int | 1-1024 | 64 |
| | Maximum Height | float | 0-2000 | 200 |
| | Audio Duration (ms) | float | 10-2000 | 50 |
| | Thickness | float | 0-100 | 2 |
| | Softness | float | 0-100 | 0 |
| | Inside/Outside Color | color | RGBA | white |
| | Display Options | enum | Digital / Analog Dots / Analog Lines | Digital |
| **Audio Waveform** | Audio Layer | layer | any | None |
| | Start/End Point | point | (x,y) | varies |
| | Displayed Samples | int | 1-4096 | 200 |
| | Maximum Height | float | 0-2000 | 200 |
| | Thickness / Softness | float | 0-100 | 2/0 |
| | Inside/Outside Color | color | RGBA | white |
| | Display Options | enum | Digital / Analog Dots / Analog Lines | Digital |
| **Beam** | Starting/Ending Point | point | (x,y) | varies |
| | Length | float | 0-100% | 100% |
| | Starting/Ending Thickness | float | 0-500 | 6/25 |
| | Softness | float | 0-100% | 0% |
| | Inside/Outside Color | color | RGBA | white/blue |
| | 3D Perspective | boolean | on/off | off |
| **Cell Pattern** | Cell Pattern | enum | Bubbles/Crystals/Pillow/Mixed Crystals/Tubular/Strings/etc. | Bubbles |
| | Invert | boolean | on/off | off |
| | Contrast / Stretch | float | varies | 100/0 |
| | Disperse | float | 0-100 | 0 |
| | Size | float | 1-1000 | 60 |
| | Offset | point | (x,y) | center |
| | Evolution | angle | revolutions | 0 |
| | Random Seed | int | 0-30000 | 0 |
| **Checkerboard** | Anchor | point | (x,y) | (0,0) |
| | Width / Height | float | 0-4000 | 100 |
| | Feather | float | 0-100 | 0 |
| | Color | color | RGBA | green |
| | Opacity | float | 0-100% | 100% |
| **Circle** | Center | point | (x,y) | center |
| | Radius | float | 0-4000 | 200 |
| | Edge | enum | None / Edge Radius / Thickness / etc. | None |
| | Feather | float | 0-500 | 0 |
| | Color | color | RGBA | white |
| | Opacity | float | 0-100% | 100% |
| **Ellipse** | Center | point | (x,y) | center |
| | Width / Height | float | 0-4000 | 200 |
| | Softness | float | 0-100 | 0 |
| | Color | color | RGBA | white |
| **Fill** | Fill Mask | enum | All Masks / mask name | All Masks |
| | Color | color | RGBA | red |
| | Invert | boolean | on/off | off |
| | Horizontal/Vertical Feather | float | 0-500 | 0 |
| | Opacity | float | 0-100% | 100% |
| **Fractal** | Fractal Type | enum | Mandelbrot / Julia | Mandelbrot |
| | (complex iteration parameters) | — | — | — |
| **Gradient Ramp** | Start of Ramp | point | (x,y) | top center |
| | Start Color | color | RGBA | black |
| | End of Ramp | point | (x,y) | bottom center |
| | End Color | color | RGBA | white |
| | Ramp Shape | enum | Linear Ramp / Radial Ramp | Linear Ramp |
| | Ramp Scatter | float | 0-100 | 0 |
| | Blend With Original | float | 0-100% | 0% |
| **Grid** | Anchor | point | (x,y) | (0,0) |
| | Size From | enum | Corner Point / Width Slider / W&H Sliders | Corner Point |
| | Width / Height | float | 0-4000 | 100 |
| | Border | float | 0-500 | 3 |
| | Feather | float | 0-100 | 0 |
| | Color | color | RGBA | white |
| | Opacity | float | 0-100% | 100% |
| **Lens Flare** | Flare Center | point | (x,y) | center |
| | Flare Brightness | float | 0-300% | 100% |
| | Lens Type | enum | 50-300mm Zoom / 35mm Prime / 105mm Prime | 50-300mm Zoom |
| | Blend With Original | float | 0-100% | 0% |
| **Paint Bucket** | Fill Point | point | (x,y) | center |
| | Tolerance | float | 0-255 | 32 |
| | Color | color | RGBA | red |
| | Opacity | float | 0-100% | 100% |
| **Radio Waves** | Wave Type | enum | Polygon / Image Contour / Mask | Polygon |
| | Center | point | (x,y) | center |
| | Frequency | float | 0-60 | 5 |
| | Expansion | float | 0-100 | 10 |
| | Color | color | RGBA | blue |
| | Lifespan (sec) | float | 0-10 | 3 |
| | Start/End Width | float | 0-100 | 5/0.5 |
| **Stroke** | Path | enum | All Masks / mask name | All Masks |
| | Color | color | RGBA | red |
| | Brush Size | float | 0-200 | 6 |
| | Brush Hardness | float | 0-100% | 100% |
| | Opacity | float | 0-100% | 100% |
| | Start / End | float | 0-100% | 0%/100% |
| | Paint Style | enum | On Original / On Transparent / Reveal Original | On Original |
| **Vegas** | Segments | int | 0-32 | 12 |
| | Length | float | 0-100 | 25 |
| | Width | float | 0-100 | 5 |
| | Color | color | RGBA | yellow |

---

## 9. Immersive Video

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **VR Blur** | Blur Radius | float | 0-100 | 0 |
| | Blur Type | enum | Gaussian / Box | Gaussian |
| **VR Chromatic Aberrations** | Aberration Type | enum | Lateral / Axial | Lateral |
| | Aberration Amount (R/G/B) | float | -100 to 100 | 0 |
| **VR Color Gradients** | (gradient with spherical mapping) | — | — | — |
| **VR De-Noise** | Noise Reduction | float | 0-100 | 50 |
| | Sharpness | float | 0-100 | 25 |
| **VR Digital Glitch** | Master Distortion | float | 0-100 | 50 |
| | Color Distortion | float | 0-100 | 50 |
| | Block Distortion | float | 0-100 | 50 |
| **VR Fractal Noise** | (同标准 Fractal Noise，球形映射) | — | — | — |
| **VR Glow** | Glow Threshold | float | 0-100% | 60% |
| | Glow Radius | float | 0-500 | 25 |
| | Glow Intensity | float | 0-10 | 1 |
| **VR Plane to Sphere / VR Sphere to Plane** | Field of View | float | 0-180 | 90 |
| | Rotation X/Y/Z | angle | -180 to 180 | 0 |
| **VR Rotate Sphere** | Tilt / Pan / Roll | angle | -180 to 180 | 0 |
| **VR Sharpen** | Sharpen Amount | float | 0-500 | 0 |

---

## 10. Keying

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Color Difference Key** | Partial A/B Input | enum | R/G/B | varies |
| | Color A / Color B matching | float | 0-100 | varies |
| **Color Key** | Key Color | color | RGBA | (eyedropper) |
| | Color Tolerance | float | 0-100 | 20 |
| | Edge Thin | float | -10 to 10 | 0 |
| | Edge Feather | float | 0-10 | 2 |
| **Color Range** | Color Space | enum | Lab / YUV / RGB | Lab |
| | (min/max for L/a/b or Y/U/V channels) | float | varies | varies |
| | Fuzziness | float | 0-100 | 10 |
| **Difference Matte** | Difference Layer | layer | any | None |
| | If Layer Sizes Differ | enum | Center / Stretch to Fit | Center |
| | Matching Tolerance | float | 0-100% | 10% |
| | Matching Softness | float | 0-100% | 0% |
| | Blur Before Difference | float | 0-100 | 0 |
| **Extract** | Channel | enum | Luminance / Red / Green / Blue / Alpha | Luminance |
| | Black Point | float | 0-255 | 0 |
| | White Point | float | 0-255 | 255 |
| | Black Softness | float | 0-255 | 0 |
| | White Softness | float | 0-255 | 0 |
| | Invert | boolean | on/off | off |
| **Inner/Outer Key** | (advanced edge matte refinement) | — | — | — |
| **Keylight (1.2)** | Screen Colour | color | RGBA | (eyedropper) |
| | Screen Gain | float | 0-200 | 100 |
| | Screen Balance | float | 0-100 | 50 |
| | Despill Bias | color | RGBA | (auto) |
| | Alpha Bias | color | RGBA | (auto) |
| | Clip Black | float | 0-100 | 0 |
| | Clip White | float | 0-100 | 100 |
| | Clip Rollback | float | 0-100 | 0 |
| | Screen Shrink/Grow | float | -100 to 100 | 0 |
| | Screen Softness | float | 0-100 | 0 |
| | Screen Despot Black/White | float | 0-100 | 0 |
| | Edge Colour Correction | (sub-panel) | — | — |
| **Linear Color Key** | Key Color | color | RGBA | (eyedropper) |
| | Matching Tolerance | float | 0-100% | 10% |
| | Matching Softness | float | 0-100% | 10% |
| | Key Operation | enum | Keep Color / Key Color | Key Color |
| **Luma Key** | Key Type | enum | Key Out Brighter / Key Out Darker / Key Out Similar / Key Out Dissimilar | Key Out Brighter |
| | Threshold | float | 0-255 | 128 |
| | Tolerance | float | 0-128 | 32 |
| | Edge Thin | float | -10 to 10 | 0 |
| | Edge Feather | float | 0-10 | 2 |
| **Spill Suppressor** | Color to Suppress | enum | Green / Blue | Green |
| | Color Accuracy | enum | Faster / Better | Better |
| | Suppression Amount | float | 0-200% | 100% |

---

## 11. Matte

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Matte Choker** | Geometric Softness 1/2 | float | -20 to 20 | 0 |
| | Choke 1/2 | float | -100 to 100 | 0 |
| | Gray Level Softness 1/2 | float | 0-100 | 0 |
| | Iterations | int | 1-3 | 1 |
| **Mocha AE** | (planar tracking — interactive UI) | — | — | — |
| **Refine Hard Matte** | (auto edge refinement for hard mattes) | — | — | — |
| **Refine Soft Matte** | (auto edge refinement for soft mattes) | — | — | — |
| **Simple Choker** | Choke Matte | float | -100 to 100 | 0 |

---

## 12. Noise & Grain

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Add Grain** | Viewing Mode | enum | Final Output / Preview / Grain Only | Final Output |
| | Intensity | float | 0-500% | 100% |
| | Size | float | 0.1-10 | 1.0 |
| | Softness | float | 0-100% | 0% |
| | Saturation | float | 0-100% | 100% |
| | Aspect Ratio | float | 0.1-10 | 1.0 |
| | Animation Speed | float | 0-1000% | 100% |
| | Color: Monochromatic | boolean | on/off | off |
| | Color: Red/Green/Blue Intensity | float | 0-200% | 100% |
| **Dust & Scratches** | Radius | int | 1-100 | 1 |
| | Threshold | int | 0-255 | 0 |
| **Fractal Noise** | Fractal Type | enum | Basic/Turbulent Smooth/Turbulent Sharp/Rocky/Multi/etc. | Basic |
| | Noise Type | enum | Block / Linear / Soft Linear / Spline | Soft Linear |
| | Invert | boolean | on/off | off |
| | Contrast | float | 0-400 | 100 |
| | Brightness | float | -200 to 200 | 0 |
| | Overflow | enum | Clip / Soft Clamp / Wrap Back | Clip |
| | Transform: Rotation | angle | unlimited | 0 |
| | Transform: Uniform Scaling | boolean | on/off | on |
| | Transform: Scale | float | 1-10000 | 100 |
| | Transform: Scale Width/Height | float | 1-10000 | 100 |
| | Transform: Offset | point | (x,y) | center |
| | Transform: Perspective Offset | point | (x,y) | (0,0) |
| | Complexity | float | 1-20 | 6 |
| | Sub Settings: Sub Influence (%) | float | 0-100 | 70 |
| | Sub Settings: Sub Scaling | float | 1-1000 | 56 |
| | Sub Settings: Sub Rotation | angle | -360 to 360 | 0 |
| | Sub Settings: Sub Offset | point | (x,y) | (0,0) |
| | Sub Settings: Center Subscale | boolean | on/off | off |
| | Evolution | angle | revolutions | 0 |
| | Evolution Options: Cycle Evolution | boolean | on/off | off |
| | Evolution Options: Cycle (Revolutions) | int | 1+ | 1 |
| | Evolution Options: Random Seed | int | 0-30000 | 0 |
| | Opacity | float | 0-100% | 100% |
| | Blending Mode | enum | standard modes | Normal |
| **Match Grain** | (matches grain profile from source layer) | — | — | — |
| **Median** | Radius | int | 1-100 | 1 |
| | Operate On | enum | All Channels / Alpha Only | All Channels |
| **Noise** | Amount of Noise | float | 0-100% | 50% |
| | Noise Type | enum | Use Color Noise / Use Alpha Noise | Use Color Noise |
| | Clipping | boolean | on/off | off |
| **Noise Alpha** | Amount | float | 0-100% | 50% |
| | Noise Type | enum | Uniform Random / Squared Uniform / etc. | Uniform Random |
| | Original Alpha | enum | Clamp / Add / Scale | Add |
| | Overflow | enum | Clip / Wrap | Clip |
| | Random Seed | int | 0-30000 | 0 |
| **Noise HLS** | Noise | float | 0-100% | 25% |
| | Hue Noise | float | 0-100% | 50% |
| | Lightness Noise | float | 0-100% | 50% |
| | Saturation Noise | float | 0-100% | 50% |
| | Grain Size | float | 1-10 | 1 |
| **Noise HLS Auto** | (同 Noise HLS + 自动动画) | — | — | — |
| **Remove Grain** | (AI-based noise reduction) | — | — | — |
| **Turbulent Noise** | (同 Fractal Noise + Turbulence 选项) | — | — | — |

---

## 13. Perspective

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **3D Camera Tracker** | Shot Type | enum | Fixed Angle of View / Variable Zoom / Specify Angle | Fixed |
| | (analysis-based, generates 3D track points) | — | — | — |
| **3D Glasses** | Left View / Right View | layer | any | None |
| | Convergence Offset | float | -500 to 500 | 0 |
| | 3D View | enum | Stereo Pair / Anaglyph / etc. | Stereo Pair |
| | Swap Left-Right | boolean | on/off | off |
| **Bevel Alpha** | Edge Thickness | float | 0-100 | 5 |
| | Light Angle | angle | 0-360 | 135 |
| | Light Color | color | RGBA | white |
| | Light Intensity | float | 0-100% | 50% |
| **Bevel Edges** | (同 Bevel Alpha 但适用于非透明边缘) | — | — | — |
| **CC Cylinder** | Rotation | angle | unlimited | 0 |
| | Position | point | (x,y) | center |
| | Radius | float | 0-500 | 100 |
| | Perspective | float | 0-200 | 100 |
| | Ambient | float | 0-100% | 50% |
| | Diffuse | float | 0-100% | 50% |
| | Specular | float | 0-100% | 50% |
| | Roughness | float | 0-100% | 50% |
| | Light Position | point | (x,y) | varies |
| | Light Color | color | RGBA | white |
| | Shading | boolean | on/off | on |
| **CC Environment** | (environmental reflection mapping) | — | — | — |
| **CC Sphere** | Rotation X/Y/Z | angle | unlimited | 0 |
| | Radius | float | 0-2000 | 200 |
| | Offset | point | (x,y) | center |
| | Light: Intensity/Color/Height/Direction | varies | varies | varies |
| | Shading: Ambient/Diffuse/Specular/Roughness/Metal | float | 0-100% | varies |
| **CC Spotlight** | Light Center | point | (x,y) | center |
| | Light Properties | (multiple) | varies | varies |
| **Drop Shadow** | Shadow Color | color | RGBA | black |
| | Opacity | float | 0-100% | 50% |
| | Direction | angle | 0-360 | 135 |
| | Distance | float | 0-1000 | 5 |
| | Softness | float | 0-250 | 5 |
| | Shadow Only | boolean | on/off | off |
| **Radial Shadow** | Shadow Color | color | RGBA | black |
| | Opacity | float | 0-100% | 100% |
| | Light Source | point | (x,y) | center |
| | Projection Distance | float | 0-500 | 100 |
| | Softness | float | 0-100 | 0 |
| | Render | enum | Regular / Only / Glass Edge | Regular |
| | Resize Layer | boolean | on/off | off |

---

## 14. Simulation

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Card Dance** | (3D card grid animated by gradient maps) | — | — | — |
| | Gradient Layer 1/2 | layer | any | None |
| | Rows / Columns | int | 1-256 | 20 |
| | X/Y/Z Rotation Source | enum | Gradient | varies |
| | X/Y/Z Position Source | enum | Gradient | varies |
| **Caustics** | Bottom / Water Surface | layer | any | None |
| | Water Depth | float | 0-1 | 0.5 |
| | Surface Opacity / Caustic Strength | float | 0-100% | varies |
| | Light: Intensity/Direction/Height | varies | varies | varies |
| | Smoothing | float | 0-100 | 10 |
| **CC Ball Action** | Scatter | float | 0-100 | 0 |
| | Ball Size | float | 0-500 | 20 |
| | Grid Spacing | float | 0-500 | 20 |
| | Rotation | angle | unlimited | 0 |
| **CC Bubbles** | Amount | float | 0-100 | 20 |
| | Size | float | 0-100 | 10 |
| | Speed | float | 0-100 | 50 |
| | Wobble | float | 0-100 | 50 |
| **CC Drizzle** | Drip Rate | float | 0-100 | 50 |
| | Ripple Size | float | 0-100 | 50 |
| | Lifespan | float | 0-100 | 50 |
| | Shading: Diffuse/Specular | float | varies | varies |
| **CC Hair** | Length | float | 0-1000 | 100 |
| | Density | float | 0-100 | 50 |
| | Thickness | float | 0-100 | 5 |
| | Color / Taper | varies | varies | varies |
| | Wind / Gravity | float | 0-100 | varies |
| **CC Mr. Mercury** | Birth Rate | float | 0-100 | 30 |
| | Longevity (sec) | float | 0-10 | 2 |
| | Producer | point | (x,y) | center |
| | Direction / Velocity | angle/float | varies | varies |
| | Gravity | float | -100 to 100 | 50 |
| | Resistance | float | 0-100 | 0 |
| | Blob Birth/Death Size | float | 0-200 | varies |
| | Influence Map | layer | any | None |
| **CC Particle Systems II** | Birth Rate | float | 0-100 | 2 |
| | Longevity (sec) | float | 0-10 | 1 |
| | Producer Position | point | (x,y) | center |
| | Producer Radius X/Y | float | 0-500 | varies |
| | Direction / Velocity / Velocity Random | varies | varies | varies |
| | Gravity | float | -100 to 100 | 0 |
| | Resistance | float | 0-100 | 0 |
| | Extra / Extra Angle | float/angle | varies | varies |
| | Particle: Type | enum | Line/Triangle/Ball/Lens/etc. | Line |
| | Particle: Birth/Death Size | float | 0-500 | varies |
| | Particle: Birth/Death Color | color | RGBA | varies |
| | Particle: Max Opacity | float | 0-100% | 100% |
| **CC Particle World** | (同 Particle Systems II + 3D空间) | — | — | — |
| | Physics: Animation | enum | Explosive/Jet/Fire/etc. | Explosive |
| | Physics: Velocity/Gravity/Resistance | float | varies | varies |
| | Particle: Type | enum | Line/Star/Lens/Bubble/Faded Sphere/etc. | Star |
| | Grid & Guides | boolean | on/off | off |
| **CC Pixel Polly** | Shatter: Force | float | 0-100 | 0 |
| | Shatter: Gravity | float | -100 to 100 | 0 |
| | Grid Spacing | float | 1-100 | 20 |
| **CC Rainfall** | Drops | float | 0-10000 | 1000 |
| | Size | float | 0-100 | 3 |
| | Speed | float | 0-200 | 200 |
| | Wind | float | -100 to 100 | 0 |
| | Spread | float | 0-100 | 100 |
| | Color | color | RGBA | white |
| | Opacity | float | 0-100% | 50% |
| **CC Snowfall** | (同 CC Rainfall + Flake Size/Wobble) | — | — | — |
| **CC Star Burst** | Scatter | float | 0-100 | 0 |
| | Speed | float | 0-1000 | 100 |
| | Size | float | 0-100 | 5 |
| **Foam** | (advanced bubble/foam simulation) | — | — | — |
| | Bubbles: Size/Size Variance | float | varies | varies |
| | Producer Point / Flow | varies | varies | varies |
| | Stickiness / Viscosity / Pop Velocity | float | varies | varies |
| **Particle Playground** | (legacy complex particle system) | — | — | — |
| | Cannon/Grid/Layer Exploder/Particle Exploder | (complex sub-panels) | — | — |
| **Shatter** | View | enum | Rendered / Wireframe+Rendered / Wireframe / etc. | Rendered |
| | Shape: Pattern | enum | Glass / Brick / Custom / etc. | Glass |
| | Shape: Repetitions / Extrusion Depth | float | varies | varies |
| | Force 1/2: Position / Depth / Radius / Strength | varies | varies | varies |
| | Gravity | float | 0-100 | 0 |
| | Physics: Rotation Speed / Viscosity / Mass Variance | float | varies | varies |
| | Lighting: Type/Direction/Intensity/Color | varies | varies | varies |
| **Wave World** | View | enum | Height Map / Wireframe / etc. | Height Map |
| | Wireframe Controls | (sub-panel) | — | — |
| | Height Map Controls: Brightness/Contrast/Gamma | float | varies | varies |
| | Simulation: Grid Resolution / Damping / Wave Speed | varies | varies | varies |
| | Producer: Position/Height/Width/Angle/Frequency/Phase | varies | varies | varies |
| | Ground | (sub-panel) | — | — |

---

## 15. Stylize

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Brush Strokes** | Stroke Angle | angle | 0-360 | 135 |
| | Brush Size | float | 0-10 | 1 |
| | Stroke Length | float | 0-100 | 10 |
| | Stroke Density | float | 0-10 | 3 |
| | Stroke Randomness | float | 0-100 | 50 |
| | Paint Surface | enum | Paint On Original / Paint On Transparent / Paint On White / etc. | Paint On Original |
| | Blend With Original | float | 0-100% | 0% |
| **Cartoon** | Render | enum | Fill Only / Edges Only / Fill+Edges | Fill+Edges |
| | Detail Radius | float | 1-50 | 7 |
| | Detail Threshold | float | 0-200 | 30 |
| | Fill: Shading Steps/Smoothness | float | varies | varies |
| | Edge: Threshold/Width/Softness/Opacity | float | varies | varies |
| **CC Block Load** | Completion | float | 0-100% | 50% |
| | Start Point | enum | Random / Top-Left / etc. | Random |
| | Block Size | float | 1-100 | 20 |
| **CC Burn Film** | Burn | float | 0-100 | 50 |
| | Color | color | RGBA | varies |
| **CC Glass** | Surface | layer | any | None |
| | Softness | float | 0-100 | 0 |
| | Height | float | 0-100 | 20 |
| | Displacement | float | -500 to 500 | 100 |
| | Light Direction | angle | 0-360 | 135 |
| | Light Intensity | float | 0-100 | 50 |
| **CC HexTile** | Radius | float | 0-500 | 30 |
| | (hex grid stylization) | — | — | — |
| **CC Kaleida** | Size | float | 0-500 | 100 |
| | Rotation | angle | 0-360 | 0 |
| | Center | point | (x,y) | center |
| **CC Mr. Smoothie** | (selective smoothing) | — | — | — |
| **CC Plastic** | Softness | float | 0-100 | 0 |
| | Height | float | 0-100 | 30 |
| | Light Direction | angle | 0-360 | 135 |
| | Light Intensity | float | 0-100 | 50 |
| | Metal | float | 0-100 | 25 |
| **CC RepeTile** | Expand Left/Right/Top/Bottom | float | 0-2000 | 0 |
| | Tiling | enum | Unfold / Tile / etc. | Unfold |
| **CC Threshold** | Threshold | float | 0-255 | 128 |
| **CC Threshold RGB** | Red/Green/Blue Threshold | float | 0-255 | 128/128/128 |
| **CC Vignette** | Amount | float | 0-100 | 0 |
| **Color Emboss** | Direction | angle | 0-360 | 135 |
| | Relief | float | 1-500 | 2 |
| | Contrast | float | 0-100 | 100 |
| | Blend With Original | float | 0-100% | 100% |
| **Emboss** | Direction | angle | 0-360 | 135 |
| | Relief | float | 1-500 | 2 |
| | Contrast | float | 0-100 | 100 |
| | Blend With Original | float | 0-100% | 0% |
| **Find Edges** | Invert | boolean | on/off | off |
| | Blend With Original | float | 0-100% | 0% |
| **Glow** | Glow Threshold | float | 0-100% | 60% |
| | Glow Radius | float | 0-500 | 25 |
| | Glow Intensity | float | 0-10 | 1 |
| | Composite Original | enum | Behind / On Top / None | Behind |
| | Glow Operation | enum | None / Blur / etc. | None |
| | Glow Colors | enum | Original Colors / A&B Colors | Original Colors |
| | Color Looping | enum | Sawtooth / Triangle | Sawtooth |
| | Color Loops | int | 1-100 | 1 |
| | Color Phase | angle | 0-360 | 0 |
| | A&B Midpoint | float | 0-100% | 50% |
| | Color A / Color B | color | RGBA | varies |
| **Mosaic** | Horizontal Blocks | int | 1-1000 | 10 |
| | Vertical Blocks | int | 1-1000 | 10 |
| | Sharp Colors | boolean | on/off | on |
| **Motion Tile** | Tile Center | point | (x,y) | center |
| | Tile Width / Height | float | 1-2000% | 100% |
| | Output Width / Height | float | 1-2000% | 100% |
| | Mirror Edges | boolean | on/off | off |
| | Phase | float | 0-360 | 0 |
| | Horizontal Phase Shift | boolean | on/off | off |
| **Posterize** | Level | int | 2-255 | 8 |
| **Roughen Edges** | Edge Type | enum | Roughen/Roughen Color/Cut/Spiky/Rusty/Photocopy | Roughen |
| | Border | float | 0-200 | 8 |
| | Edge Sharpness | float | 0-10 | 1 |
| | Fractal Influence | float | 0-1 | 1 |
| | Scale | float | 10-1000 | 100 |
| | Stretch Width / Height | float | 0.1-10 | 1 |
| | Offset | point | (x,y) | (0,0) |
| | Complexity | float | 1-10 | 1 |
| | Evolution | angle | revolutions | 0 |
| | Random Seed | int | 0-30000 | 0 |
| **Scatter** | Amount | float | 0-5000 | 5 |
| | Grain | enum | Horizontal / Vertical / Both | Both |
| | Randomize Every Frame | boolean | on/off | off |
| **Strobe Light** | Strobe Color | color | RGBA | white |
| | Blend With Original | float | 0-100% | 0% |
| | Strobe Duration (sec) | float | 0-10 | 0.5 |
| | Strobe Period (sec) | float | 0-10 | 1 |
| | Random Strobe Probability | float | 0-100% | 0% |
| | Strobe | enum | Operates on Color Only / Makes Layer Transparent | Color Only |
| | Strobe Operator | enum | Copy / Add / Subtract / Multiply / etc. | Copy |
| **Texturize** | Texture Layer | layer | any | None |
| | Light Direction | angle | 0-360 | 135 |
| | Texture Contrast | float | 0-10 | 1 |
| | Texture Placement | enum | Tile Texture / Center Texture | Tile Texture |
| **Threshold** | Level | int | 1-255 | 128 |

---

## 16. Text

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Numbers** | Type | enum | Number / Timecode / Date / etc. | Number |
| | Random Values (for Number) | boolean | on/off | off |
| | Value/Offset | float | varies | 0 |
| | Decimal Places | int | 0-10 | 0 |
| | Fill/Stroke Color | color | RGBA | varies |
| | Size | float | 1-1000 | 60 |
| | Tracking | float | -100 to 500 | 0 |
| | Composite On Original | boolean | on/off | off |
| **Timecode** | Display Format | enum | SMPTE / Frames / Feet+Frames | SMPTE |
| | Time Units | enum | Comp Time / Footage Time | Comp Time |
| | Starting Frame | int | 0+ | 0 |

---

## 17. Time

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **CC Force Motion Blur** | Motion Blur Samples | int | 1-64 | 16 |
| | Override Shutter Angle | float | 0-720 | 180 |
| | Force Motion Blur | boolean | on/off | on |
| **CC Wide Time** | (trail/echo + width) | float | varies | varies |
| **Echo** | Echo Time (sec) | float | -10 to 10 | -0.033 |
| | Number of Echoes | int | 1-100 | 4 |
| | Starting Intensity | float | 0-1 | 1 |
| | Decay | float | 0-1 | 0.5 |
| | Echo Operator | enum | Add / Maximum / Minimum / Screen / Behind / In Front / Blend / Composite | Add |
| **Pixel Motion Blur** | Shutter Angle | float | 0-720 | 180 |
| | Shutter Samples | int | 1-64 | 5 |
| | Vector Detail | float | 1-100 | 25 |
| **Posterize Time** | Frame Rate | float | 0.1-99 | 24 |
| **Time Difference** | Target | layer | any | None |
| | Time Offset (sec) | float | -10 to 10 | 0 |
| | Contrast | float | 0-1000 | 100 |
| | Absolute Difference | boolean | on/off | on |
| | Alpha Channel | enum | Off / Max / Full On / Lightness of Result | Off |
| **Time Displacement** | Time Displacement Layer | layer | any | None |
| | Max Displacement Time (sec) | float | 0-10 | 1 |
| | Time Resolution (fps) | float | 1-60 | 30 |

---

## 18. Transition

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Block Dissolve** | Transition Completion | float | 0-100% | 50% |
| | Block Width / Height | float | 1-500 | 10 |
| | Feather | float | 0-100 | 0 |
| **Card Wipe** | Transition Completion | float | 0-100% | 50% |
| | Transition Width | float | 0-100% | 50% |
| | Back Layer | layer | any | None |
| | Rows / Columns | int | 1-256 | 10 |
| | Card Scale | float | 0-200% | 100% |
| | Flip Axis | enum | X / Y / Random | Random |
| | Flip Direction | enum | Positive / Negative / Random | Random |
| | Flip Order | enum | Left to Right / Right to Left / Random | Left to Right |
| | Gradient Layer | layer | any | None |
| | Timing Randomness | float | 0-100% | 0% |
| | Camera: Position/Zoom | varies | varies | varies |
| | Lighting | (sub-panel) | — | — |
| **CC Glass Wipe** | Completion | float | 0-100% | 50% |
| | Gradient | layer | any | None |
| | Softness | float | 0-100 | 0 |
| | Displacement | float | -500 to 500 | 0 |
| **CC Grid Wipe** | Completion | float | 0-100% | 50% |
| | Grid Size | float | 1-100 | 10 |
| **CC Image Wipe** | Completion | float | 0-100% | 50% |
| | Gradient | layer | any | None |
| | Softness | float | 0-100 | 0 |
| **CC Jaws** | Completion | float | 0-100% | 50% |
| | Shape | enum | Center/Edge/etc. | Center |
| | Height | float | 0-500 | 100 |
| **CC Light Wipe** | Completion | float | 0-100% | 50% |
| | Direction | angle | 0-360 | 0 |
| | Light Intensity / Feather | float | varies | varies |
| **CC Line Sweep** | Completion | float | 0-100% | 50% |
| | Direction | angle | 0-360 | 0 |
| **CC Radial ScaleWipe** | Completion | float | 0-100% | 50% |
| | Center | point | (x,y) | center |
| **CC Scale Wipe** | Completion | float | 0-100% | 50% |
| | Direction | enum | Left to Right / Right to Left / etc. | Left to Right |
| | Stretch | boolean | on/off | on |
| **CC Twister** | Completion | float | 0-100% | 50% |
| | Center | point | (x,y) | center |
| | Axis | enum | Horizontal / Vertical | Horizontal |
| **CC WarpoMatic** | Completion | float | 0-100% | 50% |
| | Type | enum | Warp / Blend | Warp |
| | Softness | float | 0-100 | 0 |
| **Gradient Wipe** | Transition Completion | float | 0-100% | 50% |
| | Transition Softness | float | 0-100% | 0% |
| | Gradient Layer | layer | any | None |
| | Gradient Placement | enum | Tile / Center / Stretch to Fit | Stretch to Fit |
| | Invert Gradient | boolean | on/off | off |
| **Iris Wipe** | Transition Completion | float | 0-100% | 50% |
| | Iris Points | int | 6-32 | 6 |
| | Iris Roundness | float | 0-100% | 0% |
| | Use Rotation | boolean | on/off | off |
| | Rotation | angle | 0-360 | 0 |
| | Feather | float | 0-100 | 0 |
| **Linear Wipe** | Transition Completion | float | 0-100% | 50% |
| | Wipe Angle | angle | 0-360 | 0 |
| | Feather | float | 0-100 | 10 |
| **Radial Wipe** | Transition Completion | float | 0-100% | 50% |
| | Start Angle | angle | 0-360 | 0 |
| | Wipe Center | point | (x,y) | center |
| | Wipe | enum | Clockwise / Counterclockwise | Clockwise |
| | Feather | float | 0-100 | 10 |
| **Venetian Blinds** | Transition Completion | float | 0-100% | 50% |
| | Direction | angle | 0-360 | 0 |
| | Width | float | 1-500 | 20 |
| | Feather | float | 0-100 | 0 |

---

## 19. Utility

| Effect | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| **Apply Color LUT** | LUT File | file | .cube/.3dl/.look | None |
| | (auto color transformation based on LUT) | — | — | — |
| **CC Overbrights** | (highlight overexposed pixels) | — | — | — |
| **Cineon Converter** | Conversion Type | enum | Log to Linear / Linear to Log | Log to Linear |
| | 10 Bit Black/White Point | int | 0-1023 | 95/685 |
| | Internal Black/White Point | float | 0-10 | 0/1.0 |
| | Gamma | float | 0.1-10 | 1.0 |
| | Highlight Rolloff | float | 0-100% | 0% |
| **Color Profile Converter** | Input/Output Profile | enum | (ICC profiles) | varies |
| | Intent | enum | Perceptual / Relative / Saturation / Absolute | Relative |
| **Grow Bounds** | Pixels | int | 0-4000 | 0 |
| **HDR Compander** | Mode | enum | Compress / Expand | Compress |
| | Gain | float | 0-100 | 0 |
| | Gamma | float | 0.1-10 | 1.0 |
| **HDR Highlight Compression** | Amount | float | 0-100% | 100% |

---

## 附录：常用参数速查

### 最常调的 10 个效果（内容制作向）

| 效果 | 核心参数 | 典型用法 |
|------|----------|----------|
| **Gaussian Blur** | Blurriness | 背景虚化、柔焦 |
| **Levels** | Input Black/White, Gamma | 对比度、亮度精调 |
| **Hue/Saturation** | Hue, Saturation, Lightness | 调色 |
| **Lumetri Color** | Temperature-Saturation 全套 | 一站式调色 |
| **Glow** | Threshold, Radius, Intensity | 发光效果 |
| **Drop Shadow** | Distance, Softness, Opacity | 投影 |
| **CC Particle World** | Birth Rate, Velocity, Gravity, Type | 粒子特效 |
| **Fractal Noise** | Contrast, Brightness, Scale, Evolution | 噪点纹理/动态背景 |
| **Turbulent Displace** | Amount, Size, Evolution | 扭曲/液化动效 |
| **Transform** | Position, Scale, Rotation, Opacity | 二次变换 |

### 参数类型与 ExtendScript/表达式对应

| Schema Type | ExtendScript | 表达式访问 |
|-------------|-------------|-----------|
| float | Property (1D) | `effect("X")("Y").value` |
| int | Property (1D) | `effect("X")("Y").value` |
| angle | Property (1D) | 返回度数 |
| point | Property (2D) | `[x, y]` |
| point3D | Property (3D) | `[x, y, z]` |
| color | Property (4D) | `[r, g, b, a]` (0-1) |
| enum | Property (1D) | 整数索引（从1开始） |
| boolean | Property (1D) | `1` or `0` |
| layer | Property (1D) | 图层索引 |
| spline | 不可直接表达式控制 | — |
