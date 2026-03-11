#!/usr/bin/env python3
"""
Skill 蒸馏器 — 从 Gateway 原始记忆中提取可复用 skill

灵感来源: SkillRL (arXiv:2602.08234)
- 原始记忆冗长且噪声大（37 条 → 本质上 5 个模式）
- 蒸馏后的 skill 减少 10-20x token，同时效果更好
- 分层: General Skills（所有 heartbeat 加载）+ Task-Specific（按需检索）

用法:
  python3 scripts/distill-skills.py                    # 分析 + 预览，不写入
  python3 scripts/distill-skills.py --apply             # 分析 + 写入 MASONHUB.md
  python3 scripts/distill-skills.py --dry-run           # 只打印分析结果

成本: ~$0.01/次 (Haiku API)
建议: 每周日 compact-memory.sh 后运行
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
MEMORY_FILE = HUB_DIR / "data" / "gateway-memory.jsonl"
MASONHUB_FILE = HUB_DIR / "MASONHUB.md"
ARCHIVE_DIR = HUB_DIR / "data" / "archive"

CST = timezone(timedelta(hours=8))


def load_memories(days: int = 7) -> list[dict]:
    """加载最近 N 天的 gateway 记忆"""
    if not MEMORY_FILE.exists():
        return []

    cutoff = datetime.now(CST) - timedelta(days=days)
    entries = []
    for line in MEMORY_FILE.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ts = entry.get("timestamp", "")
            if ts and ts[:10] >= cutoff.strftime("%Y-%m-%d"):
                entries.append(entry)
        except json.JSONDecodeError:
            pass

    # 也加载归档记忆
    if ARCHIVE_DIR.exists():
        for f in sorted(ARCHIVE_DIR.glob("gateway-*.jsonl"))[-2:]:  # 最近 2 个月
            for line in f.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")
                    if ts and ts[:10] >= cutoff.strftime("%Y-%m-%d"):
                        entries.append(entry)
                except json.JSONDecodeError:
                    pass

    return entries


def load_existing_skills() -> list[str]:
    """从 MASONHUB.md 提取已有 skill 的标题"""
    if not MASONHUB_FILE.exists():
        return []
    content = MASONHUB_FILE.read_text()
    return re.findall(r"skill_\d+: (.+?)(?:\*\*| —)", content)


def get_next_skill_id() -> int:
    """获取下一个 skill 编号"""
    if not MASONHUB_FILE.exists():
        return 1
    content = MASONHUB_FILE.read_text()
    ids = [int(x) for x in re.findall(r"skill_(\d+)", content)]
    return max(ids) + 1 if ids else 1


def analyze_patterns(entries: list[dict]) -> dict:
    """纯规则分析：识别重复模式、失败模式、成功模式"""
    patterns = {
        "repeated_findings": [],      # 相同 finding 出现 3+ 次
        "escalation_chains": [],      # pending_mason 序列（同一问题反复升级）
        "resolved_patterns": [],      # 成功修复的模式
        "monitoring_fatigue": [],     # monitoring 超过 5 次无变化
    }

    # 1. 重复 finding 检测（关键词聚类）
    finding_groups = defaultdict(list)
    for e in entries:
        finding = e.get("finding", "")
        # 简化 finding 用于聚类：去掉数字、时间、括号内容
        key = re.sub(r"\d+/\d+|\d{4}-\d{2}-\d{2}|（.*?）|\(.*?\)", "", finding).strip()
        key = re.sub(r"\s+", " ", key)[:60]
        if key:
            finding_groups[key].append(e)

    for key, group in finding_groups.items():
        if len(group) >= 3:
            patterns["repeated_findings"].append({
                "pattern": key,
                "count": len(group),
                "statuses": [e.get("status", "?") for e in group],
                "sample": group[0].get("finding", ""),
            })

    # 2. 升级链检测（同一问题连续 pending_mason）
    pending_entries = [e for e in entries if e.get("status") == "pending_mason"]
    if len(pending_entries) >= 2:
        # 按时间排序，检测连续升级
        pending_entries.sort(key=lambda x: x.get("timestamp", ""))
        chains = []
        current_chain = [pending_entries[0]]
        for i in range(1, len(pending_entries)):
            prev_finding = current_chain[-1].get("finding", "")[:30]
            curr_finding = pending_entries[i].get("finding", "")[:30]
            # 如果前 30 字符相似度高，认为是同一问题
            overlap = sum(1 for a, b in zip(prev_finding, curr_finding) if a == b)
            if overlap > 15:
                current_chain.append(pending_entries[i])
            else:
                if len(current_chain) >= 2:
                    chains.append(current_chain)
                current_chain = [pending_entries[i]]
        if len(current_chain) >= 2:
            chains.append(current_chain)
        patterns["escalation_chains"] = chains

    # 3. 成功修复模式
    resolved = [e for e in entries if e.get("status") == "resolved"]
    for e in resolved:
        action = e.get("action_taken", "")
        if action and len(action) > 20:
            patterns["resolved_patterns"].append({
                "finding": e.get("finding", ""),
                "action": action,
                "timestamp": e.get("timestamp", ""),
            })

    # 4. monitoring 疲劳（同一状态持续 5+ 次无变化）
    monitoring = [e for e in entries if e.get("status") == "monitoring"]
    if len(monitoring) >= 5:
        patterns["monitoring_fatigue"].append({
            "count": len(monitoring),
            "sample": monitoring[-1].get("finding", ""),
        })

    return patterns


def distill_with_llm(patterns: dict, existing_skills: list[str]) -> list[dict]:
    """用 Haiku 从分析结果中蒸馏新 skill"""
    import anthropic

    # 构建提示
    patterns_text = json.dumps(patterns, indent=2, ensure_ascii=False, default=str)
    existing_text = "\n".join(f"- {s}" for s in existing_skills) if existing_skills else "（无）"

    prompt = f"""你是一个经验蒸馏器。分析以下 Gateway 运行模式，提取可复用的 skill。

## 已有 Skills（不要重复）
{existing_text}

## 运行模式分析
{patterns_text}

## 任务
从上述模式中提取新的、不与已有 skill 重复的可复用经验。每个 skill 必须：
1. 来自实际运行数据（不是猜测）
2. 可以指导未来的 heartbeat 行为
3. 足够具体，能直接执行（不是模糊建议）

## 输出格式
输出 JSON 数组，每个元素：
{{"title": "简短标题", "rule": "具体规则描述", "category": "general 或 task_specific", "source": "来源描述"}}

如果没有值得提取的新 skill，输出空数组 []。
不要勉强凑数，宁缺毋滥。"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # 解析输出
    text = response.content[0].text
    # 提取 JSON 数组
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []

    try:
        skills = json.loads(match.group())
        # 过滤掉与已有 skill 重复的
        new_skills = []
        for s in skills:
            title = s.get("title", "")
            if not any(existing.lower() in title.lower() or title.lower() in existing.lower()
                       for existing in existing_skills):
                new_skills.append(s)
        return new_skills
    except json.JSONDecodeError:
        return []


def format_skill_line(skill_id: int, skill: dict) -> str:
    """格式化为 MASONHUB.md 的 skill 行"""
    title = skill.get("title", "未命名")
    rule = skill.get("rule", "")
    source = skill.get("source", "自动蒸馏")
    today = datetime.now(CST).strftime("%Y-%m-%d")
    return f"- **skill_{skill_id:03d}: {title}** — {rule} [来源: {today} {source}]"


def apply_skills(new_skills: list[dict]) -> int:
    """将新 skill 写入 MASONHUB.md"""
    if not new_skills:
        return 0

    content = MASONHUB_FILE.read_text()
    next_id = get_next_skill_id()

    # 找到 Learned Skills section 的末尾（下一个 ## 之前）
    lines = content.split("\n")
    insert_idx = None
    in_skills = False
    for i, line in enumerate(lines):
        if line.startswith("## Learned Skills"):
            in_skills = True
        elif in_skills and line.startswith("## "):
            insert_idx = i
            break

    if insert_idx is None:
        print("❌ 找不到 Learned Skills section 的结束位置")
        return 0

    # 生成新 skill 行
    new_lines = []
    for j, skill in enumerate(new_skills):
        new_lines.append(format_skill_line(next_id + j, skill))

    # 在 section 末尾（空行之前）插入
    # 找到最后一个 skill 行
    last_skill_idx = insert_idx - 1
    while last_skill_idx > 0 and not lines[last_skill_idx].strip():
        last_skill_idx -= 1

    for j, new_line in enumerate(new_lines):
        lines.insert(last_skill_idx + 1 + j, new_line)

    MASONHUB_FILE.write_text("\n".join(lines))
    return len(new_skills)


def main():
    apply = "--apply" in sys.argv
    dry_run = "--dry-run" in sys.argv
    days = 7

    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            days = int(arg.split("=")[1])

    print(f"=== Skill 蒸馏器 ===")
    print(f"分析范围: 最近 {days} 天")
    print()

    # Step 1: 加载记忆
    entries = load_memories(days)
    print(f"📥 加载了 {len(entries)} 条记忆")
    if not entries:
        print("无记忆可分析，退出")
        return

    # Step 2: 模式分析（纯规则，零成本）
    patterns = analyze_patterns(entries)
    print(f"\n📊 模式分析结果:")
    print(f"  重复 finding: {len(patterns['repeated_findings'])} 个模式")
    for p in patterns["repeated_findings"]:
        print(f"    - \"{p['pattern'][:50]}\" × {p['count']}")
    print(f"  升级链: {len(patterns['escalation_chains'])} 条")
    for chain in patterns["escalation_chains"]:
        print(f"    - {len(chain)} 次连续升级: \"{chain[0].get('finding', '')[:50]}\"")
    print(f"  成功修复: {len(patterns['resolved_patterns'])} 个")
    print(f"  监控疲劳: {len(patterns['monitoring_fatigue'])} 个")

    if dry_run:
        print("\n--dry-run 模式，不调用 API")
        return

    # 检查是否有值得蒸馏的模式
    total_patterns = (len(patterns["repeated_findings"]) +
                      len(patterns["escalation_chains"]) +
                      len(patterns["monitoring_fatigue"]))
    if total_patterns == 0:
        print("\n✅ 没有需要蒸馏的新模式")
        return

    # Step 3: LLM 蒸馏（Haiku，~$0.01）
    existing = load_existing_skills()
    print(f"\n🧠 已有 {len(existing)} 个 skill，开始蒸馏...")
    new_skills = distill_with_llm(patterns, existing)

    if not new_skills:
        print("✅ 没有新 skill 需要添加（现有 skill 已覆盖）")
        return

    print(f"\n🆕 蒸馏出 {len(new_skills)} 个新 skill:")
    next_id = get_next_skill_id()
    for j, s in enumerate(new_skills):
        cat = "🌐" if s.get("category") == "general" else "🎯"
        print(f"  {cat} skill_{next_id + j:03d}: {s['title']}")
        print(f"     规则: {s['rule'][:80]}...")
        print()

    # Step 4: 写入
    if apply:
        count = apply_skills(new_skills)
        print(f"✅ 已写入 {count} 个新 skill 到 MASONHUB.md")
    else:
        print("💡 预览模式。用 --apply 写入 MASONHUB.md")


if __name__ == "__main__":
    main()
