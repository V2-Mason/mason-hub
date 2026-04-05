---
name: learning-weave
description: "Vault learnings 月度编织：扫描孤立笔记、发现跨领域连接、添加 backlink"
---

# /learning-weave — 知识编织

扫描 `~/vault/learnings/` 所有文件，发现应该链接但未链接的笔记对，批量添加 `see-also` backlink。

## 执行步骤

### 1. 扫描所有 learnings

读取 `~/vault/learnings/` 下所有 .md 文件。对每个文件提取：
- frontmatter tags
- 已有的 `[[backlinks]]`
- 已有的 `see-also` 引用
- 正文关键主题（1-2 个词）

### 2. 识别集群

基于 tags + 内容主题，将文件分组为自然集群。典型集群维度：
- 同一工具链（AE/Remotion/video）
- 同一基础设施（GCP/Claude Code/harness）
- 同一方法论（research/scoring/data）
- 同一业务域（XHS/ecommerce/content）

### 3. 发现缺失链接

对每个集群内的文件对，检查：
- 同 cluster 但没有互相 backlink → **应链接**
- 不同 cluster 但讨论同一个底层教训 → **跨域链接**（最有价值）

### 4. 展示给 Mason 确认

输出格式：
```
## Learning Weave Report

### 集群内缺失链接（同领域）
- ae-export-script-usage.md ↔ ae-to-remotion-route-c-workflow.md
  理由：同属 AE 导出工作流

### 跨域发现（不同领域但共享教训）
- git-push-discipline.md ↔ system-map-harness-retrospective.md
  共享教训：手动流程 → 自动化的转换模式

### 已良好链接（无需操作）
- research-scoring-pitfalls.md ↔ research-data-collection-audit.md

### 统计
孤立文件: X/Y → X'/Y（减少 N 个）
新增链接: N 条
跨域发现: N 条
```

**等 Mason 确认后**才执行链接操作。Mason 可以：
- 全部接受
- 逐条确认/拒绝
- 修改链接理由

### 5. 执行链接

对确认的链接，在两个文件的 frontmatter 中添加 `see-also`:

```yaml
---
see-also:
  - "[[learnings/other-file]]"
---
```

如果文件已有 see-also 字段，追加而非覆盖。

### 6. 更新状态

```bash
# 更新 system-state.yaml 的 learning_weave_last
python3 -c "
import yaml
from datetime import date
f = 'system-state.yaml'
state = yaml.safe_load(open(f))
state['rules']['learning_weave_last'] = date.today().isoformat()
yaml.dump(state, open(f, 'w'), default_flow_style=False, allow_unicode=True, sort_keys=False)
print(f'learning_weave_last updated to {date.today().isoformat()}')
"
```

### 7. Commit vault

```bash
cd ~/vault && git add learnings/ && git commit -m "[learning-weave] N links added, M cross-domain discoveries" && git push
```

## 触发方式

- 手动: Mason 说 `/learning-weave`
- 提醒: session-bootstrap 自动检测 `learning_weave_last` 超期时显示提醒
- 频率: 建议每 30 天一次（system-state.yaml `learning_weave_interval_days`）