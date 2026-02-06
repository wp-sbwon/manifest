# Features & Requirements from User Flow

Features and requirements are defined from **user flow**: what the user can do and what the system must provide. This document is the source of truth for product scope derived from user capabilities.

---

## User-flow principles

- **OpenCode is the interface.** Chat, terminals, and agent UX are real OpenCode. We do not duplicate them.
- **Main chat = orchestrator only.** On the main OpenCode session the agent orchestrates; it does not code or run worker workflows itself. The user talks to the orchestrator there.
- **Structured docs = JSON.** All project-wide design and state (PRD, architecture, blueprint, features, requirements) are **formatted/structured JSON**, not markdown. History is traced like git (versioned, visible).
- **View = visualization + progress.** View shows tasks, structure, progress, drift, history, and worker traces. User does not type into View for chat; commands go through OpenCode.

---

## 1. Use the service like OpenCode

**User can:** Use the service exactly as he would use OpenCode — chat interface, references, commands, etc. are all actual OpenCode.

**Requirements:**
- Entry: `manifest` starts View + OpenCode. OpenCode is the primary UI.
- No duplicate chat/terminal from Manifest. All interaction happens in OpenCode.
- On the **main** OpenCode chat, the agent is the **orchestrator**: it does not code or run worker workflows directly; it coordinates, delegates, and manages tasks/sprints/design.

---

## 2. Ideate with orchestrator → project-wide PRD and top-down docs

**User can:** Ideate with the orchestrator to form a **project-wide PRD**, which is broken down (by LLM agent) into **architecture, blueprint, features, and requirements** — the essential information needed for projects. This is **top-down**. All outputs are **formatted/structured docs (JSON, not MD)**. When the user adds/edits, he does so by talking to the orchestrator; that **renews the top-down docs**. Bottom-up changes (from the worker squad) can **suggest** changes to architecture etc.; the user **confirms (approves)** them, which **triggers top-down renewal** again. All docs are **traced like git history** and visible.

**Requirements:**
- Orchestrator has an **ideation** mode: conversation → PRD (JSON).
- PRD flows down to: architecture (JSON), blueprint (JSON), features (JSON), requirements (JSON). Breakdown is done by LLM agent(s), not manually.
- User edits via conversation with orchestrator → top-down docs are regenerated/updated.
- Worker squad or bottom-up can propose changes to architecture/blueprint; user **approves** → approval triggers top-down renewal (orchestrator/LLM regenerates affected docs).
- **Doc history:** All these docs have versioned history (like git); history is visible in View and traceable.

**Managed docs (top-down & traced):** PRD, architecture, blueprint, features, requirements — all JSON. Same schema used for both top-down (design) and bottom-up (ground truth) where applicable, so they can be mechanically compared.

---

## 3. Orchestrator creates sprints and tasks; user sees and controls them

**User can:** Have the orchestrator create a **sprint** (a set of tasks to be performed). User can **always see** these tasks and the process, and can **order the orchestrator** to add new tasks, cancel/delete, or edit tasks.

**Requirements:**
- Orchestrator can create sprints and tasks (via tools or equivalent). Tasks and sprints are stored in a structured form (e.g. `.manifest/tasks.json` or equivalent).
- View shows **task list and process** (status, order, progress) in real time.
- User can instruct the orchestrator (via main chat) to: add tasks, cancel/delete tasks, edit tasks. Orchestrator executes these commands and updates the stored task/sprint data.

---

## 4. Orchestrator breaks down tasks for Worker Squad (TDD workflow)

**User can:** Rely on the orchestrator to break down tasks into **granularity** suitable for a worker squad that follows **TDD**, with workflow: **test creation → coding → testing → debugging → review → approval**. Each step is handled by a **different agent** with a **different scope of tools**. The orchestrator **manages the context** provided to the worker squad. The orchestrator **must not be blocked** by coding work — i.e. it stays **available for chat** to the user unless it is in the middle of a **large orchestrator-level job** (e.g. big ideation or plan generation).

**Requirements:**
- Task granularity: suitable for TDD and worker squad (bounded scope per task).
- Worker workflow: test creation → coding → testing → debugging → review → approval. Each stage = different agent, different tool scope.
- Orchestrator is responsible for: task breakdown, context assembly for each worker, and delegating work. It does not run the coding/test/debug steps itself.
- Orchestrator remains responsive: not blocked by worker execution; only possibly busy during heavy orchestrator-only work.

---

## 5. Worker squad in separate containers; each agent = OpenCode process

**User can:** Have the **worker squad** run in **separate containers**. Each agent in the worker squad is an **individual OpenCode process** — as if the user had multiple OpenCode terminals, each with a different agent.

**Requirements:**
- Worker squad runs in **containers** (one per worker or per task/session as designed).
- Each worker agent runs as an **OpenCode process** (or equivalent) inside its container — same UX model as multiple OpenCode terminals with different agents.

---

## 6. Worker squad traces and read-only “chat rooms”

**User can:** See **traces** from the worker squad like normal agents. User can access **per–worker-squad “chat rooms”** (one per squad or per task) — **via OpenCode terminal**, same look and feel, except **user cannot input**; user only **sees messages**. **Input is done by the orchestrator**, not the user. (Conceptually: an OpenCode terminal that looks the same, but input is from the orchestrator agent.)

**Requirements:**
- Worker squad produces **traces** (message stream) like normal agents.
- User can open a **view** of each worker squad’s “room” (e.g. via OpenCode terminal or View): same UI as chat, but **read-only** for the user. Messages are visible; input to that room is from the **orchestrator** (orchestrator sends instructions/context to the squad), not from the user typing.

---

## 7. E2E test agent at orchestrator level

**User can:** Have an **E2E test agent** for the **whole scope**, on the **same level as the orchestrator** (i.e. not inside the worker squad; a top-level agent like the orchestrator).

**Requirements:**
- An **E2E / full-test agent** exists, same level as orchestrator (e.g. same OpenCode agent tier). It can run project/sprint-wide E2E and integration tests.
- It is available independently of the worker squad workflow (e.g. triggered by user or orchestrator).

---

## 8. Task progress always visible in View

**User can:** Always see **task progress** in the View.

**Requirements:**
- View shows **task and sprint progress** (e.g. status, completion, which stage) in real time. Data source: task/sprint store (e.g. `.manifest/tasks.json`) and any worker/sprint status the orchestrator writes. View updates when that data changes (e.g. file watch or API).

---

## 9. Bottom-up: code → structured docs and drift

**User can:** Rely on **bottom-up** flow: as code is built, on a **regular basis** (or by trigger), the **codebase is translated** into higher-level information (e.g. **blueprint**) — producing **formatted docs (JSON)**. This is the **ground truth** of current structure. For things like **architecture**, an **LLM agent** reads the ground-truth docs and builds **formatted docs (JSON)**. Bottom-up produces the **same schema** as top-down; docs are **mechanically matched** (no LLM for the match). If there is **drift**, the user is **notified** for resolving. The level of detail goes down to **methods/classes and dependencies**. All managed docs and their schemas are organized (see “Managed docs” below and legacy code/docs).

**Requirements:**
- **Scheduled or triggered** bottom-up: code → mechanical extraction → JSON (e.g. blueprint / structure). This is **ground truth** of current code.
- For higher-level constructs (e.g. architecture, features), an **LLM agent** consumes ground-truth JSON and produces **formatted JSON** (same schema as top-down where applicable).
- **Same schema** for top-down and bottom-up where they describe the same thing (e.g. blueprint, components). **Drift = mechanical comparison** (diff of JSON or normalized form), not LLM decision. User is **notified** on drift for resolution.
- Granularity: at least down to **methods, classes, and dependencies**. Legacy docs and code (e.g. blueprint_code.json, architecture.json, intent.json, CodeWatcher, BlueprintSynchronizer) define the exact docs and fields to manage.

---

## 10. Architecture and structure visible (diagram + tree + progress)

**User can:** See **architecture and all relevant information** (blueprint, features, components, etc.) **intuitively** — in **diagram** and **tree** formats. **Structure and progress** are visible: e.g. structured diagram with data flows, and **completion state** (not built, 70% built, etc.). Top-down docs provide the **skeleton**; bottom-up shows **current status**. As with top-down, **all doc history** is well managed and **visible in View**.

**Requirements:**
- View provides **diagram** and **tree** views of: architecture, blueprint, features, components, data flow.
- **Progress** is visible: e.g. which parts are built, partially built (e.g. 70%), or not started. Top-down = target/skeleton; bottom-up = current state; combine for progress.
- **History** of all these docs is managed and visible in View (same as §2).

---

## 11. Shadow process for per-component output (visual)

**User can:** See **what output each module/component** in the structure **actually produces**, via a **shadow process** that provides this on the **visual** side.

**Requirements:**
- A **shadow process** (or equivalent) runs to expose, for the user, the **output of each module/component** in the structure. This is shown in the View (or linked OpenCode/terminal view) so the user can see per-component output visually.

---

## 12. User can see and manage resources (e.g. tokens)

**User can:** **See and manage resources** (e.g. **tokens**, API usage, costs).

**Requirements:**
- View or settings expose **resource usage** (e.g. tokens, calls, optional cost). User can **manage** (e.g. set limits, choose models, or adjust settings that affect resource use). Where this lives (View vs OpenCode vs .manifest/settings) is an implementation detail; the capability must exist.

---

## 13. Project rules and skills (.rules)

**User can:** Rely on **project rules** (task granularity, code style, PRD template, etc.) so the orchestrator and worker squad follow them; context and tool scope respect these rules.

**Requirements:**
- **Project rules** live in **.rules/** (or equivalent): e.g. task-granularity (max files per task, recommended scope), code-style, PRD template. Format can be JSON or MD for templates; canonical project state remains JSON.
- **Orchestrator** and **workers** are instructed to read and follow .rules; orchestrator uses them for task breakdown and context; workers use them for scope and style.
- **Skills** (agent-specific rules or capabilities) are defined and loaded so each agent type (planner, coder, test, etc.) gets the right skills. Legacy: SkillsManager, .rules/*.md, agent_config.json agent_skills.
- **Tiered context** (Tier 0 Policy ~ Tier 3 surgical code) is provided per agent; Tier 0 includes policy from .rules; scope is bounded by task granularity and .rules.

---

## 14. Failure recovery (Worker Squad)

**User can:** Have the **worker squad** recover from failures (retry, skip, or escalate) instead of stopping the whole run.

**Requirements:**
- **Worker squad workflow** supports **failure recovery**: on stage failure (timeout, API error, validation error, etc.), the system can **retry** (same or simplified prompt), **skip** the stage and continue, or **escalate** (e.g. notify user or orchestrator). FINAL_PLAN: "Failure recovery required."
- **Failure analysis** (e.g. FailureAnalyzer) determines cause and suggests strategy (retry, skip, manual intervention). Legacy: failure_recovery.py, WorkerSquadExecutor recovery paths.
- **Event bus** (e.g. STAGE_FAILED, AGENT_COMPLETED) drives stage transitions and recovery; workflow definition (WorkflowDefinition) can define retry/conditions. Legacy: WorkflowEventBus, WorkflowDefinition.

---

## 15. Tool execution approval (config on/off)

**User can:** Optionally **approve or deny** tool executions (e.g. bash, edit, write) before the agent runs them. This is **separate** from design-change approval (§2); it is **tool-level** approval. When disabled, tools run without asking.

**Requirements:**
- **Config on/off**: User can enable "ask before tool run" (e.g. in .manifest/settings.json or View/settings). When **on**, the agent’s tool call (bash, edit, write, etc.) is **pending** until the user **approves or denies** (in UI or chat). When **off**, tools run as today (no approval step).
- **Scope**: Applies to tools that change state or run commands (e.g. terminal, file edit/write). Read-only tools (e.g. read, grep) may be excluded by policy.
- **UX**: User sees pending tool request (e.g. in OpenCode chat or View) and can approve/deny. Denied requests do not run; agent can be informed and retry or report.

---

## Managed docs and schemas (from legacy and redesign)

All of these are **JSON** (no MD for canonical project state). History is traced and visible where required above.

| Doc | Purpose | Top-down / Bottom-up | Notes |
|-----|---------|----------------------|--------|
| **prd.json** | Product requirements | Top-down (ideation) | PRDManager, StateManager |
| **intent.json** | High-level goals, features | Top-down; can be refined by LLM from code | context_provider, task_scoper |
| **architecture.json** | Architecture (components, features) | Top-down + LLM from bottom-up | Same schema for comparison |
| **blueprint.json** | Component blueprint (top-down design) | Top-down | BlueprintLoader, BlueprintSynchronizer |
| **blueprint_code.json** | Ground truth from code (bottom-up) | Bottom-up (mechanical + LLM for higher levels) | CodeWatcher, DriftMonitor |
| **tasks.json** | Tasks and sprints | Orchestrator / tools | TaskManagementTool, View |
| **state.json** | Mission/task state, session | Runtime | StateManager |
| **worker_spawns.json** | Worker spawn log | Runtime | WorkerSquadSpawnTool |
| **sprints/** | Sprint files (e.g. sprint-{id}.json) | Orchestrator | StateManager |
| **Design history** | PRD / architecture / blueprint history | — | Versioned, visible in View (§2, §10) |

Ensure all managed docs are listed and schemas are aligned for **mechanical drift** (top-down vs bottom-up). Legacy code: `manifest_dir` usage, `BlueprintLoader`, `BlueprintSynchronizer`, `CodeWatcher`, `DriftMonitor`, `PRDManager`, `task_scoper` (intent, blueprint), `context_provider` (Tier 1 = intent, architecture).

---

## Other requirements from legacy (covered above or implicit)

Legacy docs (FINAL_PLAN, CORE_FEATURES_STATUS, MANIFEST_REQUIREMENTS, MODULES, and related) were checked. No additional features were added beyond the 15 above; anything from legacy that matters for user flow is already reflected in those features or in the managed docs.

---

## Summary: 15 user-flow features

| # | Feature | One-line |
|---|---------|----------|
| 1 | Use service like OpenCode | Chat/UI = OpenCode; main chat = orchestrator only (no coding there). |
| 2 | Ideate → PRD → top-down docs | Orchestrator ideation → PRD/architecture/blueprint/features/requirements (JSON). User/edit → renew. Bottom-up suggestions → user approval → top-down renewal. All docs traced (git-like history). |
| 3 | Sprints and tasks | Orchestrator creates sprints/tasks; user sees them and can add/cancel/edit via orchestrator. |
| 4 | Task breakdown for Worker Squad | Granularity for TDD; workflow test→code→test→debug→review→approval; per-agent tool scope; orchestrator manages context; orchestrator not blocked. |
| 5 | Worker squad in containers | Each worker = separate container; each agent = OpenCode process. |
| 6 | Worker traces and read-only rooms | User sees worker squad traces; per-squad “chat room” (OpenCode-like, read-only for user; input = orchestrator). |
| 7 | E2E test agent | Same level as orchestrator; whole-scope E2E. |
| 8 | Task progress in View | Always visible in View. |
| 9 | Bottom-up and drift | Code → JSON (blueprint/structure); mechanical + LLM where needed; same schema as top-down; mechanical drift; notify user. Down to methods/classes/deps. |
| 10 | Architecture/structure visible | Diagram + tree; structure + progress (skeleton + current status); doc history in View. |
| 11 | Shadow process for component output | Visual: what each module/component outputs. |
| 12 | See and manage resources | Tokens etc. visible and manageable. |
| 13 | Project rules and skills (.rules) | Task granularity, code style, PRD template; orchestrator and workers follow; tiered context respects .rules. |
| 14 | Failure recovery (Worker Squad) | Retry, skip, or escalate on stage failure; event-driven; WorkflowDefinition. |
| 15 | Tool execution approval | Config on/off; when on, user approves/denies tool runs (bash, edit, etc.) before execution. |

All new implementation should align with these 15 features and the managed docs above.
