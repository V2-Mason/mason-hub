# NOW — 当前待办

> 最后更新: 2026-04-08 S29 (Episode 001 Mason Hub 脚本就绪)
> 完整项目历史见 tasks/backlog.md

## Growth Memo #001 — 🟢 对标池需求分析完成, 等 Mason 选方向

**正确产出** (需求驱动):
- [x] preset bilibili-mason-target.md v0.1 → v0.1.1 (加 C10 商单硬规则)
- [x] 对标池 15 账号清单 + 数据状态盘点 (Tier 1×4 + Tier 2×8 + Tier 3×3)
- [x] 补爬 Tier 1 × 4 账号 × Top 5 视频 × 20 评论 = 394 条新评论 (evidence-2026-04-09/)
- [x] 11 大 fine-grained 需求簇 (跨 666 评论 = 394 新 + 272 round1 关键词池)
- [x] Mason × 需求 匹配矩阵 (7 强命中 + 3 弱)
- [x] 7 选题方向清单: [accounts/growth-memo/analysis/competitor_pool_needs_2026-04-09.md](accounts/growth-memo/analysis/competitor_pool_needs_2026-04-09.md)
- [ ] **BLOCKING**: Mason review 上面的分析 + 从 7 方向选 1-3 个
- [ ] 可选: 补爬 Tier 2 (4 独立开发 + 5 财经) × Top 5 评论 ~800 条 (1.5-2 h) → 11 簇置信度从 4/11 高 → 10/11 高
- [ ] 基于 Mason 选中方向写脚本 + 过 9 check 自审 (preset v0.1.1)
- [ ] 录制 + 剪辑 + 发布 → D7 dogfood

**走偏的第一轮产出** (供给驱动, 保留参考不对齐):
- ~~episode-001-mason-hub/topic-decision.md~~ — auto-pick T1 (方向错)
- ~~episode-001-mason-hub/script-v1.md~~ — 直接写脚本 (方向错)
- ~~episode-001-mason-hub/9check-audit.md~~ — 9/9 PASS 但题材是反向推的

## 刚完成

- [x] CC Native 迁移: 4 个 CC agent 定义 + Hooks 更新 + RemoteTrigger (3/3) + SYSTEM_MAP 瘦身 + /standup 重写
- [x] Email Patrol: MCP Server + skill + Railway 部署 + UX 设计 + /standup 集成

## P0 — 当前焦点

**验证 CC Agent 系统**
- [ ] Spawn 每个 CC agent 做一个简单任务，确认 context 加载正确 (platform-dev/biz-dev/data-engineer/content-dev)
- [ ] 验证 RemoteTrigger Unit Tests 是否按时触发 (明日 06:17 UTC 检查)

## P1 — 本周目标

**SocialMesh 功能补全** (用 CC Agent `content-dev` 派活)
- [ ] Content.status 发布后更新
- [ ] 界面中文化
- [ ] "立即发布"按钮
- [ ] 内容列表/草稿管理

**Email Patrol 优化**
- [ ] 首次 RemoteTrigger 巡逻结果审查 + 规则调优

**数据管道** (用 CC Agent `data-engineer` 派活)
- [ ] GCP crontab 注册 data_health_check (需 SSH)
- [ ] XHS 主干管道统一

## P2 — 排队中

**TTS 自然度**
- [ ] CosyVoice 调参 / 换引擎

**Scout v2 调度**
- [ ] 决定: 替换 AIGC Reminder trigger / 手动 /scout / GCP crontab

**SocialMesh 模块化**
- [ ] video-download/ -> socialmesh/backend/ 代码迁移
- [ ] xhs-*.sh -> socialmesh/ 迁移

## 等待外部条件

| 条件 | 等谁 | 解锁什么 |
|------|------|---------|
| 品牌授权书 | 清谭/DAERA/CDL | XHS 店铺申请 |
| XHS 企业号 | Mason (营业执照) | 店铺运营 |
| XHS 开发者账号 | 平台 | API 对接 |
| Kling API key | Mason | ComfyUI 节点 |

## 上次 session 遗留

- CC Native 迁移完成，旧脚本待归档 (Phase 4)
- /dev-task skill 需要更新: 不再用 run-agent.sh，改为 CC Agent tool
