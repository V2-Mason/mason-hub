---
name: skill-lookup
description: >
  搜索、评估、安装 Agent Skills。从 prompts.chat 注册中心 或 GitHub 搜索可复用的 AI agent 技能，
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

### Step 2. 多源搜索（按优先级）

**Source A — skills.sh（首选，CLI 直接搜索+安装，有安装量数据）**
```bash
npx skills find "{关键词}"
```
输出包含：技能名、安装量、skills.sh 链接。安装量是质量的最佳代理指标。
安装命令：`npx skills add {owner/repo@skill}`

**Source B — SkillsMP（skillsmp.com，400K+ 技能，有分类和过滤）**
```
WebSearch: site:skillsmp.com {关键词} skill
```
或直接浏览：`https://skillsmp.com/search?q={关键词}`

**Source C — Anthropic 官方**
```
WebSearch: site:github.com/anthropics/skills {关键词}
```
官方技能质量有保障，但数量少。

**Source D — GitHub 社区（量大，需筛选）**
```
WebSearch: github.com .claude/skills SKILL.md {关键词}
```
重点仓库：
- `obra/superpowers` — 高质量系列（brainstorming 53K+, debugging 29K+, code-review 22K+）
- `supercent-io/skills-template` — 全品类模板（每个 ~10K installs）
- `wshobson/agents` — 实用工具集

### Step 3. 展示结果（必须包含评估）

每个结果必须包含以下信息：

```
📦 [技能名称]
   描述：[一句话说明]
   来源：[prompts.chat / GitHub repo 名 / 作者]
   链接：[URL]
   评分：⭐⭐⭐⭐☆ (4/5)
   安全：🟢 安全 / 🟡 需审查 / 🔴 有风险
   理由：[评分和安全判断的依据]
```

### Step 4. 评分标准（1-5 星）

| 维度 | 权重 | 判断依据 |
|------|------|---------|
| **实用性** | 30% | 是否解决真实痛点，还是 demo/toy |
| **质量** | 25% | SKILL.md 结构完整、步骤清晰、有 checklist |
| **维护** | 20% | 最近更新时间、star 数、是否有活跃维护 |
| **兼容性** | 15% | 是否依赖特定 MCP/工具、能否在 mason-hub 直接用 |
| **文档** | 10% | 有无 reference 文件、示例、使用说明 |

评分映射：
- ⭐⭐⭐⭐⭐ (5): 生产可用，直接安装
- ⭐⭐⭐⭐☆ (4): 优秀，可能需要小调整
- ⭐⭐⭐☆☆ (3): 可用，需要适配
- ⭐⭐☆☆☆ (2): 有参考价值，但需大幅改造
- ⭐☆☆☆☆ (1): 不推荐

### Step 5. 安全评估（必须）

检查以下红线：

| 检查项 | 🟢 安全 | 🟡 需审查 | 🔴 有风险 |
|--------|---------|----------|----------|
| **外部请求** | 无网络调用 | 调用已知 API（GitHub, Google） | 调用未知第三方服务 |
| **文件操作** | 只读 + 写到 skill 目录 | 写到项目目录 | 删除/覆盖系统文件 |
| **命令执行** | 无 Bash 调用 | 执行明确的 CLI 工具 | 执行动态构建的命令 |
| **敏感数据** | 不涉及 | 读取 .env 但不泄露 | 发送数据到外部 |
| **依赖** | 纯 prompt，无依赖 | 需要常见工具（git, npm） | 需要安装未知包 |

**🔴 有风险的 skill 必须告知 Mason 具体风险，由 Mason 决定是否安装。**

### Step 6. 获取技能内容

**方式 A（推荐）— npx skills 直接安装：**
```bash
npx skills add {owner/repo@skill}
```
自动下载 SKILL.md + 附属文件到 `.claude/skills/`。

**方式 B — 手动获取：**
用 WebFetch 从 skills.sh 链接获取 SKILL.md 内容：
```
WebFetch: https://skills.sh/{owner}/{repo}/{skill}
```
或 GitHub raw 文件：
```
WebFetch: https://raw.githubusercontent.com/{owner}/{repo}/main/.claude/skills/{skill}/SKILL.md
```

### Step 7. 安装

**自动安装（npx skills）：**
```bash
npx skills add {owner/repo@skill}
```
安装后验证：`npx skills list`

**手动安装：**
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
- **每个结果必须有评分+安全评估**：不能只列链接
- **适配 mason-hub**：安装后检查是否需要适配（如工具名映射、路径调整）
- **记录安装**：安装新技能后告知 Mason，说明什么时候会触发
- **不装冗余**：如果现有 skill 已覆盖需求，不重复安装
