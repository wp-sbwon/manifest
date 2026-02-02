#!/usr/bin/env python3
"""
Setup script to register manifest-orchestrator agent with OpenCode.

OpenCode loads agents from opencode.json (project root) or from markdown files
in .opencode/agents/. This script writes/updates opencode.json so the
manifest-orchestrator and manifest-full-test agents are available.
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

FULL_TEST_PROMPT = """You are the Manifest full-test (E2E) agent. Your role is to:

1. Run project- and sprint-wide end-to-end and integration tests
2. Execute test suites (pytest, etc.) for the whole scope
3. Report test results and failures
4. Work independently of the Worker Squad workflow; triggered by user or orchestrator

Use available tools (terminal, file_read, etc.) to run tests and report outcomes."""


def create_opencode_agent_config():
    """Create or update opencode.json with manifest agents (OpenCode loads agents from here)."""
    project_root = Path.cwd()
    opencode_json = project_root / "opencode.json"

    # OpenCode schema: agent.<id>.description, mode, model, prompt, tools (write/edit/bash)
    agents = {
        "manifest-orchestrator": {
            "description": "Manifest orchestrator agent for mission coordination, task management, and workflow orchestration",
            "mode": "primary",
            "model": "anthropic/claude-3-5-sonnet-20241022",
            "prompt": ORCHESTRATOR_PROMPT,
            "tools": {"write": True, "edit": True, "bash": True},
        },
        "manifest-full-test": {
            "description": "Manifest E2E / full-test agent. Runs project- and sprint-wide E2E and integration tests. Same tier as orchestrator.",
            "mode": "primary",
            "model": "anthropic/claude-3-5-sonnet-20241022",
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
        "default_agent": "manifest-orchestrator",
        "agent": {**(existing.get("agent") or {}), **agents},
    }
    # Preserve other top-level keys from existing config
    for key in existing:
        if key not in ("agent", "default_agent"):
            config[key] = existing[key]

    with open(opencode_json, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated OpenCode config: {opencode_json}")
    print(f"✅ Agent 'manifest-orchestrator' is now available (default_agent)")
    print(f"✅ Agent 'manifest-full-test' is now available")
    print(f"\nTo use:")
    print(f"  manifest  # Uses manifest-orchestrator by default")
    print(f"  opencode . --agent manifest-orchestrator -c")
    print(f"  opencode . --agent manifest-full-test -c")
    return True


if __name__ == "__main__":
    try:
        create_opencode_agent_config()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
