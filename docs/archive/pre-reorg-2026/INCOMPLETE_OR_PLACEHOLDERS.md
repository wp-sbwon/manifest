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

3. **Short-term clarification** — **Done**
   - Docstring of `sync_blueprints` now documents that `mode="merge"` is not implemented (returns conflict count only). A warning is logged when `mode="merge"` is used.

---

## 2. ConfigManager — API key handling — **Removed**

**Location:** `src/manifest/core/config.py`

**Resolution:** API key storage and validation were removed. OpenCode manages model selection and keys. ConfigManager no longer has get_api_keys, save_api_keys, has_all_keys, validate_key, or validate_all_keys; get_agent_model_config returns provider and model only (api_key always None). No further work for key validation in Manifest.

---

## 3. Context provider — task description — **Resolved**

**Location:** `src/manifest/agents/context_provider.py` — `_get_task_description(task_id)`

**Resolution:** `_get_task_description` calls `self.state_manager.get_task(task_id)` and returns `task.get("name") or task.get("description") or f"Task {task_id}"`; fallback `f"Task {task_id}"` when task is None. Agent prompts now receive the actual task name/description when available.

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

**Location:** N/A — no `manifest.ui` package in repo.

### Status

- The codebase has `manifest.view` only (dashboard, viz panels). There is no `manifest.ui` package; nothing references it. Chat and terminal are in OpenCode. If a legacy or external reference to `manifest.ui` appears, point it to `manifest.view` or add a thin `manifest.ui` redirect with a docstring.

---

## 6. Failure recovery — retry with delay — **Short-term resolved**

**Location:** `src/manifest/agents/failure_recovery.py` — `_retry_with_delay()`

**Resolution:** The method was renamed from `_retry_with_simplified_prompt` to `_retry_with_delay`. The docstring now states that it only retries after a short delay with the same context; it does not reduce context or change the prompt. A true "simplified prompt" retry (reduced context) may be added later.

---

## Summary table

| Item | Location | Severity | Status |
|------|----------|----------|--------|
| Blueprint merge mode | blueprint_synchronizer.py | Medium | Not implemented; docstring + warning log when mode=merge |
| Key validation | config.py | — | Removed; OpenCode manages keys |
| Task description | context_provider.py | — | Resolved; uses state_manager.get_task() |
| View chat area | view/app.py | Low | Chat in OpenCode; View is visualization-only |
| UI package | — | Low | No manifest.ui in repo; use manifest.view |
| Retry with delay | failure_recovery.py | Medium | Renamed from simplified-prompt; docstring updated |

None of these block normal use of the app; they are improvements for correctness, UX, and maintainability.
