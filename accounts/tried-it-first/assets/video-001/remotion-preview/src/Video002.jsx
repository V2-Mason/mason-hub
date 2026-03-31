import { AbsoluteFill, Sequence, Audio, staticFile } from "remotion";
import {
  TextCard, Sub, BlackScreen, TerminalView, DiffView, FileTreeView,
  ScrollingWall, NumberReveal, TokenChart, AgentListView, ChatUI,
  RevealText, ToolLogosWall, DocView,
} from "./components.jsx";

const sec = (s) => Math.round(s * 30);

// === 数据 ===

const COMMIT_LINES = [
  "e25a7e5 feat: shared_lessons 跨 Agent 经验共享机制",
  "0e7ca7a feat: 知识板块IP设计 + 分镜表 + 经历素材 + 视频骨架",
  "e74ee84 Update SocialMesh connector: FastAPI → Postiz API",
  "7da7f01 EMP_0001 system_feedback 第3次巡检",
  "430b814 feat: wechat-sync v3 — group chat sender mapping",
  "2324eec EMP_0001 system_feedback 巡检 (3/24)",
  "1cbc60d 标记 Role/Playbook 增强任务已完成",
  "9650134 EMP_0015 加趋势归因+决策回顾方法论",
  "61124a5 wechat-sync v7: grouped analysis + exclude list",
  "4834a60 fix: wechat-sync uses X-API-Key auth",
  "490cbfe feat: wechat-sync v2 — discover mode + protobuf decoder",
  "c7d79bd feat: wechat-sync tool — chat analysis + image OCR",
  "f72a439 refactor: memory migration — fix EMP_0005 path",
  "1e4e4d3 update: execution engine design doc + event data sync",
  "1fdee20 chore: /standup — update SYSTEM_MAP",
  "ef4b64b fix: replace 6 broken symlinks with actual files",
  "aacfc3b refactor: final mason-hub cleanup — eliminate redundancy",
  "da551dc feat: complete kernel migration + fix EMP_0002 root cause",
  "5dfc170 feat: add kernel layer — Option C architecture (OS model)",
  "56e12b4 chore: save current state before kernel restructure",
  "a04d7c7 联邦架构 v0.1：mason-hub 升级为多项目中枢调度层",
  "f3ac349 Backlog 职责分离：新建 tasks/NOW.md",
  "12f3846 v2 兼容性修复：12 个脚本切换到 v2 格式",
  "68805fd SYSTEM_MAP 自动更新闭环 + CLAUDE.md 指针",
  "3e5afce 通信治理四层补齐：权限控制 + 验证机制 + 异常处理",
  "2137c75 task_assign 协议 + 首个 multi-agent 跑通",
  "de65581 inbox 通信机制：send_message/check_inbox",
  "99f5419 agent-loader.sh 创建 + run-agent.sh v2 适配",
  "adee6dc feat: add cross-agent message schema",
  "fb62a6f refactor: migrate all EMPs to v2 4-file structure",
  "d521bab 日常运行数据同步：agent 日志、事件归档",
  "471f583 配置隔离：session-bootstrap hook 从全局迁移到项目级",
  "07706c5 /standup SYSTEM_MAP 增量更新",
  "e503877 Session 收工：Backlog 更新 + 四支柱评估记录",
  "34c6b38 质量框架集成到 run-agent.sh 执行流程",
  "a6bbea4 任务执行质量框架：递归拆解 + 多维 Critic",
  "f60584d 铁律执行层：pre-commit hook 硬阻塞 config 膨胀",
  "d7bbaff Config 膨胀修复：EMP_0000 5.4K→4.1K + EMP_0008 7.3K→5.0K",
  "340aac2 Roster 动态匹配完成：dispatcher.sh 按能力索引分配",
  "b28d3f6 Agent OS v2 S3-S6: Task Engine + Memory Router 全部完成",
  "71097e0 Agent OS v2 S2: Protocols 声明式 YAML + 版本管理",
  "e4ad364 Agent OS v2 S1: Roster 能力索引 + Accounts 隔离验证",
  "d8197e0 Agent OS v2 Phase 1+2：Accounts 标准化 + 四管 Memory",
  "8d567ff 注入优化三级架构：CLAUDE.md 瘦身 + registry.yaml",
  "680e37f Backlog 执行转化率修复 + Dispatcher 让路",
  "e23f422 feat: 时区统一 ET + 自愈框架 + Dispatcher 解锁",
  "22341b5 feat: Slack /pause + /resume — Mason 上线前暂停系统",
  "73501f6 feat: Gateway + Dispatcher 24h 运行",
  "e3b86a2 feat: Dispatcher 并行派发 — 按 lane 同时执行多任务",
  "e1c234f feat: Backlog 主动消化 — 自动派发 backlog 任务",
  "b3e3014 feat: 收工流程统一 + Dispatcher 动态任务注册表",
  "b5f0d6f feat: 自治闭环 — Event Router + Dispatcher 四层设计",
  "46ff136 fix: Gateway 重巡成本失控 — 日成本从 $10+ 降到 ~$1",
  "1997e92 Dispatcher 失败任务降级",
  "410b99e 成本优化：Gateway LLM 停用 + Dispatcher 改走 Max 订阅",
  "d5f4093 Meta Manager 每日规划闭环",
  "5ef94d7 feat: 自治系统修复 + 目录重组 + Token 优化",
  "a5c7ae2 Token 成本优化三件套",
  "c09fa13 feat: semantic search, memory compaction, context budget",
  "981c7a4 feat: add PM retry limits (max 2)",
  "adfc784 initial: mason-hub full backup",
];

const NEWS_WALL_ITEMS = [
  // 正面 — 真实标题来自 HackerNews / TechCrunch
  { title: "Show HN: Vibe coding a bookshelf with Claude Code", source: "HackerNews", sentiment: "positive" },
  { title: "Vibe-Coding a PCB — surprisingly good", source: "Substack", sentiment: "positive" },
  { title: "Vibe coding as a coding veteran: from 8-bit assembly to English-as-code", source: "Medium", sentiment: "positive" },
  { title: "GLM-5: From Vibe Coding to Agentic Engineering", source: "Zhipu AI", sentiment: "positive" },
  { title: "Vibe Coding and the Future of Software Engineering", source: "alexp.pl", sentiment: "positive" },
  { title: "Vibe coding tips and tricks", source: "AWS Labs", sentiment: "positive" },
  { title: "Vibe coding the MIT course catalog", source: "stackdiver", sentiment: "positive" },
  { title: "Vibe coding has turned senior devs into 'AI babysitters' — but they say it's worth it", source: "TechCrunch", sentiment: "positive" },
  { title: "My spicy take on vibe coding for PMs", source: "ddmckinnon", sentiment: "positive" },
  { title: "Vibe Coding in the 90s", source: "ssg.dev", sentiment: "positive" },
  // 负面 — 真实标题来自 HackerNews / fast.ai / arXiv
  { title: "Breaking the spell of vibe coding", source: "fast.ai", sentiment: "negative" },
  { title: "Vibe coding kills open source", source: "arXiv", sentiment: "negative" },
  { title: "Vibe coding is mad depressing", source: "gmnz.xyz", sentiment: "negative" },
  { title: "Vibe Coding is not an excuse for low-quality work", source: "Substack", sentiment: "negative" },
  { title: "Vibe coding creates a bus factor of zero", source: "mindflash", sentiment: "negative" },
  { title: "\"Vibe Coding\" vs. Reality", source: "cendyne.dev", sentiment: "negative" },
  { title: "I won't be vibe coding anymore: a noob's perspective", source: "varunraghu", sentiment: "negative" },
  { title: "The problem with \"vibe coding\"", source: "dylanbeattie", sentiment: "negative" },
  { title: "Karpathy's 'Vibe Coding' Movement Considered Harmful", source: "nmn.gl", sentiment: "negative" },
  { title: "Perverse incentives of vibe coding", source: "Medium", sentiment: "negative" },
];

const FILE_TREE_ITEMS = [
  { name: "mason-hub", type: "folder", depth: 0 },
  { name: "accounts", type: "folder", depth: 1, highlight: true },
  { name: "surenxuan", type: "folder", depth: 2 },
  { name: "tried-it-first", type: "folder", depth: 2 },
  { name: "growth-memo", type: "folder", depth: 2 },
  { name: "restaurant-ops", type: "folder", depth: 2 },
  { name: "agents", type: "folder", depth: 1 },
  { name: "EMP_0000 ~ EMP_0015", type: "folder", depth: 2 },
  { name: "kernel", type: "folder", depth: 1 },
  { name: "standards", type: "folder", depth: 2 },
  { name: "connectors", type: "folder", depth: 2 },
  { name: "scripts", type: "folder", depth: 1 },
  { name: "run-agent.sh", type: "file", depth: 2 },
  { name: "dispatcher.sh", type: "file", depth: 2 },
  { name: "tasks", type: "folder", depth: 1 },
  { name: "backlog.md", type: "file", depth: 2 },
  { name: "NOW.md", type: "file", depth: 2 },
  { name: "SYSTEM_MAP.md", type: "file", depth: 1 },
  { name: "CLAUDE.md", type: "file", depth: 1 },
];

const BUDGET_DIFF_LINES = [
  "  # scripts/run-agent.sh",
  "  ",
  "  # --- Token 成本上限（防止上下文累积失控）---",
  "  # 默认 $0.50/session，可通过环境变量覆盖",
  "- MAX_BUDGET_USD=\"${MAX_BUDGET_USD:-0.50}\"",
  "+ MAX_BUDGET_USD=\"${MAX_BUDGET_USD:-2.00}\"",
  "  ",
  "  # --- Chain depth 限制（防止无限递归）---",
];

const TOKEN_DATA = [
  { label: "EMP_01", value: 8000 },
  { label: "EMP_02", value: 12000 },
  { label: "EMP_04", value: 6000 },
  { label: "EMP_05", value: 15000 },
  { label: "EMP_06", value: 9000 },
  { label: "EMP_08", value: 11000 },
  { label: "EMP_09", value: 7000 },
  { label: "EMP_10", value: 10000 },
  { label: "EMP_14", value: 75000 },
  { label: "EMP_15", value: 8500 },
];

const AGENTS = [
  { id: "EMP_0000", name: "Meta Manager", role: "总调度", active: true },
  { id: "EMP_0001", name: "素仁轩 PM", role: "项目管理", active: true },
  { id: "EMP_0002", name: "Platform Dev", role: "基础设施开发", active: true },
  { id: "EMP_0003", name: "电商 DM", role: "行业判断协调", active: true },
  { id: "EMP_0004", name: "SRE", role: "运维", active: true },
  { id: "EMP_0005", name: "电商 Dev", role: "业务开发", active: true },
  { id: "EMP_0006", name: "Scout", role: "情报搜集", active: true },
  { id: "EMP_0008", name: "内容运营总监", role: "内容策略", active: true },
  { id: "EMP_0009", name: "Content Dev", role: "内容技术开发", active: true },
  { id: "EMP_0010", name: "Content Creator", role: "内容生产", active: true },
  { id: "EMP_0011", name: "Account Mgr", role: "品牌管理", active: true },
  { id: "EMP_0012", name: "Product Arch", role: "产品定义", active: true },
  { id: "EMP_0013", name: "店铺运营", role: "XHS运营", active: true },
  { id: "EMP_0014", name: "Data Engineer", role: "数据中台", active: true },
  { id: "EMP_0015", name: "数据分析师", role: "分析报告", active: true },
];

const CHATGPT_MSGS = [
  { role: "user", text: "帮我写一封请假邮件" },
  { role: "assistant", text: "好的，请问您需要请几天假？请假原因是什么？我来帮您拟一封正式的请假邮件。" },
  { role: "user", text: "请两天，感冒了" },
  { role: "assistant", text: "尊敬的领导：\n\n您好，由于身体不适（感冒），需请假两天（3月28日-29日），望批准。\n\n此致\n敬礼" },
];

const DECISION_MSGS = [
  { role: "user", text: "kernel 架构用哪种模式？Option A 联邦制、Option B 中心化、Option C OS 模式？" },
  { role: "assistant", text: "三个方案的 trade-off：\n\nOption A 联邦制 — 最灵活，但跨域协调成本高\nOption B 中心化 — 最简单，但扩展性差\nOption C OS 模式 — 中间路线，kernel 管标准和协议，accounts 管业务\n\n推荐 Option C，理由：你已经有 16 个 Agent，需要统一标准但不能中心化瓶颈。" },
  { role: "user", text: "用 C，走 OS 模式" },
];

const PAUSE_COMMIT_LINES = [
  "  commit 22341b5",
  "  Author: Mason <mason@surenxuan.com>",
  "  Date: Wed Mar 11 2026",
  "  ",
  "  feat: Slack /pause + /resume",
  "  ",
  "  /pause: 写 /tmp/mason-pause 标志",
  "         Gateway 停止 heartbeat",
  "         Dispatcher 停止派发",
  "         正在运行的 agent 自然完成，不中断",
  "  ",
  "  /resume: 删除标志，系统恢复运转",
  "  ",
  "  避免 Mason 上线时与 agent 同时改代码",
  "  产生 git 冲突",
];

const FIRST_COMMITS = [
  { text: "adfc784 initial: mason-hub full backup", color: "rgb(200,200,200)" },
  { text: "f6cca37 feat: token tracking + backlog workflow", color: "rgb(80,220,120)" },
  { text: "c0b04e7 docs: add backlog management rules", color: "rgb(80,220,120)" },
  { text: "87babc3 feat: add QA skills framework", color: "rgb(80,220,120)" },
  { text: "ff51bc5 feat: auto backend lifecycle + verify loop", color: "rgb(80,220,120)" },
];

const TOOLS = [
  { icon: "📝", name: "Notion" },
  { icon: "🪶", name: "飞书" },
  { icon: "📊", name: "Trello" },
  { icon: "💬", name: "Slack" },
  { icon: "📈", name: "Google Sheets" },
  { icon: "🗂️", name: "Airtable" },
  { icon: "📋", name: "Asana" },
  { icon: "🔄", name: "Zapier" },
];

const SYSTEM_MAP_LINES = [
  "# SYSTEM_MAP.md",
  "",
  "**Agent OS v2 + Kernel 架构落地**",
  "16 EMP v2 四文件 + 通信协议栈",
  "kernel 层: standards / registry / deployments",
  "多租户 accounts/ + surenxuan 完全对齐",
  "",
  "## 能力线",
  "  Agent 自治线 → active",
  "  数据线 → active",
  "  内容生产线 → waiting",
  "  商业运营线 → waiting",
  "  审计与可观测性线 → active",
  "",
  "## Dispatcher: ▶️ active",
];

const CONFIG_LINES = [
  "  # agents/EMP_0002/config.md",
  "  ",
  "  id: EMP_0002",
  "  name: Platform Dev",
  "  role: 平台基础设施开发",
  "  domain: platform",
  "  status: active",
  "  ",
  "  launcher_args:",
  "    model: claude-sonnet-4-6",
  "    budget: $2.00",
  "    max_turns: 15",
  "  ",
  "  # 这些参数是人类定义的",
  "  # AI 不会替你决定预算给多少",
];

// === 主视频组件 ===

export const Video002 = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "rgb(10,10,10)" }}>

      {/* ============ BGM ============ */}
      {/* TODO: Mason 提供 BGM 后取消注释 */}
      {/* <Sequence from={0} durationInFrames={sec(285)}>
        <Audio src={staticFile("audio/bgm-vibe-coding.mp3")} volume={0.25} />
      </Sequence> */}

      {/* ============ 钩子 0:00-0:30 ============ */}

      {/* 镜1: Vibe Coding 文字卡 (0:00-0:03) */}
      <Sequence from={0} durationInFrames={sec(3)}>
        <TextCard text="Vibe Coding" fontSize={96} accent />
      </Sequence>

      {/* 镜2: 什么是Vibe Coding (0:03-0:06) */}
      <Sequence from={sec(3)} durationInFrames={sec(3)}>
        <TextCard text="不懂代码，靠 AI 写程序" fontSize={56} subText="— Andrej Karpathy" />
      </Sequence>

      {/* 镜3: 新闻截图墙 争议 (0:06-0:10) */}
      <Sequence from={sec(6)} durationInFrames={sec(4)}>
        <ScrollingWall items={NEWS_WALL_ITEMS} columns={3} scrollDistance={1200} />
        <Sub text="有人说这是革命，有人说这是笑话" />
      </Sequence>

      {/* 镜4: 一个真实案例 (0:10-0:12) */}
      <Sequence from={sec(10)} durationInFrames={sec(2)}>
        <TextCard text="一个真实案例" fontSize={60} />
      </Sequence>

      {/* 镜5: git log 滚动 (0:12-0:18) */}
      <Sequence from={sec(12)} durationInFrames={sec(6)}>
        <TerminalView
          lines={COMMIT_LINES}
          title="mason-hub — git log --oneline"
          scrollSpeed={0.3}
        />
        <Sub text="269 次提交，16 个 AI Agent，一个完整的运营系统" />
      </Sequence>

      {/* 镜6: 零 (0:18-0:21) */}
      <Sequence from={sec(18)} durationInFrames={sec(3)}>
        <NumberReveal number={0} label="我的技术背景" />
      </Sequence>

      {/* 镜7: 5分钟你自己判断 (0:21-0:24) */}
      <Sequence from={sec(21)} durationInFrames={sec(3)}>
        <TextCard text="5 分钟，你自己判断" fontSize={56} />
      </Sequence>

      {/* 过渡 */}
      <Sequence from={sec(24)} durationInFrames={sec(1)}>
        <BlackScreen />
      </Sequence>

      {/* ============ Part 1: 怎么开始的 0:25-1:25 ============ */}

      {/* 镜8: 文件树 多项目 (0:25-0:32) */}
      <Sequence from={sec(25)} durationInFrames={sec(7)}>
        <FileTreeView items={FILE_TREE_ITEMS} />
        <Sub text="我同时运营好几个项目" />
      </Sequence>

      {/* 镜9: backlog 待办 (0:32-0:37) */}
      <Sequence from={sec(32)} durationInFrames={sec(5)}>
        <TerminalView
          lines={[
            "# tasks/backlog.md",
            "",
            "- [ ] 2026-content-calendar.md 重写",
            "- [ ] EMP_0010 内容标准更新",
            "- [ ] 竞品库建立（两个板块各 10-15 个参考账号）",
            "- [ ] 付费产品交付平台调研",
            "- [ ] 企业号注册+个体户认证",
            "- [ ] 买手号开通橱窗",
            "- [ ] 素仁轩第一条视频拍摄+剪辑+发布",
            "- [ ] 小红书店铺上架产品",
            "- [ ] M面罩设计/制作",
            "- [ ] 各平台注册（B站/视频号/YouTube/小红书/X）",
            "- [ ] #001 脚本细化",
            "- [ ] 睡眠打卡器项目开发",
            "- [ ] Remotion 视频管线 skill",
            "- [ ] B站背景图设计",
            "- [ ] YouTube频道注册",
            "- [ ] IP 形象设计",
          ].map(l => ({ text: l, color: l.startsWith("- [ ]") ? "rgb(220,180,80)" : "rgb(120,120,120)" }))}
          title="tasks/backlog.md"
        />
        <Sub text="每天要做的事特别碎" />
      </Sequence>

      {/* 镜10: 工具Logo墙 + X (0:37-0:42) */}
      <Sequence from={sec(37)} durationInFrames={sec(5)}>
        <ToolLogosWall tools={TOOLS} />
        <Sub text="想过用各种工具拼，互相不打通" />
      </Sequence>

      {/* 镜11: 让AI串起来 (0:42-0:45) */}
      <Sequence from={sec(42)} durationInFrames={sec(3)}>
        <TextCard text="能不能让 AI 串起来？" fontSize={56} />
      </Sequence>

      {/* 镜12: ChatGPT 写邮件 (0:45-0:50) */}
      <Sequence from={sec(45)} durationInFrames={sec(5)}>
        <ChatUI messages={CHATGPT_MSGS} style="chatgpt" />
        <Sub text='不是"帮我写封邮件"的用法' />
      </Sequence>

      {/* 镜13: SYSTEM_MAP 架构 (0:50-0:56) */}
      <Sequence from={sec(50)} durationInFrames={sec(6)}>
        <DocView lines={SYSTEM_MAP_LINES} title="SYSTEM_MAP.md" />
        <Sub text="是真的搭一个系统，能自己跑的那种" />
      </Sequence>

      {/* 镜14: 第一条commit (0:56-1:01) */}
      <Sequence from={sec(56)} durationInFrames={sec(5)}>
        <TerminalView lines={FIRST_COMMITS} title="git log --reverse --oneline | head -5" />
        <Sub text="打开 Claude Code，开始了第一次 commit" />
      </Sequence>

      {/* 过渡 */}
      <Sequence from={sec(61)} durationInFrames={sec(1)}>
        <BlackScreen />
      </Sequence>

      {/* ============ Part 2: 真实发生了什么 1:02-2:32 ============ */}

      {/* 镜15: [需要Mason录屏] Claude Code 写代码 (1:02-1:12) */}
      {/* TODO: 替换为真实录屏 clips/claude-coding.mp4 */}
      <Sequence from={sec(62)} durationInFrames={sec(10)}>
        <TerminalView
          lines={[
            { text: "$ claude", color: "rgb(200,200,200)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  Claude Code v1.0.0", color: "rgb(120,120,220)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "> 帮我创建 wechat-sync 工具，需要解析聊天记录...", color: "rgb(200,200,200)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  Creating scripts/wechat-sync/main.py...", color: "rgb(80,220,120)" },
            { text: "  Writing chat parser with protobuf decoder...", color: "rgb(80,220,120)" },
            { text: "  Adding group chat sender mapping...", color: "rgb(80,220,120)" },
            { text: "  Creating config.json template...", color: "rgb(80,220,120)" },
            { text: "  Running tests... ✓ All passed", color: "rgb(80,220,120)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  5 files created, 490 lines written", color: "rgb(200,200,200)" },
          ]}
          title="Claude Code"
        />
        <Sub text="第一天特别兴奋，它真的在写代码，能跑" />
      </Sequence>

      {/* 镜16: Day 3 (1:12-1:14) */}
      <Sequence from={sec(72)} durationInFrames={sec(2)}>
        <TextCard text="Day 3" fontSize={120} />
      </Sequence>

      {/* 镜17: 空输出 (1:14-1:19) */}
      <Sequence from={sec(74)} durationInFrames={sec(5)}>
        <TerminalView
          lines={[
            { text: "$ bash scripts/run-agent.sh EMP_0002", color: "rgb(200,200,200)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  [2026-03-15 14:32:01] Starting EMP_0002 (Platform Dev)", color: "rgb(120,120,120)" },
            { text: "  [2026-03-15 14:32:03] Task: analyze infrastructure metrics", color: "rgb(120,120,120)" },
            { text: "  [2026-03-15 14:32:15] claude -p exited", color: "rgb(220,180,80)" },
            { text: "  [2026-03-15 14:32:15] Checking output...", color: "rgb(120,120,120)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  Output: (empty)", color: "rgb(220,80,80)" },
            { text: "  Status: error_empty_output", color: "rgb(220,80,80)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  18 consecutive failures. All budget_exceeded.", color: "rgb(220,80,80)" },
          ]}
          title="run-agent.sh — EMP_0002"
        />
        <Sub text="Agent 跑完了——输出是空的" />
      </Sequence>

      {/* 镜18: Budget Diff (1:19-1:25) */}
      <Sequence from={sec(79)} durationInFrames={sec(6)}>
        <DiffView
          title="scripts/run-agent.sh — commit da551dc"
          lines={BUDGET_DIFF_LINES}
        />
        <Sub text="原因是预算设太低了，0.5 美元，还没分析完就被掐断了" />
      </Sequence>

      {/* 镜19: 75000 tokens (1:25-1:30) */}
      <Sequence from={sec(85)} durationInFrames={sec(5)}>
        <NumberReveal number={75000} label="一次对话的 Token 消耗" suffix="" />
      </Sequence>

      {/* 镜20: Token 图表 (1:30-1:37) */}
      <Sequence from={sec(90)} durationInFrames={sec(7)}>
        <TokenChart data={TOKEN_DATA} label="Token Usage per Agent (single session)" />
        <Sub text="上下文像滚雪球一样越滚越大" />
      </Sequence>

      {/* 镜21: Dispatcher /pause (1:37-1:43) */}
      <Sequence from={sec(97)} durationInFrames={sec(6)}>
        <TerminalView lines={PAUSE_COMMIT_LINES} title="git show 22341b5" />
        <Sub text="Dispatcher 失控了，我不得不手动暂停" />
      </Sequence>

      {/* 镜22: 架构决策 (1:43-1:46) */}
      <Sequence from={sec(103)} durationInFrames={sec(3)}>
        <TextCard text="架构决策" accent fontSize={72} />
      </Sequence>

      {/* 镜23: config.md (1:46-1:52) */}
      <Sequence from={sec(106)} durationInFrames={sec(6)}>
        <TerminalView lines={CONFIG_LINES.map(l => ({ text: l, color: l.includes("budget") || l.includes("人类") ? "rgb(220,180,80)" : "rgb(160,160,160)" }))} title="agents/EMP_0002/config.md" />
        <Sub text="预算给多少、流程怎么串、什么时候该停" />
      </Sequence>

      {/* 镜24: AI不会替你想 (1:52-1:56) */}
      <Sequence from={sec(112)} durationInFrames={sec(4)}>
        <TextCard text="AI 不会替你想" accent fontSize={64} />
      </Sequence>

      {/* 过渡 */}
      <Sequence from={sec(116)} durationInFrames={sec(1)}>
        <BlackScreen />
      </Sequence>

      {/* ============ Part 3: 到底行不行 1:57-3:10 ============ */}

      {/* 镜25: 269 commits (1:57-2:03) */}
      <Sequence from={sec(117)} durationInFrames={sec(6)}>
        <NumberReveal number={269} label="代码提交" suffix=" commits" />
      </Sequence>

      {/* 镜26: Agent 列表 (2:03-2:11) */}
      <Sequence from={sec(123)} durationInFrames={sec(8)}>
        <AgentListView agents={AGENTS} />
        <Sub text="16 个 Agent，各有分工" />
      </Sequence>

      {/* 镜27: [需要Mason录屏] 系统实际输出 (2:11-2:19) */}
      {/* TODO: 替换为真实录屏 clips/standup-output.mp4 */}
      <Sequence from={sec(131)} durationInFrames={sec(8)}>
        <TerminalView
          lines={[
            { text: "$ /standup", color: "rgb(200,200,200)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  ☀️ 晨会报告 — 2026-03-31", color: "rgb(220,180,80)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  系统状态: Agent OS v2 运行中", color: "rgb(80,220,120)" },
            { text: "  活跃 Agent: 14/16", color: "rgb(80,220,120)" },
            { text: "  昨日 commit: 3", color: "rgb(200,200,200)" },
            { text: "  Dispatcher: ▶️ active", color: "rgb(80,220,120)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  能力线状态:", color: "rgb(200,200,200)" },
            { text: "    Agent 自治线 → active", color: "rgb(80,220,120)" },
            { text: "    数据线 → active", color: "rgb(80,220,120)" },
            { text: "    内容生产线 → waiting", color: "rgb(220,180,80)" },
            { text: "    商业运营线 → waiting", color: "rgb(220,180,80)" },
          ]}
          title="/standup"
        />
        <Sub text="数据采集、内容生成、竞品分析，都能跑" />
      </Sequence>

      {/* 镜28: AI帮我省的 (2:19-2:25) */}
      <Sequence from={sec(139)} durationInFrames={sec(6)}>
        <TerminalView
          lines={[
            { text: "  5 files created, 490 lines written", color: "rgb(80,220,120)" },
            { text: "  wechat-sync v7 完成", color: "rgb(80,220,120)" },
            { text: "  shared_lessons 机制创建完成 (799 lines)", color: "rgb(80,220,120)" },
            { text: "  kernel migration 完成 (83 files changed)", color: "rgb(80,220,120)" },
            { text: "  Agent OS v2 S1-S6 全部完成", color: "rgb(80,220,120)" },
            { text: "", color: "rgb(80,80,80)" },
            { text: "  Total: 269 commits, ~15000 lines of code", color: "rgb(200,200,200)" },
          ]}
          title="Claude Code — 产出"
        />
        <Sub text="AI 帮我省掉的是写代码的时间" />
      </Sequence>

      {/* 镜29: AI没帮我省的 — 方案讨论 (2:25-2:34) */}
      <Sequence from={sec(145)} durationInFrames={sec(9)}>
        <ChatUI messages={DECISION_MSGS} style="claude" />
        <Sub text="AI 没帮我省掉的是做决策的时间" />
      </Sequence>

      {/* 镜30: 核心金句 (2:34-2:40) */}
      <Sequence from={sec(154)} durationInFrames={sec(6)}>
        <TextCard text="会写代码 → 会做决策" accent fontSize={64} subText="门槛变了，但门槛没消失" />
      </Sequence>

      {/* 过渡 */}
      <Sequence from={sec(160)} durationInFrames={sec(1)}>
        <BlackScreen />
      </Sequence>

      {/* ============ 收尾 2:41-3:10 ============ */}

      {/* 镜31: 可以重新想想 (2:41-2:49) */}
      <Sequence from={sec(161)} durationInFrames={sec(8)}>
        <TerminalView lines={COMMIT_LINES.slice(0, 20)} title="mason-hub — running" scrollSpeed={0.15} />
        <Sub text="以前不会写代码放弃了——现在可以重新想想" />
      </Sequence>

      {/* 镜32: 会比以前更累 (2:49-2:54) */}
      <Sequence from={sec(169)} durationInFrames={sec(5)}>
        <TextCard text="会比以前更累" fontSize={64} />
      </Sequence>

      {/* 镜33: 品牌结尾 (2:54-3:00) */}
      <Sequence from={sec(174)} durationInFrames={sec(6)}>
        <TextCard text="先试为敬" accent fontSize={96} subText="我们下期见" />
      </Sequence>

      {/* 镜34: 黑屏 (3:00-3:02) */}
      <Sequence from={sec(180)} durationInFrames={sec(2)}>
        <BlackScreen />
      </Sequence>

    </AbsoluteFill>
  );
};
