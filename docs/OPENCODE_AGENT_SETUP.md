# OpenCode Agent Setup - manifest-orchestrator

## Overview

Manifest uses OpenCode with a custom `manifest-orchestrator` agent that handles:
- Mission coordination
- Task delegation
- Sprint management
- Blueprint synchronization
- Workflow orchestration

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
- **System Prompt**: Full orchestrator identity and workflow modes
- **Capabilities**: Mission planning, task delegation, workflow coordination

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

You can customize the agent by editing `.opencode/agents/manifest-orchestrator.json`:

- **systemPrompt**: Change the agent's behavior and instructions
- **model**: Change the LLM model used
- **tools**: Modify available tools
- **capabilities**: Update agent capabilities

After changes, restart OpenCode for them to take effect.

## Integration with Manifest

The orchestrator agent integrates with Manifest's:
- **StateManager**: For task and mission persistence
- **AgentBridge**: For agent communication
- **BlueprintSynchronizer**: For blueprint management
- **TaskManager**: For task lifecycle

All these are available through the agent's context and tools.
