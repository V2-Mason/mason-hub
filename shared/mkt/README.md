# 营销技能公共库

> PM 在项目启动或迭代时，从本目录选取适用的技能，内化到 `domains/<domain>/projects/<project>/mkt/` 下。
> 执行层（Creator/Dev）只读项目级文件，不直接读本目录。

## 技能目录

| 技能文件 | 一句话描述 | 适用场景 |
|---------|-----------|---------|
| [copywriting.md](copywriting.md) | 转化导向的文案框架 + 质量检查清单 | 写产品介绍、落地页、社交帖文案 |
| [content-strategy.md](content-strategy.md) | 内容规划方法论：类型分类 + 选题优先级 + 内容支柱 | 制定周/月内容计划 |
| [hooks-library.md](hooks-library.md) | 标题和开头公式库（通用 + 小红书 + 电商） | 写标题、开头句、CTA |
| [customer-language.md](customer-language.md) | 客户原话采集和应用方法 | 提炼卖点话术、写走心文案 |
| [competitor-analysis.md](competitor-analysis.md) | 竞品分析框架：定位对比 + 差异化提炼 | 竞品监控、差异化策略 |
| [scoring.md](scoring.md) | 内容优先级 4 维评分公式 | 选题排序、复盘内容效果 |

## PM 内化流程

### 1. 选技能

读本目录，评估哪些技能对当前项目有用。不需要全选 — 只选跟项目阶段匹配的。

**选型参考：**

| 项目阶段 | 建议选取 |
|---------|---------|
| 刚启动，还没内容 | content-strategy + copywriting + hooks-library |
| 已有内容，优化转化 | scoring + customer-language + competitor-analysis |
| 扩品类/加新号 | competitor-analysis + content-strategy |

### 2. 内化到项目

复制选中的技能到项目目录，结合品牌上下文改写：

```
domains/<domain>/projects/<project>/mkt/
├── context.md              ← 必须有：品牌定位、人设、调性、禁忌
├── copywriting-<平台>.md   ← 从公共版改写，加入品牌话术
├── hooks-<平台>.md         ← 从公共版筛选，翻译成平台风格
└── weekly-direction.md     ← briefing 自动写入（可选）
```

**内化 ≠ 复制粘贴**。要做的：
- 删掉不适用的部分（比如电商项目不需要 SEO 段落）
- 替换通用示例为品牌真实案例
- 加入品牌禁忌（绝对不能说的话）
- 加入平台限制（如小红书标题 20 字限制）

### 3. 通知执行层

内化完成后告诉 Creator/Dev："项目营销知识已更新，路径是 xxx/mkt/"。

### 4. 持续迭代

- 公共库更新时：Meta Manager 或 Mason 通知 PM，PM 评估是否同步
- 项目实践中发现新 pattern：PM 提炼后反馈到公共库（上游贡献）
- 每月复盘：哪些框架有用、哪些没用，调整选用
