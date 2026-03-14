#!/usr/bin/env python3
"""protocol-check.py — 协议完整性与冲突检测

检查项：
1. 所有 YAML protocol 格式合法
2. 每个 protocol 有 id + version + type + description
3. config.md 引用的 protocol 存在且版本匹配
4. 无 trigger 冲突（同一 trigger 不同 action）

用法：
  python3 scripts/protocol-check.py
  python3 scripts/protocol-check.py --verbose
"""

import argparse
import os
import re
import sys
import yaml
from pathlib import Path
from collections import defaultdict

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
PROTOCOLS_DIR = HUB_DIR / "shared" / "protocols"
AGENTS_DIR = HUB_DIR / "agents"


def check_yaml_validity(verbose=False):
    """检查所有 YAML protocol 格式"""
    issues = []
    protocols = {}

    for f in sorted(PROTOCOLS_DIR.glob("**/*.yaml")):
        try:
            data = yaml.safe_load(f.read_text())
            if not isinstance(data, dict):
                issues.append(f"❌ {f.name}: 不是字典格式")
                continue

            # 检查必需字段
            required = ["id", "version", "type", "description"]
            missing = [k for k in required if k not in data]
            if missing:
                issues.append(f"⚠️ {f.name}: 缺少字段 {missing}")

            protocols[data.get("id", f.stem)] = {
                "file": str(f.relative_to(HUB_DIR)),
                "version": data.get("version", "?"),
                "type": data.get("type", "?"),
                "data": data,
            }

            if verbose:
                print(f"  ✅ {f.name} (v{data.get('version', '?')})")

        except yaml.YAMLError as e:
            issues.append(f"❌ {f.name}: YAML 解析错误 — {e}")

    return protocols, issues


def check_trigger_conflicts(protocols):
    """检查 trigger 冲突"""
    issues = []
    trigger_map = defaultdict(list)

    for pid, pinfo in protocols.items():
        triggers = pinfo["data"].get("triggers", [])
        for t in triggers:
            condition = t.get("condition", t.get("trigger", ""))
            action = t.get("action", "")
            if condition:
                trigger_map[condition].append({"protocol": pid, "action": action})

    for condition, entries in trigger_map.items():
        actions = set(e["action"] for e in entries)
        if len(actions) > 1:
            protocols_involved = [e["protocol"] for e in entries]
            issues.append(
                f"⚠️ Trigger 冲突: '{condition}' 在 {protocols_involved} 中定义了不同 action: {actions}"
            )

    return issues


def check_config_references(protocols, verbose=False):
    """检查 config.md 引用的 protocol 是否存在"""
    issues = []
    protocol_ids = set(protocols.keys())

    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        config_path = agent_dir / "config.md"
        if not config_path.exists():
            continue

        content = config_path.read_text()
        # 查找 protocol 引用：shared/protocols/xxx.yaml 或 shared/protocols/xxx.md
        refs = re.findall(r'shared/protocols/(\S+?)(?:\.yaml|\.md)', content)
        for ref in refs:
            # 检查 YAML 版本是否存在
            yaml_path = PROTOCOLS_DIR / f"{ref}.yaml"
            md_path = PROTOCOLS_DIR / f"{ref}.md"
            if not yaml_path.exists() and not md_path.exists():
                issues.append(f"⚠️ {agent_dir.name}/config.md 引用 shared/protocols/{ref} 但文件不存在")

        # 检查版本引用（protocol: xxx@1.0 格式）
        version_refs = re.findall(r'protocol:\s*(\w+)@([\d.]+)', content)
        for pid, ver in version_refs:
            if pid in protocols:
                actual_ver = protocols[pid].get("version", "?")
                if actual_ver != ver:
                    issues.append(
                        f"⚠️ {agent_dir.name}/config.md 引用 {pid}@{ver} 但实际版本是 {actual_ver}"
                    )

    return issues


def check_md_without_yaml():
    """检查还有哪些 .md protocol 没有对应的 .yaml"""
    issues = []
    for md_file in sorted(PROTOCOLS_DIR.glob("*.md")):
        yaml_file = md_file.with_suffix(".yaml")
        if not yaml_file.exists():
            issues.append(f"ℹ️ {md_file.name} 尚未转为 YAML（保留作参考）")
    return issues


def main():
    parser = argparse.ArgumentParser(description="协议完整性检测")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--brief", action="store_true", help="只输出 pass/fail")
    args = parser.parse_args()

    if not args.brief:
        print("=== Protocol 完整性检查 ===\n")

    all_issues = []

    # 1. YAML 合法性 + 必需字段
    if not args.brief:
        print("1. YAML 格式检查:")
    protocols, issues = check_yaml_validity(args.verbose)
    all_issues.extend(issues)
    if not args.brief:
        print(f"   {len(protocols)} 个 protocol 已加载\n")

    # 2. Trigger 冲突
    if not args.brief:
        print("2. Trigger 冲突检查:")
    issues = check_trigger_conflicts(protocols)
    all_issues.extend(issues)
    if not args.brief:
        print(f"   {'无冲突' if not issues else f'{len(issues)} 个冲突'}\n")

    # 3. Config 引用检查
    if not args.brief:
        print("3. Config 引用检查:")
    issues = check_config_references(protocols, args.verbose)
    all_issues.extend(issues)
    if not args.brief:
        print(f"   {'引用完整' if not issues else f'{len(issues)} 个断裂引用'}\n")

    # 4. MD 未迁移检查
    if not args.brief:
        print("4. MD→YAML 迁移状态:")
    issues = check_md_without_yaml()
    all_issues.extend(issues)

    # 输出
    if all_issues:
        if not args.brief:
            print("\n--- 发现的问题 ---")
        for issue in all_issues:
            print(f"  {issue}")

    errors = sum(1 for i in all_issues if i.startswith("❌"))
    warnings = sum(1 for i in all_issues if i.startswith("⚠️"))
    infos = sum(1 for i in all_issues if i.startswith("ℹ️"))

    if not args.brief:
        print(f"\n=== 结果: {errors} 错误, {warnings} 警告, {infos} 信息 ===")

    if args.brief:
        if errors > 0:
            print(f"FAIL: {errors} errors, {warnings} warnings")
            sys.exit(1)
        elif warnings > 0:
            print(f"WARN: {warnings} warnings")
        else:
            print("PASS")

    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
