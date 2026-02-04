# Redesign Architecture and Intent

Single source of truth for **target architecture** and **feature list** from the redesign (FINAL_PLAN, UI_REDESIGN_PLAN, PROJECT_STRUCTURE). Use this to assess the current codebase and to add/remove/alter code so implementation matches the redesign.

---

## 1. Target architecture (from redesign)

### 1.1 Entry and flow

| Component | Role |
|-----------|------|
| **Entry** | `manifest` or `python -m manifest` → Launcher |
| **Launcher** | (1) Start **View** process (separate window, visualization only). (2) Run **OpenCode**: `opencode . --agent orchestrator -c`. |
| **Chat / commands / tools** | **All in OpenCode terminal.** Manifest does not duplicate chat UI. |
| **View** | Visualization + view switching only. **Does not** run tasks or handle commands. Syncs by watching `.manifest/`. |

### 1.2 Data flow

- **Tasks / sprints**: Orchestrator (OpenCode agent) uses **task_management** / **sprint_management** tools → write `.manifest/tasks.json` → ViewFileWatcher → View refresh.
- **Blueprint / drift**: CodeWatcher / DriftMonitor → `.manifest/blueprint_code.json`, blueprint.json → View.
- **State**: StateManager → `.manifest/state.json`. Tiered context (Tier 0–3) for agents.
- **Workers**: Worker Squad runs **in containers**. Host runs **Container API**; each container runs an agent (e.g. runner.py). Main OpenCode terminal uses channel/tab switching to see per-container messages.

### 1.3 What to keep (from FINAL_PLAN §6)

- WorkflowDefinition, WorkflowEventBus, AgentMessageBus
- Container (Worker Squad container execution), Skills, Failure recovery
- Task Management Tool, Blueprint Sync/Drift (mechanical comparison), Design History
- View (separate process, `.manifest` watch, real-time display)
- OpenCode agents: orchestrator (default), architect, full-test (same level as Orchestrator)

### 1.4 What to remove or not use (from FINAL_PLAN §7)

- **OpenCode Terminal Adapter**: Do not use. OpenCode handles terminal.
- **Our own chat UI**: Do not duplicate. Use OpenCode as-is.

---

## 2. Feature list from redesign

Required (FINAL_PLAN §2) and “keep” (§6) features, as a checklist.

| # | Feature | Redesign intent | Status (assess against code) |
|---|---------|------------------|------------------------------|
| 1 | **Task Management** | Task/Sprint CRUD, state, progress. Real-time. View + OpenCode tools. | Implemented: tools + .manifest/tasks.json + View. |
| 2 | **Ground Truth & Drift** | Top-down vs bottom-up .json → mechanical comparison (no LLM). | Implemented: BlueprintSync, DriftCheck, blueprint_code.json. |
| 3 | **Bottom-up** | Code → mechanical extract → definition docs. | Implemented: CodeWatcher, code extractor, blueprint_code. |
| 4 | **Top-down** | PRD → LLM → blueprint/architecture. | Implemented: PRD/ideation in orchestrator; blueprint/architecture. |
| 5 | **Tiered Context** | Tier 0 (Policy) ~ Tier 3 (surgical code). Per-agent. | Implemented: ContextProvider, task_scoper, .rules. |
| 6 | **State Continuity** | Mission/task state persisted; session resume. | Implemented: StateManager, .manifest/state.json. |
| 7 | **Design Change History** | PRD/blueprint/architecture history. View History = Git + design history. | Partial: Git/history in View; design history may be partial. |
| 8 | **Worker Squad** | planner, coder, test, debug, approver **in containers**, OpenCode, Skills, failure recovery. | Implemented in code; **no trigger** (no OpenCode tool/CLI/API started). |
| 9 | **Container** | Worker = container unit; main terminal = channel/tab per container. | Container API + runner.py exist; **no host server** runs API; worker_squad_spawn is stub. |
| 10 | **Approval** | Tool execution approval, config on/off. | Stub: “approval not implemented”; always allow. |
| 11 | **Full-test agent** | Same level as Orchestrator; project/sprint E2E, integration. | Not wired as OpenCode agent; project_review_agent exists. |
| 12 | **Module output View** | Container output by channel → View in real time. | channel_manager in AgentBridge optional; View does not show container channels. |
| 13 | **Workflow** | WorkflowDefinition for Worker Squad stages/conditions/retry/parallel. | Implemented: WorkflowDefinition, WorkerSquadExecutor. |
| 14 | **Event Bus** | Workflow events (e.g. AGENT_COMPLETED), subscribe/publish. | Implemented: WorkflowEventBus. |
| 15 | **Agent Message Bus** | Agent-to-agent messaging (planner→coder etc.). | Implemented: AgentMessageBus; container_api for container messaging. |
| — | **View (compact)** | Sidebar + metrics; task panel toggle; no chat. | Implemented: ManifestViewApp; chat area is placeholder (OpenCode). |
| — | **OpenCode tools** | task_management, sprint_management, worker_squad_spawn, blueprint_sync, drift_check. | Implemented; worker_squad_spawn only logs (no real spawn). |

---

## 3. Legacy assessment: what to remove or alter

Assess current code against the redesign; remove or change anything that contradicts it.

### 3.1 Remove or reduce

| Item | Reason | Action |
|------|--------|--------|
| **`manifest.ui`** | Chat TUI removed by redesign; only stub left. | Remove `src/manifest/ui/` or keep single `__init__.py` with “Deprecated: use manifest.view”. |
| **OpenCode Terminal Adapter** | FINAL_PLAN §7: do not use; OpenCode handles terminal. | If any module implements “our terminal adapter” for OpenCode, remove or gate behind “internal only”; do not use in main path. |
| **channel_manager dependency in AgentBridge** | Old TUI used it for chat; View does not provide it. | Keep as **optional**: when None, AgentBridge already falls back to state only. Remove any code that *requires* channel_manager for core flow. Optionally later: connect View to container channels (feature #12). |
| **Duplicate chat/command handling** | Any remaining CommandHandler/slash-command logic for chat. | Already removed with ui; ensure no other “chat UI” or duplicate terminal command handling remains. |

### 3.2 Align with redesign (do not remove, but wire correctly)

| Item | Current state | Target (redesign) | Action |
|------|----------------|-------------------|--------|
| **Worker Squad trigger** | No entry: no OpenCode tool, no CLI, no API. | Orchestrator (or user) starts Worker Squad via OpenCode tool or CLI. | Add OpenCode-callable trigger: e.g. tool `start_worker_squad(task_id)` that calls host API or CLI which runs `AgentCoordinator.execute_worker_squad(task_id)` (or equivalent). |
| **Container API** | Exists; only used in tests. | Host runs Container API so containers (runner.py) can talk to host. | Start Container API from Launcher (or a dedicated “host” mode) when Worker Squad / containers are used. |
| **worker_squad_spawn tool** | Logs to worker_spawns.json only; does not spawn. | Should start container (or call host API that starts container). | Implement real spawn: call container manager / host API to start runner container, or document “spawn” = host API call. |
| **Approval** | Permission “ask” → allow; no UI. | Approval on/off in config; when on, tool execution approval. | Implement approval flow when config is on; or clearly mark as “future” and keep allow-only. |
| **View ↔ container channels** | View does not show per-container output. | Feature #12: container output by channel in View. | Either connect AgentBridge channel_manager to View (when running in-process with UI) or stream container output to .manifest/channels or API that View polls. |

### 3.3 Keep as-is (matches redesign)

- Launcher, View (ManifestViewApp), ViewFileWatcher
- OpenCode tools: task_management, sprint_management, blueprint_sync, drift_check (and worker_squad_spawn after it is fixed)
- StateManager, TaskManager, SprintManager, ConfigManager, .manifest/, .rules/
- BlueprintLoader, BlueprintSynchronizer, BlueprintComparator, CodeWatcher, DriftMonitor
- AgentCoordinator, AgentBridge, WorkerSquadExecutor, SprintExecutor (host-side orchestration for Worker Squad)
- runtime/agent (orchestrator, planner, coder, test, debug, approver, project_review), ExecutorFactory, OpenCode LLM Adapter
- WorkflowDefinition, WorkflowEventBus, AgentMessageBus
- Container API (create_container_api), runner.py (container entry)
- Skills, failure recovery, Tiered Context, ContextProvider, task_scoper

---

## 4. Implementation checklist (from redesign)

Use this to drive work; tick when done.

1. **Architecture**
   - [ ] No duplicate chat/terminal handling; OpenCode is the only chat/terminal.
   - [ ] View is visualization-only; .manifest/ watch only.
   - [ ] Worker Squad runs in containers; host runs Container API when needed.

2. **Legacy cleanup**
   - [ ] Remove or deprecate `manifest.ui` (stub only).
   - [ ] Ensure no “OpenCode Terminal Adapter” in main path.
   - [ ] channel_manager in AgentBridge optional; no required dependency on old TUI.

3. **Worker Squad and containers**
   - [ ] Trigger: OpenCode tool or CLI that starts Worker Squad (e.g. `start_worker_squad(task_id)`).
   - [ ] Container API started by Launcher (or documented host start).
   - [ ] worker_squad_spawn tool: real spawn (container or host API), not log-only.

4. **Approval and full-test**
   - [ ] Approval: implement when config on, or document as future.
   - [ ] full-test agent: register as OpenCode agent (same level as orchestrator) if required.

5. **Module output View**
   - [ ] View shows container/channel output (feature #12), or document as follow-up.

6. **Docs and consistency**
   - [ ] PROJECT_STRUCTURE.md, WORKER_SQUAD_AND_AGENTS.md, README point to this doc.
   - [ ] Remove or archive docs that contradict the redesign.

---

## 5. Doc references

- **FINAL_PLAN** (archive): `docs/archive/superseded-2026/FINAL_PLAN.md` — final plan (OpenCode-based).
- **UI_REDESIGN_PLAN**: `docs/UI_REDESIGN_PLAN.md` — layout, sidebar, no chat in View.
- **PROJECT_STRUCTURE**: `docs/PROJECT_STRUCTURE.md` — OpenCode-first layout and data flow.
- **WORKER_SQUAD_AND_AGENTS**: `docs/WORKER_SQUAD_AND_AGENTS.md` — Worker Squad vs OpenCode agents, trigger gap.

All new implementation and refactors should align with **this document** and the redesign; remove or alter legacy code that conflicts with it.
