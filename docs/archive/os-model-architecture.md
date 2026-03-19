# Mason Hub — OS-Model 架构

> 日期: 2026-03-11
> 灵感来源: 王军杰 × 小军杰 "Model 派 vs Harness 派" 讨论
> 状态: 架构描述文档，非规范

## 核心命题

大模型不是 Chatbot，而是一个 **自带编译器、运行时、环境探针和系统调用的认知计算核心（Cognitive CPU）**。

Mason Hub 是这个 Cognitive CPU 的操作系统。

## 架构映射

```
传统 OS 概念          Mason Hub 对应              实现文件
─────────────────────────────────────────────────────────
Kernel               Gateway (mason-gateway.py)   永驻 daemon，中断处理，权限管理
Process Scheduler    Dispatcher (dispatcher.sh)   按 lane 并行，时间窗口控制
Process              Agent (EMP_XXXX)             独立进程，lane lock 隔离
System Call          Tool (read/write/run/slack)   白名单控制，审计日志
File System          Memory (JSONL + .md)          分层存储，归档机制
IPC                  Event Queue (queue.jsonl)     异步消息传递，event_router 路由
Self-Repair          Repair Session (claude -p)    故障检测 → 自动修复 → 验证
Cron Daemon          crontab + dispatcher          定时触发 + 事件触发混合
Shell                Claude Code (/skill)          Mason 的人机交互界面
```

## 三层执行模型

```
Layer 0: 纯脚本（零 token）
  data_health_check.sh, data-sync.sh, emit_event.sh
  → 传统 OS 的 shell script

Layer 1: 轻量推理（Haiku, ~$0.001/次）
  事件分析, 常规 heartbeat, Slack /ask
  → 传统 OS 的 user-space daemon

Layer 2: 深度推理（Sonnet/Opus, ~$0.01-0.10/次）
  Repair session, 4h 强制重巡, L3 事件
  → 传统 OS 的 kernel-mode 操作
```

## Gene 系统（可编程行为原语）

受 OpenClaw 的 gene 机制启发，mason-hub 实现了轻量版：

```
shared/genes/
├── skeptical_verification.md    # 质疑验证：诊断后强制自检
├── practical_epistemology.md    # 知行转化：规划时检查可执行性
└── ashby_variety.md             # 多样性审视：监控覆盖率检查
```

Gene 通过 run-agent.sh Phase 2.7 自动注入到对应角色的 agent：
- 执行层（Dev/SRE/Data）→ skeptical_verification
- 管理层（PM/Manager）→ practical_epistemology
- 基础设施层（Platform/SRE）→ ashby_variety

与 OpenClaw 的区别：
- OpenClaw: gene 是可编程对象，支持组合、变异、继承
- Mason Hub: gene 是 markdown 文本，通过 inject_if_exists 注入 system prompt
- 当 agent 数量 > 20 时，考虑升级为结构化 YAML + 模板引擎

## Self-Evolution Flywheel

```
运行 → 发现模式 → 蒸馏为 Learned Skill → 改变 Gateway 行为
  ↑                                              │
  └──────────────── 下一轮运行更好 ←──────────────┘
```

度量指标：
- **Skill applied_count**: 每条 Skill 被应用的次数（data/learned-skills-stats.json）
- **知行转化率**: backlog 可自动执行 / 总未完成（/standup 每日输出）
- **Ashby 覆盖率**: Gateway 检查项 / 能力线故障模式总数

淘汰机制：每月 review，applied_count = 0 的 Skill 标记为候选淘汰。

## Mason 的角色：Reward Function Provider

系统中唯一不可自动化的环节是 **定义"什么是好"**：
- 品牌方向、审美标准、成本约束
- 哪些问题值得修、哪些可以忍
- 战略优先级（四条能力线的权重分配）

这是 Mason 最不可替代的贡献，也是系统进化的方向盘。
Agent 负责 How（如何执行），Mason 负责 Why（为什么做这个）。

## 与 OpenClaw 的关系

| 维度 | OpenClaw | Mason Hub |
|------|----------|-----------|
| 基础模型 | Gemini | Claude |
| Gene 实现 | 可编程对象 | Markdown 注入 |
| 记忆 | EvoMap + Memory System | JSONL + .md 分层 |
| 自我进化 | SkillRL 论文级 | Learned Skills + distill |
| 部署 | 单机 | GCP + 阿里云双节点 |
| 商业场景 | 研究实验室 | 跨境电商 + 内容管道 |

Mason Hub 不追求复刻 OpenClaw，而是在实际业务场景中验证相同的架构直觉。
