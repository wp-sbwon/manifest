# Manifest User Guide

## Overview

Manifest is an AI-Native Orchestration IDE that helps developers manage complex software projects through a structured, blueprint-first approach.

## Quick Start

1. **Installation**:
```bash
git clone <repository>
cd manifest
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **First Run**:
```bash
PYTHONPATH=src python -m manifest
```

The app will check for API keys. If missing, it will prompt you to configure them.

## Core Concepts

### Views

Manifest provides 5 main views:

1. **Architect View**: Shows high-level intent and requirements
2. **Blueprint View**: Displays technical design and API contracts
3. **Inspector View**: Three modes for verification
   - Visual: UI matching
   - Data: Execution traces
   - Drift: Architecture conflicts
4. **Mission Control**: Task management and approval gates
5. **History View**: Git timeline integration

### Agent System

Manifest uses a multi-agent system:

- **Orchestrator**: Mission coordination and task delegation
- **Planner**: Detailed task planning and blueprint creation
- **Coder**: Code implementation
- **Test**: Test writing and execution
- **Review**: Code review

### LLM Execution Backend

Manifest supports two LLM execution backends:

1. **OpenCode** (Default, Recommended)
   - Uses OpenCode HTTP API for LLM interactions
   - Handles context management and tool execution automatically
   - Requires OpenCode server running (auto-started by default)

2. **Direct API**
   - Direct LLM API calls (Anthropic, OpenAI, etc.)
   - Full control over prompts and context
   - Requires API keys configured

#### OpenCode Backend Configuration

OpenCode is the default backend. Configure it in `.manifest/settings.json`:

```json
{
  "agent": {
    "execution_backend": "opencode"
  },
  "opencode": {
    "server_host": "localhost",
    "server_port": 4096,
    "auto_start": true
  }
}
```

**Settings**:
- `agent.execution_backend`: "opencode" or "direct" (default: "opencode")
- `opencode.server_host`: OpenCode server hostname (default: "localhost")
- `opencode.server_port`: OpenCode server port (default: 4096)
- `opencode.auto_start`: Automatically start OpenCode server if not running (default: true)

**Benefits of OpenCode**:
- Automatic context management
- Optimized tool execution
- Better token usage
- Focus on workflow orchestration

#### Direct API Backend

To use direct API calls instead:

```json
{
  "agent": {
    "execution_backend": "direct"
  }
}
```

**Note**: Direct backend requires API keys to be configured in `.manifest/keys.json`.

#### Terminal Command Execution

Manifest agents can optionally use OpenCode for terminal command execution:

- **Automatic**: If OpenCode is installed, agents will automatically use it
- **Seamless Fallback**: If OpenCode is not available, agents use the internal implementation
- **No Configuration Needed**: Works out of the box with or without OpenCode

## Commands

### Basic Commands

- `/audit` - Run architecture drift detection
- `/reload` - Reload all views
- `/status` - Get current mission status

### Agent Commands

- `/start_agent <task_id> <agent_type>` - Start an agent on a task
  - Agent types: `orchestrator`, `planner`, `coder`, `test`, `review`
- `/stop_agent <task_id>` - Stop an agent working on a task
- `/agent_status <task_id>` - Get agent status

### View Commands

- Switch views using `Tab` key or mouse clicks
- Use `Ctrl+1` through `Ctrl+5` for quick view switching

## Configuration

### API Keys

Configure API keys in `.manifest/keys.json`:

```json
{
  "anthropic": "sk-ant-...",
  "openai": "sk-...",
  "google": "..."
}
```

**Note**: API keys are only required for the "direct" backend. OpenCode backend uses its own API key configuration.

### Execution Backend Settings

Configure LLM execution backend in `.manifest/settings.json`:

```json
{
  "agent": {
    "execution_backend": "opencode"
  },
  "opencode": {
    "server_host": "localhost",
    "server_port": 4096,
    "auto_start": true
  }
}
```

**Changing Backend**:
1. Edit `.manifest/settings.json`
2. Set `agent.execution_backend` to "opencode" or "direct"
3. Restart Manifest application

### Agent Models

Configure which models agents use in `.manifest/agent_config.json`:

```json
{
  "agent_models": {
    "orchestrator": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    },
    "planner": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    },
    "coder": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    }
  }
}
```

## Agent Assignment

Assign agents to tasks:
```bash
/start_agent TASK-01 coder
```

This starts a coder agent working on task TASK-01.

## Architecture Drift Detection

Manifest continuously monitors code structure against the blueprint:

1. **Automatic Detection**: Runs on file changes
2. **Conflict Classification**: Errors, Warnings, Info
3. **Resolution Workflow**: Review, approve, or reject changes

## Troubleshooting

### State Issues

- Check `.manifest/state.json` exists
- Verify file permissions
- Check JSON syntax is valid

### Agent Bridge Connection Issues

- Verify agent bridge is initialized
- Check agent system communication
- Review error messages in History view

### Drift Detection Issues

- Ensure `blueprint.json` is up to date
- Check AST parsing is working
- Review conflict reports in Inspector view

## Best Practices

1. **Blueprint-First**: Always update blueprint before code changes
2. **Task Scoping**: Use task scoping to limit agent access
3. **Regular Audits**: Run `/audit` regularly to catch drift early
4. **Session Management**: Use session resumption for long missions
