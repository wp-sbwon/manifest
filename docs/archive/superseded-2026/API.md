# Manifest API Documentation

## Overview

This document describes the API and module structure of the Manifest project. Manifest uses a modular architecture with clear separation of concerns.

## Package Structure

```
src/manifest/
├── core/          # Core functionality (config, state)
├── ui/            # User interface components
├── agents/        # Multi-agent coordination
├── bridge/        # Agent system integration
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

**Purpose**: Coordinates agents with task boundaries.

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
- `orchestrator`: Mission coordination and task delegation
- `planner`: Detailed task planning and blueprint creation
- `coder`: Code implementation
- `test`: Test agent
- `review`: Review agent

### `manifest.agents.context_provider`

**Purpose**: Provides tiered context to agents.

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

## Runtime Modules

### `manifest.runtime.agent.core.executor_factory`

**Purpose**: Factory for creating LLM execution backends.

**Classes**:
- `ExecutorFactory`: Creates appropriate executor backend based on configuration

**Key Methods**:
```python
ExecutorFactory.create_executor(
    config_manager: ConfigManager,
    state_manager: StateManager,
    backend: Optional[str] = None
) -> BaseAgentExecutor

ExecutorFactory.get_available_backends() -> List[str]
```

**Supported Backends**:
- `"direct"`: Direct LLM API calls via `AgentExecutor`
- `"opencode"`: OpenCode HTTP API via `OpenCodeLLMAdapter` (default)

**Usage**:
```python
from manifest.runtime.agent.core.executor_factory import ExecutorFactory
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager

config = ConfigManager()
state = StateManager()

# Create executor (defaults to "opencode")
executor = ExecutorFactory.create_executor(config, state)

# Explicitly use direct backend
executor = ExecutorFactory.create_executor(config, state, backend="direct")
```

### `manifest.runtime.agent.core.base_executor`

**Purpose**: Abstract base class for all LLM executors.

**Classes**:
- `BaseAgentExecutor`: Abstract interface for agent executors

**Key Methods**:
```python
@abstractmethod
async def execute_agent(
    agent_id: str,
    agent_type: str,
    prompt: Optional[str],
    model_config: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    message_history: Optional[List[Dict[str, Any]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None
) -> AsyncIterator[Dict[str, Any]]

@abstractmethod
def get_session_status(agent_id: str) -> Optional[Dict[str, Any]]

@abstractmethod
def stop_session(agent_id: str) -> bool
```

**Chunk Format**:
```python
{
    "type": str,  # "chunk", "complete", "tool_use", "error"
    "content": str,  # Text content (for "chunk" and "complete")
    "tool_call": Dict[str, Any],  # Tool call info (for "tool_use")
}
```

### `manifest.runtime.opencode_llm_adapter`

**Purpose**: OpenCode HTTP API adapter for LLM execution.

**Classes**:
- `OpenCodeLLMAdapter`: Adapter for OpenCode server

**Key Methods**:
```python
OpenCodeLLMAdapter.__init__(
    config_manager: ConfigManager,
    state_manager: StateManager,
    server_host: str = "localhost",
    server_port: int = 4096,
    auto_start: bool = True
)

async def execute_agent(...) -> AsyncIterator[Dict[str, Any]]
def get_session_status(agent_id: str) -> Optional[Dict[str, Any]]
def stop_session(agent_id: str) -> bool
```

**Configuration**:
- `opencode.server_host`: Server hostname (default: "localhost")
- `opencode.server_port`: Server port (default: 4096)
- `opencode.auto_start`: Auto-start server if not running (default: true)

## Bridge Modules

### `manifest.bridge.agent_bridge`

**Purpose**: Direct integration with agent system.

**Classes**:
- `AgentBridge`: Agent system integration bridge

**Key Methods**:
```python
AgentBridge.start_mission(mission_description: str) -> Awaitable[bool]
AgentBridge.get_status() -> Awaitable[Optional[Dict[str, Any]]]
AgentBridge.promote_task(task_id: str) -> Awaitable[bool]
AgentBridge.start_agent_mission(
    task_id: str,
    agent_type: str,
    context: Dict[str, Any],
    model_config: Dict[str, Any]
) -> Awaitable[bool]
AgentBridge.stop_agent(task_id: str) -> Awaitable[bool]
AgentBridge.get_agent_status(task_id: str) -> Awaitable[Optional[Dict[str, Any]]]
```

**Executor Integration**:
- Uses `ExecutorFactory` to create LLM executor
- Backend selection via `agent.execution_backend` setting
- Default: "opencode"

**Message Protocol**:
- JSON-based message format
- Commands: `start_mission`, `get_status`, `promote_task`
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
        "orchestrator": {
            "provider": str,
            "model": str,
            "use_default_key": bool
        },
        "planner": {
            "provider": str,
            "model": str,
            "use_default_key": bool
        },
        "coder": {
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
- `RuntimeError`: Agent system communication errors

## Async/Await Patterns

Most methods that interact with external processes or file I/O are async:

```python
# State operations
await state_manager.save_state()
await state_manager.load_state()

# Agent bridge operations
await agent_bridge.start_mission(description)
await agent_bridge.get_status()
```

## Examples

### Starting an Agent Mission

```python
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import get_config_manager
from manifest.core.state_manager import StateManager

# Initialize components
agent_bridge = AgentBridge(state_manager, config_manager)
context_provider = ContextProvider()
task_scoper = TaskScoper()
config_manager = get_config_manager()
state_manager = StateManager()

# Create coordinator
coordinator = AgentCoordinator(
    agent_bridge,
    context_provider,
    task_scoper,
    config_manager,
    state_manager
)

# Start worker agent
await coordinator.start_worker_agent(
    task_id="TASK-01",
    agent_type="coder",
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
