# System Map

> 最后更新: 2026-04-05 (CC native 迁移)

## 工作模式

**CC Native** — 2026-04-05 从自建编排层 (run-agent.sh/Dispatcher/Gateway) 迁移到 Claude Code 原生能力。
Agent 通过 `.claude/agents/` 定义，调度通过 RemoteTrigger，规则通过 `.claude/rules/`。
旧基础设施 (scripts/archived/) 保留但不再使用。

## CC Agents

| Agent | 合并自 | Model | 用途 |
|-------|--------|-------|------|
| platform-dev | EMP_0002+0004 | opus | 基础设施 + DevOps |
| biz-dev | EMP_0005 | sonnet | 业务功能开发 |
| data-engineer | EMP_0014 | haiku | 数据管道 |
| content-dev | EMP_0009 | sonnet | SocialMesh + 视频 |

Lens 模式 (读 config 切视角): EMP_0000/0001/0003/0008/0012/0015

## RemoteTrigger

| Trigger | 频率 | 状态 |
|---------|------|------|
| Email Patrol | -- | 已迁入 /standup (RemoteTrigger 无法加载 MCP) |
| AIGC Reminder | 每日 22:00 UTC | active |
| Unit Tests | 每日 06:17 UTC | active |

限额 2/3 已用。Email Patrol 改为 /standup 手动触发。空出 1 个名额可用。

## 能力线状态

| 线 | 状态 | 一句话 |
|----|------|--------|
| 数据 | active | 17/17 全绿, SDK v0.1, Scout v2 跑通 |
| 内容 | waiting | SocialMesh 基础完成, 等 TTS + 数据输入 |
| 商业 | waiting | 全是外部依赖 (品牌授权/企业号/开发者账号) |

## 硬性等待项

| 等什么 | 等谁 | 解锁什么 |
|--------|------|---------|
| 品牌授权书 | 清谭/DAERA/CDL | XHS 店铺申请 |
| XHS 企业号 | Mason (营业执照) | 店铺运营 |
| XHS 开发者账号 | 平台 | API 对接 |

## 联邦节点

| 节点 | 状态 | 端点 |
|------|------|------|
| surenxuan | active | aliyun:8000 |
| socialmesh | active | gcp:8001 |
| tiktok-viral | active | script-based |

---

> 旧版详细内容 (五线受力分析/通信协议/kernel架构/联邦能力全景) 见 git history: `git show HEAD~1:SYSTEM_MAP.md`
