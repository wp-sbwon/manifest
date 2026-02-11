# Hardcoded contents

Inventory of hardcoded URLs, paths, ports, provider/model names, file names, timeouts, and other literals in `src/`. Use this to decide what to move to config or env.

---

## 1. URLs and hosts

| Location | Value | Note |
|----------|--------|------|
| `runtime/tools/tool_executor.py` | `http://127.0.0.1:{port}/api/worker_squad/run` | Container API URL; port from config or `CONTAINER_API_PORT`. |
| `agents/container_communication.py` | `base_url: str = "http://manifest-app:8000"` | Default for container→host; overridable. |
| `agents/runner.py` | `base_url = os.environ.get("MANIFEST_API_URL", "http://manifest-app:8000")` | Env override. |
| `agents/runner.py` | `manifest_dir = Path("/app/.manifest")` | Container path; not configurable. |
| `runtime/opencode_llm_adapter.py` | `server_host: str = "localhost"` | OpenCode host; config has `opencode.server_host`. |
| `core/config.py` | `"server_host": "localhost"` in default settings | Same. |
| `launcher.py` | `"0.0.0.0"` (bind address for Container API) | Fixed for listening on all interfaces. |

---

## 2. Ports

| Location | Value | Note |
|----------|--------|------|
| `launcher.py` | `CONTAINER_API_PORT = 4097` | Default; can be overridden by `container_api.port` in config. |
| `runtime/tools/tool_executor.py` | `CONTAINER_API_PORT = 4097` | Same constant; used when calling Container API. |
| `agents/container_communication.py` | `8000` (in `manifest-app:8000`) | Default host API port. |

---

## 3. Paths

| Location | Value | Note |
|----------|--------|------|
| `core/paths.py` | `Path.cwd() / ".manifest"` | Default manifest dir. |
| Many modules | `manifest_dir or Path(".manifest")` | Default when None. |
| `runtime/tools/tool_executor.py` | `Path.cwd() / ".manifest"` | Default manifest_dir. |
| `agents/runner.py` | `Path("/app")` (working_dir), `Path("/app/.manifest")` | Container layout. |
| `agents/container_manager.py` | `"PYTHONPATH": "/app/src"`, `"bind": "/app"` | Container mounts. |
| `launcher.py` | `DEV_PROJECT_DIR_NAME = "tmp"` | Dev project dir name. |
| `launcher.py` | `Path.cwd() / ".manifest"` | In config help path. |

---

## 4. File names (canonical)

| Location | Value | Note |
|----------|--------|------|
| `audit/blueprint/manifest_filenames.py` | `blueprint_design.json`, `blueprint_code.json`, `blueprint_view.json` | Canonical; used everywhere. |
| `core/state_manager.py` | `"state.json"` | State file. |
| `core/config.py` | `agent_config.json` | Agent config file. |
| `runtime/opencode/tools/task_management.py` | `TASKS_FILE = "tasks.json"` | Tasks file. |
| `runtime/opencode/tools/sprint_management.py` | `TASKS_FILE = "tasks.json"` | Same. |
| `view/file_watcher.py` | `WATCH_FILES = ("tasks.json", "state.json", ...)` | List of watched files. |
| `audit/doc_set.py` | `"blueprint": "blueprint_code.json"`, etc. | Doc type → filename. |
| `core/design_history.py` | design history file name | In module. |
| `runtime/shadow_manager.py` | `['src', '.manifest', 'requirements.txt', 'pyproject.toml']` | Copy list. |

---

## 5. Provider and model defaults

| Location | Value | Note |
|----------|--------|------|
| `core/config.py` | `_default_agent_config()` | `anthropic` for orchestrator/planner/coder/review, `openai` for test. |
| `core/config.py` | `provider = "anthropic"` when agent_type not in config | Default provider. |
| `core/config.py` | API validation: `"https://api.anthropic.com/v1/messages"`, `"claude-3-sonnet-20240229"`, `max_tokens: 10` | Key validation request. |
| `core/config.py` | `all(keys.get(k) for k in ["anthropic", "openai"])` | Required keys for validation. |
| `runtime/opencode_llm_adapter.py` | `model_config.get("provider", "anthropic")` | Default provider. |
| `launcher.py` | `cfg.get("provider", "anthropic")` | When showing/setting worker-model. |
| `runtime/agent/agents/test_agent.py` | `model_config.get("provider", "anthropic")` | Format branching. |
| `runtime/agent/agents/coder_agent.py` | `model_config.get("provider", "anthropic")` | Same. |
| `agents/context_size_calculator.py` | `MODEL_TOKEN_LIMITS` | Full dict of model names → token limits (Claude, GPT, Gemini). |
| `agents/context_size_calculator.py` | `DEFAULT_TOKEN_LIMIT = 100000`, `RESPONSE_TOKEN_RESERVE = 4000`, `CHARS_PER_TOKEN = 4` | Heuristics. |
| `runtime/permissions/permission_manager.py` | `"orchestrator": { ... }` and other agent types | Default permission map. |

---

## 6. Agent type and default agent

| Location | Value | Note |
|----------|--------|------|
| `launcher.py` | `DEFAULT_AGENT = "orchestrator"` | Default OpenCode agent. |
| `agents/runner.py` | `if agent_type == "orchestrator":` | Special handling. |
| `runtime/agent/core/manager.py` | `"orchestrator": ORCHESTRATOR_IDENTITY` | Identity map. |
| `runtime/shadow_manager.py` | `"{agent_type}"`, `"{task_id}"`, `"{stage}"` in generated script | Template placeholders in f-string; interpolated when script is generated. |
| `runtime/opencode/tools/doc_creation_tool.py` | `opencode.layer_writer_agent` default `"architect"` | Agent run by OpenCode for blueprint layer writing; config overridable. |

---

## 7. Timeouts (seconds)

| Location | Value | Note |
|----------|--------|------|
| `agents/container_communication.py` | `timeout=30.0`, `5.0`, `10.0` | HTTP/client. |
| `runtime/opencode_llm_adapter.py` | `5.0`, `300.0`, `10.0` (from config or default), `2.0`, `5` | Health check, request, server start, wait. |
| `runtime/tools/tool_executor.py` | `timeout=300.0` | Container API POST. |
| `agents/container_manager.py` | `2`, `5`, `10` | Docker operations. |
| `agents/worker_squad_executor.py` | `300.0`, `900.0`, `600.0` (per stage) | Stage timeouts; some from `self.timeouts`. |
| `agents/workflow_definition.py` | `300.0`, `900.0`, `600.0` | Default stage timeouts. |
| `agents/watchdog.py` | `command_timeout: float = 300.0` | Default command timeout. |
| `agents/agent_message_bus.py` | `timeout: float = 30.0` | Bus operations. |
| `agents/failure_recovery.py` | `600.0` | Recovery timeouts. |
| `launcher.py` | `5`, `10` | Subprocess/availability checks. |
| `audit/code/health_from_code.py` | `10`, `45` | Health check timeouts. |
| `runtime/shadow_manager.py` | `5.0` | Process wait. |

---

## 8. Other literals

| Location | Value | Note |
|----------|--------|------|
| `runtime/opencode/tools/worker_squad_spawn.py` | `"manifest-approver"` | Agent name in spawn data. |
| `core/config.py` | `"version": "1.0"` | Config version. |
| `core/config.py` | `"anthropic-version": "2023-06-01"` | API header for validation. |
| `view/app.py` | `APP_VERSION = "0.0"` | Footer version. |

---

## 9. Summary

- **Ports:** `4097` and `8000` are the main ones; 4097 is already overridable via `container_api.port`.
- **Hosts/URLs:** `localhost`, `127.0.0.1`, `manifest-app:8000`, `/app` are the main ones; runner uses `MANIFEST_API_URL`.
- **Paths:** `.manifest` and container `/app` are standard; dev uses `tmp` when in manifest repo.
- **File names:** Centralized in `manifest_filenames.py` and a few `TASKS_FILE` / `state.json` / `agent_config.json` usages.
- **Providers/models:** Defaults in config and many `"anthropic"` / `"openai"` defaults; token limits and model list in `context_size_calculator`.
- **Timeouts:** Many 2–600 second values; some come from config (e.g. opencode timeouts), others are fixed.

To externalize: consider config or env for default provider, default agent, Container API host/port, runner manifest path and host URL, and timeout defaults where desired.
