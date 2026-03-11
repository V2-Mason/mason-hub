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

### 4b. Agent 记忆（agents/memory/EMP_*/long_term.md 或 lessons.md）
基于步骤 3 的归属判断，写 lesson 到**对应 agent** 的记忆文件：
- 内容：做了什么、发现了什么、踩了什么坑
- 控制在 5-15 行
- **禁止跳过**：即使是"纯讨论/规划"，只要产出了决策或方法论，就必须有归属

## 5. 执行 Git Commit

- `git add` 所有相关文件（包括步骤 2-3 更新的记忆和 backlog）
- **不要 add** 敏感文件（.env、credentials）、大型二进制文件（.db）、日志文件（logs/）
- 写 commit message：
  - 一句话总结主要变更
  - 如果变更较多，分点列出
  - 结尾加 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- 运行 `git status` 确认提交成功

## 6. 汇报

简洁输出：
```
✅ Commit: <hash> <message 前 50 字>
📝 Backlog: 更新了 X 项 / 无需更新
🧠 记忆: 更新了 MEMORY.md + EMP_XXXX / 无需更新
```

## 注意事项

- 步骤 2-3 的更新必须遵循铁律 3（追加不删除）
- 如果不确定某个变更是否值得记录，宁可记录
- commit message 用中文，格式参照 git log 现有风格
- 不要 push（除非 Mason 明确说 push）
