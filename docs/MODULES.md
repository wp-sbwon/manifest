# Manifest Module Documentation

This document provides detailed documentation for each module in the Manifest project.

## Table of Contents

- [Core Modules](#core-modules)
- [UI Modules](#ui-modules)
- [Agent Modules](#agent-modules)
- [Bridge Modules](#bridge-modules)
- [Audit Modules](#audit-modules)

## Core Modules

### `manifest.core.config`

**Location**: `src/manifest/core/config.py`

**Purpose**: Manages API keys, encryption, and agent model configurations.

#### Classes

##### `ConfigManager`

Manages configuration including API keys and agent model settings.

**Methods**:

- `get_api_keys() -> Dict[str, str]`
  - Returns all stored API keys
  - Keys are decrypted automatically

- `save_api_keys(keys: Dict[str, str]) -> None`
  - Saves API keys with encryption
  - Validates keys before saving

- `validate_key(provider: str, key: str) -> bool`
  - Validates an API key for a provider
  - Returns True if valid

- `get_agent_model_config(agent_type: str) -> Dict[str, Any]`
  - Gets model configuration for an agent type
  - Returns provider, model, and API key info

- `set_agent_model_config(agent_type: str, config: Dict[str, Any]) -> None`
  - Sets model configuration for an agent type

**Configuration Files**:
- `.manifest/keys.json`: Encrypted API keys
- `.manifest/agent_config.json`: Agent model configurations

### `manifest.core.state_manager`

**Location**: `src/manifest/core/state_manager.py`

**Purpose**: Manages application state persistence and session resumption.

#### Classes

##### `StateManager`

Handles state persistence including mission tree, tasks, and chat history.

**Initialization**:
```python
StateManager(manifest_dir: Path = None)
```

**Methods**:

- `get_mission_tree() -> Dict[str, Any]`
  - Returns current mission tree structure

- `set_mission_tree(tree: Dict[str, Any]) -> None`
  - Updates mission tree

- `get_task_checklist() -> List[Dict[str, Any]]`
  - Returns list of tasks with status

- `set_task_checklist(tasks: List[Dict[str, Any]]) -> None`
  - Updates task checklist

- `add_chat_message(role: str, content: str) -> None`
  - Adds message to chat history
  - Roles: "user", "assistant", "system"

- `get_chat_history() -> List[Dict[str, Any]]`
  - Returns chat history

- `set_last_action(action: str) -> None`
  - Records last action performed

- `save_state() -> Awaitable[None]`
  - Persists current state to disk

- `load_state() -> Awaitable[Optional[Dict[str, Any]]]`
  - Loads state from disk
  - Returns None if no state exists

**State Schema**:
```python
{
    "version": "1.0",
    "session_id": str,
    "last_updated": str,
    "mission_tree": Dict[str, Any],
    "task_checklist": List[Dict[str, Any]],
    "chat_history": List[Dict[str, str]],
    "last_action": Optional[str]
}
```

## UI Modules

### `manifest.ui.app`

**Location**: `src/manifest/ui/app.py`

**Purpose**: Main TUI application entry point and view management.

#### Classes

##### `ManifestApp`

Main Textual application class managing all views and interactions.

**Views**:
- Architect: Feature and requirement view
- Blueprint: Architecture visualization
- Inspector: Drift detection and verification
- Mission Control: Task and mission management
- History: Chat history
- Feature Explorer: Feature exploration
- Project Info: Project metadata

**Key Methods**:

- `on_mount() -> None`
  - Initializes application on startup
  - Loads state, sets up views

- `on_input_submitted(event: Input.Submitted) -> None`
  - Handles user input
  - Processes commands

- `process_command(command: str) -> None`
  - Processes command strings
  - Routes to appropriate handlers

**Commands**:
- `/help`: Show help
- `/quit`: Exit application
- `/start_mission <desc>`: Start mission
- `/start_agent <task_id> <type>`: Start agent
- `/view <name>`: Switch view

### `manifest.ui.widgets`

**Location**: `src/manifest/ui/widgets.py`

**Purpose**: Custom Textual widgets for Manifest UI.

#### Widgets

##### `RequirementMap`

Visual widget for displaying requirement mappings.

##### `ArchitectureGraph`

Graph widget for architecture visualization.

##### `FeatureTree`

Tree widget for feature hierarchy.

##### `TaskTree`

Tree widget for task structure.

##### `GateController`

Widget for gate control and status display.

### `manifest.ui.bootstrap_ui`

**Location**: `src/manifest/ui/bootstrap_ui.py`

**Purpose**: Bootstrap mode TUI for API key configuration.

#### Classes

##### `BootstrapApp`

Bootstrap mode application for initial setup.

**Functions**:

- `run_bootstrap() -> None`
  - Runs bootstrap UI for API key configuration

## Agent Modules

### `manifest.agents.agent_coordinator`

**Location**: `src/manifest/agents/agent_coordinator.py`

**Purpose**: Coordinates agents with task boundaries.

#### Classes

##### `AgentCoordinator`

Manages orchestrator and worker agent lifecycle.

**Initialization**:
```python
AgentCoordinator(
    agent_bridge: AgentBridge,
    context_provider: ContextProvider,
    task_scoper: TaskScoper,
    config_manager: ConfigManager,
    state_manager: StateManager
)
```

**Methods**:

- `start_orchestrator(mission_description: str) -> Awaitable[bool]`
  - Starts orchestrator agent
  - Returns True if successful

- `start_worker_agent(
    task_id: str,
    agent_type: str,
    mission_description: str
) -> Awaitable[bool]`
  - Starts worker agent on a task
  - Agent types: "planner", "coder", "test", "review"
  - Returns True if successful

- `stop_agent(task_id: str) -> Awaitable[bool]`
  - Stops agent working on task
  - Returns True if successful

### `manifest.agents.context_provider`

**Location**: `src/manifest/agents/context_provider.py`

**Purpose**: Provides tiered context to agents.

#### Classes

##### `ContextProvider`

Manages tiered context provisioning.

**Context Tiers**:

- **Tier 0 (The Law)**: `.claude/rules/manifest-policy.md`
- **Tier 1 (The Intent)**: `intent.json`, `architecture.json`
- **Tier 2 (The Blueprint)**: Scoped `blueprint.json` nodes
- **Tier 3 (Surgical Code)**: Scoped file contents

**Methods**:

- `get_orchestrator_context() -> Dict[str, Any]`
  - Returns full context for orchestrator
  - Includes Tier 0 and Tier 1

- `get_worker_context(task_id: str, agent_type: str) -> Dict[str, Any]`
  - Returns scoped context for worker
  - Includes all tiers, scoped to task

### `manifest.agents.task_scoper`

**Location**: `src/manifest/agents/task_scoper.py`

**Purpose**: Manages task boundaries and context scoping.

#### Classes

##### `TaskScoper`

Manages task scope and file boundaries.

**Methods**:

- `get_task_context(task_id: str) -> Dict[str, Any]`
  - Returns context for a task
  - Includes blueprint components, files, requirements

- `validate_task_scope(task_id: str, file_path: str) -> bool`
  - Validates if file is in task scope
  - Returns True if file can be modified

- `get_files_in_scope(task_id: str) -> List[str]`
  - Returns list of files in task scope

## Bridge Modules

### `manifest.runtime`

Runtime agent system modules.

#### `manifest.runtime.router.terminal_router`

**Location**: `src/manifest/runtime/router/terminal_router.py`

**Purpose**: Terminal command execution router.

##### `TerminalRouter`

Routes terminal commands through OpenCode router system.

**Methods**:
- `execute_command(command, args, timeout, stream)`: Execute a terminal command
- `stream_command_output(command, args)`: Stream command output line by line
- `cancel_command(command_id)`: Cancel a running command
- `is_command_running(command_id)`: Check if a command is running

#### `manifest.runtime.agent`

Runtime agent system integration.

##### `Orchestrator`

**Location**: `src/manifest/runtime/agent/orchestrator.py`

Agent orchestration system.

**Methods**:
- `start_mission(task_id, mission_description)`: Start a new mission
- `stop_mission(task_id)`: Stop a mission
- `get_mission_status(task_id)`: Get mission status

##### `AgentManager`

**Location**: `src/manifest/runtime/agent/manager.py`

Manages agent lifecycle.

**Methods**:
- `create_agent(agent_type, context, model_config, task_id)`: Create a new agent
- `start_agent(agent_id)`: Start an agent
- `stop_agent(agent_id)`: Stop an agent
- `get_agent(agent_id)`: Get agent information
- `list_agents()`: List all agent IDs
- `shutdown()`: Shutdown all agents

### `manifest.agents.container_manager`

**Location**: `src/manifest/agents/container_manager.py`

**Purpose**: Manages Docker containers for Agent Squad execution.

##### `ContainerManager`

Manages Docker containers for agent execution with lifecycle management, monitoring, and logging.

**Methods**:
- `start_agent_container(task_id, agent_type, environment, volumes, network)`: Start an agent container
- `stop_agent_container(task_id)`: Stop an agent container
- `get_container_status(task_id)`: Get container status
- `get_container_logs(task_id, tail, follow)`: Get container logs
- `list_active_containers()`: List all active container task IDs
- `cleanup_all()`: Stop and remove all managed containers
- `is_docker_available()`: Check if Docker is available

### `manifest.bridge.agent_bridge`

**Location**: `src/manifest/bridge/agent_bridge.py`

**Purpose**: Direct integration with agent system.

#### Classes

##### `AgentBridge`

Agent system integration bridge.

**Initialization**:
```python
AgentBridge(state_manager: StateManager, config_manager: Optional[ConfigManager] = None)
```

**Methods**:

- `start_mission(mission_description: str) -> Awaitable[bool]`
  - Starts a mission
  - Returns True if successful

- `get_status() -> Awaitable[Optional[Dict[str, Any]]]`
  - Gets current mission status
  - Returns status dictionary

- `promote_task(task_id: str) -> Awaitable[bool]`
  - Promotes task to next stage
  - Returns True if successful

- `start_agent_mission(
    task_id: str,
    agent_type: str,
    context: Dict[str, Any],
    model_config: Dict[str, Any]
) -> Awaitable[bool]`
  - Starts agent mission
  - Returns True if successful

- `stop_agent(task_id: str) -> Awaitable[bool]`
  - Stops agent
  - Returns True if successful

- `get_agent_status(task_id: str) -> Awaitable[Optional[Dict[str, Any]]]`
  - Gets agent status
  - Returns status dictionary

**Message Protocol**:
- JSON-based messages
- Commands: `start_mission`, `send_message`, `get_status`, etc.
- Responses include status and data

## Audit Modules

### `manifest.audit.drift_auditor`

**Location**: `src/manifest/audit/drift_auditor.py`

**Purpose**: Detects architecture drift by comparing code against blueprint.

#### Classes

##### `DriftAuditor`

Architecture drift detection engine.

**Methods**:

- `audit_file(file_path: Path) -> List[DriftConflict]`
  - Audits single file for drift
  - Returns list of conflicts

- `audit_directory(directory: Path) -> List[DriftConflict]`
  - Audits directory recursively
  - Returns list of all conflicts

- `compare_with_blueprint(
    ast_nodes: List[ast.AST],
    blueprint_components: List[Dict[str, Any]]
) -> List[DriftConflict]`
  - Compares AST nodes with blueprint
  - Returns list of conflicts

##### `DriftConflict`

Represents a drift conflict.

**Attributes**:
- `severity: Severity`
- `message: str`
- `file_path: Path`
- `component_id: Optional[str]`
- `line_number: Optional[int]`

##### `Severity`

Enum for conflict severity.

**Values**:
- `ERROR`: Critical violation
- `WARNING`: Potential issue
- `INFO`: Informational note

## Module Dependencies

```
app.py
├── config
├── state_manager
    ├── agent_bridge
│   └── state_manager
├── drift_auditor
├── widgets
├── bootstrap_ui
│   └── config
├── task_scoper
├── context_provider
│   └── task_scoper
└── agent_coordinator
    ├── agent_bridge
    ├── context_provider
    ├── task_scoper
    ├── config
    └── state_manager
```

## Best Practices

1. **Core modules**: Keep minimal dependencies, no UI
2. **UI modules**: Use Textual, keep widgets reusable
3. **Agent modules**: Coordinate, don't implement agents
4. **Bridge modules**: Abstract protocol, handle errors
5. **Audit modules**: Focus on detection, not fixing
