# Mason Hub — 日常运营手册

**版本：** 1.0
**日期：** 2026-02-27
**读者：** Mason（人类操作者）

---

## 你每天要做的事

### 早上（5 分钟）

1. 打开 Claude Code，`cd ~/mason-hub`
2. 输入 `/standup`
3. 看 Slack：
   - **#system-alerts** — 系统自动在 08:00/09:00/09:30 发了 3 条报告
   - **#srx-alerts** — 有没有库存/临期预警
4. 有问题就处理，没问题就去忙别的

### 需要改代码时

```
/dev-task 修复 XXX 的 bug，具体描述...
```

然后等。Dev 会自己改代码、跑测试、最多修 3 轮。成功了自动 commit + Slack 通知你。失败了会一路 escalate 到你的 Slack。

### 需要部署时

```
/deploy
```

一键搞定：推代码到阿里云 → 编译前端 → 重启后端 → 健康检查。

### 觉得系统不对劲时

```
/health
```

会检查所有 agent、GCP 资源、阿里云端点，只报告异常。

### 每周一看情报

```
/scout
```

斥候会扫 GitHub、Anthropic、技术趋势，生成情报简报发到 **#scout**。

---

## 五个命令，够用了

| 命令 | 干嘛的 | 频率 |
|------|--------|------|
| `/standup` | 晨会：昨天做了啥、系统状态、今天待办 | 每天早上 |
| `/deploy` | 部署到阿里云生产 | 改完代码后 |
| `/health` | 全局健康检查 | 有疑问时 |
| `/dev-task <描述>` | 派活给 Dev | 需要改代码时 |
| `/scout` | 技术情报巡逻 | 每周一次 |

---

## 你不需要做的事（系统自动做）

| 事情 | 谁做 | 什么时候 |
|------|------|---------|
| 库存/临期/滞销巡检 | PM (EMP_0001) | 每天 08:00 |
| 基础设施日报 | SRE (EMP_0004) | 每天 09:00 |
| Agent 状态报告 | 自动脚本 | 每天 09:30 |
| 记忆压缩（PM 经验） | PM (EMP_0001) | 每周一 10:00 |
| 全量记忆清理 | 自动脚本 | 每周日 11:00 |
| API token 消耗报告 | 自动脚本 | 每天 23:00 |

所有报告发到 Slack，你看 Slack 就行。

---

## 当事情出问题时

### Dev 改代码失败了

你什么都不用做。系统会自动：

```
Dev 3 轮修复 → 失败 → PM 评估 → 重新分配 Dev
                       ↓ 还是失败（最多 2 次）
                 Platform Dev 介入 → 3 轮修复
                       ↓ 还是失败
                 Slack 通知你：🔴 需要 Mason 手动介入
```

**只有收到 🔴 通知时你才需要介入。** 其他层级的失败系统会自己处理。

### Slack 告警分级

| 标记 | 含义 | 你要做什么 |
|------|------|-----------|
| ✅ | 任务完成 | 不用管 |
| ⚠️ | 失败但还在自动修复 | 不用管，等结果 |
| 🔄 | PM 重新分配中 | 不用管 |
| ⬆️ | Escalate 到 Platform Dev | 关注但不用急 |
| 🔴 | 需要你决策 | **打开看，做决定** |

---

## 你的 Agent 团队

```
你 (Mason)
│
├── 直接对话 → EMP_0000 Meta Manager
│   他是你的 AI COO，负责跨域协调
│   找他：不确定该找谁的时候
│
├── 电商业务 → EMP_0003 Domain Manager → EMP_0001 PM → EMP_0005 Dev
│   PM 管项目，Dev 写代码，Domain Manager 做行业判断
│   找 PM：素仁轩项目的事
│   找 Domain Manager：电商行业的事
│
├── 技术运维 → EMP_0004 SRE
│   他看 Slack 告警、查日志、重启服务
│   找他：系统挂了或者变慢了
│
├── 平台开发 → EMP_0002 Platform Dev
│   他改 mason-hub 本身的代码
│   找他：agent 系统需要新功能
│
└── 情报搜集 → EMP_0006 Scout
    他扫 GitHub 和 Anthropic 的动态
    找他：/scout 或者想了解技术趋势
```

---

## Slack 频道地图

| 频道 | 看什么 | 谁发 |
|------|--------|------|
| **#system-alerts** | 基础设施日报、系统告警、部署通知 | SRE、自动脚本 |
| **#srx-alerts** | 库存预警、临期预警、销售异常 | PM |
| **#srx-business** | 项目进展、日常沟通 | PM |
| **#scout** | 技术情报简报 | Scout |
| **#mason-alerts** | 🔴 需要你决策的事 | 任何 agent escalate |

**优先看 #mason-alerts**，这是唯一需要你行动的频道。

---

## 文件在哪

你日常可能需要看的文件：

```
~/mason-hub/
  tasks/backlog.md          ← 所有待办事项（唯一的 source of truth）
  meta/roadmap.md           ← 系统演化路线图
  logs/audit.jsonl          ← agent 做了什么（审计记录）
  intel/watchlist.md        ← 技术关注列表
  intel/digests/            ← 每周情报简报
```

你一般不需要看的（agent 自己用）：

```
  agents/EMP_*.md           ← agent 角色定义
  skills/*.sh               ← 可执行脚本
  scripts/run-agent.sh      ← agent 调度引擎
  memory/                   ← agent 经验记忆
```

---

## 成本

### 自动化成本（每月）

| 触发器 | 频率 | 预估单次 | 月度 |
|--------|------|---------|------|
| PM 库存巡检 | 30次/月 | $0.05 | $1.50 |
| SRE 基础设施日报 | 30次/月 | $0.03 | $0.90 |
| PM 记忆压缩 | 4次/月 | $0.05 | $0.20 |
| agent-status-report | 30次/月 | $0 (无 API) | $0 |
| compact-memory | 4次/月 | $0.05 | $0.20 |
| **小计** | | | **~$2.80/月** |

### 手动任务成本

| 操作 | 预估 |
|------|------|
| `/dev-task` 成功（1 轮通过） | ~$0.15 |
| `/dev-task` 失败（3 轮 + PM） | ~$0.45 |
| 最坏情况（全链 escalation） | ~$2.00 |
| `/scout` 情报巡逻 | ~$0.10 |
| `/standup` 晨会 | ~$0.05 |

**总预算目标：< ¥50/月**（按当前使用频率绰绰有余）

---

## 快速排障

| 症状 | 怎么办 |
|------|--------|
| `/deploy` 失败 | 看输出的哪个 Step 失败。通常是阿里云 SSH 断了，等几分钟重试 |
| Dev 改了代码但测试全 skip | GCP 数据库是空的（0 条数据），不影响功能，只影响集成测试 |
| Slack 没收到通知 | `cat ~/slack-bot/.env` 确认 webhook URL 还有效 |
| 阿里云打不开 | 检查 tunnel：`ssh root@106.14.44.68 "echo ok"` |
| Agent 报 "Credit balance too low" | 去 Anthropic console 充值 API key |
| cron 没触发 | `crontab -l` 检查还在不在；`tail ~/mason-hub/logs/triggers.log` 看最近执行 |

---

## 一句话总结

**你是审批者，不是操作者。** 系统自动跑，Slack 自动报，出问题自动修。你只需要：
1. 早上看 Slack
2. 有任务就 `/dev-task`
3. 要部署就 `/deploy`
4. 收到 🔴 才需要动手
