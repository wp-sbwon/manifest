# Manifest API Documentation

## Overview

This document describes the API and module structure of the Manifest project. Manifest uses a modular architecture with clear separation of concerns.

## Package Structure

```
src/manifest/
├── core/          # Core functionality (config, state)
├── ui/            # User interface components
├── agents/        # Multi-agent coordination
├── bridge/        # OMOC IPC communication
└── audit/         # Architecture drift detection
```

## Core Modules

### `manifest.core.config`

**Purpose**: API key management and configuration.

**Classes**:
- `ConfigManager`: Manages encrypted API keys and agent model configurations

**Key Methods**:
```python
get_config_manager() -> ConfigManager
ConfigManager.get_api_keys() -> Dict[str, str]
ConfigManager.save_api_keys(keys: Dict[str, str]) -> None
ConfigManager.validate_key(provider: str, key: str) -> bool
ConfigManager.get_agent_model_config(agent_type: str) -> Dict[str, Any]
```

**Usage**:
```python
from manifest.core.config import get_config_manager

config = get_config_manager()
api_keys = config.get_api_keys()
```

### `manifest.core.state_manager`

**Purpose**: Application state persistence and session management.

**Classes**:
- `StateManager`: Manages mission tree, task checklist, and chat history

**Key Methods**:
```python
StateManager.get_mission_tree() -> Dict[str, Any]
StateManager.set_mission_tree(tree: Dict[str, Any]) -> None
StateManager.get_task_checklist() -> List[Dict[str, Any]]
StateManager.set_task_checklist(tasks: List[Dict[str, Any]]) -> None
StateManager.add_chat_message(role: str, content: str) -> None
StateManager.get_chat_history() -> List[Dict[str, Any]]
StateManager.save_state() -> Awaitable[None]
StateManager.load_state() -> Awaitable[Optional[Dict[str, Any]]]
```

**Usage**:
```python
from manifest.core.state_manager import StateManager

state = StateManager()
await state.save_state()
```

## UI Modules

### `manifest.ui.app`

**Purpose**: Main TUI application entry point.

**Classes**:
- `ManifestApp`: Main Textual application class

**Key Methods**:
```python
ManifestApp.on_mount() -> None
ManifestApp.on_input_submitted(event: Input.Submitted) -> None
ManifestApp.process_command(command: str) -> None
```

**Views**:
- Architect (Intention)
- Blueprint
- Inspector (Verification)
- Mission Control
- History
- Feature Explorer
- Project Info

### `manifest.ui.widgets`

**Purpose**: Custom Textual widgets for the Manifest UI.

**Classes**:
- `RequirementMap`: Visual requirement mapping widget
- `ArchitectureGraph`: Architecture visualization widget
- `FeatureTree`: Feature tree widget
- `TaskTree`: Task tree widget
- `GateController`: Gate control widget

### `manifest.ui.bootstrap_ui`

**Purpose**: Bootstrap mode TUI for API key configuration.

**Classes**:
- `BootstrapApp`: Bootstrap mode application

**Functions**:
```python
run_bootstrap() -> None
```

## Agent Modules

### `manifest.agents.agent_coordinator`

**Purpose**: Coordinates agents through OMOC with task boundaries.

**Classes**:
- `AgentCoordinator`: Manages orchestrator and worker agent lifecycle

**Key Methods**:
```python
AgentCoordinator.start_orchestrator(mission_description: str) -> Awaitable[bool]
AgentCoordinator.start_worker_agent(
    task_id: str,
    agent_type: str,
    mission_description: str
) -> Awaitable[bool]
AgentCoordinator.stop_agent(task_id: str) -> Awaitable[bool]
```

**Agent Types**:
- `prometheus`: Orchestrator/Planner
- `sisyphus`: Worker/Coder
- `test`: Test agent
- `review`: Review agent

### `manifest.agents.context_provider`

**Purpose**: Provides tiered context to OMOC for agents.

**Classes**:
- `ContextProvider`: Manages tiered context provisioning

**Key Methods**:
```python
ContextProvider.get_orchestrator_context() -> Dict[str, Any]
ContextProvider.get_worker_context(task_id: str, agent_type: str) -> Dict[str, Any]
```

**Context Tiers**:
- **Tier 0**: The Law (manifest-policy.md)
- **Tier 1**: The Intent (intent.json, architecture.json)
- **Tier 2**: The Blueprint (blueprint.json - scoped)
- **Tier 3**: Surgical Code (files - scoped)

### `manifest.agents.task_scoper`

**Purpose**: Manages task boundaries and context scoping.

**Classes**:
- `TaskScoper`: Manages task scope and file boundaries

**Key Methods**:
```python
TaskScoper.get_task_context(task_id: str) -> Dict[str, Any]
TaskScoper.validate_task_scope(task_id: str, file_path: str) -> bool
TaskScoper.get_files_in_scope(task_id: str) -> List[str]
```

## Bridge Modules

### `manifest.bridge.omoc_bridge`

**Purpose**: IPC engine for communicating with OMOC process.

**Classes**:
- `OMOCBridge`: IPC bridge to OMOC via standard I/O pipes

**Key Methods**:
```python
OMOCBridge.start_mission(mission_description: str) -> Awaitable[bool]
OMOCBridge.send_message(message: Dict[str, Any]) -> Awaitable[Optional[Dict[str, Any]]]
OMOCBridge.get_status() -> Awaitable[Optional[Dict[str, Any]]]
OMOCBridge.promote_task(task_id: str) -> Awaitable[bool]
OMOCBridge.start_agent_mission(
    task_id: str,
    agent_type: str,
    context: Dict[str, Any],
    model_config: Dict[str, Any]
) -> Awaitable[bool]
OMOCBridge.stop_agent(task_id: str) -> Awaitable[bool]
OMOCBridge.get_agent_status(task_id: str) -> Awaitable[Optional[Dict[str, Any]]]
```

**Message Protocol**:
- JSON-based message format
- Commands: `start_mission`, `send_message`, `get_status`, `promote_task`
- Agent commands: `start_agent_mission`, `stop_agent`, `get_agent_status`

## Audit Modules

### `manifest.audit.drift_auditor`

**Purpose**: Detects architecture drift by comparing code against blueprint.

**Classes**:
- `DriftAuditor`: Architecture drift detection engine
- `DriftConflict`: Represents a drift conflict
- `Severity`: Enum for conflict severity levels

**Key Methods**:
```python
DriftAuditor.audit_file(file_path: Path) -> List[DriftConflict]
DriftAuditor.audit_directory(directory: Path) -> List[DriftConflict]
DriftAuditor.compare_with_blueprint(
    ast_nodes: List[ast.AST],
    blueprint_components: List[Dict[str, Any]]
) -> List[DriftConflict]
```

**Severity Levels**:
- `ERROR`: Critical architectural violation
- `WARNING`: Potential issue
- `INFO`: Informational note

## Data Structures

### State Schema

```python
{
    "version": "1.0",
    "session_id": str,
    "last_updated": str,  # ISO format
    "mission_tree": Dict[str, Any],
    "task_checklist": List[Dict[str, Any]],
    "chat_history": List[Dict[str, str]],
    "last_action": Optional[str]
}
```

### Task Schema

```python
{
    "id": str,
    "description": str,
    "status": str,  # "pending", "wip", "done", "blocked"
    "agent": Optional[Dict[str, Any]],
    "scope": Optional[Dict[str, Any]]
}
```

### Agent Configuration Schema

```python
{
    "version": "1.0",
    "agent_models": {
        "prometheus": {
            "provider": str,
            "model": str,
            "use_default_key": bool
        },
        # ... other agents
    },
    "default_models": {
        "anthropic": str,
        "openai": str,
        "google": str
    }
}
```

## Error Handling

All modules use standard Python exceptions. Common exceptions:

- `FileNotFoundError`: Configuration or state files not found
- `ValueError`: Invalid configuration or state data
- `KeyError`: Missing required configuration keys
- `RuntimeError`: OMOC process communication errors

## Async/Await Patterns

Most methods that interact with external processes or file I/O are async:

```python
# State operations
await state_manager.save_state()
await state_manager.load_state()

# OMOC bridge operations
await omoc_bridge.start_mission(description)
await omoc_bridge.send_message(message)
```

## Examples

### Starting an Agent Mission

```python
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.bridge.omoc_bridge import OMOCBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import get_config_manager
from manifest.core.state_manager import StateManager

# Initialize components
omoc_bridge = OMOCBridge()
context_provider = ContextProvider()
task_scoper = TaskScoper()
config_manager = get_config_manager()
state_manager = StateManager()

# Create coordinator
coordinator = AgentCoordinator(
    omoc_bridge,
    context_provider,
    task_scoper,
    config_manager,
    state_manager
)

# Start worker agent
await coordinator.start_worker_agent(
    task_id="TASK-01",
    agent_type="sisyphus",
    mission_description="Implement authentication system"
)
```

### Detecting Architecture Drift

```python
from manifest.audit.drift_auditor import DriftAuditor
from pathlib import Path

auditor = DriftAuditor()
conflicts = await auditor.audit_directory(Path("src/"))

for conflict in conflicts:
    print(f"{conflict.severity.value}: {conflict.message}")
    print(f"  File: {conflict.file_path}")
    print(f"  Component: {conflict.component_id}")
```
