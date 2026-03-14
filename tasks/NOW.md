# NOW — 当前待办

> 最后更新: Mason · 2026-03-14
> 完整项目历史见 tasks/backlog.md

## P0 — 必须推进

**Agent OS 四支柱（当前焦点）**
- [ ] Planning 能力：agent 收到目标自主拆解步骤（decompose.py 需接 LLM）
- [ ] Reflection 能力：critic.py 接 LLM 做真正质量评估
- [ ] Tool Use 自主化：agent 运行时查 registry.yaml 自主选择工具
- [ ] claude -p → Claude API 调用层：嵌套限制是 agent 自主执行的硬阻塞
- [ ] workflow 文件兼容性验证：v2 迁移后四个 grep 命令待跑
- [ ] run-agent.sh 拆分：1300 行 God Script → 模块化 Agent Runtime

**选品闭环**
- [ ] 用销售数据反馈优化 Agent 评估模型权重 — 等销售数据积累

## P1 — 本周目标

**Agent OS 补全**
- [ ] Role/Playbook 增强：EMP_0015 加趋势归因方法论、EMP_0000 加自主度评估方法论
- [ ] 效率审计自动化 — post-task hook 检测异常消耗，/standup 呈现 efficiency digest

**记忆 v1.5**
- [ ] Lesson 压缩规则 — 连续相同结果合并为 1 条+计数，控制 long_term <300 行（EMP_0002）
- [ ] Gap Triage 自动化 — Dispatcher 每日扫描 🏗️ 未修标记，通知 owner（EMP_0002）
- [ ] 跨 Agent 经验广播 — /commit 检测跨 agent 影响，append 到对方 short_term（EMP_0002）
- [ ] 连续运行 7 天无崩溃 — 观察中

**SocialMesh 内容管理**
- [ ] 内容编辑器增加图片上传（EMP_0009）
- [ ] 内容列表/草稿管理（EMP_0009）
- [ ] 界面中文化（EMP_0009）
- [ ] 增加"立即发布"按钮（EMP_0009）
- [ ] 错误提示可关闭 + 自动消失时间延长（EMP_0009）
- [ ] XHS 标题长度实时校验 — 限制 20 字（EMP_0009）

**SocialMesh 模块化迁移**
- [ ] 模块1 代码迁移：video-download/ → socialmesh/backend/（EMP_0009）
- [ ] 模块3 代码迁移：xhs-*.sh → socialmesh/（EMP_0009）
- [ ] 依赖项处理：Google OAuth credentials 共享方案（EMP_0009 + EMP_0004）

**TTS 自然度优化**
- [ ] 调参优化：全文一次性生成、限制语速 0.9-1.2、换 cosyvoice-v3-plus
- [ ] 如调参不够：换 TTS 引擎（Fish Audio / 豆包 TTS / Azure Neural TTS）
- [ ] 终极方案：真人录 10s → voice clone；或直接找配音

**XHS 店铺 API 对接（等准入完成后启动）**
- [ ] 签名+鉴权模块（EMP_0005）
- [ ] 商品+库存双向同步（EMP_0005）
- [ ] 订单+售后自动处理（EMP_0005）

**china-hub 分析看板**
- [ ] 看板后端 — FastAPI 查询采集数据库（EMP_0005）
- [ ] 看板前端 — Mason 从美国浏览器访问阿里云看板（EMP_0005）
- [ ] DeepSeek 分析集成 — 阿里云本地调 DeepSeek（EMP_0005）

**数据中台**
- [ ] 方案 C 升级（触发条件：数据总量 >50MB）— FastAPI + SDK（EMP_0014）

**Radar**
- [ ] 关键词淘汰回顾 — 每两周检查命中质量（Mason）

## P2 — 排队中

**UX**
- [ ] 根据 system_feedback 表持续迭代（EMP_0001）— 2 条待深入：加载速度 + UI 美观度

**XHS 模块增强**
- [ ] Webhook 实时推送 — 替代定时轮询（EMP_0004 + EMP_0005）

**ComfyUI**
- [ ] Seedance 2.0 节点 — 等官方 API 开放
- [ ] Qwen Image Edit 模型下载（~31GB）

**EMP_0013 店铺运营（等开店后激活）**
- [ ] 物流体验 / 服务咨询 / 商品体验 / 售后退款 / 交易纠纷（5 维店铺分）
- [ ] Phase 2: 供应链协调 / 促销执行 / 竞品追踪（月均订单>100 后）

**EMP_0015 反馈闭环（等店铺后台数据）**
- [ ] Phase 0: 店铺后台数据采集方案确认 + 手动跑一轮分析（Mason）
- [ ] Phase 1-3: 自动采集 → 漏斗诊断 → 闭环打通（EMP_0014/0015）

## 等待外部条件

| 条件 | 等谁 | 解锁什么 |
|------|------|---------|
| 品牌授权书（DAERA + CDL） | 清谭 | XHS 店铺申请 |
| XHS 企业专业号 + 个体店注册 | Mason（需营业执照） | 店铺运营 |
| XHS 开发者账号注册 | Mason（需中国手机号+营业执照） | API 对接 |
| Kling API access_key | Mason（klingai.com/dev） | ComfyUI Kling 节点 |
| XHS 爬虫小号注册（2个）| Mason（养号 3-5 天） | 采集 cron 注册 |
| XHS 小号 cookie | 小号养号完成 | 双账号采集调度 |
| Gemini API key | Mason | Scout MediaEngine |
| 店铺后台数据 | 开店后 | EMP_0015 反馈闭环 |
| 销售数据积累 | 实际运营 | 选品模型权重优化 |
| Seedance 2.0 API | 火山引擎开放 | ComfyUI 节点 |

## 上次 session 遗留

（EMP_0000 每次收工填这里，下次 session 接着做）
- v2 文件架构全量上线 + inbox 通信闭环已完成
- Dispatcher 处于 /pause 状态，待恢复
- 四支柱差距：Planning 10% / Reflection 15% / Tool Use 40% / Multi-agent 10%
