import {
  AbsoluteFill,
  Sequence,
  Img,
  Video,
  Audio,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
  staticFile,
} from "remotion";

// === 通用组件 ===

const TextCard = ({ text, accent = false, subText = null, fontSize = 72 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", opacity }}>
      <div style={{ color: "white", fontSize, fontWeight: "bold", fontFamily: "Microsoft YaHei, sans-serif", textAlign: "center", padding: "0 120px", lineHeight: 1.4 }}>
        {text}
      </div>
      {accent && <div style={{ width: Math.min(text.length * fontSize * 0.9, 1200), height: 4, backgroundColor: "rgb(220,50,50)", marginTop: 15 }} />}
      {subText && <div style={{ color: "rgb(100,100,100)", fontSize: 36, marginTop: 40, fontFamily: "Microsoft YaHei, sans-serif" }}>{subText}</div>}
      <div style={{ position: "absolute", bottom: 60, left: 60, color: "rgb(60,60,60)", fontSize: 28, fontFamily: "Microsoft YaHei, sans-serif" }}>先试为敬</div>
    </AbsoluteFill>
  );
};

const ImageSlide = ({ src }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)", opacity }}>
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </AbsoluteFill>
  );
};

const ImageSlideZoom = ({ src, zoomFrom = 1, zoomTo = 1.1 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const scale = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)", opacity }}>
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }} />
    </AbsoluteFill>
  );
};

const Sub = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", bottom: 80, left: 0, right: 0, textAlign: "center", opacity }}>
      <span style={{ backgroundColor: "rgba(0,0,0,0.7)", color: "white", fontSize: 36, padding: "8px 24px", borderRadius: 4, fontFamily: "Microsoft YaHei, sans-serif" }}>{text}</span>
    </div>
  );
};

const BlackScreen = () => <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)" }} />;

const ThreeLines = ({ lines }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", gap: 20 }}>
      {lines.map((line, i) => {
        const opacity = interpolate(frame, [i * 25, i * 25 + 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return <div key={i} style={{ color: "white", fontSize: 60, fontFamily: "Microsoft YaHei, sans-serif", opacity }}>{line}</div>;
      })}
      <div style={{ position: "absolute", bottom: 60, left: 60, color: "rgb(60,60,60)", fontSize: 28, fontFamily: "Microsoft YaHei, sans-serif" }}>先试为敬</div>
    </AbsoluteFill>
  );
};

const RevealText = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)", display: "flex", justifyContent: "center", alignItems: "center" }}>
      <div style={{ color: "white", fontSize: 80, fontWeight: "bold", fontFamily: "Microsoft YaHei, sans-serif", transform: `scale(${scale})` }}>{text}</div>
      <div style={{ position: "absolute", bottom: "48%", width: interpolate(frame, [0, 20], [0, 500], { extrapolateRight: "clamp" }), height: 4, backgroundColor: "rgb(220,50,50)" }} />
    </AbsoluteFill>
  );
};

// 快闪截图组件（多张图快速切换）
const FlashImages = ({ images, interval = 15 }) => {
  const frame = useCurrentFrame();
  const idx = Math.floor(frame / interval) % images.length;
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)" }}>
      <Img src={images[idx]} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
    </AbsoluteFill>
  );
};

// 视频片段组件（静音，只取画面）
const VideoClip = ({ src, startFrom = 0 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity }}>
      <Video src={src} startFrom={startFrom} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </AbsoluteFill>
  );
};

// 灰度变暗效果
const GrayOut = ({ children }) => {
  const frame = useCurrentFrame();
  const grayscale = interpolate(frame, [0, 15], [0, 100], { extrapolateRight: "clamp" });
  const brightness = interpolate(frame, [0, 15], [100, 50], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ filter: `grayscale(${grayscale}%) brightness(${brightness}%)` }}>
      {children}
    </AbsoluteFill>
  );
};

// 所有素材通过 Remotion 的 public/ 目录 serve
const sf = (path) => staticFile(path);
const sec = (s) => Math.round(s * 30);

// 视频文件名（编码后的路径）
const CLIP = {
  shezhan: sf("clips/shezhan_BV1vhcBeFEQt.mp4"),
  laji: sf("clips/laji_BV1GpcQzpEUG.mp4"),
  shenghua: sf("clips/shenghua_BV1HK4y1t7M3.mp4"),
  jieda985: sf("clips/jieda985_BV1fE41187Dd.mp4"),
};

export const Video001 = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)" }}>

      {/* ============ BGM 音轨 ============ */}
      {/* BGM1: 克制钢琴 0:00 - 1:05 */}
      <Sequence from={0} durationInFrames={sec(65)}>
        <Audio src={sf("audio/bgm1-calm-narrative.mp3")} volume={0.3} />
      </Sequence>
      {/* BGM2: 暗调紧张 1:05 - 2:40 */}
      <Sequence from={sec(65)} durationInFrames={sec(95)}>
        <Audio src={sf("audio/bgm2-dark-tension.mp3")} volume={0.25} />
      </Sequence>
      {/* BGM3: 温暖上升 2:40 - 4:45 */}
      <Sequence from={sec(160)} durationInFrames={sec(125)}>
        <Audio src={sf("audio/bgm3-uplifting-build.mp3")} volume={0.3} />
      </Sequence>

      {/* ============ PART 1: 开头 0:00-1:05 ============ */}

      {/* 镜1: 张雪峰讲台演讲（舌战群儒片段） */}
      <Sequence from={0} durationInFrames={sec(3)}>
        <VideoClip src={CLIP.shezhan} startFrom={sec(10)} />
        <Sub text="最近，张雪峰老师走了。" />
      </Sequence>

      {/* 镜2: 张雪峰金句（舌战群儒另一段） */}
      <Sequence from={sec(3)} durationInFrames={sec(3)}>
        <VideoClip src={CLIP.shezhan} startFrom={sec(30)} />
        <Sub text="全网都在发悼念视频。" />
      </Sequence>

      {/* 镜3: 张雪峰"别报"（垃圾专业片段） */}
      <Sequence from={sec(6)} durationInFrames={sec(4)}>
        <VideoClip src={CLIP.laji} startFrom={sec(5)} />
        <Sub text="有人翻出他当年的金句，有人盘点他改变了多少人的命运" />
      </Sequence>

      {/* 镜4: 悼念新闻截图快闪 */}
      <Sequence from={sec(10)} durationInFrames={sec(3)}>
        <FlashImages images={[
          sf("screenshots/zhangxf-guancha.png"),
          sf("screenshots/zhangxf-21jingji.png"),
          sf("screenshots/zhangxf-farewell.png"),
        ]} interval={30} />
        <Sub text="有人说他是这个时代最被需要的人。" />
      </Sequence>

      {/* 镜5: 文字卡 */}
      <Sequence from={sec(13)} durationInFrames={sec(5)}>
        <TextCard text="但今天，我想聊一个更大的问题" fontSize={60} />
      </Sequence>

      {/* 镜6: 文字卡 */}
      <Sequence from={sec(18)} durationInFrames={sec(4)}>
        <TextCard text="他做了十年的事，到底是什么？" fontSize={60} />
      </Sequence>

      {/* 镜7: 争议评论（用新闻截图代替） */}
      <Sequence from={sec(22)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("screenshots/zhangxf-guancha.png")} />
        <Sub text="有人说他是骗子，他推荐过的专业现在也没什么前途。" />
      </Sequence>

      {/* 镜8: 粉丝感谢（用追悼会新闻） */}
      <Sequence from={sec(25)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("screenshots/zhangxf-farewell.png")} />
        <Sub text="有人说他是救星，改变了无数小镇做题家的命运。" />
      </Sequence>

      {/* 镜9: 打破信息差 */}
      <Sequence from={sec(28)} durationInFrames={sec(4)}>
        <TextCard text="打破信息差" accent />
      </Sequence>

      {/* 镜10: 小镇高中 */}
      <Sequence from={sec(32)} durationInFrames={sec(3)}>
        <ImageSlideZoom src={sf("stock/rural-school.jpg")} />
        <Sub text="一个小镇的高中生，家里没人上过大学" />
      </Sequence>

      {/* 镜11: 志愿表（用stock替代） */}
      <Sequence from={sec(35)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("stock/graduation.jpg")} />
        <Sub text='他不知道"生物工程"毕业以后能干什么' />
      </Sequence>

      {/* 镜12: 土木工地 */}
      <Sequence from={sec(37)} durationInFrames={sec(3)}>
        <ImageSlideZoom src={sf("stock/construction-abandoned.jpg")} />
        <Sub text='不知道"土木工程"这个行业已经在走下坡路' />
      </Sequence>

      {/* 镜13: 城市饭桌 */}
      <Sequence from={sec(40)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("stock/family-dinner.jpg")} />
        <Sub text="大城市的孩子从小饭桌上就听到了，但他没有" />
      </Sequence>

      {/* 镜14: 张雪峰讲课（7分钟985） */}
      <Sequence from={sec(43)} durationInFrames={sec(7)}>
        <VideoClip src={CLIP.jieda985} startFrom={sec(20)} />
        <Sub text="张雪峰做的事，就是把这些信息，用最直接的方式，塞到了他面前" />
      </Sequence>

      {/* 镜15: 他不是先知 */}
      <Sequence from={sec(50)} durationInFrames={sec(5)}>
        <TextCard text="他不是先知" fontSize={60} />
      </Sequence>

      {/* 镜16: 至少知道真实情况 */}
      <Sequence from={sec(55)} durationInFrames={sec(7)}>
        <TextCard text="让你在做选择之前" subText="至少知道真实情况是什么" fontSize={60} />
      </Sequence>

      {/* 过渡静默 */}
      <Sequence from={sec(62)} durationInFrames={sec(3)}>
        <BlackScreen />
      </Sequence>

      {/* ============ PART 2: 转折 1:05-2:40 ============ */}

      {/* 镜17: 2026 */}
      <Sequence from={sec(65)} durationInFrames={sec(2)}>
        <TextCard text="2026" fontSize={120} />
      </Sequence>

      {/* 镜18-19: AI新闻快闪（每0.5秒一张） */}
      <Sequence from={sec(67)} durationInFrames={sec(6)}>
        <FlashImages images={[
          sf("screenshots/ai-news-36kr-layoffs.png"),
          sf("screenshots/ai-news-21jingji-netease.png"),
          sf("screenshots/ai-news-meta-layoff.png"),
          sf("screenshots/ai-news-block-layoff.png"),
          sf("screenshots/ai-news-jobs-replaced.png"),
        ]} interval={15} />
        <Sub text="都说2026年是AI Agent元年。都说AI是万能的，什么都能做。" />
      </Sequence>

      {/* 镜20: 急刹变灰 */}
      <Sequence from={sec(73)} durationInFrames={sec(4)}>
        <GrayOut>
          <ImageSlide src={sf("screenshots/ai-news-meta-layoff.png")} />
        </GrayOut>
        <Sub text="可为什么......我感觉信息差比以前更严重了？" />
      </Sequence>

      {/* 镜21: 深夜刷手机 */}
      <Sequence from={sec(77)} durationInFrames={sec(2)}>
        <ImageSlideZoom src={sf("stock/phone-dark-room.jpg")} />
        <Sub text="你有没有这种感觉？" />
      </Sequence>

      {/* 镜22-25: 手机通知 + AI新闻分镜 */}
      <Sequence from={sec(79)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("stock/phone-dark-room-2.jpg")} />
        <Sub text="每天醒来，手机里全是新消息" />
      </Sequence>
      <Sequence from={sec(81)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-news-36kr-layoffs.png")} />
        <Sub text="某某AI又更新了" />
      </Sequence>
      <Sequence from={sec(83)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-news-meta-layoff.png")} />
        <Sub text="某某公司又裁员了" />
      </Sequence>
      <Sequence from={sec(85)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-news-jobs-replaced.png")} />
        <Sub text="某个岗位可能要没了" />
      </Sequence>

      {/* 镜26: 然后呢？ */}
      <Sequence from={sec(87)} durationInFrames={sec(2)}>
        <TextCard text="然后呢？" fontSize={80} />
      </Sequence>

      {/* 镜27-29: AI课程广告 */}
      <Sequence from={sec(89)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-course-liyizhou.png")} />
        <Sub text="你还不学AI？" />
      </Sequence>
      <Sequence from={sec(91)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-course-scam-sohu.png")} />
        <Sub text="再不上车就晚了？" />
      </Sequence>
      <Sequence from={sec(93)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-course-sina.png")} />
        <Sub text="你想被时代抛弃？" />
      </Sequence>

      {/* 镜30: 听着耳熟吗？ */}
      <Sequence from={sec(95)} durationInFrames={sec(3)}>
        <TextCard text="听着耳熟吗？" fontSize={72} />
      </Sequence>

      {/* 镜31-32: 新旧焦虑对比 */}
      <Sequence from={sec(98)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("screenshots/ai-anxiety-jiemian.png")} />
        <Sub text='"报错专业毁一生"——这是当年的版本。' />
      </Sequence>
      <Sequence from={sec(101)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("screenshots/ai-anxiety-epochtimes.png")} />
        <Sub text='"不学AI毁一生"——这是现在的版本。' />
      </Sequence>

      {/* 镜33: 先吓你再卖课 */}
      <Sequence from={sec(104)} durationInFrames={sec(4)}>
        <TextCard text="先吓你，再卖课" accent />
      </Sequence>

      {/* 镜34: 思考的人 */}
      <Sequence from={sec(108)} durationInFrames={sec(4)}>
        <ImageSlideZoom src={sf("stock/person-thinking.jpg")} />
        <Sub text="他们说的，到底是真的吗？" />
      </Sequence>

      {/* 镜35-36: AI场景 + 问号 */}
      <Sequence from={sec(112)} durationInFrames={sec(4)}>
        <ImageSlide src={sf("stock/ai-robot.jpg")} />
        <Sub text="AI真的要取代你了吗？还是说......有些人需要你相信这件事？" />
      </Sequence>

      {/* 镜37: 说实话我自己也一样 */}
      <Sequence from={sec(116)} durationInFrames={sec(3)}>
        <TextCard text="说实话，我自己也一样。" fontSize={60} />
      </Sequence>

      {/* 镜38: Claude 界面 */}
      <Sequence from={sec(119)} durationInFrames={sec(5)}>
        <ImageSlideZoom src={sf("screenshots/claude-ui.png")} zoomTo={1.15} />
        <Sub text="我刚开始用 Claude 的时候很兴奋" />
      </Sequence>

      {/* 镜39: VS Code 界面 */}
      <Sequence from={sec(124)} durationInFrames={sec(5)}>
        <ImageSlideZoom src={sf("screenshots/vscode-official.png")} zoomTo={1.15} />
        <Sub text="每天更新迭代的快感让我沉溺其中无法自拔" />
      </Sequence>

      {/* 镜40: 竞品产品（用AI新闻替代） */}
      <Sequence from={sec(129)} durationInFrames={sec(2)}>
        <ImageSlide src={sf("screenshots/ai-news-block-layoff.png")} />
        <Sub text="发现别的团队用更快更好的方式做了出来......" />
      </Sequence>

      {/* 镜41: 深夜沉思 */}
      <Sequence from={sec(131)} durationInFrames={sec(2)}>
        <ImageSlideZoom src={sf("stock/late-night-working.jpg")} zoomTo={1.08} />
        <Sub text="我陷入了沉思。" />
      </Sequence>

      {/* 镜42-43: 框架更迭（用文字卡） */}
      <Sequence from={sec(133)} durationInFrames={sec(3)}>
        <TextCard text="LangChain → CrewAI → ..." fontSize={48} subText="你今天学的框架，明天会不会就被推翻了？" />
      </Sequence>

      {/* 镜44: 越想越焦虑 */}
      <Sequence from={sec(136)} durationInFrames={sec(3)}>
        <TextCard text="越想搞清楚，反而越焦虑。" accent />
      </Sequence>

      {/* 镜45: 评论拼贴（用焦虑新闻） */}
      <Sequence from={sec(139)} durationInFrames={sec(5)}>
        <ImageSlide src={sf("screenshots/ai-anxiety-jiemian.png")} />
        <Sub text="没人给你答案。给你答案的人，不是想卖你东西，就是自己也还在找答案。" />
      </Sequence>

      {/* 镜46: 跑步被超越 */}
      <Sequence from={sec(144)} durationInFrames={sec(5)}>
        <ImageSlideZoom src={sf("stock/runner-behind.jpg")} zoomTo={1.1} />
        <Sub text="感觉自己怎么追，也追不上" />
      </Sequence>

      {/* 镜47: 但就是在那个时候 */}
      <Sequence from={sec(149)} durationInFrames={sec(4)}>
        <TextCard text="但就是在那个时候——" fontSize={60} />
      </Sequence>

      {/* 过渡 */}
      <Sequence from={sec(153)} durationInFrames={sec(7)}>
        <BlackScreen />
      </Sequence>

      {/* ============ PART 3: 核心观点 2:40-4:03 ============ */}

      {/* 镜48: 晨光桌面 */}
      <Sequence from={sec(160)} durationInFrames={sec(3)}>
        <ImageSlideZoom src={sf("stock/morning-light-desk.jpg")} zoomFrom={1.05} zoomTo={1} />
        <Sub text="后来我想了想：" />
      </Sequence>

      {/* 镜49: 焦虑本身就是正常的 */}
      <Sequence from={sec(163)} durationInFrames={sec(5)}>
        <TextCard text="也许焦虑本身，就是正常的。" accent />
      </Sequence>

      {/* 镜50: 信息流（正常速度） */}
      <Sequence from={sec(168)} durationInFrames={sec(5)}>
        <FlashImages images={[
          sf("screenshots/ai-news-36kr-layoffs.png"),
          sf("screenshots/ai-news-21jingji-netease.png"),
          sf("screenshots/ai-news-meta-layoff.png"),
        ]} interval={45} />
        <Sub text="每天这么多新东西冒出来，真的假的混在一起，谁看了不头大？" />
      </Sequence>

      {/* 镜51: 毕业照 + 办公室 */}
      <Sequence from={sec(173)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("stock/graduation.jpg")} />
        <Sub text="不管你是刚毕业的大学生" />
      </Sequence>
      <Sequence from={sec(176)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("stock/office-worker.jpg")} />
        <Sub text="还是干了十年的老手" />
      </Sequence>

      {/* 镜53: 怎么办 */}
      <Sequence from={sec(179)} durationInFrames={sec(3)}>
        <TextCard text="那......怎么办呢？" fontSize={60} />
      </Sequence>

      {/* 镜54: 降解 */}
      <Sequence from={sec(182)} durationInFrames={sec(4)}>
        <TextCard text="降解" accent fontSize={100} />
      </Sequence>

      {/* 镜55-57: 不是...不是...不是... + ❌ */}
      <Sequence from={sec(186)} durationInFrames={sec(3)}>
        <AbsoluteFill>
          <ImageSlide src={sf("stock/phone-dark-room.jpg")} />
          <div style={{ position: "absolute", top: "40%", left: "50%", transform: "translate(-50%,-50%)", fontSize: 200, color: "rgba(220,50,50,0.8)" }}>✕</div>
        </AbsoluteFill>
        <Sub text="不是去刷更多的文章" />
      </Sequence>
      <Sequence from={sec(189)} durationInFrames={sec(3)}>
        <AbsoluteFill>
          <ImageSlide src={sf("screenshots/ai-course-liyizhou.png")} />
          <div style={{ position: "absolute", top: "40%", left: "50%", transform: "translate(-50%,-50%)", fontSize: 200, color: "rgba(220,50,50,0.8)" }}>✕</div>
        </AbsoluteFill>
        <Sub text="不是去买更多的课" />
      </Sequence>
      <Sequence from={sec(192)} durationInFrames={sec(3)}>
        <AbsoluteFill>
          <ImageSlide src={sf("screenshots/ai-course-scam-sohu.png")} />
          <div style={{ position: "absolute", top: "40%", left: "50%", transform: "translate(-50%,-50%)", fontSize: 200, color: "rgba(220,50,50,0.8)" }}>✕</div>
        </AbsoluteFill>
        <Sub text='也不是去听更多人告诉你"你应该怎么做"' />
      </Sequence>

      {/* 镜58: 自己动手试 */}
      <Sequence from={sec(195)} durationInFrames={sec(3)}>
        <TextCard text="而是自己动手试一下。" accent fontSize={64} />
      </Sequence>

      {/* 镜59: 打开电脑 */}
      <Sequence from={sec(198)} durationInFrames={sec(4)}>
        <ImageSlideZoom src={sf("stock/opening-laptop.jpg")} zoomTo={1.1} />
        <Sub text="不如花二十分钟自己打开用一下" />
      </Sequence>

      {/* 镜61: 释然 */}
      <Sequence from={sec(202)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("stock/relieved-person.jpg")} />
        <Sub text="用完你就知道了：跟我有没有关系" />
      </Sequence>

      {/* 镜62: 三行浮现 */}
      <Sequence from={sec(205)} durationInFrames={sec(5)}>
        <ThreeLines lines={["不用学完。", "不用精通。", "不用成为专家。"]} />
      </Sequence>

      {/* 镜63: 核心句 */}
      <Sequence from={sec(210)} durationInFrames={sec(5)}>
        <TextCard text="这件事，跟我有什么关系。" accent fontSize={72} />
      </Sequence>

      {/* 镜64: 轻松释然 */}
      <Sequence from={sec(215)} durationInFrames={sec(3)}>
        <ImageSlide src={sf("stock/relieved-person.jpg")} />
        <Sub text="搞清楚了，该学学，该忽略忽略" />
      </Sequence>

      {/* 镜65: 试过的人 */}
      <Sequence from={sec(218)} durationInFrames={sec(5)}>
        <TextCard text="试过的人，比光看的人" subText="少焦虑一半。" accent />
      </Sequence>

      {/* ============ PART 4: 揭晓 4:03-4:28 ============ */}

      {/* 镜66-67: 张雪峰讲课（最后出现）→ 渐远 */}
      <Sequence from={sec(227)} durationInFrames={sec(4)}>
        <VideoClip src={CLIP.jieda985} startFrom={sec(60)} />
        <Sub text="张雪峰用十年，帮几百万人打破了高考的信息差。" />
      </Sequence>
      <Sequence from={sec(231)} durationInFrames={sec(4)}>
        <GrayOut>
          <VideoClip src={CLIP.jieda985} startFrom={sec(64)} />
        </GrayOut>
        <Sub text="但他一个人，不可能帮所有人，打破所有的信息差。" />
      </Sequence>

      {/* 镜68: AI时代的信息差 */}
      <Sequence from={sec(235)} durationInFrames={sec(4)}>
        <TextCard text="AI时代的信息差" fontSize={64} />
      </Sequence>

      {/* 镜69: 接力棒传给了谁 */}
      <Sequence from={sec(239)} durationInFrames={sec(4)}>
        <TextCard text="这根接力棒，传给了谁？" fontSize={64} />
      </Sequence>

      {/* 镜70: 全黑屏 3秒 */}
      <Sequence from={sec(243)} durationInFrames={sec(3)}>
        <BlackScreen />
      </Sequence>

      {/* 镜71: 揭晓 */}
      <Sequence from={sec(246)} durationInFrames={sec(4)}>
        <RevealText text="没错，就是屏幕前的你。" />
      </Sequence>

      {/* 镜72: 日出 */}
      <Sequence from={sec(250)} durationInFrames={sec(3)}>
        <ImageSlideZoom src={sf("stock/sunrise-landscape.jpg")} zoomFrom={1.1} zoomTo={1} />
        <Sub text="你不需要等谁来告诉你该怎么办" />
      </Sequence>

      {/* 镜73: 键盘打字 */}
      <Sequence from={sec(253)} durationInFrames={sec(5)}>
        <ImageSlideZoom src={sf("stock/typing-keyboard.jpg")} zoomTo={1.08} />
        <Sub text="从今天开始，我会自己去试。试完了，分享给你们。" />
      </Sequence>

      {/* 镜74-76: 宣言三连 */}
      <Sequence from={sec(258)} durationInFrames={sec(3)}>
        <TextCard text="不教你该学什么。" fontSize={60} />
      </Sequence>
      <Sequence from={sec(261)} durationInFrames={sec(3)}>
        <TextCard text="不告诉你该焦虑什么。" fontSize={60} />
      </Sequence>
      <Sequence from={sec(264)} durationInFrames={sec(3)}>
        <TextCard text="只是替你先试一步。" accent fontSize={64} />
      </Sequence>

      {/* ============ PART 5: 结尾 4:28-4:45 ============ */}

      {/* 镜77: 敬你一杯 */}
      <Sequence from={sec(268)} durationInFrames={sec(5)}>
        <TextCard text="我先试了，敬你一杯。" fontSize={60} />
      </Sequence>

      {/* 镜78: 你自己决定 */}
      <Sequence from={sec(273)} durationInFrames={sec(5)}>
        <TextCard text="这杯喝不喝，你自己决定。" fontSize={60} />
      </Sequence>

      {/* 镜79: 品牌 */}
      <Sequence from={sec(278)} durationInFrames={sec(5)}>
        <TextCard text="先试为敬" accent fontSize={96} />
      </Sequence>

      {/* 镜80: 黑屏渐出 */}
      <Sequence from={sec(283)} durationInFrames={sec(2)}>
        <BlackScreen />
      </Sequence>
    </AbsoluteFill>
  );
};
