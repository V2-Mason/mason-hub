#!/usr/bin/env python3
"""critic.py — 多维评估引擎（E2E + Component Level）

评估层次：
  E2E: 整体产出是否满足原始目标
  Component: 每个子步骤的质量

评估维度（可扩展）：
  correctness: 正确性（结果是否对）
  completeness: 完整性（是否遗漏）
  consistency: 一致性（品牌/风格/格式）
  efficiency: 效率（token/时间消耗合理性）
  safety: 安全性（无敏感数据泄露/无破坏性操作）

多模态支持：
  text → Claude (默认)
  image/video → Gemini (标记 needs_multimodal)
  reasoning → 标记 needs_reflection

用法：
  # E2E 评估
  python3 skills/task-engine/critic.py e2e \
    --task-file data/tasks/task_xxx.yaml \
    --output-file path/to/output

  # Component 评估
  python3 skills/task-engine/critic.py component \
    --task-file data/tasks/task_xxx.yaml \
    --step 2 \
    --artifact path/to/step_output

  # 自定义评估标准
  python3 skills/task-engine/critic.py e2e \
    --task-file data/tasks/task_xxx.yaml \
    --criteria "品牌一致性,内容深度,SEO 优化"
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))

# 默认评估维度
DEFAULT_DIMENSIONS = {
    "correctness": {
        "weight": 0.3,
        "description": "结果是否正确完成了任务要求",
        "checks": [
            "输出格式是否符合要求",
            "核心功能/内容是否到位",
            "数据/引用是否准确",
        ],
    },
    "completeness": {
        "weight": 0.25,
        "description": "是否遗漏了任务的某些部分",
        "checks": [
            "所有子任务是否都已完成",
            "边界情况是否考虑",
            "验收标准是否全部满足",
        ],
    },
    "consistency": {
        "weight": 0.2,
        "description": "风格/格式/品牌是否一致",
        "checks": [
            "命名约定是否统一",
            "输出格式是否与系统其他部分一致",
            "品牌调性是否符合（如适用）",
        ],
    },
    "efficiency": {
        "weight": 0.15,
        "description": "是否用合理的资源完成",
        "checks": [
            "代码行数/文件数是否合理",
            "是否有不必要的复杂性",
            "token 消耗是否在预算内",
        ],
    },
    "safety": {
        "weight": 0.1,
        "description": "是否引入安全风险",
        "checks": [
            "是否涉及敏感数据",
            "是否有破坏性操作",
            "是否符合权限边界",
        ],
    },
}

# 按任务类型扩展的维度
TASK_TYPE_DIMENSIONS = {
    "content": {
        "brand_voice": {
            "weight": 0.2,
            "description": "品牌调性和声音一致性",
            "checks": ["是否符合 brief.md 的调性要求", "是否用了禁用词", "是否过于 AI 感"],
        },
        "engagement": {
            "weight": 0.15,
            "description": "内容的吸引力和互动潜力",
            "checks": ["hook 是否有力", "标题是否有搜索价值", "CTA 是否清晰"],
        },
    },
    "code": {
        "testability": {
            "weight": 0.15,
            "description": "代码是否可测试",
            "checks": ["是否有对应测试", "函数是否可独立测试", "边界条件是否覆盖"],
        },
    },
    "analysis": {
        "actionability": {
            "weight": 0.2,
            "description": "分析结论是否可操作",
            "checks": ["是否有具体建议", "建议是否可执行", "是否区分了事实和推断"],
        },
    },
}


def detect_task_type(task: dict) -> str:
    """从 task 描述推断类型"""
    desc = task.get("description", "").lower()
    if any(kw in desc for kw in ["内容", "视频", "文案", "帖子"]):
        return "content"
    elif any(kw in desc for kw in ["代码", "修复", "实现", "开发", "脚本"]):
        return "code"
    elif any(kw in desc for kw in ["分析", "报告", "评估", "审计"]):
        return "analysis"
    return "general"


def detect_modality(artifact_path: str) -> str:
    """检测产出物的模态"""
    if not artifact_path:
        return "text"
    ext = Path(artifact_path).suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return "image"
    elif ext in (".mp4", ".avi", ".mov", ".webm"):
        return "video"
    return "text"


def build_dimensions(task: dict, custom_criteria: list = None) -> dict:
    """构建评估维度集（默认 + 任务类型扩展 + 自定义）"""
    dims = dict(DEFAULT_DIMENSIONS)

    # 按任务类型扩展
    task_type = detect_task_type(task)
    if task_type in TASK_TYPE_DIMENSIONS:
        dims.update(TASK_TYPE_DIMENSIONS[task_type])
        # 重新归一化权重
        total_weight = sum(d["weight"] for d in dims.values())
        for d in dims.values():
            d["weight"] = round(d["weight"] / total_weight, 3)

    # 自定义标准
    if custom_criteria:
        for crit in custom_criteria:
            dims[crit.lower().replace(" ", "_")] = {
                "weight": 0.1,
                "description": crit,
                "checks": [f"是否满足: {crit}"],
            }
        # 重新归一化
        total_weight = sum(d["weight"] for d in dims.values())
        for d in dims.values():
            d["weight"] = round(d["weight"] / total_weight, 3)

    return dims


def evaluate_rule_based(artifact_path: str, dimensions: dict, task: dict) -> dict:
    """基于规则的评估（不调 LLM，用文件存在性和大小等启发式）"""
    scores = {}

    for dim_name, dim_info in dimensions.items():
        # 默认给 0.5（中性分，表示"无法自动判断"）
        score = 0.5
        notes = []

        if dim_name == "correctness":
            if artifact_path and Path(artifact_path).exists():
                size = Path(artifact_path).stat().st_size
                if size > 100:
                    score = 0.7
                    notes.append(f"产出物存在且有内容 ({size} bytes)")
                else:
                    score = 0.3
                    notes.append(f"产出物过小 ({size} bytes)")
            elif task.get("status") == "done":
                score = 0.6
                notes.append("任务标记完成但无产出文件")
            else:
                score = 0.2
                notes.append("任务未完成或无产出")

        elif dim_name == "completeness":
            criteria = task.get("acceptance_criteria", "")
            if criteria:
                score = 0.6
                notes.append(f"有验收标准: {criteria[:50]}")
            else:
                score = 0.4
                notes.append("无验收标准，无法判断完整性")

        elif dim_name == "efficiency":
            cost = task.get("cost_usd", 0)
            duration = task.get("duration_seconds", 0)
            if isinstance(cost, (int, float)) and cost > 0:
                if cost < 0.5:
                    score = 0.9
                    notes.append(f"成本合理 (${cost:.2f})")
                elif cost < 2.0:
                    score = 0.6
                    notes.append(f"成本偏高 (${cost:.2f})")
                else:
                    score = 0.3
                    notes.append(f"成本过高 (${cost:.2f})")

        elif dim_name == "safety":
            # 检查产出物是否包含敏感信息
            score = 0.8  # 默认安全
            if artifact_path and Path(artifact_path).exists():
                try:
                    content = Path(artifact_path).read_text(errors="replace")[:5000]
                    sensitive_patterns = ["password", "secret", "api_key", "token=", "credentials"]
                    if any(p in content.lower() for p in sensitive_patterns):
                        score = 0.2
                        notes.append("检测到可能的敏感信息")
                except Exception:
                    pass

        scores[dim_name] = {
            "score": score,
            "weight": dim_info["weight"],
            "weighted_score": round(score * dim_info["weight"], 3),
            "notes": notes,
            "auto_evaluated": True,
            "needs_llm": score == 0.5,  # 中性分表示需要 LLM 深度评估
        }

    # 计算加权总分
    total = sum(s["weighted_score"] for s in scores.values())
    needs_multimodal = detect_modality(artifact_path or "") != "text"

    return {
        "total_score": round(total, 3),
        "max_possible": 1.0,
        "pass": total >= 0.6,
        "needs_llm_review": any(s["needs_llm"] for s in scores.values()),
        "needs_multimodal": needs_multimodal,
        "dimensions": scores,
    }


def e2e_evaluate(task_file: str, output_file: str = "", criteria: list = None) -> dict:
    """E2E 整体评估"""
    with open(task_file) as f:
        task = yaml.safe_load(f)

    dimensions = build_dimensions(task, criteria)
    eval_result = evaluate_rule_based(output_file, dimensions, task)

    return {
        "type": "e2e",
        "task_id": task.get("id", "?"),
        "task_type": detect_task_type(task),
        "generated_at": datetime.now().isoformat(),
        "evaluation": eval_result,
    }


def component_evaluate(task_file: str, step: int, artifact: str = "",
                       criteria: list = None) -> dict:
    """Component Level 单步评估"""
    with open(task_file) as f:
        task = yaml.safe_load(f)

    dimensions = build_dimensions(task, criteria)
    eval_result = evaluate_rule_based(artifact, dimensions, task)

    return {
        "type": "component",
        "task_id": task.get("id", "?"),
        "step": step,
        "generated_at": datetime.now().isoformat(),
        "evaluation": eval_result,
    }


def main():
    parser = argparse.ArgumentParser(description="多维评估引擎")
    subparsers = parser.add_subparsers(dest="command")

    e2e_parser = subparsers.add_parser("e2e", help="E2E 整体评估")
    e2e_parser.add_argument("--task-file", required=True)
    e2e_parser.add_argument("--output-file", default="")
    e2e_parser.add_argument("--criteria", help="逗号分隔的自定义评估标准")

    comp_parser = subparsers.add_parser("component", help="Component 单步评估")
    comp_parser.add_argument("--task-file", required=True)
    comp_parser.add_argument("--step", type=int, required=True)
    comp_parser.add_argument("--artifact", default="")
    comp_parser.add_argument("--criteria", help="逗号分隔的自定义评估标准")

    dims_parser = subparsers.add_parser("dimensions", help="显示评估维度")
    dims_parser.add_argument("--task-type", default="general")

    args = parser.parse_args()

    if args.command == "e2e":
        criteria = args.criteria.split(",") if args.criteria else None
        result = e2e_evaluate(args.task_file, args.output_file, criteria)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "component":
        criteria = args.criteria.split(",") if args.criteria else None
        result = component_evaluate(args.task_file, args.step, args.artifact, criteria)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "dimensions":
        fake_task = {"description": f"dummy {args.task_type} task"}
        dims = build_dimensions(fake_task)
        for name, info in dims.items():
            print(f"  {name} (weight: {info['weight']}): {info['description']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
