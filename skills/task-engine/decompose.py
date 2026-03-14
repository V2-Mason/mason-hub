#!/usr/bin/env python3
"""decompose.py — 递归任务拆解 + 动态可行性评估

流程：
  任务 → 拆解为子任务 → 对每个子任务评估可行性
  → 不通过的继续拆 → 评估标准随拆解动态增长
  → 直到所有叶子节点评估通过

评估维度：
  - can_llm_do: LLM 能否完成（需要外部 API/硬件/人工的不行）
  - has_skill: 是否有现成 skill 可用
  - model_fit: 需要什么模型（text→Claude, vision→Gemini, reasoning→reflection）
  - granularity: 是否足够原子化（一步能完成）
  - testable: 是否有明确的验收标准

用法：
  python3 skills/task-engine/decompose.py "素仁轩需要一条新的 XHS 视频"
  python3 skills/task-engine/decompose.py "优化 Agent 记忆注入效率" --max-depth 4
  python3 skills/task-engine/decompose.py --from-file task_description.txt
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))


def load_capability_index():
    """加载能力索引，用于评估 has_skill"""
    cap_file = HUB_DIR / "data" / "roster" / "capability_index.json"
    if cap_file.exists():
        with open(cap_file) as f:
            return json.load(f)
    return {"capabilities": {}, "agents": {}}


def load_skill_registry():
    """加载 skill 注册表，用于评估是否有现成工具"""
    reg_file = HUB_DIR / "skills" / "registry.yaml"
    if reg_file.exists():
        with open(reg_file) as f:
            return yaml.safe_load(f) or {}
    return {}


def evaluate_subtask(subtask: dict, cap_index: dict, skills: dict) -> dict:
    """评估单个子任务的可行性（规则引擎，不调 LLM）"""
    desc = subtask.get("description", "").lower()
    eval_result = {
        "subtask_id": subtask["id"],
        "description": subtask["description"],
        "scores": {},
        "pass": True,
        "issues": [],
        "suggestions": [],
    }

    # 1. can_llm_do: 检查是否需要外部依赖
    external_markers = [
        ("需要人工", "human_required"),
        ("手动", "manual_step"),
        ("登录", "auth_required"),
        ("购买", "purchase_required"),
        ("注册", "registration_required"),
        ("硬件", "hardware_required"),
        ("手机", "phone_required"),
    ]
    can_llm = True
    for marker, reason in external_markers:
        if marker in desc:
            can_llm = False
            eval_result["issues"].append(f"需要外部操作: {reason}")

    eval_result["scores"]["can_llm_do"] = 1.0 if can_llm else 0.0

    # 2. has_skill: 检查 skill registry 匹配
    skill_match = None
    for skill_name, skill_info in skills.items():
        if isinstance(skill_info, dict):
            skill_desc = skill_info.get("description", "").lower()
            # 简单关键词匹配
            desc_words = set(desc.replace("，", " ").replace("、", " ").split())
            skill_words = set(skill_desc.replace("，", " ").replace("、", " ").split())
            overlap = desc_words & skill_words
            if len(overlap) >= 2:
                skill_match = skill_name
                break

    eval_result["scores"]["has_skill"] = 1.0 if skill_match else 0.3
    if skill_match:
        eval_result["suggestions"].append(f"可用 skill: {skill_match}")
    else:
        eval_result["suggestions"].append("无现成 skill，可能需要自建或分解")

    # 3. model_fit: 判断需要什么模型
    if any(kw in desc for kw in ["图片", "视频", "图像", "视觉", "截图"]):
        model = "gemini"
        eval_result["suggestions"].append("多模态任务，建议用 Gemini")
    elif any(kw in desc for kw in ["推理", "为什么", "分析原因", "归因", "反思"]):
        model = "reasoning"
        eval_result["suggestions"].append("需要深度推理，建议 Reflection 步骤")
    else:
        model = "claude"
    eval_result["scores"]["model_fit"] = 1.0
    eval_result["model"] = model

    # 4. granularity: 是否原子化
    complexity_markers = ["并且", "同时", "以及", "然后", "接着", "之后再"]
    compound = sum(1 for m in complexity_markers if m in desc)
    if compound >= 2:
        eval_result["scores"]["granularity"] = 0.3
        eval_result["issues"].append(f"复合任务（{compound} 个连接词），需要继续拆解")
        eval_result["pass"] = False
    elif compound == 1:
        eval_result["scores"]["granularity"] = 0.6
        eval_result["issues"].append("可能需要拆分为两步")
    else:
        eval_result["scores"]["granularity"] = 1.0

    # 5. testable: 是否有明确验收标准
    testable_markers = ["验证", "检查", "确认", "输出", "生成", "创建", "文件"]
    has_testable = any(m in desc for m in testable_markers)
    eval_result["scores"]["testable"] = 1.0 if has_testable else 0.4
    if not has_testable:
        eval_result["issues"].append("缺乏明确的验收标准")

    # 综合判断
    avg_score = sum(eval_result["scores"].values()) / len(eval_result["scores"])
    eval_result["avg_score"] = round(avg_score, 2)
    if avg_score < 0.6 or not can_llm:
        eval_result["pass"] = False

    return eval_result


def decompose_task(description: str, task_id: str = "root", depth: int = 0,
                   max_depth: int = 3, cap_index: dict = None, skills: dict = None) -> dict:
    """递归拆解任务"""
    if cap_index is None:
        cap_index = load_capability_index()
    if skills is None:
        skills = load_skill_registry()

    node = {
        "id": task_id,
        "description": description,
        "depth": depth,
        "subtasks": [],
        "evaluation": None,
        "status": "pending",
    }

    # 先评估当前任务
    eval_result = evaluate_subtask({"id": task_id, "description": description}, cap_index, skills)
    node["evaluation"] = eval_result

    if eval_result["pass"]:
        node["status"] = "ready"  # 可以直接执行
        return node

    if depth >= max_depth:
        node["status"] = "needs_human"  # 达到最大深度仍未通过
        node["evaluation"]["issues"].append(f"达到最大拆解深度 {max_depth}，需要人工判断")
        return node

    # 不通过 → 尝试拆解
    # 基于规则的简单拆解（生产环境应该用 LLM）
    subtask_descriptions = rule_based_decompose(description, eval_result)

    if not subtask_descriptions:
        node["status"] = "needs_human"
        return node

    for i, sub_desc in enumerate(subtask_descriptions, 1):
        sub_id = f"{task_id}.{i}"
        sub_node = decompose_task(
            sub_desc, sub_id, depth + 1, max_depth, cap_index, skills
        )
        node["subtasks"].append(sub_node)

    # 检查所有子任务是否都通过
    all_ready = all(
        s["status"] == "ready" for s in node["subtasks"]
    )
    node["status"] = "decomposed" if all_ready else "partial"

    return node


def rule_based_decompose(description: str, eval_result: dict) -> list:
    """基于规则的任务拆解（简单版）"""
    subtasks = []

    # 按连接词拆分
    for sep in ["并且", "同时", "以及", "然后", "接着", "之后再"]:
        if sep in description:
            parts = description.split(sep, 1)
            subtasks = [p.strip() for p in parts if p.strip()]
            break

    # 如果没有连接词但 granularity 不够，按模式拆
    if not subtasks:
        if "分析" in description and "报告" in description:
            subtasks = [
                f"数据收集：{description.split('分析')[0]}的数据",
                f"分析：对收集的数据进行分析",
                f"报告：生成分析报告",
            ]
        elif "视频" in description:
            subtasks = [
                f"脚本：为{description}写分镜脚本",
                f"素材：准备视频所需的图片和文案素材",
                f"生成：使用视频工具生成视频",
                f"审核：检查视频质量和品牌一致性",
            ]
        elif "部署" in description:
            subtasks = [
                f"验证：检查{description}的前置条件",
                f"执行：{description}",
                f"验证：确认部署成功",
            ]

    return subtasks


def count_nodes(tree: dict) -> dict:
    """统计拆解树的节点数"""
    stats = {"total": 0, "ready": 0, "needs_human": 0, "partial": 0}

    def walk(node):
        stats["total"] += 1
        if node["status"] == "ready":
            stats["ready"] += 1
        elif node["status"] == "needs_human":
            stats["needs_human"] += 1
        elif node["status"] == "partial":
            stats["partial"] += 1
        for sub in node.get("subtasks", []):
            walk(sub)

    walk(tree)
    return stats


def print_tree(node: dict, indent: int = 0):
    """打印拆解树"""
    prefix = "  " * indent
    status_icon = {
        "ready": "✅", "decomposed": "📦",
        "partial": "⚠️", "needs_human": "🔴", "pending": "⏳"
    }
    icon = status_icon.get(node["status"], "?")
    score = node["evaluation"]["avg_score"] if node["evaluation"] else 0

    print(f"{prefix}{icon} [{node['id']}] {node['description'][:60]} (score: {score})")

    if node["evaluation"] and node["evaluation"]["issues"]:
        for issue in node["evaluation"]["issues"]:
            print(f"{prefix}   ⚡ {issue}")
    if node["evaluation"] and node["evaluation"]["suggestions"]:
        for sug in node["evaluation"]["suggestions"]:
            print(f"{prefix}   💡 {sug}")

    for sub in node.get("subtasks", []):
        print_tree(sub, indent + 1)


def main():
    parser = argparse.ArgumentParser(description="递归任务拆解 + 动态评估")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--from-file", help="从文件读取任务描述")
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--format", default="tree", choices=["tree", "json"])
    args = parser.parse_args()

    if args.from_file:
        with open(args.from_file) as f:
            task_desc = f.read().strip()
    elif args.task:
        task_desc = args.task
    else:
        parser.print_help()
        sys.exit(1)

    tree = decompose_task(task_desc, max_depth=args.max_depth)
    stats = count_nodes(tree)

    if args.format == "json":
        output = {
            "generated_at": datetime.now().isoformat(),
            "task": task_desc,
            "stats": stats,
            "tree": tree,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"=== 任务拆解 (max_depth={args.max_depth}) ===\n")
        print_tree(tree)
        print(f"\n--- 统计: {stats['total']} 节点, {stats['ready']} 就绪, {stats['needs_human']} 需人工 ---")


if __name__ == "__main__":
    main()
