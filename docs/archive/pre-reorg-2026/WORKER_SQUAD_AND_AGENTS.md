# Worker Squad and Agent Registration Status

## Summary

| Area | Status | Description |
|------|--------|-------------|
| **Worker Squad logic** | Done | Inside Manifest (WorkerSquadExecutor, AgentCoordinator) |
| **Worker agent classes** | Done | planner, coder, test, debug, approver, project_review, etc. (AgentManager) |
| **OpenCode agent registration** | Partial | orchestrator, architect, etc. in `.opencode/agents/orchestrator.json`, `architect.json` |
| **Worker agent OpenCode registration** | None | planner, coder, test, etc. are not registered as OpenCode agents |
| **Worker Squad trigger** | Missing | Old TUI `/start_task` removed; need API/tool callable from OpenCode |

---

## 1. How the Worker Squad is implemented

### 1.1 Execution flow

```
AgentCoordinator.execute_worker_squad(task_id)
  → WorkerSquadExecutor.execute(task_id)
  → Stage-by-stage execution:
       planner → tdd_test → coder → test → debug → self_review → approver
  → Each stage: coordinator.start_worker_agent(task_id, agent_type, stage=...)
  → AgentBridge.start_agent_mission(task_id, agent_type, ...)
  → AgentManager.create_agent() → PlannerAgent / CoderAgent / TestAgent, etc.
  → executor.execute_agent() → LLM call (OpenCode LLM Adapter or Direct API)
```

### 1.2 Code locations

| Role | File | Description |
|------|------|-------------|
| Workflow orchestration | `src/manifest/agents/worker_squad_executor.py` | Stage order, event-driven, timeout, recovery |
| Agent startup | `src/manifest/agents/agent_coordinator.py` | `start_worker_agent`, `_start_task_worker_squad`, `execute_worker_squad` |
| Agent–executor bridge | `src/manifest/bridge/agent_bridge.py` | `start_agent_mission`, planner/coder channel handling |
| Agent creation/execution | `src/manifest/runtime/agent/core/manager.py` | `create_agent`, planner/coder/test/debug/approver, etc. |
| planner | `src/manifest/runtime/agent/agents/planner_agent.py` | PlannerAgent |
| coder | `src/manifest/runtime/agent/agents/coder_agent.py` | CoderAgent |
| test | `src/manifest/runtime/agent/agents/test_agent.py` | TestAgent |
| debug | `src/manifest/runtime/agent/agents/debug_agent.py` | DebugAgent |
| approver | `src/manifest/runtime/agent/agents/approver_agent.py` | ApproverAgent |
| project_review | `src/manifest/runtime/agent/agents/project_review_agent.py` | ProjectReviewAgent |

Worker Squad and planner/coder/test, etc., are implemented **inside Manifest** only; they are separate from the “chat agents” visible in the OpenCode UI.

---

## 2. Agent registration status

### 2.1 OpenCode side (project `.opencode/agents/`)

- **Registered**: orchestrator, architect, etc.
  - Files: `.opencode/agents/orchestrator.json`, `architect.json`, etc.
  - Purpose: Used as “default agents” in OpenCode chat (mission coordination, task breakdown, guidance).

- **Not registered**: planner, coder, test, review, debug, approver, project_review
  - These types have no JSON in `.opencode/agents/`.
  - OpenCode does not treat them as “agents”.

### 2.2 Manifest side (internal “agents”)

- **Registered/configured**:
  - `AgentManager` creates planner, coder, test, debug, approver, project_review, e2e_test, integration_test **in code**.
  - Instances created via `create_agent(agent_type="planner")`, etc.; then `Executor` (OpenCode LLM Adapter or Direct API) performs LLM calls.

In short:

- **OpenCode agent registration**: orchestrator, architect, etc. are registered.
- **Worker squad “agents”**: Not registered in OpenCode; created and run **inside Manifest** only.

---

## 3. How to run the Worker Squad today

- **Past**: When the TUI existed, `CommandHandler` called `/start_task <task_id>` → `agent_coordinator._start_task_worker_squad(task_id)` → Worker Squad ran.
- **Current**: TUI (CommandHandler) was removed, so **there is no path to start the Worker Squad from OpenCode chat alone.**

Implementation exists, but there is no “press to run” entry point.

Possible directions:

1. **Add an OpenCode-callable Manifest tool**
   - Define a tool such as `start_task(task_id)` and wire OpenCode tool calls to a Manifest API (e.g. HTTP or local CLI).
   - Inside that API, call `AgentCoordinator.execute_worker_squad(task_id)` or `_start_task_worker_squad(task_id)`.

2. **Provide a local CLI**
   - Add a command such as `manifest start-task <task_id>` that calls `execute_worker_squad(task_id)` internally.
   - Users run it from the terminal, or OpenCode invokes it via the `terminal` tool.

3. **Register workers as OpenCode “subagents”**
   - If OpenCode supports subagent/tool invocation, register “planner”, “coder”, etc. as subagents that wrap an API/CLI calling Manifest’s corresponding agent type.
   - Depends on OpenCode docs/spec.

---

## 4. Summary

- **Worker Squad**: Fully implemented inside Manifest (stages, agent classes, bridge, executor).
- **Agent registration**:
  - **orchestrator**, **architect**, etc. are registered in OpenCode.
  - planner, coder, test, etc. are **not** registered as OpenCode agents; they are used only **inside** Manifest.
- **Execution trigger**:
  - The old `/start_task` path is gone; to run tasks/Worker Squad from OpenCode, one of the **API/CLI/OpenCode tool** options above must be added.

This document describes the current status.
