# Incomplete or Not-Yet-Implemented Items (Detail + Suggestions)

This document describes parts of the codebase that are not yet fully implemented (as of 2026-02), with explanations and suggestions.

---

## 1. BlueprintSynchronizer — merge mode

**Location:** `src/manifest/audit/blueprint/blueprint_synchronizer.py` — `sync_blueprints(..., mode="merge")`

### What’s incomplete

- `sync_blueprints()` supports three modes: **strict**, **workflow**, **merge**.
- **Strict:** blocks if there are ERROR/WARNING conflicts.
- **Workflow:** triggers the conflict workflow (report, user resolution).
- **Merge:** currently does **not** perform any auto-merge. It only runs the comparator and returns:
  - `success: True`
  - `merged: False` (with comment "Not implemented yet")
  - `conflicts: len(conflicts)` (count only; no resolution).

So "merge" does not update the top-down blueprint with bottom-up changes; it just reports that conflicts exist.

### Why it matters

- Users or tools that choose `sync_blueprint(mode="merge")` expect design and code to be reconciled automatically where safe.
- Without real merge logic, merge mode is indistinguishable from "report-only" and can be misleading.

### Suggestions

1. **Define merge semantics**
   Decide what "merge" means, e.g.:
   - **Accept bottom-up where no conflict:** e.g. add components that exist only in bottom-up as "accepted"; update top-down component metadata (methods/attributes) from bottom-up when there’s no semantic conflict.
   - **Resolve only low-severity items:** e.g. auto-apply INFO (and maybe IN_PROGRESS) from comparator; leave ERROR/WARNING for workflow.
   - **Three-way style:** treat top-down as base, bottom-up as "current code", and produce a merged blueprint (e.g. with conflict markers or a resolved structure).

2. **Implement merge in code**
   - Use `BlueprintComparator.compare_blueprints()` to get conflicts.
   - For each conflict, apply rules (e.g. by `Severity` and `ConflictType`): which changes to merge into a new blueprint, which to leave for workflow.
   - Write the merged blueprint (e.g. update `.manifest/blueprint.json` or a dedicated "merged" artifact) and return `merged: True` and a summary of what was merged.

3. **Short-term clarification**
   - If merge is not planned soon: document in the tool description and/or docstring that `mode="merge"` is not yet implemented and only returns conflict count.
   - Optionally add a warning log when `mode="merge"` is used so operators know merge is not implemented.

---

## 2. ConfigManager — Google API key validation

**Location:** `src/manifest/core/config.py` — `validate_key(provider="google", key=...)`

Provider keys are managed by OpenCode; Manifest does not require or validate them.

### What’s incomplete

- For **Anthropic** and **OpenAI**, `validate_key()` does a real check (e.g. minimal API request; 200/400 or 200 means valid).
- For **Google**, it only checks that the key is non-empty: `return len(key) > 0`. There is no call to a Google API to verify the key.

So a non-empty but invalid Google key can be stored and reported as "valid" until a real request fails later.

### Why it matters

- Settings/UI that "validate all keys" will show Google as valid even when it isn’t.
- Debugging auth issues is harder when validation is misleading.

### Suggestions

1. **Implement Google validation**
   - Use a minimal Google AI/Gen AI request (e.g. list models or a tiny generate call) with the key, similar to OpenAI.
   - Respect timeout and handle 401/403 as invalid; 200 (or documented "key valid" responses) as valid.
   - Document which Google API/product (e.g. Vertex, Gemini API) is assumed and add the corresponding endpoint.

2. **If Google is optional**
   - Keep the non-empty check but document it clearly (e.g. "Google: key presence only; no API validation").
   - In the UI or docs, state that "Validate" for Google only checks that a key is set, not that it works.

3. **Consistency**
   - Ensure error handling and logging for Google match Anthropic/OpenAI (e.g. log validation failures, don’t swallow network errors as "invalid key" without logging).

---

## 3. Context provider — task description

**Location:** `src/manifest/agents/context_provider.py` — `_get_task_description(task_id)`

### What’s incomplete

- `_get_task_description(task_id)` is used when building context for stages (e.g. `tdd_test`, and anywhere `task_description` is needed).
- Previously returned only `f"Task {task_id}"`; now uses `state_manager.get_task()` to load name/description.

`ContextProvider` already has `self.state_manager` (injected or created in `__init__`). So at runtime there is no missing dependency; the method simply doesn’t use it.

### Why it matters

- Agent prompts get a generic "Task &lt;id&gt;" instead of the actual task name/description, which can hurt planning and execution quality.

### Suggestions

1. **Use StateManager already on self**
   - In `_get_task_description(task_id)`, call `task = self.state_manager.get_task(task_id)`.
   - If `task` is not None, return a short description, e.g. `task.get("name") or task.get("description") or f"Task {task_id}"`.
   - If `task` is None, keep fallback `f"Task {task_id}"` and optionally log that the task was not found.

2. **Avoid circular imports**
   - `StateManager` is already a dependency of `ContextProvider`; `get_task` is on `StateManager`. There is no need to import `ContextProvider` inside `StateManager` or `TaskManager`. If a circular import appears, fix it by moving the import inside the method that uses it (already the case for `TaskManager` in `StateManager.get_task`).

3. **Optional enrichment**
   - If tasks have more structure (e.g. acceptance criteria, links), consider returning a one-line summary (e.g. name + first line of description) so context stays useful but bounded.

---

## 4. View app — main chat area

**Location:** `src/manifest/view/app.py` — main area content and `MAIN_CHAT_PLACEHOLDER`

### What’s incomplete

- The Manifest View app is a visualization dashboard (header, sidebar, task/status/viz panels).
- The main area shows a short message that chat and terminal are in OpenCode. The View app is visualization-only; chat is in OpenCode.

### Why it matters

- By design, chat is in OpenCode.

### Suggestions

1. **Treat as design choice, not missing code**
   - View states that chat and terminal are in OpenCode. README and architecture docs state that View is visualization-only.

2. **If in-app chat is desired later**
   - Define a small "chat bridge" interface (e.g. send message / get stream) that could be implemented by OpenCode (current) or by an in-app widget later.
   - The main area could then switch between "OpenCode instructions" and an embedded chat when that backend exists.

3. **No code change required for current scope**
   - As long as the product decision is "chat in OpenCode," no implementation is strictly incomplete; only documentation and wording can be clarified.

---

## 5. UI package

**Location:** `src/manifest/ui/__init__.py`

### What’s incomplete

- The `manifest.ui` package redirects to `manifest.view`; chat and terminal are in OpenCode.

So there is no real UI code in `manifest.ui`; it exists for backwards compatibility or to avoid import errors.

### Why it matters

- Code or docs that reference `manifest.ui` get an empty package. If something used to live here, it may be unclear where it moved.

### Suggestions

1. **Document and redirect**
   - Docstring points to `manifest.view`; chat/terminal are in OpenCode. README states that `manifest.view` is the View package.

3. **Removal only when safe**
   - Remove the package only after grepping the repo and dependent code for `manifest.ui` / `from manifest import ui` and updating or dropping those references.

---

## 6. Failure recovery — simplified-prompt retry

**Location:** `src/manifest/agents/failure_recovery.py` — `_retry_with_simplified_prompt()`

### What’s incomplete

- `_retry_with_simplified_prompt()` is supposed to retry a failed stage with a "simplified prompt" (reduced context) to avoid overload or confusion.
- The implementation does **not** change the prompt or context. It only:
  - Logs that it’s retrying with a simplified prompt
  - Sleeps 2 seconds
  - Calls the same `start_worker_agent_and_wait(...)` as a normal retry, with the same arguments.

So the behavior is "retry after a delay," not "retry with less context."

### Why it matters

- Failures that are due to context size or prompt complexity won’t be addressed by this path; only timing changes.
- The method name and docstring promise behavior that isn’t implemented.

### Suggestions

1. **Implement simplified context**
   - Define what "simplified" means (e.g. drop Tier 3, shorten Tier 2, or use a smaller task scope).
   - In `_retry_with_simplified_prompt`, build a new context dict with less content (reuse existing tier/scope helpers with stricter limits or a "minimal" mode).
   - Call the worker agent with this reduced context (and the same task_id, stage, previous_stages) so the same stage runs with a smaller prompt.

2. **Optional: prompt variant**
   - If prompts are configurable, add a "retry / simplified" variant (e.g. "Be brief; focus on the immediate fix") and pass that into the executor for this retry only.

3. **Short-term honesty**
   - Rename the method to something like `_retry_with_delay()` and update the docstring to say it only retries after a short delay, and that true "simplified prompt" retry is planned. That way callers and future implementers aren’t misled.

---

## Summary table

| Item | Location | Severity | Suggested priority |
|------|----------|----------|--------------------|
| Blueprint merge mode | blueprint_synchronizer.py | Medium | Define semantics, then implement or document as not implemented |
| Google key validation | config.py | Low | Add real API check or document as presence-only |
| Task description | context_provider.py | Medium | Use `state_manager.get_task()` in `_get_task_description` |
| View chat area | view/app.py | Low | Chat in OpenCode; View is visualization-only |
| UI package | ui/__init__.py | Low | Document deprecation; optional DeprecationWarning |
| Simplified-prompt retry | failure_recovery.py | Medium | Implement reduced context or rename and document |

None of these block normal use of the app; they are improvements for correctness, UX, and maintainability.
