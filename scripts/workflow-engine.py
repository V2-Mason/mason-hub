#!/usr/bin/env python3
"""
workflow-engine.py — v1.1 §7 Workflow Engine

管理 workflow 实例的生命周期：创建、推进、审批、恢复。

用法:
  python3 workflow-engine.py create <template> [--input key=value ...]
  python3 workflow-engine.py advance <workflow_id>
  python3 workflow-engine.py approve <workflow_id> <step_id>
  python3 workflow-engine.py reject <workflow_id> <step_id> [--reason "..."]
  python3 workflow-engine.py status [workflow_id]
  python3 workflow-engine.py list
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HUB_DIR = Path(os.environ.get("HUB_DIR", os.path.expanduser("~/mason-hub")))
TEMPLATES_DIR = HUB_DIR / "shared" / "workflows"
WORKFLOWS_DIR = HUB_DIR / "data" / "workflows"
EMIT_EVENT = HUB_DIR / "scripts" / "emit_event.sh"
RUN_AGENT = HUB_DIR / "scripts" / "run-agent.sh"


def parse_yaml_simple(filepath: Path) -> dict:
    """简单 YAML 解析（不依赖 PyYAML）"""
    result = {"steps": []}
    current_step = None
    in_steps = False

    for line in filepath.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- id:") and in_steps:
            if current_step:
                result["steps"].append(current_step)
            current_step = {"id": stripped.split(":", 1)[1].strip()}
            continue

        if ":" in stripped and not stripped.startswith("-"):
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if key == "steps":
                in_steps = True
                continue

            if in_steps and current_step is not None:
                if val:
                    current_step[key] = val
            elif not in_steps:
                if val:
                    result[key] = val

    if current_step:
        result["steps"].append(current_step)

    return result


def create_workflow(template_name: str, inputs: dict) -> str:
    """创建新 workflow 实例"""
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        # 尝试加 .yaml
        template_path = TEMPLATES_DIR / f"{template_name}.yaml"
    if not template_path.exists():
        print(f"❌ Template not found: {template_name}")
        sys.exit(1)

    template = parse_yaml_simple(template_path)
    now = datetime.utcnow()

    # 生成 workflow ID
    existing = list(WORKFLOWS_DIR.glob(f"wf-{now.strftime('%Y%m%d')}-*"))
    seq = len(existing) + 1
    wf_id = f"wf-{now.strftime('%Y%m%d')}-{template.get('id', 'unknown')}-{seq:03d}"

    # 创建目录
    wf_dir = WORKFLOWS_DIR / wf_id
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "artifacts").mkdir(exist_ok=True)

    # 构建 state
    steps_state = {}
    for step in template.get("steps", []):
        steps_state[step["id"]] = {
            "status": "pending",
            "instance_id": "",
            "output": "",
            "started_at": "",
            "completed_at": "",
            "error": "",
        }

    state = {
        "workflow_id": wf_id,
        "template": template_name,
        "account": template.get("account", "surenxuan"),
        "status": "pending",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "current_step": template["steps"][0]["id"] if template.get("steps") else "",
        "trigger_input": inputs,
        "steps": steps_state,
    }

    state_file = wf_dir / "state.yaml"
    _write_state(state_file, state)

    print(f"✅ Workflow created: {wf_id}")
    print(f"   Template: {template_name}")
    print(f"   Steps: {len(template.get('steps', []))}")
    print(f"   First step: {state['current_step']}")
    return wf_id


def advance_workflow(wf_id: str) -> bool:
    """推进 workflow 到下一个可执行步骤"""
    wf_dir = WORKFLOWS_DIR / wf_id
    state_file = wf_dir / "state.yaml"
    if not state_file.exists():
        print(f"❌ Workflow not found: {wf_id}")
        return False

    state = _read_state(state_file)
    if state["status"] in ("completed", "failed"):
        print(f"⏹ Workflow {wf_id} already {state['status']}")
        return False

    template_name = state["template"]
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        template_path = TEMPLATES_DIR / f"{template_name}.yaml"
    template = parse_yaml_simple(template_path)

    # 找到当前步骤
    current = state.get("current_step", "")
    steps = template.get("steps", [])
    step_ids = [s["id"] for s in steps]

    if not current or current not in step_ids:
        print(f"❌ Invalid current step: {current}")
        return False

    step_idx = step_ids.index(current)
    step_def = steps[step_idx]
    step_state = state["steps"].get(current, {})

    # 检查是否需要审批
    if step_state.get("status") == "awaiting_approval":
        print(f"⏸ Step {current} awaiting approval")
        return False

    # 检查当前步骤是否已完成
    if step_state.get("status") == "done":
        # 推进到下一步
        if step_idx + 1 < len(steps):
            next_step = steps[step_idx + 1]
            state["current_step"] = next_step["id"]
            state["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            _write_state(state_file, state)
            print(f"➡️ Advanced to step: {next_step['id']}")
            # 递归推进（如果下一步可以自动执行）
            return advance_workflow(wf_id)
        else:
            # 所有步骤完成
            state["status"] = "completed"
            state["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            _write_state(state_file, state)
            print(f"✅ Workflow {wf_id} completed!")
            _emit("workflow-complete", wf_id, "ok", 1,
                   {"workflow_id": wf_id, "status": "completed"})
            return True

    # 执行当前步骤
    if step_state.get("status") in ("pending", "failed"):
        print(f"🚀 Executing step: {current} (role: {step_def.get('role', '?')})")

        role = step_def.get("role", "")
        task = step_def.get("task", "")
        # v2 优先目录格式，fallback config.md
        identity_path = f"agents/{role}/identity.md"
        if os.path.exists(identity_path):
            config_path = f"agents/{role}/"
        else:
            config_path = f"agents/{role}/config.md"

        # 更新状态
        state["status"] = "in_progress"
        state["steps"][current]["status"] = "in_progress"
        state["steps"][current]["started_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        state["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_state(state_file, state)

        # 构建任务描述（注入上游 artifact 路径）
        input_from = step_def.get("input_from", "")
        if input_from:
            artifacts_info = []
            for ref in input_from.strip("[]").split(","):
                ref = ref.strip()
                # ref 格式: step_id.output_artifact
                parts = ref.split(".")
                if len(parts) >= 1:
                    ref_step = parts[0]
                    ref_output = state["steps"].get(ref_step, {}).get("output", "")
                    if ref_output:
                        artifacts_info.append(f"输入文件: {ref_output}")
            if artifacts_info:
                task += "\n\n## 上游产出\n" + "\n".join(artifacts_info)

        task = f"[Workflow {wf_id} / Step {current}]\n\n{task}"

        # 输出 artifact 路径
        output_artifact = step_def.get("output_artifact", "")
        if output_artifact:
            artifact_path = str(wf_dir / "artifacts" / output_artifact)
            task += f"\n\n## 输出要求\n结果写入: {artifact_path}"

        # 启动 agent（非阻塞）
        timeout = int(step_def.get("timeout", 600))
        print(f"   Task: {task[:100]}...")
        print(f"   Config: {config_path}")
        print(f"   Timeout: {timeout}s")

        # 标记：如果需要审批，步骤完成后不自动推进
        if step_def.get("requires_approval") == "true":
            print(f"   ⚠️ This step requires approval after completion")

        _emit("workflow-step-start", role, "ok", 0,
              {"workflow_id": wf_id, "step_id": current, "role": role})
        return True

    return False


def approve_step(wf_id: str, step_id: str):
    """审批通过某个步骤"""
    state_file = WORKFLOWS_DIR / wf_id / "state.yaml"
    if not state_file.exists():
        print(f"❌ Workflow not found: {wf_id}")
        return

    state = _read_state(state_file)
    if step_id not in state["steps"]:
        print(f"❌ Step not found: {step_id}")
        return

    state["steps"][step_id]["status"] = "done"
    state["steps"][step_id]["completed_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    state["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_state(state_file, state)

    print(f"✅ Step {step_id} approved")
    advance_workflow(wf_id)


def reject_step(wf_id: str, step_id: str, reason: str = ""):
    """拒绝某个步骤（会重新执行）"""
    state_file = WORKFLOWS_DIR / wf_id / "state.yaml"
    if not state_file.exists():
        print(f"❌ Workflow not found: {wf_id}")
        return

    state = _read_state(state_file)
    if step_id not in state["steps"]:
        print(f"❌ Step not found: {step_id}")
        return

    state["steps"][step_id]["status"] = "failed"
    state["steps"][step_id]["error"] = reason or "Rejected by human"
    state["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_state(state_file, state)

    print(f"❌ Step {step_id} rejected: {reason}")


def show_status(wf_id: str = ""):
    """显示 workflow 状态"""
    if wf_id:
        state_file = WORKFLOWS_DIR / wf_id / "state.yaml"
        if not state_file.exists():
            print(f"❌ Workflow not found: {wf_id}")
            return
        state = _read_state(state_file)
        print(f"Workflow: {state['workflow_id']}")
        print(f"Template: {state['template']}")
        print(f"Status: {state['status']}")
        print(f"Current: {state.get('current_step', 'N/A')}")
        print(f"Created: {state['created_at']}")
        print(f"Updated: {state['updated_at']}")
        print(f"\nSteps:")
        for sid, sdata in state.get("steps", {}).items():
            status = sdata.get("status", "?")
            emoji = {"pending": "⏳", "in_progress": "🔄", "done": "✅",
                     "failed": "❌", "awaiting_approval": "⏸", "skipped": "⏭"}.get(status, "?")
            print(f"  {emoji} {sid}: {status}")
    else:
        print("Active workflows:")
        if not WORKFLOWS_DIR.exists():
            print("  (none)")
            return
        for d in sorted(WORKFLOWS_DIR.iterdir()):
            if d.is_dir() and (d / "state.yaml").exists():
                state = _read_state(d / "state.yaml")
                print(f"  {state['workflow_id']} | {state['status']} | step: {state.get('current_step', '?')} | {state['template']}")


def _write_state(path: Path, state: dict):
    """写 state 为简单 YAML 格式"""
    lines = []
    for k, v in state.items():
        if k == "steps":
            lines.append("steps:")
            for sid, sdata in v.items():
                lines.append(f"  {sid}:")
                for sk, sv in sdata.items():
                    lines.append(f"    {sk}: {sv}")
        elif k == "trigger_input":
            lines.append(f"trigger_input: {json.dumps(v, ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {v}")
    path.write_text("\n".join(lines) + "\n")


def _read_state(path: Path) -> dict:
    """读 state YAML"""
    state = {"steps": {}}
    current_step = None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ":" not in stripped:
            continue

        if indent == 0:
            key, val = stripped.split(":", 1)
            key, val = key.strip(), val.strip()
            if key == "steps":
                continue
            elif key == "trigger_input":
                try:
                    state[key] = json.loads(val)
                except (json.JSONDecodeError, Exception):
                    state[key] = val
            else:
                state[key] = val
        elif indent == 2 and ":" in stripped:
            key = stripped.rstrip(":")
            if not stripped.endswith(":"):
                k, v = stripped.split(":", 1)
                # This is a step with inline value - skip
                pass
            else:
                current_step = key
                state["steps"][current_step] = {}
        elif indent == 4 and current_step:
            key, val = stripped.split(":", 1)
            state["steps"][current_step][key.strip()] = val.strip()

    return state


def _emit(event: str, source: str, status: str, level: int, data: dict):
    """发射事件"""
    if EMIT_EVENT.exists():
        try:
            subprocess.run([str(EMIT_EVENT), event, source, status, str(level),
                           json.dumps(data, ensure_ascii=False)],
                          timeout=5, capture_output=True)
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create":
        template = sys.argv[2] if len(sys.argv) > 2 else ""
        inputs = {}
        for arg in sys.argv[3:]:
            if arg.startswith("--input") or "=" not in arg:
                continue
            k, v = arg.split("=", 1)
            inputs[k] = v
        create_workflow(template, inputs)

    elif cmd == "advance":
        wf_id = sys.argv[2] if len(sys.argv) > 2 else ""
        advance_workflow(wf_id)

    elif cmd == "approve":
        wf_id = sys.argv[2] if len(sys.argv) > 2 else ""
        step_id = sys.argv[3] if len(sys.argv) > 3 else ""
        approve_step(wf_id, step_id)

    elif cmd == "reject":
        wf_id = sys.argv[2] if len(sys.argv) > 2 else ""
        step_id = sys.argv[3] if len(sys.argv) > 3 else ""
        reason = ""
        if "--reason" in sys.argv:
            idx = sys.argv.index("--reason")
            reason = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        reject_step(wf_id, step_id, reason)

    elif cmd == "status":
        wf_id = sys.argv[2] if len(sys.argv) > 2 else ""
        show_status(wf_id)

    elif cmd == "list":
        show_status()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
