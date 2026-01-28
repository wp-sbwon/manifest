#!/usr/bin/env python3
"""
Setup script to register manifest-orchestrator agent with OpenCode.

This script creates the necessary OpenCode agent configuration files
so that 'manifest-orchestrator' agent is available when running OpenCode.
"""
import json
import sys
from pathlib import Path

def create_opencode_agent_config():
    """Create OpenCode agent configuration for manifest-orchestrator."""
    project_root = Path.cwd()
    opencode_dir = project_root / ".opencode"
    agents_dir = opencode_dir / "agents"

    # Create directories
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Agent configuration
    agent_config = {
        "name": "manifest-orchestrator",
        "description": "Manifest orchestrator agent for mission coordination, task management, and workflow orchestration",
        "type": "primary",
        "systemPrompt": """You are the Manifest orchestrator agent. Your role is to:

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

When a user provides a mission description, break it down into tasks and coordinate execution. Use the available tools and agents to accomplish the mission efficiently.""",
        "tools": [
            "file_read",
            "file_write",
            "terminal",
            "code_analysis",
            "task_management",
            "sprint_management",
            "worker_squad_spawn",
            "blueprint_sync",
            "drift_check"
        ],
        "model": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022"
        },
        "capabilities": [
            "mission_planning",
            "task_delegation",
            "workflow_coordination",
            "blueprint_sync",
            "drift_detection",
            "sprint_management"
        ]
    }

    # Write agent config
    agent_file = agents_dir / "manifest-orchestrator.json"
    with open(agent_file, "w", encoding="utf-8") as f:
        json.dump(agent_config, f, indent=2, ensure_ascii=False)

    print(f"✅ Created OpenCode agent config: {agent_file}")
    print(f"✅ Agent 'manifest-orchestrator' is now available in OpenCode")

    # manifest-full-test: E2E / full-test agent at same level as orchestrator (§7)
    full_test_config = {
        "name": "manifest-full-test",
        "description": "Manifest E2E / full-test agent. Runs project- and sprint-wide E2E and integration tests. Same tier as orchestrator.",
        "type": "primary",
        "systemPrompt": """You are the Manifest full-test (E2E) agent. Your role is to:

1. Run project- and sprint-wide end-to-end and integration tests
2. Execute test suites (pytest, etc.) for the whole scope
3. Report test results and failures
4. Work independently of the Worker Squad workflow; triggered by user or orchestrator

Use available tools (terminal, file_read, etc.) to run tests and report outcomes.""",
        "tools": ["file_read", "file_write", "terminal", "code_analysis"],
        "model": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
        "capabilities": ["e2e_testing", "integration_testing", "test_reporting"],
    }
    full_test_file = agents_dir / "manifest-full-test.json"
    with open(full_test_file, "w", encoding="utf-8") as f:
        json.dump(full_test_config, f, indent=2, ensure_ascii=False)
    print(f"✅ Created OpenCode agent config: {full_test_file}")
    print(f"✅ Agent 'manifest-full-test' is now available in OpenCode (same level as orchestrator)")

    print(f"\nTo use it:")
    print(f"  manifest  # Will use manifest-orchestrator by default")
    print(f"  opencode . --agent manifest-orchestrator -c")
    print(f"  opencode . --agent manifest-full-test -c  # E2E / full-test agent")

    return True


if __name__ == "__main__":
    try:
        create_opencode_agent_config()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
