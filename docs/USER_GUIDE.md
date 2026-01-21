# Manifest User Guide

## Introduction

Manifest is an **AI-Native Orchestration IDE** that helps developers manage complex software projects by providing visual truth, tiered context management, and architecture drift detection.

## Getting Started

### Installation

See [DEV_SETUP.md](./DEV_SETUP.md) for detailed installation instructions.

### Quick Start

1. **Setup environment:**
   ```bash
   ./scripts/setup.sh
   source venv/bin/activate
   ```

2. **Run Manifest:**
   ```bash
   PYTHONPATH=src python -m manifest
   ```

## User Interface

### Views

Manifest provides 7 main views accessible via tabs:

#### 1. Architect (Intention)
- **Purpose**: View and manage project intentions and features
- **Shows**: Sprint information, feature list, requirements status
- **Use Case**: Planning and tracking feature development

#### 2. Blueprint
- **Purpose**: Visual representation of system architecture
- **Shows**: Component zones (client, server, data), component relationships
- **Use Case**: Understanding system structure and dependencies

#### 3. Inspector (Verification)
- **Purpose**: Verify implementation against design
- **Shows**: Drift conflicts, component status, verification results
- **Use Case**: Detecting architectural violations

#### 4. Mission Control
- **Purpose**: Manage active missions and tasks
- **Shows**: Mission tree, task checklist, agent assignments
- **Use Case**: Coordinating development work

#### 5. History
- **Purpose**: View chat history and interactions
- **Shows**: Conversation history with agents
- **Use Case**: Reviewing past decisions and context

#### 6. Feature Explorer
- **Purpose**: Explore features and their components
- **Shows**: Feature tree, methods, classes per feature
- **Use Case**: Understanding feature implementation

#### 7. Project Info
- **Purpose**: Project metadata and status
- **Shows**: Project information, status, metrics
- **Use Case**: Overview of project health

### Navigation

- **Tab Navigation**: Use `Tab` key or click on tab headers
- **Input Field**: Bottom of screen for commands
- **Quit**: Press `q` or type `/quit`

## Commands

### Basic Commands

- `/help` - Show help message
- `/quit` or `q` - Exit application
- `/clear` - Clear chat history

### Mission Commands

- `/start_mission <description>` - Start a new mission
- `/promote_task <task_id>` - Promote a task to next stage
- `/status` - Get current mission status

### Agent Commands

- `/start_agent <task_id> <agent_type>` - Start an agent on a task
  - Agent types: `prometheus`, `sisyphus`, `test`, `review`
- `/stop_agent <task_id>` - Stop an agent working on a task
- `/agent_status <task_id>` - Get agent status

### View Commands

- `/view <view_name>` - Switch to a specific view
  - View names: `architect`, `blueprint`, `inspector`, `mission_control`, `history`, `feature_explorer`, `project_info`

## Working with Missions

### Starting a Mission

1. Type `/start_mission` followed by a description
2. Mission will be created and displayed in Mission Control view
3. Tasks will be automatically generated based on the mission

### Managing Tasks

Tasks appear in the Mission Control view with status indicators:
- **Pending**: Not yet started
- **WIP**: Work in progress
- **Done**: Completed
- **Blocked**: Blocked by dependencies

### Agent Assignment

Assign agents to tasks:
```bash
/start_agent TASK-01 sisyphus
```

This starts a Sisyphus (coder) agent working on task TASK-01.

## Architecture Drift Detection

The Inspector view shows architecture drift conflicts:

- **ERROR**: Critical violations that must be fixed
- **WARNING**: Potential issues to review
- **INFO**: Informational notes

Drift detection runs automatically when:
- Files are modified
- Blueprint is updated
- Manual refresh is triggered

## State Management

Manifest automatically saves your state:
- Mission tree
- Task checklist
- Chat history
- Agent assignments

State is persisted in `.manifest/state.json` and restored on next launch.

## Configuration

### API Keys

Manifest requires API keys for AI providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)

Keys are stored encrypted in `.manifest/keys.json`.

### Agent Model Configuration

Configure which models agents use in `.manifest/agent_config.json`:

```json
{
  "agent_models": {
    "prometheus": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    }
  }
}
```

## Tips and Best Practices

1. **Regular State Saves**: State is auto-saved, but you can manually save with `/save`

2. **Use Feature Explorer**: Explore features to understand code organization

3. **Monitor Drift**: Check Inspector view regularly for architecture violations

4. **Agent Coordination**: Use Mission Control to coordinate multiple agents

5. **Context Awareness**: Manifest provides tiered context - agents only see what they need

## Troubleshooting

### Application Won't Start

- Check Python version: `python3 --version` (requires 3.9+)
- Verify dependencies: `pip install -r requirements.txt`
- Check PYTHONPATH: `export PYTHONPATH=src`

### Import Errors

- Ensure you're using `PYTHONPATH=src` when running
- Verify virtual environment is activated
- Check that all dependencies are installed

### State Not Loading

- Check `.manifest/state.json` exists
- Verify file permissions
- Check JSON syntax is valid

### OMOC Connection Issues

- Verify OMOC process is running
- Check pipe communication
- Review error messages in History view

## Keyboard Shortcuts

- `q` - Quit application
- `Tab` - Navigate between views
- `Enter` - Submit command in input field
- `Esc` - Cancel input

## Getting Help

- Type `/help` in the application
- Check [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details
- Review [API.md](./API.md) for developer documentation
- See [DEV_SETUP.md](./DEV_SETUP.md) for setup issues
