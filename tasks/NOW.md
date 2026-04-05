# NOW — 当前待办

> 最后更新: 2026-04-05 (CC native 迁移后重置)
> 完整项目历史见 tasks/backlog.md

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
