# OpenCode Agent Setup - manifest-orchestrator

## Overview

Manifest uses OpenCode with a custom `manifest-orchestrator` agent that handles:
- Mission coordination
- Task delegation
- Sprint management
- Blueprint synchronization
- Workflow orchestration

## Model selection

- **Primary (orchestrator)**: The model is **chosen by the user in the OpenCode terminal** when starting the session (or in OpenCode settings). Do not set `model` in agent JSON.
- **Worker agents**: The user can **change the model per agent** via an OpenCode command (e.g. in-session command or settings per agent type). See OpenCode documentation for the exact command.

## Setup

The agent configuration is automatically created in `.opencode/agents/manifest-orchestrator.json` when you run:

```bash
python scripts/setup_opencode_agent.py
```

Or it's created automatically when you first run `manifest`.

## Agent Configuration

The agent is configured with:
- **Name**: `manifest-orchestrator`
- **Type**: Primary agent (main assistant)
- **System Prompt**: Full orchestrator identity, workflow modes, and **instructions to follow project rules in `.rules/`** (task-granularity.md, prd-template.md, etc.)
- **Capabilities**: Mission planning, task delegation, workflow coordination
- **Model**: Not set in the JSON. **You choose the model in the OpenCode terminal** (or OpenCode settings). Do not hardcode a model in this repo.

## Pre-loaded agents

We ship **six agents** in `.opencode/agents/`: manifest-orchestrator (primary), manifest-planner, manifest-coder, manifest-test, manifest-debug, manifest-approver (workers). All have defined scope, role, and guidelines; no `model` field—model is chosen by you. See `.opencode/README.md`.

## Project rules (.rules)

The orchestrator and workers are instructed to **read and follow** `.rules/` (task-granularity.md, prd-template.md, code-style, etc.). That directory is the single source of truth for task granularity, PRD structure, and other policy. See `.rules/README.md` if present.

## Usage

### Default Usage

When you run `manifest`, it automatically uses `manifest-orchestrator`:

```bash
manifest
```

This will:
1. Start Manifest View (background visualization)
2. Start OpenCode with `manifest-orchestrator` agent

### Manual Usage

You can also use the agent directly with OpenCode:

```bash
opencode . --agent manifest-orchestrator -c
```

## Agent Capabilities

The orchestrator agent can:

1. **Mission Planning**
   - Receive high-level mission descriptions
   - Break down into manageable tasks
   - Create task checklists

2. **Task Delegation**
   - Assign tasks to worker agents (planner, coder, test, review)
   - Coordinate multi-agent workflows
   - Monitor task progress

3. **Sprint Management**
   - Group tasks into sprints
   - Manage sprint execution
   - Handle parallel task execution

4. **Blueprint Sync**
   - Monitor blueprint changes
   - Detect drift
   - Coordinate synchronization

## Troubleshooting

### Agent Not Found

If you see "manifest agent not found":

1. **Check agent file exists**:
   ```bash
   ls -la .opencode/agents/manifest-orchestrator.json
   ```

2. **Recreate agent config**:
   ```bash
   python scripts/setup_opencode_agent.py
   ```

3. **Verify OpenCode can see it**:
   ```bash
   opencode agent list  # If supported
   ```

### Agent Not Working

If the agent doesn't behave correctly:

1. **Check system prompt**: Verify `.opencode/agents/manifest-orchestrator.json` has correct system prompt
2. **Check OpenCode version**: Ensure you're using a compatible OpenCode version
3. **Check logs**: Look for errors in OpenCode output

## Configuration

You can customize any agent by editing its JSON under `.opencode/agents/`:

- **systemPrompt**: Change the agent's behavior and instructions
- **tools**: Modify available tools
- **capabilities**: Update agent capabilities

**Model selection** (do not set in JSON):
- **Primary/orchestrator**: Choose the model in the OpenCode terminal when you start the session (or in OpenCode settings).
- **Worker agents**: Use the OpenCode command to change the model per agent (e.g. in-session command or settings per agent type). See OpenCode docs for the exact command.

After changes, restart OpenCode for them to take effect.

## Integration with Manifest

The orchestrator agent integrates with Manifest's:
- **StateManager**: For task and mission persistence
- **AgentBridge**: For agent communication
- **BlueprintSynchronizer**: For blueprint management
- **TaskManager**: For task lifecycle

All these are available through the agent's context and tools.
