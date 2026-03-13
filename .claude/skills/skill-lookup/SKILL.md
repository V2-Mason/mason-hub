---
name: skill-lookup
description: >
  搜索、查看、安装 Agent Skills。从 prompts.chat 注册中心 或 GitHub 搜索可复用的 AI agent 技能，
  安装到 .claude/skills/ 目录。用于扩展 Claude 的能力。
  触发词：找 skill、搜索技能、安装 skill、有没有 XX 的 skill
user_invocable: true
---

# /skill-lookup — 技能搜索与安装

> **触发时机**：用户想找现成的 skill、想扩展 Claude 能力、或者想看看有什么可用的技能
> **原则**：先搜索现有 skill，再考虑自己写（Superpowers 原则）

## 搜索流程

### Step 1. 理解需求

从用户描述中提取：
- **关键词**：用户想要什么能力（如 "code review", "TDD", "debugging"）
- **场景**：什么时候用（如 "写完代码后", "遇到 bug 时"）

### Step 2. 搜索 prompts.chat

用 WebSearch 搜索 prompts.chat 注册中心：

```
搜索查询: site:prompts.chat {关键词} skill
```

也可以直接搜索 GitHub：
```
搜索查询: github.com .claude/skills SKILL.md {关键词}
```

### Step 3. 展示结果

每个结果展示：
```
📦 [技能名称]
   描述：[一句话说明]
   来源：[prompts.chat / GitHub repo]
   链接：[URL]
```

### Step 4. 获取技能内容

用户选定后，用 WebFetch 获取 SKILL.md 内容：
- prompts.chat：`WebFetch` 技能详情页
- GitHub：`WebFetch` raw 文件内容

### Step 5. 安装

1. 创建目录 `.claude/skills/{slug}/`
2. 保存 `SKILL.md`（主文件）
3. 保存附属文件（reference docs, scripts）
4. 读回 `SKILL.md` 验证 frontmatter 完整
5. 告知用户技能已安装，说明触发方式

## 本地技能管理

### 列出已安装技能

```bash
ls -d .claude/skills/*/SKILL.md | while read f; do
  dir=$(dirname "$f")
  name=$(basename "$dir")
  desc=$(grep "^description:" "$f" | head -1 | sed 's/description: *//')
  echo "  $name: $desc"
done
```

### 创建新技能

如果搜索不到现成的，帮用户创建：

1. 确定技能名称（kebab-case）
2. 创建 `.claude/skills/{name}/SKILL.md`
3. 必须包含 frontmatter：
   ```yaml
   ---
   name: skill-name
   description: >
     一句话描述触发条件和功能
   user_invocable: true  # 如果可以用 /skill-name 手动调用
   ---
   ```
4. 正文写清楚：触发时机、步骤、验收标准
5. 类型标注：Rigid（严格执行）或 Flexible（灵活适配）

### 卸载技能

```bash
rm -rf .claude/skills/{name}/
```

## Guidelines

- **先搜后写**：永远先搜索是否有现成 skill，再考虑自己写
- **适配 mason-hub**：安装后检查是否需要适配（如工具名映射、路径调整）
- **记录安装**：安装新技能后告知 Mason，说明什么时候会触发
- **不装冗余**：如果现有 skill 已覆盖需求，不重复安装
