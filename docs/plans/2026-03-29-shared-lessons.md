# Shared Lessons 跨 Agent 经验共享机制

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 EMP agent 踩过的坑自动沉淀并跨 agent 共享，消除记忆孤岛

**Architecture:** 在 `data/shared_lessons.jsonl` 新增共享经验池，agent-loader.sh 新增 write/load 两个函数，agent 启动时按 domain + severity pull 相关 lessons。独立于 inbox 机制，不新增消息类型。

**Tech Stack:** Bash + Python3 (inline), JSONL, agents.yaml domain 字段

---

### Task 1: 创建 shared_lessons.jsonl 和 schema 定义

**Files:**
- Create: `data/shared_lessons.jsonl`
- Create: `kernel/standards/schemas/shared_lesson.yaml`

**Step 1: 创建空的 shared_lessons.jsonl**

```bash
touch data/shared_lessons.jsonl
```

**Step 2: 写 schema 定义**

```yaml
# kernel/standards/schemas/shared_lesson.yaml
# Shared Lesson 记录格式定义
#
# 写入方: agent-loader.sh write_shared_lesson()
# 读取方: agent-loader.sh load_shared_lessons()

fields:
  id:
    type: string
    format: "LESSON-YYYYMMDD-NNN"
    required: true
    description: 全局唯一 ID

  source_agent:
    type: string
    format: "EMP_XXXX"
    required: true
    description: 写入方 agent ID

  domain:
    type: string
    enum: [meta, ecommerce, platform, socialmesh, independent]
    required: true
    description: 复用 agents.yaml 的 domain 值

  tags:
    type: array[string]
    required: true
    description: 自由标签，3-6 个，用于辅助搜索

  severity:
    type: string
    enum: [high, medium, low]
    required: true
    description: "high=数据丢失/流程阻断, medium=效率损失, low=最佳实践"

  title:
    type: string
    max_length: 80
    required: true
    description: 一句话摘要

  body:
    type: string
    required: true
    description: 具体描述 + 建议做法

  task_id:
    type: string
    required: false
    description: 关联的 task_id，可在 audit.jsonl 追溯

  created_at:
    type: string
    format: ISO8601
    required: true
```

**Step 3: Commit**

```bash
git add data/shared_lessons.jsonl kernel/standards/schemas/shared_lesson.yaml
git commit -m "feat: add shared_lessons schema and empty data file"
```

---

### Task 2: 新增 write_shared_lesson 函数

**Files:**
- Modify: `scripts/agent-loader.sh:190` (在 check_inbox 函数之后插入)

**Step 1: 在 agent-loader.sh 的 check_inbox 函数之后（第 190 行后），插入 write_shared_lesson 函数**

```bash
# ============================================================
# write_shared_lesson — 写入跨 agent 共享经验
# ============================================================
# 用法: write_shared_lesson <source_agent> <domain> <tags_csv> <severity> <title> <body> [task_id]
# 写入: data/shared_lessons.jsonl
# severity: high(数据丢失/流程阻断) | medium(效率损失) | low(最佳实践)
write_shared_lesson() {
  local source_agent="$1"
  local domain="$2"
  local tags_csv="$3"
  local severity="$4"
  local title="$5"
  local body="$6"
  local task_id="${7:-}"

  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"
  local file="$hub_dir/data/shared_lessons.jsonl"

  # 去重：title 精确匹配
  if grep -qF "\"title\": \"$title\"" "$file" 2>/dev/null; then
    echo "⚠️ shared_lesson 已存在: $title" >&2
    return 0
  fi

  # 生成 ID + 写入
  python3 -c "
import json, sys, os
from datetime import datetime, timezone

file_path = '$file'
today = datetime.now(timezone.utc).strftime('%Y%m%d')

# 计算当日序号
count = 0
if os.path.exists(file_path):
    with open(file_path) as f:
        for line in f:
            if f'LESSON-{today}' in line:
                count += 1

lesson = {
    'id': f'LESSON-{today}-{count+1:03d}',
    'source_agent': '$source_agent',
    'domain': '$domain',
    'tags': [t.strip() for t in '$tags_csv'.split(',') if t.strip()],
    'severity': '$severity',
    'title': '$title',
    'body': '''$body''',
    'task_id': '$task_id' if '$task_id' else None,
    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
}

with open(file_path, 'a') as f:
    f.write(json.dumps(lesson, ensure_ascii=False) + '\n')

print(f\"📝 shared_lesson 写入: {lesson['id']} ({lesson['title']})\", file=sys.stderr)
"
}
```

**Step 2: 验证函数语法**

Run: `bash -n scripts/agent-loader.sh`
Expected: 无输出（语法正确）

**Step 3: 测试写入**

Run:
```bash
source scripts/agent-loader.sh
write_shared_lesson "EMP_0005" "ecommerce" "xhs,cookie,采集" "high" \
  "XHS Cookie 过期后采集静默失败" \
  "Cookie 登录方式几天到几周过期。过期后 MediaCrawler 采集无错误码静默失败。建议每次采集前检查 cookie 有效性。"
cat data/shared_lessons.jsonl
```
Expected: 1 行 JSON 记录，id 为 LESSON-20260329-001

**Step 4: 测试去重**

Run:
```bash
source scripts/agent-loader.sh
write_shared_lesson "EMP_0005" "ecommerce" "xhs,cookie" "high" \
  "XHS Cookie 过期后采集静默失败" "重复测试"
```
Expected: stderr 输出 `⚠️ shared_lesson 已存在`，文件仍然只有 1 行

**Step 5: 清理测试数据，Commit**

```bash
> data/shared_lessons.jsonl
git add scripts/agent-loader.sh
git commit -m "feat: add write_shared_lesson to agent-loader.sh"
```

---

### Task 3: 新增 load_shared_lessons 函数

**Files:**
- Modify: `scripts/agent-loader.sh` (在 write_shared_lesson 函数之后插入)

**Step 1: 在 write_shared_lesson 之后插入 load_shared_lessons 函数**

```bash
# ============================================================
# load_shared_lessons — 加载跨 agent 共享经验（按 domain + severity 过滤）
# ============================================================
# 用法: load_shared_lessons <agent_id>
# stdout: 格式化的相关 lessons（注入 agent context）
# 过滤规则：
#   - severity=high → 全员可见
#   - 同 domain → 可见
#   - source_agent=自己 → 排除
load_shared_lessons() {
  local agent_id="$1"
  local hub_dir="${HUB_DIR:-$HOME/mason-hub}"
  local file="$hub_dir/data/shared_lessons.jsonl"
  local agents_yaml="$hub_dir/kernel/standards/agents.yaml"

  [ ! -f "$file" ] || [ ! -s "$file" ] && return 0

  python3 -c "
import json, sys, os

try:
    import yaml
except ImportError:
    # PyYAML 不可用时用 grep 降级
    import subprocess
    result = subprocess.run(
        ['grep', '-A1', 'id: $agent_id', '$agents_yaml'],
        capture_output=True, text=True
    )
    my_domain = ''
    for line in result.stdout.split('\n'):
        if 'domain:' in line:
            my_domain = line.split('domain:')[1].strip()
            break
else:
    with open('$agents_yaml') as f:
        data = yaml.safe_load(f)
    my_domain = ''
    for a in data.get('agents', []):
        if a['id'] == '$agent_id':
            my_domain = a.get('domain', '')
            break

results = []
with open('$file') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except:
            continue
        if rec.get('source_agent') == '$agent_id':
            continue
        if rec.get('severity') == 'high' or rec.get('domain') == my_domain:
            results.append(rec)

if not results:
    sys.exit(0)

print('--- shared_lessons: {} 条相关经验 ---'.format(len(results)))
print()
for r in results:
    tags_str = ','.join(r.get('tags', [])[:3])
    print('[{}][{}] from {} - {}'.format(
        r.get('severity', '?'), tags_str,
        r.get('source_agent', '?'), r.get('title', '?')))
    body = r.get('body', '')
    if len(body) > 200:
        body = body[:200] + '...'
    print('  {}'.format(body))
    print()
"
}
```

**Step 2: 验证语法**

Run: `bash -n scripts/agent-loader.sh`
Expected: 无输出

**Step 3: 写入测试数据并测试加载**

Run:
```bash
source scripts/agent-loader.sh

# 写入 2 条测试 lesson
write_shared_lesson "EMP_0005" "ecommerce" "xhs,cookie,采集" "high" \
  "XHS Cookie 过期后采集静默失败" \
  "Cookie 过期后 MediaCrawler 静默失败，无错误码。建议每次采集前检查。"

write_shared_lesson "EMP_0002" "platform" "docker,searxng" "medium" \
  "SearXNG Docker 需要 --restart always" \
  "不加 restart 策略的话 GCP 重启后服务不会自动恢复。"

# 测试：EMP_0010 (content, domain=socialmesh) 应该只看到 high severity 的
load_shared_lessons "EMP_0010"
echo "---"
# 测试：EMP_0001 (PM, domain=ecommerce) 应该看到 high + ecommerce domain 的
load_shared_lessons "EMP_0001"
echo "---"
# 测试：EMP_0005 应该排除自己写的，只看到 platform medium 如果有交集
load_shared_lessons "EMP_0005"
```

Expected:
- EMP_0010: 只看到 1 条 (XHS high)
- EMP_0001: 看到 1 条 (XHS high + ecommerce domain)
- EMP_0005: 只看到 0 或 1 条 (SearXNG 是 platform domain，EMP_0005 是 ecommerce，所以看不到 medium 的)

**Step 4: 清理测试数据，Commit**

```bash
> data/shared_lessons.jsonl
git add scripts/agent-loader.sh
git commit -m "feat: add load_shared_lessons to agent-loader.sh"
```

---

### Task 4: 修改 load_agent_context 插入 shared_lessons 加载

**Files:**
- Modify: `scripts/agent-loader.sh:266` (memory 加载之后、inbox 之前)

**Step 1: 在 load_agent_context 函数中，第 266 行（memory 加载的 fi 之后）和第 268 行（inbox 注释之前）之间，插入 shared_lessons 加载**

找到这段代码（约第 259-268 行）：
```bash
    if [ -f "$memory" ]; then
      echo ""
      echo "--- memory/memory.md ---"
      cat "$memory"
    else
      echo "⚠️ agent-loader: memory/memory.md 不存在，跳过" >&2
    fi
  fi

  # --- inbox: 启动时自动检查未读消息 ---
```

在 `fi` 和 `# --- inbox` 之间插入：

```bash

    # --- shared_lessons: 加载相关跨 agent 经验 ---
    local lessons_content
    lessons_content=$(load_shared_lessons "$agent_id") || true
    if [ -n "$lessons_content" ]; then
      echo ""
      echo "$lessons_content"
    fi
```

注意：这段代码需要在 `if [ "$layer" = "01" ]` 的 fi 之后、inbox 之前。但 agent_id 变量在 inbox 段才定义（第 270 行）。所以需要把 agent_id 提取移到 shared_lessons 之前。

实际修改：将第 269-270 行的 `agent_id` 提取上移到 shared_lessons 之前：

```bash
  fi

  # --- agent_id 提取（shared_lessons 和 inbox 共用）---
  local agent_id
  agent_id=$(basename "$agent_dir")

  # --- shared_lessons: 加载相关跨 agent 经验（仅 layer 01）---
  if [ "$layer" = "01" ]; then
    local lessons_content
    lessons_content=$(load_shared_lessons "$agent_id") || true
    if [ -n "$lessons_content" ]; then
      echo ""
      echo "$lessons_content"
    fi
  fi

  # --- inbox: 启动时自动检查未读消息 ---
  local inbox_content
  inbox_content=$(check_inbox "$agent_id") || true
```

**Step 2: 验证语法**

Run: `bash -n scripts/agent-loader.sh`
Expected: 无输出

**Step 3: 端到端测试**

Run:
```bash
source scripts/agent-loader.sh

# 写入一条 high severity 测试 lesson
write_shared_lesson "EMP_0005" "ecommerce" "xhs,cookie" "high" \
  "测试 lesson" "这是端到端测试用的 lesson"

# 加载 EMP_0002 的完整 context，看 shared_lessons 是否出现
load_agent_context agents/EMP_0002 01 2>/dev/null | grep -A5 "shared_lessons"
```

Expected: 输出包含 `--- shared_lessons: 1 条相关经验 ---` 和测试 lesson 内容

**Step 4: 清理测试数据，Commit**

```bash
> data/shared_lessons.jsonl
git add scripts/agent-loader.sh
git commit -m "feat: integrate shared_lessons into load_agent_context"
```

---

### Task 5: 修改 update_agent_state 支持失败时自动写入 lesson

**Files:**
- Modify: `scripts/agent-loader.sh:337-344` (update_agent_state 的消息发送之后)

**Step 1: 在 update_agent_state 函数末尾（第 344 行 `fi` 之后），插入失败时自动写 lesson**

```bash

  # 失败时自动写入 shared_lesson
  if [ "$status" = "failed" ] && [ -n "$summary" ]; then
    # 从 agents.yaml 获取 domain
    local domain
    domain=$(python3 -c "
import sys
try:
    import yaml
    with open('${hub_dir}/kernel/standards/agents.yaml') as f:
        data = yaml.safe_load(f)
    for a in data.get('agents', []):
        if a['id'] == '$agent_id':
            print(a.get('domain', 'unknown'))
            sys.exit(0)
except:
    pass
print('unknown')
") || domain="unknown"
    write_shared_lesson "$agent_id" "$domain" "failure,auto" "medium" \
      "任务 $task_id 失败: $(echo "$summary" | head -c 60)" \
      "Agent: $agent_id\n任务: $task_id\n失败摘要: $summary" \
      "$task_id"
  fi
```

**Step 2: 验证语法**

Run: `bash -n scripts/agent-loader.sh`
Expected: 无输出

**Step 3: Commit**

```bash
git add scripts/agent-loader.sh
git commit -m "feat: auto-write shared_lesson on agent task failure"
```

---

### Task 6: 更新 autonomous_tasks.yaml 支持 lesson_on_fail 字段

**Files:**
- Modify: `data/autonomous_tasks.yaml:1-22` (头部注释区增加字段说明)
- Modify: `data/autonomous_tasks.yaml` (给有 verify_command 的任务加 lesson_on_fail)

**Step 1: 在 autonomous_tasks.yaml 头部注释区（第 21 行 account 说明之后）新增字段说明**

```yaml
#   lesson_on_fail: true 时，失败自动写入 data/shared_lessons.jsonl（默认 false）
#   lesson_tags:    预设 tags（逗号分隔），lesson_on_fail=true 时使用
```

**Step 2: 给有 verify_command 的任务加 lesson_on_fail: true**

以下任务需要加（因为有明确验证标准，失败更有诊断价值）：

- `searxng-docker`: 加 `lesson_on_fail: true` 和 `lesson_tags: "docker,searxng,部署"`
- `unit-tests`: 加 `lesson_on_fail: true` 和 `lesson_tags: "测试,pytest,回归"`
- `health-fix`: 加 `lesson_on_fail: true` 和 `lesson_tags: "数据,健康检查,pipeline"`
- `scout-v2-cron`: 加 `lesson_on_fail: true` 和 `lesson_tags: "cron,scout,调度"`

**Step 3: Commit**

```bash
git add data/autonomous_tasks.yaml
git commit -m "feat: add lesson_on_fail field to autonomous_tasks.yaml"
```

---

### Task 7: 更新 agent-loader.sh 头部注释

**Files:**
- Modify: `scripts/agent-loader.sh:1-14`

**Step 1: 更新头部注释，加入新函数说明**

将第 8-9 行之后插入：

```bash
#   write_shared_lesson <src> <domain> <tags> <sev> <title> <body> [task_id]
#   load_shared_lessons <agent_id>                # 按 domain+severity 加载相关经验
```

**Step 2: Commit**

```bash
git add scripts/agent-loader.sh
git commit -m "docs: update agent-loader.sh header with shared_lessons functions"
```
