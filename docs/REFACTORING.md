# Refactoring Notes

High-level refactoring opportunities and completed work.

## Completed

### ToolExecutor result dicts (`src/manifest/runtime/tools/tool_executor.py`)

- **Change:** Introduced `_tool_result(tool_input, tool_name, result=None, error=None, **extra)` to build standard tool result dicts.
- **Replaced:** Returns in `_execute_bash`, `_run_squad_via_container_api`, `_execute_worker_squad_spawn`, `_execute_blueprint_sync`, `_execute_drift_check`, and the approval-gate return.
- **Remaining:** Many other methods still build `{"tool_call_id": ..., "tool_name": ..., "result": ...}` or error dicts by hand. Migrating those to `_tool_result` would reduce duplication and keep shapes consistent.

## Opportunities

### 1. ToolExecutor – finish _tool_result migration

- **Where:** `tool_executor.py` – `execute_tool` dispatch, `_execute_task_management`, `_execute_sprint_management`, file-manager/read/edit/write/grep/glob/list branches, etc.
- **What:** Replace every manual `return {"tool_call_id": tool_input.get("id", "unknown"), "tool_name": ..., ...}` with `return self._tool_result(tool_input, "<name>", result=...| error=..., **extra)`.
- **Benefit:** Single place for result shape; fewer copy-paste mistakes.

### 2. View app – lazy service access (`src/manifest/view/app.py`)

- **Where:** `_get_state_manager`, `_get_task_manager`, `_get_blueprint_sync`, `_get_git_manager`, `_get_blueprint_comparator`.
- **What:** Optional helper, e.g. `_get_or_init(attr, factory)` to avoid repeating `if self._x is None: self._x = ...; return self._x`. Low priority; current code is clear.

### 3. HTTP client usage

- **Where:** `tool_executor._run_squad_via_container_api`, `opencode_llm_adapter._send_prompt`, `executor._call_openai`, `config.validate_key` – all use `httpx.AsyncClient` with different timeouts and patterns (stream vs non-stream).
- **What:** A small shared module (e.g. `manifest.core.http_client`) could offer `async_post_json(url, payload, timeout=...)` and optionally a streaming helper. Only worthwhile if more call sites appear or we want a single place for timeouts/retries.

### 4. Large modules

- **agent_coordinator.py**, **agent_bridge.py**, **worker_squad_executor.py** – high line counts. Consider splitting by responsibility (e.g. coordinator: lifecycle vs messaging vs task routing) when touching those areas.

## Scope policy

- Refactor only within the file or feature you are changing; avoid broad “cleanup” commits that touch many modules.
- Prefer small, mechanical steps (e.g. one method or one tool at a time) and run tests after each step.
