# Task Status, Stages, and Agent Metrics

## 1. What is "palette"?

**In this codebase:** The word "palette" does not appear anywhere. It is not a Manifest concept.

**Likely meaning elsewhere:** In Cursor/OpenCode or similar IDEs, "palette" usually refers to:

- **Command palette** – Quick action menu (e.g. Cmd/Ctrl+Shift+P) to run commands.
- **Agent/tool palette** – UI to choose which agent or tool to use (e.g. orchestrator vs full-test).

So "palette" is almost certainly an **external UI term** (Cursor or OpenCode), not something defined in Manifest. If you need to change what appears there, that would be in OpenCode/Cursor configuration (e.g. which agents are visible in the switcher), which we already touched in `opencode.json` and `scripts/setup_opencode_agent.py`.

---

## 2. Task management – status (and stages)

We need clear, consistent **status** values (lifecycle state) and **stage** values (workflow phase). Avoid informal words like "doing" or "stopped"; use the terms below.

### Recommended status set (single source of truth)

Use one canonical set everywhere: **OpenCode tool** (`.manifest/tasks.json`), **TaskManager/state**, **types**, and **View**.

| Status        | Meaning |
|---------------|--------|
| `pending`     | Not started; waiting to be picked up. |
| `in_progress` | Currently being worked on (agent or user). |
| `paused`      | Temporarily halted (user or system pause; can be resumed). |
| `blocked`     | Cannot proceed due to dependency or external condition. |
| `completed`   | Work finished successfully. |
| `cancelled`   | No longer required; will not be done. |

- **"Doing"** → use **`in_progress`**.
- **"Stopped"** → use **`paused`** (temporary) or **`cancelled`** (permanent). Prefer **`paused`** for "stopped but resumable".

### Where status is defined/used

- **`src/manifest/runtime/opencode/tools/task_management.py`**
  - `VALID_STATUSES = {"pending", "in_progress", "blocked", "completed", "cancelled"}`
  - Add **`paused`** here and in the OpenCode tool’s `update_task_status` (and any validation).
- **`src/manifest/core/task_manager.py`**
  - Docstring mentions "pending", "in_progress", "done", "blocked", "approved", "cancelled".
  - Align with the set above: use `in_progress` (not "wip"/"done"), `completed` (not "done"), and add `paused` where needed.
- **`src/manifest/core/types.py`**
  - `TaskDict.status`: docstring lists "pending", "wip", "done", "blocked", "cancelled", "completed".
  - Update to: **pending, in_progress, paused, blocked, completed, cancelled**.
- **View** (`src/manifest/view/app.py`)
  - Task list shows `t.get("status")` and `t.get("stage")`. No code change needed if status values match the set above; optional: map status → display label (e.g. "In progress", "Paused", "Blocked").
- **Worker squad / coordinator**
  - Agent completion is reflected in task state (e.g. moving to next stage or setting status). Keep using the same status enum when updating task status from the executor/coordinator.

### Recommended stage set (already consistent)

Keep and reuse where applicable:

- **`task_management.py`:** `VALID_STAGES = {"planning", "coding", "testing", "review", "done"}`.
- **TaskManager** uses stages like "planning", "implementation", "testing", "review", "completed". Prefer aligning on one list (e.g. planning → coding → testing → review → done) and use it in both OpenCode tool and internal state.

### Implementation checklist (status) — done

1. **Single source of truth:** `src/manifest/core/task_constants.py` defines `TASK_STATUSES`, `TASK_STAGES`, `STATUS_DISPLAY_LABELS`, `is_valid_status()`, `is_valid_stage()`, `status_display_label()`.
2. **OpenCode tool:** `task_management.py` uses `TASK_STATUSES` / `TASK_STAGES`; **`paused`** is valid in `update_task_status`.
3. **TaskManager:** Validates status/stage in create/update; added `pause_task()` and `resume_task()`; `complete_task` sets stage to `done`; `is_task_blocked` uses `completed` (not "done"); rollback uses `_STAGE_ORDER`.
4. **types.py:** `TaskDict.status` docstring updated to the canonical set.
5. **tool_definitions.py:** Schema description for status includes `paused`.
6. **View:** Task list shows human-readable labels via `status_display_label()`.

---

## 3. Agent metrics (e.g. token usage) – is it possible? Structure and logic

### Is it possible?

**Yes, if the backend exposes usage.** Token usage and cost come from the LLM provider (OpenCode → Anthropic/OpenAI/etc.). If the OpenCode HTTP API returns usage in its response (e.g. `input_tokens`, `output_tokens`, or a `usage` object), we can capture it and store it. If OpenCode does not return it, we need either an OpenCode change or a different integration point that does.

### Current state

- **`src/manifest/agents/resource_monitor.py`** – Tracks CPU, memory, disk, containers. **No token or cost metrics.**
- **`src/manifest/agents/context_size_calculator.py`** – Model token **limits** and estimation (chars → tokens). **No actual usage tracking.**
- **`src/manifest/runtime/opencode_llm_adapter.py`** – Sends prompts to OpenCode and streams chunks. It does **not** read or persist any `usage` / `input_tokens` / `output_tokens` from the response.
- **Coder agent** – Has `tool_execution_summary` (tool calls, files modified/read, commands). **No token counts.**

So today we have **no** agent-level token (or cost) metrics; the plumbing would need to be added.

### Proposed structure and logic

1. **Source of truth for usage**
   - OpenCode API (or whatever backend we use) must include usage in the stream or in a final message (e.g. on `complete` / `done`).
   - Check OpenCode’s API docs or response schema for fields like: `usage`, `input_tokens`, `output_tokens`, `total_tokens`, or `cost`.

2. **Capture in the adapter**
   - In **`opencode_llm_adapter.py`**:
     - In `_send_prompt` (and any other code that consumes the OpenCode stream): when handling `complete`/`done` (or a dedicated `usage` event), read `usage` from the payload.
     - Pass usage upward (e.g. in the yielded chunk or as part of a final summary).
     - In `execute_agent` (and `call_llm_once` if used for agent work): collect usage from the stream and return it (e.g. last chunk or a separate field).

3. **Store per task / per agent**
   - **Option A – In state:** Extend task or agent state (e.g. in `state_manager` / task checklist or a dedicated `agent_sessions` structure) with a field like `last_usage` or `usage_summary`:
     `{ "input_tokens": int, "output_tokens": int, "total_tokens": int, "model": str, "timestamp": iso }`
     and optionally accumulate per task: `task["metrics"]["token_usage"]` or `task["agent"]["last_usage"]`.
   - **Option B – Dedicated metrics store:** New small module (e.g. `agent_metrics.py`) that writes to a file (e.g. `.manifest/agent_metrics.json`) or in-memory store, keyed by `task_id` and optionally `agent_type` / `session_id`, so we can show totals per task and per agent type.

4. **Expose in View**
   - In **View** (e.g. Mission / Task panel in `app.py`): for each task (or for the active agent), display:
     - Last or cumulative **input_tokens**, **output_tokens**, **total_tokens**.
     - Optionally **cost** if the backend or we compute it (e.g. from token counts and a simple cost table).

5. **Optional: resource_usage in state**
   - State already has `resource_usage` (see View’s "Resources" section). We could add a top-level or task-level **token_usage** (and later cost) there so the View and any reporting stay consistent.

### Minimal implementation order

1. **Verify** OpenCode API: confirm response format and where usage appears (stream event vs final JSON).
2. **Parse and expose** in `opencode_llm_adapter`: read usage from response, add it to the chunk/summary returned to callers.
3. **Persist** in state or `agent_metrics`: store by `task_id` (and agent_type/session if useful).
4. **Display** in View: show token (and optionally cost) in the task/agent section.

This gives a clear path from "is it possible?" (yes, if the API gives usage) to a concrete structure: **adapter → state/metrics store → View**, with a single place (adapter) where we depend on the backend’s usage format.
