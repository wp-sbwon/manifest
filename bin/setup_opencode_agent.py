#!/usr/bin/env python3
"""
Setup script to register Manifest agents with OpenCode.

Writes opencode.json (tools: {write, edit, bash}). OpenCode may also load
.opencode/agents/*.json which use tools as string arrays. Schema compatibility
depends on OpenCode version; merge order (project vs .opencode) determines precedence.
Default agent: architect. Built-in agents build and plan are disabled.
"""
import json
import sys
from pathlib import Path

ARCHITECT_PROMPT = """You are the Manifest Architect agent. Your role is to:

1. Ideate with the user: discuss product goals, requirements, and design
2. Create PRD first: use write_prd to save .manifest/prd.json (fixed format: title, mission, sections)
3. Then create blueprint from PRD: use create_blueprint_from_prd to build .manifest/blueprint_design.json from prd.json; it runs layer-by-layer expansion recursively
4. You cannot edit project code, run terminal commands, create tasks, or spawn worker agents

Flow: ideate → write_prd (prd.json) → create_blueprint_from_prd (blueprint_design.json). You have access to: read-only tools and architect tools (write_prd, write_architecture, create_blueprint_from_prd, ideate). Do not use task_management, worker_squad_spawn, edit, write, or bash."""

FULL_TEST_PROMPT = """You are the Manifest full-test (E2E) agent. Your role is to:

1. Run project- and sprint-wide end-to-end and integration tests
2. Execute test suites (pytest, etc.) for the whole scope
3. Report test results and failures
4. Triggered by user when needed.

Use available tools (terminal, file_read, etc.) to run tests and report outcomes."""


def create_opencode_agent_config():
    """Create or update opencode.json: architect default; full-test subagent."""
    project_root = Path.cwd()
    opencode_json = project_root / "opencode.json"

    agents = {
        "build": {"disable": True},
        "plan": {"disable": True},
        "architect": {
            "description": "Manifest Architect agent for ideation and top-down docs only (PRD, architecture, intent). Cannot edit code or execute.",
            "mode": "primary",
            "prompt": ARCHITECT_PROMPT,
            "tools": {"write": False, "edit": False, "bash": False},
        },
        "full-test": {
            "description": "Manifest E2E / full-test agent (subagent).",
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
        "default_agent": "architect",
        "agent": {**(existing.get("agent") or {}), **agents},
    }
    # Preserve other top-level keys from existing config
    for key in existing:
        if key not in ("agent", "default_agent"):
            config[key] = existing[key]

    with open(opencode_json, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated OpenCode config: {opencode_json}")
    print(f"✅ Default agent: architect")
    print(f"✅ full-test: subagent")
    return True


if __name__ == "__main__":
    try:
        create_opencode_agent_config()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
