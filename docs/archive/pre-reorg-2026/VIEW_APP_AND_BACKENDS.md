# View App, Pluggable Backends, Architect, and Reflector

Design notes for (1) making the Manifest View App backend-agnostic and (2) Architect and Reflector agents in the OpenCode interface. Architect (ideation + top-down docs) and Reflector (bottom-up docs) are implemented in code.

---

## 1. View App and Pluggable Backends

### 1.1 Goal

- **One Manifest View App**: we own it; **presentation** is our choice (TUI now, Electron later, etc.).
- The app **connects to a backend** via a single contract. It does not assume orchestrator/worker squad.
- **Orchestrator + worker squad** = separate, optional module (e.g. for full OpenCode/Podman setups). Not required in every dev environment (Cursor, Claude Code, OpenCode, etc.).
- So: **app** = presentation (TUI/Electron) + **backend client**. **Backends** = different implementations (full stack, thin .manifest reader, future Cursor/Claude adapters).

### 1.2 Diagram: One App, Multiple Backends

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Manifest View App (our product)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Presentation (we choose)                                            │    │
│  │     TUI (Textual)  │  Electron  │  future...                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Backend client (single interface)                                   │    │
│  │  - get_project_status()  - get_tasks()  - get_design()  - ...         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
                    Backend contract (in-process adapter or HTTP/WS)
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────────┐         ┌───────────────────┐         ┌───────────────────┐
│  Backend A (Full) │         │  Backend B (Thin) │         │  Backend C        │
│  Orchestrator +   │         │  .manifest only   │         │  (future)         │
│  worker squad,    │         │  Read state,       │         │  Cursor / Claude  │
│  containers       │         │  tasks, blueprint │         │  Code adapter     │
│  (separate module)│         │  Same contract    │         │  Same contract    │
└───────────────────┘         └───────────────────┘         └───────────────────┘
```

### 1.3 Implications

| Piece | Role |
|-------|------|
| **View app** | Presentation (TUI/Electron) + backend client. Uses one backend interface. No orchestrator/worker logic inside the app. |
| **Backend interface** | Contract the app expects: project status, tasks, design, mission, etc. (structured/JSON). In-process or HTTP/WS. |
| **Backend implementations** | **Thin**: reads `.manifest/` only (Cursor, Claude Code, etc.). **Full**: orchestrator + worker squad as a separate module implementing the same contract. **Others**: Cursor/Claude/OpenCode-specific adapters. |
| **Orchestrator + worker squad** | Separate module; optional. Used only where that stack runs. The app does not depend on it—only on “a backend” fulfilling the contract. |

### 1.4 Changes Needed (when implemented)

1. **Define the backend contract**: what the view app needs (project status, tasks, design/mission/inspector view data). One small API (methods or HTTP + payload types).
2. **Make the app backend-client only**: app (TUI or Electron) does not instantiate StateManager/Orchestrator; it has a backend client that fulfills the contract.
3. **Implement at least two backends**: (a) Thin: reads `.manifest/` and returns the contract. (b) Full: current orchestrator + worker squad (separate module) exposing the same contract.
4. **Presentation stays in the app**: TUI vs Electron is how the app renders data from the backend.

---

## 2. Architect Agent (OpenCode Interface)

### 2.1 Goal

- **Architect** agent: available through the main OpenCode interface; user can switch between **orchestrator** and **architect**.
- **Architect** can ideate with the user and write **top-down docs only**: PRD, architecture, intent (`.manifest/prd.json`, `.manifest/architecture.json`, `.manifest/intent.json`).
- **No other permissions**: no edit, no write (except via the architect tool), no bash, no task_management, no worker_squad_spawn. The only way to persist is the **architect** tool.

### 2.2 Implementation (in code)

- **Architect tool** (`runtime/opencode/tools/architect_tool.py`): actions `write_prd`, `write_architecture`, `write_intent`, `ideate`. Writes only to the three top-down doc paths.
- **Tool definition** in `tool_definitions.py`; **ToolExecutor** branch `architect`; **PermissionManager** agent type `architect` with read=allow, write=deny, edit=deny, bash=deny.
- Orchestrator is denied from writing top-down docs (orchestrator does not get the architect tool; only architect agent gets it). Bottom-up docs are written by the Reflector (or relevant agent), not the orchestrator.

### 2.3 Diagram: Agent Selection in OpenCode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  OpenCode (main interface)                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Agent selection (user switch)                                        │    │
│  │     [ Orchestrator ]  │  [ Architect ]                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
┌───────────────────────────────┐           ┌───────────────────────────────┐
│  Orchestrator agent          │           │  Architect agent              │
│  - Assign tasks, coordinate  │           │  - architect tool only       │
│  - task_management,          │           │    (write_prd, write_arch,    │
│    worker_squad_spawn, etc.  │           │    write_intent, ideate)      │
│  - Cannot write top-down docs│           │  - read for ideation         │
│                               │           │  - No edit, no bash, no      │
│                               │           │    task_management           │
└───────────────────────────────┘           └───────────────────────────────┘
```

---

## 3. Reflector Agent (Bottom-Up Docs)

### 3.1 Goal

- **Reflector** is the agent that produces **bottom-up docs** from code: `blueprint_code.json`, `intent_code.json`, `architecture_code.json`.
- Renamed from `bottom_up_docs` in code (`opencode_llm_adapter.py`: `REFLECTOR_AGENT_ID = "reflector"`).
- Bottom-up docs are written by the Reflector (or relevant agent), not the orchestrator.

### 3.2 In Code

- Session/agent type in OpenCode LLM adapter: `reflector` (was `bottom_up_docs`).
- PermissionManager agent type `reflector`: read=allow, write=allow (for bottom-up doc files), edit=deny, bash=deny.

---

## 4. Summary

- **View app**: One app, our presentation (TUI/Electron), connects to different backends via a single contract. Orchestrator/worker squad is a separate, optional backend.
- **Architect**: Agent that can ideate and write only top-down docs (PRD, architecture, intent) via the `architect` tool; no other permissions.
- **Reflector**: Agent/session that produces bottom-up docs from code (renamed from bottom_up_docs).
- **Orchestrator**: Assigns tasks, coordinates; does not write top-down or bottom-up docs.
