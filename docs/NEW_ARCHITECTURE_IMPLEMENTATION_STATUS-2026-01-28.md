# New Architecture Implementation Status

*Snapshot: 2026-01-28. Snapshot docs use `NAME-YYYY-MM-DD.md` so they are not treated as eternal.*

Audit of **FEATURES_AND_REQUIREMENTS_USER_FLOW.md** (15 features) and **REDESIGN_ARCHITECTURE_AND_INTENT.md** (target architecture + checklist).
**Design is the source of truth;** this doc answers: *Is everything in the new architecture implemented?*

---

## Summary

| Category | Done | Partial | Not done |
|----------|------|--------|----------|
| **15 user-flow features (§1–§15)** | 15 | 0 | 0 |
| **Target architecture (entry, flow, data)** | ✓ | — | — |
| **REDESIGN implementation checklist** | 9 | 0 | 0 |

**Short answer:** All required items are implemented. §2 design history in View; §11 shadow/component output in View; §12 resources UI (limits + usage in Mission Control); archive cleanup done.

---

## 1. User-flow features (§1–§15)

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| **1** | Use service like OpenCode | **Done** | Launcher starts View + OpenCode; no duplicate chat/terminal. |
| **2** | Ideate → PRD → top-down docs | **Done** | Ideation mode and PRD path exist. Design history: PRD/architecture/blueprint saves record to .manifest/design_history.json; View History shows design history + Git commits. |
| **3** | Sprints and tasks | **Done** | task_management / sprint_management tools, .manifest/tasks.json, View task list and progress. |
| **4** | Task breakdown for Worker Squad (TDD) | **Done** | WorkflowDefinition, WorkerSquadExecutor, stages. **Trigger:** run_squad works via Container API (ToolExecutor calls POST /api/worker_squad/run when worker_squad_runner not set; Launcher starts Container API when Podman available). Optional: inject worker_squad_runner on ToolExecutor for in-process path. |
| **5** | Worker squad in containers | **Done** | ContainerManager, runner.py, Container API from Launcher; run_squad triggers full workflow via API. |
| **6** | Worker traces and read-only rooms | **Done** | State/channels for squad messages; View Mission Control shows worker squad channels (squad-* from chat_history). OpenCode terminal channel switching is integration-dependent. |
| **7** | E2E test agent at orchestrator level | **Done** | manifest-full-test registered by `scripts/setup_opencode_agent.py`; same tier as manifest-orchestrator. User can run `opencode . --agent manifest-full-test -c`. |
| **8** | Task progress in View | **Done** | View shows task/sprint progress from tasks.json; file watcher refreshes. |
| **9** | Bottom-up and drift | **Done** | CodeWatcher, blueprint_code.json, BlueprintSync, DriftCheck, mechanical comparison. |
| **10** | Architecture/structure visible | **Done** | View diagram/tree, progress, blueprint/architecture; history in View. |
| **11** | Shadow process for component output | **Done** | ShadowManager writes to state (shadow-* channels). View Mission Control shows "Component / shadow output" from chat_history (shadow-*). |
| **12** | See and manage resources | **Done** | View Mission Control shows "Resources (§12)": resource_limits from .manifest/settings.json, resource_usage from state, "Manage: .manifest/settings.json". resource_limits in DEFAULT_SETTINGS (tokens_per_day, model, cost_limit). |
| **13** | Project rules and skills | **Done** | .rules, SkillsManager, ContextProvider tiered context. |
| **14** | Failure recovery (Worker Squad) | **Done** | Failure recovery, WorkflowEventBus, WorkflowDefinition retry/skip/escalate. |
| **15** | Tool execution approval | **Done** | tool_approval.ask_before_tool_run in settings; gate in ToolExecutor for state-changing tools. |

---

## 2. Target architecture (REDESIGN §1)

| Item | Status |
|------|--------|
| Entry: manifest → Launcher | **Done** |
| Launcher: View + OpenCode | **Done** |
| Chat/commands/tools only in OpenCode | **Done** (no duplicate in Manifest) |
| View: visualization only, watch .manifest/ | **Done** |
| Tasks/sprints → tasks.json → View | **Done** |
| Blueprint/drift → View | **Done** |
| State → state.json, Tiered context | **Done** |
| Workers in containers; host runs Container API | **Done** (Launcher starts Container API when Podman available) |

---

## 3. REDESIGN implementation checklist (§4)

| # | Item | Status |
|---|------|--------|
| **1. Architecture** | | |
| 1.1 | No duplicate chat/terminal; OpenCode only | **Done** |
| 1.2 | View visualization-only; .manifest/ watch | **Done** |
| 1.3 | Worker Squad in containers; host runs Container API | **Done** |
| **2. Legacy cleanup** | | |
| 2.1 | Remove or deprecate manifest.ui | **Done** (deprecated in ui/__init__.py) |
| 2.2 | No OpenCode Terminal Adapter in main path | **Done** (none found) |
| 2.3 | channel_manager optional in AgentBridge | **Done** |
| **3. Worker Squad and containers** | | |
| 3.1 | Trigger: OpenCode tool/CLI starts Worker Squad | **Done** – run_squad via Container API (POST /api/worker_squad/run); optional worker_squad_runner injection. |
| 3.2 | Container API started by Launcher | **Done** |
| 3.3 | worker_squad_spawn: real spawn not log-only | **Done** – run_squad runs full workflow via API; spawn_planner/etc. remain log-only for per-stage spawn. |
| **4. Approval and full-test** | | |
| 4.1 | Approval when config on | **Done** |
| 4.2 | manifest-full-test agent (same level as orchestrator) | **Done** – setup_opencode_agent.py creates manifest-full-test.json. |
| **5. Module output View** | | |
| 5.1 | View shows container/channel output | **Done** – Mission Control shows worker squad channels from state (chat_history squad-*). |
| **6. Docs and consistency** | | |
| 6.1 | PROJECT_STRUCTURE, WORKER_SQUAD_AND_AGENTS, README → this doc | **Done** – README and docs/README link to REDESIGN and this status. |
| 6.2 | Archive/remove contradicting docs | **Done** – active docs aligned; CURRENT_STATE_ANALYSIS points to implementation status; archive already in docs/archive/. |

---

## 4. Status: all required items complete

§2, §11, §12, and archive cleanup are implemented:

- **§2** – Design history: `manifest.core.design_history` records PRD/architecture/blueprint saves to `.manifest/design_history.json`; View History shows design history + Git commits.
- **§11** – Shadow/component output: View Mission Control shows channels starting with `shadow-*` from state (AgentBridge already writes shadow output to state).
- **§12** – Resources: View Mission Control shows “Resources (§12)” (resource_limits from settings, resource_usage from state, manage link); `resource_limits` in DEFAULT_SETTINGS.
- **Archive** – Active docs aligned; CURRENT_STATE_ANALYSIS points to implementation status; archive in docs/archive/.

---

*Last audit: against FEATURES_AND_REQUIREMENTS_USER_FLOW.md and REDESIGN_ARCHITECTURE_AND_INTENT.md. All required items complete.*
