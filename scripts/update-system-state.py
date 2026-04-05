#!/usr/bin/env python3
"""update-system-state.py — Auto-update system-state.yaml based on session activity.

Called by Stop hook at end of each session.
Reads git diff to infer what changed, updates relevant fields.
Never overwrites Mason's manual edits to blockers/waiting_for.
"""

import subprocess
import yaml
import sys
from datetime import datetime, date
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "system-state.yaml"
TODAY = date.today().isoformat()


def run(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=STATE_FILE.parent)
    return result.stdout.strip()


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE) as f:
        return yaml.safe_load(f) or {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        yaml.dump(state, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_session_changes() -> dict:
    """Analyze git diff to determine what areas were touched."""
    diff = run("git diff --name-only HEAD~1 HEAD 2>/dev/null") or run("git diff --name-only 2>/dev/null")
    files = [f for f in diff.split("\n") if f.strip()]

    areas = {
        "infrastructure": False,  # scripts/, .claude/, kernel/
        "data": False,            # data/, intel/
        "content": False,         # socialmesh references, video pipeline
        "commerce": False,        # surenxuan references, store API
        "agents": False,          # .claude/agents/
        "state": False,           # system-state.yaml itself
    }

    for f in files:
        if any(f.startswith(p) for p in ["scripts/", ".claude/", "kernel/"]):
            areas["infrastructure"] = True
        if any(f.startswith(p) for p in ["data/", "intel/"]):
            areas["data"] = True
        if "socialmesh" in f or "video" in f or "content" in f:
            areas["content"] = True
        if "surenxuan" in f or "store" in f or "shop" in f:
            areas["commerce"] = True
        if ".claude/agents/" in f:
            areas["agents"] = True
        if f == "system-state.yaml":
            areas["state"] = True

    return {"files": files, "areas": areas}


def check_stale_actions(state: dict) -> list:
    """Return list of stale next_actions exceeding threshold."""
    threshold = state.get("rules", {}).get("stale_threshold_days", 7)
    alerts = []

    for name, line in state.get("lines", {}).items():
        action_since = line.get("next_action_since")
        action = line.get("next_action")
        if action and action_since:
            try:
                since_date = date.fromisoformat(action_since)
                days = (date.today() - since_date).days
                if days > threshold:
                    alerts.append(f"{name}: '{action}' stale for {days} days (threshold: {threshold})")
            except ValueError:
                pass

    return alerts


def check_stale_blockers(state: dict) -> list:
    """Return list of external blockers exceeding review threshold."""
    threshold = state.get("rules", {}).get("blocker_review_days", 14)
    alerts = []

    for item in state.get("waiting_for", []):
        since = item.get("since")
        if since:
            try:
                since_date = date.fromisoformat(since)
                days = (date.today() - since_date).days
                if days > threshold:
                    alerts.append(f"{item['id']}: waiting {days} days — {item.get('desc', '')}")
            except ValueError:
                pass

    return alerts


def update_agent_usage(state: dict, changes: dict):
    """If agent definition files were touched, note it."""
    if changes["areas"]["agents"]:
        state.setdefault("agents", {})
        # Don't overwrite specific fields, just mark activity
        for f in changes["files"]:
            if ".claude/agents/" in f:
                agent_name = Path(f).stem
                if agent_name in state["agents"]:
                    state["agents"][agent_name]["last_used"] = TODAY


def main():
    state = load_state()
    if not state:
        print("system-state.yaml not found or empty, skipping update")
        return

    changes = get_session_changes()
    state["last_updated"] = TODAY

    # Update agent usage tracking
    update_agent_usage(state, changes)

    # Check for stale items
    stale_actions = check_stale_actions(state)
    stale_blockers = check_stale_blockers(state)

    # Save updated state
    save_state(state)

    # Output alerts (captured by hook, shown in session)
    if stale_actions:
        print("STALE ACTIONS:")
        for a in stale_actions:
            print(f"  ! {a}")

    if stale_blockers:
        print("STALE BLOCKERS (review needed):")
        for b in stale_blockers:
            print(f"  ? {b}")

    file_count = len(changes["files"])
    active_areas = [k for k, v in changes["areas"].items() if v]
    if active_areas:
        print(f"Session touched {file_count} files in: {', '.join(active_areas)}")
    else:
        print(f"Session touched {file_count} files (no recognized area)")


if __name__ == "__main__":
    main()
