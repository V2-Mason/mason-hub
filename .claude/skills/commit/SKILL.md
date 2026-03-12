# /commit — 智能提交

执行以下步骤，确保记忆和 backlog 在 commit 前同步更新：

## 1. 盘点本次 session 变更

- 运行 `git status` 和 `git diff --stat` 查看所有变更
- 回顾本次 session 做了什么（从对话上下文判断）
- 识别：涉及哪些 agent、哪些项目、哪些新发现

## 2. 更新 Backlog（tasks/backlog.md）

检查并更新：
- 本次完成的任务 → 标记 `[x]` 并注明日期
- 新发现的问题或待办 → 添加到对应优先级
- 过时的任务描述 → 标注更新（如发现某功能已存在）
- 如果没有需要更新的内容，跳过此步

## 3. EMP_0012 归属判断（必须在写记忆前完成）

**每次 commit 前，用 EMP_0012 的 Checklist A 判断本次工作的 lesson 归谁：**

1. 这次工作的输出是什么？
2. 它属于现有哪个 agent 的职责范围？
3. 如果横跨多个 agent → 拆分：哪部分归谁？

**判断完成后，明确声明**："本次 lesson 归 EMP_XXXX，理由：XXX"

如果归属不清 → **停下来问 Mason**，不要跳过或默认存全局记忆。

## 4. 更新记忆

### 4a. 全局记忆（~/.claude/projects/-home-hangn-mason-hub/memory/MEMORY.md）
检查本次 session 是否有跨 session 价值的信息：
- Mason 的新偏好或决策
- 新的技术限制或踩坑
- 架构决策变更
- 新的工作流程规则

如果有 → 追加到 MEMORY.md 对应 section（遵循铁律 3：追加不删除）
如果没有 → 跳过

### 4b. Agent 记忆（agents/EMP_*/memory/long_term.md 或 lessons.md）
基于步骤 3 的归属判断，写 lesson 到**对应 agent** 的记忆文件：
- 内容：做了什么、发现了什么、踩了什么坑
- 控制在 5-15 行
- **禁止跳过**：即使是"纯讨论/规划"，只要产出了决策或方法论，就必须有归属

## 5. Gateway 决策广播检查

检查本次 session 中 Mason 是否做了影响 Gateway 行为的决策：

**触发关键词**："不用管"、"暂时不做"、"先不管"、"这是预期的"、"确认了"、"是正常的"、"已知问题"

如果有 → 追加条目到 `data/gateway-known-states.yaml`，格式：
```yaml
- id: kebab-case-unique-id
  date: YYYY-MM-DD
  decision: Mason 说了什么
  impact: Gateway 遇到什么情况应该跳过
  expires: YYYY-MM-DD  # 默认 +14 天，重要决策可以更长
```

如果没有 → 跳过

**注意**：只写"影响 Gateway 告警行为"的决策。战略讨论、产品定义、架构方向等留在 MEMORY.md，不写这里。

## 5b. 配置架构一致性检查（自动）

如果本次变更涉及 `agents/EMP_*/config.md`、`shared/protocols/`、`docs/playbooks/`，运行：

```bash
bash ~/mason-hub/scripts/config-health-check.sh --brief
```

有警告时：
- **Config 膨胀** → 必须拆分到 playbook 后再 commit
- **引用断裂** → 修复引用或创建缺失文件后再 commit
- **Protocol/Playbook 过时** → 记录到 commit message 中，不阻塞提交

## 6. 执行 Git Commit

- `git add` 所有相关文件（包括步骤 2-4 更新的记忆、backlog、gateway-known-states.yaml）
- **不要 add** 敏感文件（.env、credentials）、大型二进制文件（.db）、日志文件（logs/）
- 写 commit message：
  - 一句话总结主要变更
  - 如果变更较多，分点列出
  - 结尾加 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- 运行 `git status` 确认提交成功

## 7. 汇报

简洁输出：
```
✅ Commit: <hash> <message 前 50 字>
📝 Backlog: 更新了 X 项 / 无需更新
🧠 记忆: 更新了 MEMORY.md + EMP_XXXX / 无需更新
📡 Gateway: 广播了 X 条决策 / 无需广播
```

## 注意事项

- 步骤 2-3 的更新必须遵循铁律 3（追加不删除）
- 如果不确定某个变更是否值得记录，宁可记录
- commit message 用中文，格式参照 git log 现有风格
- 不要 push（除非 Mason 明确说 push）
