#!/usr/bin/env python3
"""build-capability-index.py — 从 agents.yaml + identity.md/soul.md 生成能力索引

输出 data/roster/capability_index.json：
{
  "capabilities": {
    "python": ["EMP_0002", "EMP_0005", "EMP_0009", "EMP_0014"],
    "xhs": ["EMP_0008", "EMP_0010", "EMP_0013"],
    ...
  },
  "agents": {
    "EMP_0002": {"name": "Platform Dev", "capabilities": ["python", "bash", "infrastructure", ...]},
    ...
  }
}

用法：
  python3 scripts/roster/build-capability-index.py
  python3 scripts/roster/build-capability-index.py --query python
"""

import argparse
import json
import os
import re
import yaml
from collections import defaultdict
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
AGENTS_YAML = HUB_DIR / "docs" / "system" / "agents.yaml"
AGENTS_DIR = HUB_DIR / "agents"
OUTPUT = HUB_DIR / "data" / "roster" / "capability_index.json"

# 能力关键词映射（从 config.md 的描述/职责中提取）
CAPABILITY_KEYWORDS = {
    "python": ["python", "py", "脚本", "script"],
    "bash": ["bash", "shell", "脚本", "cron", "systemd"],
    "frontend": ["react", "frontend", "前端", "jsx", "tsx", "css"],
    "backend": ["fastapi", "flask", "后端", "api", "endpoint"],
    "infrastructure": ["deploy", "部署", "服务器", "docker", "nginx", "systemd", "基础设施"],
    "xhs": ["小红书", "xhs", "红书", "rednote"],
    "content": ["内容", "content", "视频", "图文", "文案", "创作"],
    "data_analysis": ["分析", "数据", "analysis", "指标", "metrics", "漏斗"],
    "data_engineering": ["管道", "pipeline", "etl", "数据中台", "catalog", "sdk"],
    "ecommerce": ["电商", "选品", "库存", "订单", "售后", "店铺"],
    "marketing": ["营销", "推广", "投流", "种草", "策略"],
    "intelligence": ["情报", "scout", "趋势", "监控", "搜索"],
    "devops": ["运维", "sre", "监控", "告警", "health check"],
    "video": ["视频", "comfyui", "kling", "剪辑", "tts"],
    "coordination": ["调度", "协调", "管理", "分配", "汇报"],
}


def load_agents():
    """加载 agents.yaml"""
    with open(AGENTS_YAML) as f:
        data = yaml.safe_load(f)
    return [a for a in data["agents"] if a.get("status") != "deprecated"]


def extract_capabilities(agent_id: str) -> set:
    """从 identity.md + soul.md（v2）或 config.md（v1 fallback）提取能力关键词"""
    # v2: 合并 identity.md + soul.md 内容
    identity_path = AGENTS_DIR / agent_id / "identity.md"
    soul_path = AGENTS_DIR / agent_id / "soul.md"
    config_path = AGENTS_DIR / agent_id / "config.md"

    if identity_path.exists():
        content = identity_path.read_text(encoding="utf-8").lower()
        if soul_path.exists():
            content += "\n" + soul_path.read_text(encoding="utf-8").lower()
    elif config_path.exists():
        content = config_path.read_text(encoding="utf-8").lower()
    else:
        return set()
    caps = set()

    for cap, keywords in CAPABILITY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in content:
                caps.add(cap)
                break

    return caps


def build_index():
    """构建双向索引"""
    agents = load_agents()

    # agent → capabilities
    agent_caps = {}
    for agent in agents:
        aid = agent["id"]
        caps = extract_capabilities(aid)
        agent_caps[aid] = {
            "name": agent["name"],
            "domain": agent.get("domain", ""),
            "role": agent.get("role", ""),
            "can_own_tasks": agent.get("can_own_tasks", False),
            "capabilities": sorted(caps),
        }

    # capability → agents（反向索引）
    cap_agents = defaultdict(list)
    for aid, info in agent_caps.items():
        for cap in info["capabilities"]:
            if info["can_own_tasks"]:  # 只索引能执行任务的 agent
                cap_agents[cap].append(aid)

    index = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "total_agents": len(agent_caps),
        "total_capabilities": len(cap_agents),
        "capabilities": {k: sorted(v) for k, v in sorted(cap_agents.items())},
        "agents": agent_caps,
    }

    return index


def main():
    parser = argparse.ArgumentParser(description="构建能力索引")
    parser.add_argument("--query", help="查询某个能力可用的 agent")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    index = build_index()

    if args.query:
        # 查询模式
        cap = args.query.lower()
        agents = index["capabilities"].get(cap, [])
        if agents:
            print(f"能力 '{cap}' 可用 agent: {', '.join(agents)}")
            for aid in agents:
                info = index["agents"][aid]
                print(f"  {aid} ({info['name']}): {', '.join(info['capabilities'])}")
        else:
            # 模糊匹配
            matches = [k for k in index["capabilities"] if cap in k]
            if matches:
                print(f"未找到 '{cap}'，相近: {', '.join(matches)}")
            else:
                print(f"未找到 '{cap}' 相关能力")
    else:
        # 生成模式
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"✅ 能力索引已生成: {args.output}")
        print(f"   {index['total_agents']} 个 agent, {index['total_capabilities']} 个能力维度")
        for cap, agents in sorted(index["capabilities"].items()):
            print(f"   {cap}: {', '.join(agents)}")


if __name__ == "__main__":
    main()
