#!/usr/bin/env python3
"""
Setup script to register Manifest agents with OpenCode.

Writes opencode.json (tools: {write, edit, bash}). OpenCode may also load
.opencode/agents/*.json which use tools as string arrays. Schema compatibility
depends on OpenCode version; merge order (project vs .opencode) determines precedence.
- default_agent = orchestrator (orchestrator in agent switcher).
- Built-in agents build and plan are disabled.
- full-test is a subagent (callable by orchestrator only; not in switcher).
"""
import json
import sys
from pathlib import Path

ORCHESTRATOR_PROMPT = """You are the Manifest orchestrator agent. Your role is to:

1. Receive high-level mission descriptions from users
2. Break down missions into manageable tasks
3. Coordinate task execution through worker agents (planner, coder, test, review)
4. Manage sprints and task dependencies
5. Monitor blueprint synchronization and drift detection
6. Provide status updates and coordinate workflow

You have access to:
- Mission tree and task checklist
- Blueprint and architecture data
- Worker agents for task execution
- Sprint management
- Drift detection and blueprint synchronization

When a user provides a mission description, break it down into tasks and coordinate execution. Use the available tools and agents to accomplish the mission efficiently."""

ARCHITECT_PROMPT = """You are the Manifest Architect agent. Your role is to:

1. Ideate with the user: discuss product goals, requirements, and design
2. Write top-down design docs only: PRD (.manifest/prd.json) and blueprint (.manifest/blueprint_design.json)
3. You cannot edit project code, run terminal commands, create tasks, or spawn worker agents

You have access to: read-only tools and the architect tool (write_prd, write_architecture, ideate). Use the architect tool to persist top-down docs. Do not use task_management, worker_squad_spawn, edit, write, or bash."""

FULL_TEST_PROMPT = """You are the Manifest full-test (E2E) agent. Your role is to:

1. Run project- and sprint-wide end-to-end and integration tests
2. Execute test suites (pytest, etc.) for the whole scope
3. Report test results and failures
4. Work independently of the Worker Squad workflow; triggered by user or orchestrator

Use available tools (terminal, file_read, etc.) to run tests and report outcomes."""


def create_opencode_agent_config():
    """Create or update opencode.json: orchestrator only in switcher; full-test subagent."""
    project_root = Path.cwd()
    opencode_json = project_root / "opencode.json"

    agents = {
        "build": {"disable": True},
        "plan": {"disable": True},
        "orchestrator": {
            "description": "Manifest orchestrator agent for mission coordination, task management, and workflow orchestration",
            "mode": "primary",
            "prompt": ORCHESTRATOR_PROMPT,
            "tools": {"write": True, "edit": True, "bash": True},
        },
        "architect": {
            "description": "Manifest Architect agent for ideation and top-down docs only (PRD, architecture, intent). Cannot edit code or execute.",
            "mode": "primary",
            "prompt": ARCHITECT_PROMPT,
            "tools": {"write": False, "edit": False, "bash": False},
        },
        "full-test": {
            "description": "Manifest E2E / full-test agent. Callable by orchestrator only (subagent).",
            "mode": "subagent",
            "hidden": True,
            "prompt": FULL_TEST_PROMPT,
            "tools": {"write": True, "edit": True, "bash": True},
        },
    }

    existing = {}
    if opencode_json.exists():
        try:
            with open(opencode_json, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    config = {
        "$schema": "https://opencode.ai/config.json",
        "default_agent": "orchestrator",
        "agent": {**(existing.get("agent") or {}), **agents},
    }
    # Preserve other top-level keys from existing config
    for key in existing:
        if key not in ("agent", "default_agent"):
            config[key] = existing[key]

    with open(opencode_json, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated OpenCode config: {opencode_json}")
    print(f"✅ Agents in switcher: orchestrator, architect")
    print(f"✅ full-test: subagent (callable by orchestrator only)")
    return True


if __name__ == "__main__":
    try:
        create_opencode_agent_config()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
