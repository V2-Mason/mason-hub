import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

// === 品牌常量 ===
const BRAND = {
  bg: "rgb(10,10,10)",
  text: "white",
  accent: "rgb(220,50,50)",
  muted: "rgb(100,100,100)",
  font: "Microsoft YaHei, sans-serif",
  green: "rgb(80,200,120)",
  red: "rgb(220,80,80)",
  termBg: "rgb(30,30,30)",
  termGreen: "rgb(80,220,120)",
  cardBg: "rgb(24,24,24)",
};

// === 文字卡（改进版）===
export const TextCard = ({ text, accent = false, subText = null, fontSize = 72 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", opacity }}>
      <div style={{ color: BRAND.text, fontSize, fontWeight: "bold", fontFamily: BRAND.font, textAlign: "center", padding: "0 120px", lineHeight: 1.4 }}>
        {text}
      </div>
      {accent && <div style={{ width: Math.min(text.length * fontSize * 0.6, 1200), height: 4, backgroundColor: BRAND.accent, marginTop: 15 }} />}
      {subText && <div style={{ color: BRAND.muted, fontSize: 36, marginTop: 40, fontFamily: BRAND.font }}>{subText}</div>}
      <div style={{ position: "absolute", bottom: 60, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === 字幕条 ===
export const Sub = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", bottom: 80, left: 0, right: 0, textAlign: "center", opacity }}>
      <span style={{ backgroundColor: "rgba(0,0,0,0.75)", color: "white", fontSize: 36, padding: "10px 28px", borderRadius: 6, fontFamily: BRAND.font, lineHeight: 1.6 }}>{text}</span>
    </div>
  );
};

// === 黑屏 ===
export const BlackScreen = () => <AbsoluteFill style={{ backgroundColor: BRAND.bg }} />;

// === 终端视图（模拟终端输出）===
export const TerminalView = ({ lines, title = "Terminal", scrollSpeed = 0, startLine = 0 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const visibleOffset = scrollSpeed > 0 ? Math.floor(frame * scrollSpeed) + startLine : startLine;

  const visibleLines = lines.slice(visibleOffset, visibleOffset + 28);

  // 统一 line 格式：字符串 → {text, color}
  const normalizeLine = (line) => {
    if (typeof line === "string") return { text: line, color: BRAND.termGreen };
    return { text: String(line.text || ""), color: line.color || BRAND.termGreen };
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(20,20,20)", padding: 40, opacity }}>
      {/* 标题栏 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: "12px 16px", backgroundColor: "rgb(40,40,40)", borderRadius: "8px 8px 0 0" }}>
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "rgb(255,95,87)" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "rgb(255,189,46)" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "rgb(39,201,63)" }} />
        <span style={{ color: BRAND.muted, fontSize: 14, marginLeft: 8, fontFamily: "Consolas, monospace" }}>{title}</span>
      </div>
      {/* 终端内容 */}
      <div style={{ backgroundColor: BRAND.termBg, padding: 24, borderRadius: "0 0 8px 8px", flex: 1, overflow: "hidden" }}>
        {visibleLines.map((rawLine, i) => {
          const line = normalizeLine(rawLine);
          return (
            <div key={i + visibleOffset} style={{
              color: line.color,
              fontSize: 20,
              fontFamily: "Consolas, monospace",
              lineHeight: 1.6,
              whiteSpace: "nowrap",
              overflow: "hidden",
            }}>
              {line.text}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === Git Diff 视图 ===
export const DiffView = ({ title, lines }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(20,20,20)", padding: 40, opacity }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: "12px 16px", backgroundColor: "rgb(40,40,40)", borderRadius: "8px 8px 0 0" }}>
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "rgb(255,95,87)" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "rgb(255,189,46)" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "rgb(39,201,63)" }} />
        <span style={{ color: BRAND.muted, fontSize: 14, marginLeft: 12, fontFamily: "Consolas, monospace" }}>{title}</span>
      </div>
      <div style={{ backgroundColor: BRAND.termBg, padding: 24, borderRadius: "0 0 8px 8px", flex: 1 }}>
        {lines.map((line, i) => {
          const isAdd = line.startsWith("+");
          const isDel = line.startsWith("-");
          const bg = isAdd ? "rgba(80,200,120,0.15)" : isDel ? "rgba(220,80,80,0.15)" : "transparent";
          const color = isAdd ? BRAND.green : isDel ? BRAND.red : "rgb(180,180,180)";
          const appear = interpolate(frame, [i * 4, i * 4 + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              color, backgroundColor: bg, fontSize: 22, fontFamily: "Consolas, monospace",
              lineHeight: 1.8, padding: "2px 8px", opacity: appear,
            }}>
              {line}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === 文件树视图（模拟VS Code侧栏）===
export const FileTreeView = ({ items, title = "EXPLORER" }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(30,30,30)", padding: 40, opacity }}>
      <div style={{ display: "flex", height: "100%" }}>
        {/* 侧栏 */}
        <div style={{ width: 500, backgroundColor: "rgb(37,37,38)", padding: 20, borderRight: "1px solid rgb(60,60,60)" }}>
          <div style={{ color: "rgb(150,150,150)", fontSize: 13, fontFamily: BRAND.font, marginBottom: 16, letterSpacing: 1 }}>{title}</div>
          {items.map((item, i) => {
            const appear = interpolate(frame, [i * 3, i * 3 + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const indent = (item.depth || 0) * 20;
            const isFolder = item.type === "folder";
            return (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 6,
                paddingLeft: indent + 8, paddingTop: 3, paddingBottom: 3, opacity: appear,
                backgroundColor: item.highlight ? "rgba(255,255,255,0.05)" : "transparent",
              }}>
                <span style={{ color: isFolder ? "rgb(220,180,80)" : "rgb(150,150,150)", fontSize: 16 }}>
                  {isFolder ? "📁" : "📄"}
                </span>
                <span style={{ color: isFolder ? "rgb(220,220,220)" : "rgb(180,180,180)", fontSize: 16, fontFamily: "Consolas, monospace" }}>
                  {item.name}
                </span>
              </div>
            );
          })}
        </div>
        {/* 主编辑区（暗色占位）*/}
        <div style={{ flex: 1, backgroundColor: "rgb(30,30,30)", display: "flex", justifyContent: "center", alignItems: "center" }}>
          <div style={{ color: "rgb(60,60,60)", fontSize: 48, fontFamily: BRAND.font }}>mason-hub</div>
        </div>
      </div>
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === 新闻截图墙（滚动）===
export const ScrollingWall = ({ items, columns = 3, scrollDistance = 2000 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const scrollY = interpolate(
    frame,
    [0, 15, durationInFrames - 15, durationInFrames],
    [0, 0, -scrollDistance, -scrollDistance],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, overflow: "hidden", opacity }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: 16,
        padding: 32,
        transform: `translateY(${scrollY}px)`,
      }}>
        {items.map((item, i) => (
          <div key={i} style={{
            backgroundColor: BRAND.cardBg,
            borderRadius: 12,
            padding: 24,
            border: "1px solid rgb(50,50,50)",
          }}>
            {/* 来源标签 */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div style={{
                backgroundColor: item.sentiment === "positive" ? "rgba(80,200,120,0.2)" : "rgba(220,80,80,0.2)",
                color: item.sentiment === "positive" ? BRAND.green : BRAND.red,
                fontSize: 12, padding: "3px 8px", borderRadius: 4, fontFamily: BRAND.font,
              }}>
                {item.source}
              </div>
            </div>
            {/* 标题 */}
            <div style={{
              color: "rgb(220,220,220)", fontSize: 20, fontFamily: BRAND.font,
              lineHeight: 1.5, fontWeight: "bold",
            }}>
              {item.title}
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// === 数字动画 ===
export const NumberReveal = ({ number, label, suffix = "" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const currentNumber = Math.floor(interpolate(frame, [0, 30], [0, number], { extrapolateRight: "clamp" }));

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
      <div style={{
        color: BRAND.text, fontSize: 140, fontWeight: "bold",
        fontFamily: "Consolas, monospace", transform: `scale(${scale})`,
      }}>
        {currentNumber.toLocaleString()}{suffix}
      </div>
      {label && <div style={{ color: BRAND.muted, fontSize: 36, marginTop: 20, fontFamily: BRAND.font }}>{label}</div>}
      <div style={{ position: "absolute", bottom: 60, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === Token 增长图表 ===
export const TokenChart = ({ data, label = "Token Usage" }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const maxVal = Math.max(...data.map(d => d.value));

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, padding: 80, opacity }}>
      <div style={{ color: BRAND.muted, fontSize: 20, fontFamily: BRAND.font, marginBottom: 20 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 600 }}>
        {data.map((d, i) => {
          const targetH = (d.value / maxVal) * 500;
          const h = interpolate(frame, [i * 3, i * 3 + 15], [0, targetH], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const isAlert = d.value > 50000;
          return (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
              <div style={{ color: isAlert ? BRAND.red : BRAND.muted, fontSize: 12, fontFamily: "Consolas, monospace", marginBottom: 4 }}>
                {d.value > 1000 ? `${Math.round(d.value / 1000)}K` : d.value}
              </div>
              <div style={{
                width: "100%", height: h, borderRadius: "4px 4px 0 0",
                backgroundColor: isAlert ? BRAND.red : "rgb(80,120,200)",
              }} />
              <div style={{ color: "rgb(80,80,80)", fontSize: 11, fontFamily: "Consolas, monospace", marginTop: 4 }}>
                {d.label}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === Agent 列表视图 ===
export const AgentListView = ({ agents }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, padding: 60, opacity }}>
      <div style={{ color: BRAND.muted, fontSize: 16, fontFamily: "Consolas, monospace", marginBottom: 24 }}>kernel/standards/agents.yaml</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
        {agents.map((agent, i) => {
          const appear = interpolate(frame, [i * 3, i * 3 + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              backgroundColor: BRAND.cardBg, borderRadius: 8, padding: 16,
              border: "1px solid rgb(50,50,50)", opacity: appear,
              display: "flex", gap: 12, alignItems: "center",
            }}>
              <div style={{
                backgroundColor: agent.active ? "rgba(80,200,120,0.2)" : "rgba(100,100,100,0.2)",
                color: agent.active ? BRAND.green : BRAND.muted,
                fontSize: 14, fontFamily: "Consolas, monospace", padding: "4px 8px", borderRadius: 4,
                minWidth: 80, textAlign: "center",
              }}>
                {agent.id}
              </div>
              <div>
                <div style={{ color: BRAND.text, fontSize: 18, fontFamily: BRAND.font, fontWeight: "bold" }}>{agent.name}</div>
                <div style={{ color: BRAND.muted, fontSize: 14, fontFamily: BRAND.font }}>{agent.role}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === ChatGPT 风格对话（用于镜12）===
export const ChatUI = ({ messages, style = "chatgpt" }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const isClaude = style === "claude";

  return (
    <AbsoluteFill style={{ backgroundColor: isClaude ? "rgb(25,25,25)" : "rgb(52,53,65)", padding: 60, opacity }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32, paddingBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          backgroundColor: isClaude ? "rgb(200,120,60)" : "rgb(116,184,117)",
          display: "flex", justifyContent: "center", alignItems: "center",
          color: "white", fontSize: 16, fontWeight: "bold",
        }}>
          {isClaude ? "C" : "G"}
        </div>
        <span style={{ color: "rgb(200,200,200)", fontSize: 18, fontFamily: BRAND.font }}>
          {isClaude ? "Claude" : "ChatGPT"}
        </span>
      </div>
      {/* Messages */}
      {messages.map((msg, i) => {
        const appear = interpolate(frame, [i * 12, i * 12 + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const isUser = msg.role === "user";
        return (
          <div key={i} style={{
            display: "flex", justifyContent: isUser ? "flex-end" : "flex-start",
            marginBottom: 16, opacity: appear,
          }}>
            <div style={{
              backgroundColor: isUser ? "rgb(80,80,100)" : "rgba(255,255,255,0.05)",
              color: "rgb(220,220,220)", fontSize: 20, fontFamily: BRAND.font,
              padding: "14px 20px", borderRadius: 12, maxWidth: "75%", lineHeight: 1.6,
            }}>
              {msg.text}
            </div>
          </div>
        );
      })}
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === 揭晓文字（弹性放大）===
export const RevealText = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, display: "flex", justifyContent: "center", alignItems: "center" }}>
      <div style={{ color: BRAND.text, fontSize: 80, fontWeight: "bold", fontFamily: BRAND.font, transform: `scale(${scale})` }}>{text}</div>
      <div style={{ position: "absolute", bottom: "48%", width: interpolate(frame, [0, 20], [0, 500], { extrapolateRight: "clamp" }), height: 4, backgroundColor: BRAND.accent }} />
    </AbsoluteFill>
  );
};

// === 工具Logo墙 ===
export const ToolLogosWall = ({ tools }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg, display: "flex", justifyContent: "center", alignItems: "center", opacity }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24 }}>
        {tools.map((tool, i) => {
          const appear = interpolate(frame, [i * 4, i * 4 + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              backgroundColor: BRAND.cardBg, borderRadius: 12, padding: 24,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
              opacity: appear, border: "1px solid rgb(50,50,50)",
              width: 160, height: 100, justifyContent: "center",
            }}>
              <div style={{ fontSize: 32 }}>{tool.icon}</div>
              <div style={{ color: BRAND.muted, fontSize: 14, fontFamily: BRAND.font }}>{tool.name}</div>
            </div>
          );
        })}
      </div>
      {/* X overlay */}
      <div style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%,-50%)",
        fontSize: 300, color: "rgba(220,50,50,0.5)",
        opacity: interpolate(frame, [40, 55], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>✕</div>
      <div style={{ position: "absolute", bottom: 60, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};

// === 系统架构文档视图 ===
export const DocView = ({ lines, title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(30,30,30)", padding: 40, opacity }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: "12px 16px", backgroundColor: "rgb(40,40,40)", borderRadius: "8px 8px 0 0" }}>
        <span style={{ color: "rgb(200,200,200)", fontSize: 15, fontFamily: "Consolas, monospace" }}>{title}</span>
      </div>
      <div style={{ backgroundColor: "rgb(30,30,30)", padding: 24, borderRadius: "0 0 8px 8px", flex: 1 }}>
        {lines.map((line, i) => {
          const appear = interpolate(frame, [i * 2, i * 2 + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const isHeader = line.startsWith("#") || line.startsWith("**");
          const isBold = line.includes("**");
          return (
            <div key={i} style={{
              color: isHeader ? "rgb(220,180,80)" : isBold ? "rgb(200,200,200)" : "rgb(160,160,160)",
              fontSize: isHeader ? 24 : 18,
              fontFamily: isHeader ? BRAND.font : "Consolas, monospace",
              fontWeight: isHeader || isBold ? "bold" : "normal",
              lineHeight: 1.8, opacity: appear,
            }}>
              {line}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 40, left: 60, color: "rgb(40,40,40)", fontSize: 24, fontFamily: BRAND.font }}>先试为敬</div>
    </AbsoluteFill>
  );
};
