# Refactoring Recommendations

High-level refactoring opportunities identified from code review. Ordered by impact and ease.

**Done:** 1–6, 7a (debug/approver loop helpers in execute()), 7b (WorkerRegistration extracted; coordinator delegates registration).

---

## 1. **AgentCoordinator: Remove dead `_execute_*` methods** (Low effort, clear win)

**Location:** `src/manifest/agents/agent_coordinator.py` (lines ~1018–1220)

**Issue:** `AgentCoordinator` defines `_execute_planner_stage`, `_execute_coder_stage`, `_execute_tdd_test_stage`, `_execute_test_stage`, `_execute_debug_stage`, `_execute_self_review_stage`, `_execute_approver_stage`. These only **start** an agent (return `bool` or minimal dict) and are **never called**. All real workflow execution goes through `WorkerSquadExecutor.execute()`, which uses the executor’s own `_execute_*` methods that call `coordinator.start_worker_agent_and_wait()` and return full stage results.

**Action:** Delete the coordinator’s `_execute_planner_stage` through `_execute_approver_stage` (and any helpers only used by them). Keep `execute_worker_squad` (it correctly delegates to `worker_squad_executor.execute(task_id)`).

**Benefit:** ~200 lines removed, less confusion about where workflow stages run.

---

## 2. **Extract agent output parsing into a dedicated module** (Medium effort)

**Location:** `AgentCoordinator._parse_agent_output` (lines ~638–820)

**Issue:** One long method with many `if agent_type == "planner"` / `elif agent_type == "test"` branches and regex-heavy logic. Hard to test and extend.

**Action:** Add e.g. `src/manifest/agents/agent_output_parser.py`:

- `AgentOutputParser` (or a module of functions) with one parser per `(agent_type, stage)` or per agent type.
- Register parsers in a small registry (e.g. `dict[(agent_type, stage)] -> callable`) or use a single entrypoint that delegates by agent type/stage.
- `AgentCoordinator._parse_agent_output` becomes a thin wrapper that calls this module.

**Benefit:** Parsing is testable in isolation; adding a new agent type or stage is a single new parser.

---

## 3. **Extract “wait for agent completion” loop** (Medium effort)

**Location:** `AgentCoordinator.start_worker_agent_and_wait` (lines ~402–496)

**Issue:** A long `while` loop with six different completion checks (active_agents, bridge._active_agents, executor.active_sessions, get_agent_status, channel history, completed_at). Hard to read and to change completion policy.

**Action:** Extract to a private helper, e.g. `_wait_for_agent_completion(task_id, channel, timeout) -> Tuple[bool, str]` (or a small async generator / helper that yields “still running” until done). Keep the logic in one place and document the canonical order of checks.

**Benefit:** Shorter `start_worker_agent_and_wait`, easier to adjust or test completion behavior.

---

## 4. **Deduplicate “register worker agent” in `start_worker_agent`** (Low effort)

**Location:** `AgentCoordinator.start_worker_agent` (container path ~271–306, in-process path ~315–339)

**Issue:** Both branches do the same conceptual steps: set `active_agents[task_id]`, update `task["agent"]`, set `task["scope"]`, `set_task_checklist`, `set_last_action`, `save_state`. Only the “channel” and “container_id” / “execution_mode” details differ.

**Action:** Extract e.g. `_register_worker_agent(task_id, agent_type, channel, execution_mode="direct", container_id=None)`. Call it from both the container and in-process paths with the right channel and mode.

**Benefit:** One place for registration rules; less duplication and drift.

---

## 5. **Single source of truth for stage sequence** (Medium effort)

**Location:** Stage order / names appear in:

- `agent_coordinator._get_next_stage`: hardcoded `stage_sequence` list
- `worker_squad_executor._determine_next_stage_legacy`: `stage_sequence` dict
- `worker_squad_executor._is_workflow_complete`: `required_stages` set
- `workflow_definition`: `WorkflowDefinition.stages`

**Issue:** Adding or reordering a stage requires edits in several places.

**Action:** Prefer `WorkflowDefinition` (or a small constants module) as the single source:

- Define default workflow stages (and optionally “required” set) in one place (e.g. `WorkflowDefinition` or `workflow_definition.DEFAULT_STAGE_ORDER`).
- `_get_next_stage` and legacy “next stage” logic should derive from that (or from `WorkflowDefinition` when available) instead of local lists/dicts.
- Keep backward compatibility during migration (e.g. executor still supports legacy path until fully switched).

**Benefit:** One place to change stage order or add stages; fewer bugs from inconsistent ordering.

---

## 6. **WorkerSquadExecutor.execute() length and duplication** (Higher effort)

**Location:** `WorkerSquadExecutor.execute()` (sequential branch, lines ~681–846)

**Issue:** One long method that runs planner → tdd_test → coder → test → debug loop → self_review → approver loop. Each stage repeats: run stage, save to state, maybe run recovery, maybe publish WORKFLOW_FAILED and return. Same pattern many times.

**Action:** Options (can combine):

- Extract “run one stage and optionally recover” into e.g. `_run_stage_with_recovery(task_id, stage_name, previous_stages, ...) -> (result, ok)` and use it for each stage.
- For the debug and approver loops, extract small helpers e.g. `_run_debug_loop_until_tests_pass(...)` and `_run_approver_loop_until_approved(...)` so `execute()` reads as a linear sequence of steps.
- Consider a small state machine or “stage runner” that takes the list of stages from `WorkflowDefinition` and runs each in order with a common “run + save + recover” wrapper.

**Benefit:** Shorter `execute()`, easier to add stages or change recovery/loop behavior.

---

## 7. **AgentCoordinator as a facade only** (Larger refactor)

**Location:** `AgentCoordinator` (~1298 lines before removing dead code)

**Issue:** The class mixes lifecycle (start/stop/status), worker registration, completion waiting, output parsing, blueprint conflict handling, sprint start, and workflow entry (execute_worker_squad). That’s a lot of responsibilities in one type.

**Action:** Long term, consider splitting into focused components, e.g.:

- **AgentLifecycle**: start/stop agent, get status, “wait for completion” (uses bridge/container).
- **WorkerRegistration**: register/unregister worker in active_agents and task state (used by lifecycle).
- **AgentOutputParser**: see item 2 (no need to live inside coordinator).
- **AgentCoordinator**: keeps `start_orchestrator`, `start_worker_agent`, `start_worker_agent_and_wait` (delegating to lifecycle + registration), `execute_worker_squad` (delegate to WorkerSquadExecutor), `handle_blueprint_conflict`, `start_sprint`, and references to WorkerSquadExecutor/SprintExecutor. It becomes a thin facade over these services.

**Benefit:** Smaller, testable units; clearer boundaries; easier to change one area (e.g. completion policy or parsing) without touching others.

---

## Summary

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 1 | Remove dead `_execute_*` from AgentCoordinator | Low | Less code, less confusion |
| 2 | Extract agent output parser module | Medium | Testability, extensibility |
| 3 | Extract completion-wait loop | Medium | Readability, maintainability |
| 4 | Deduplicate worker registration in start_worker_agent | Low | DRY, fewer bugs |
| 5 | Single source for stage sequence | Medium | Consistency, easier workflow changes |
| 6 | Shorten WorkerSquadExecutor.execute() | Medium–High | Readability, reuse |
| 7 | Coordinator as facade + smaller components | High | Clear boundaries, testability |

Suggested order: do **1** and **4** first (quick wins), then **2** and **3**, then **5** and **6**. Consider **7** when you’re ready for a larger structural pass.
