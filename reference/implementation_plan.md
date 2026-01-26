# Manifest TUI MVP: Final Implementation Plan

Manifest is an **AI-Native Orchestration IDE** designed to solve "Code Blindness" by elevating the developer to a **Conductor**. This plan achieves **Phase 1: TUI MVP** by integrating agent system as the back-end engine and building a high-fidelity **Textual-based interface**.

## User Review Required

> [!IMPORTANT]
> **API Bootstrap Gate**: Upon startup, Manifest will verify the presence of required API keys (Anthropic, Google, OpenAI).
> - If keys are missing, the app will enter a **Bootstrap Mode**, providing a TUI interface to configure and save keys locally.
> - The IDE functionality is **completely blocked** until valid keys are detected and verified via a simple ping test.

> [!IMPORTANT]
> **Manifest Context Engine (Tiered Orchestration)**:
> Context is no longer a dump of all files. Manifest manages what an agent sees based on the Mission Stage.
> - **Tier 0 (The Law)**: `.claude/rules/manifest-policy.md` is forced into EVERY agent.
> - **Tier 1 (The Intent)**: `architecture.json` and high-level goals are provided to the **Planner**.
> - **Tier 2 (The Blueprint)**: Relevant `blueprint.json` nodes and their structural specs are provided to the **Coder**.
> - **Tier 3 (Surgical Code)**: Full file contents are ONLY provided for files referenced in the `blueprint.json` or specifically requested by the agent via `LSP/AST-Grep` exploration.

> [!IMPORTANT]
> **Context Injection Hooks**: The `agent_bridge.py` will actively intercept agent prompts to inject "Visual Reality" updates.
> - Example: "Dependency Node [AuthAPI] is currently in GHOST status; do not attempt to call its real endpoints yet."

> [!IMPORTANT]
> **Structural Spec-First Management**: File system structure is managed as part of the Blueprint.
> - **Structural Proposals**: Agents must propose directory changes (creating, moving, deleting) in the `blueprint.json` before execution.
> - **Structural Drift**: The **Drift Resolver** treats an unexpected folder or a missing file as a high-priority architectural conflict.
> - **Logical Explorer**: The TUI's **Feature Explorer** view will group files by **Feature Logic** rather than just physical path, bridging the gap between intention and file system.

> [!IMPORTANT]
> **Validation Gate**: The `agent_bridge.py` will act as a strict validator. Any agent action that modifies architecture without matching the JSON schema will be automatically rejected and the agent will be "Locked" until the spec is corrected.

## Proposed Changes

### 1. Core Orchestrator (The Command Center)
The central Python engine that manages state, IPC, and agent squads.

#### [NEW] [agent_bridge.py](file:///Users/wonseongbae/Documents/GoogleAG/Manifest/agent_bridge.py)
- **Agent System Integration**: Direct integration with agent system for maximum speed.
- **State Persistence (Continuation Enforcer)**:
    - Serialize Mission Tree, Task Checklist, and Chat History to `.manifest/state.json`.
    - Handle session resumption with "Next Action" prompts.
- **Drift Auditor**: Use **AST-Grep** to compare code structure against `blueprint.md` in real-time.
- **Shadow Manager**: Sandbox operations and safe promotion (merge) logic.

---

### 2. The 5-View Workspace (Unified IDE)
A modular interface built with the Textual library, supporting the PRD's vision.

#### [MODIFY] [app.py](file:///Users/wonseongbae/Documents/GoogleAG/Manifest/app.py)
- **View 1: Architect (Intention)**:
    - **Visual Intent Map**: Renders \`architecture/intent.md\` showing Features, Requirements, and User Goals.
    - Powered by \`intent.json\`.
- **View 2: Blueprint (Design)**:
    - **Visual Translation**: Renders \`architecture/blueprint.md\` showing the technical API contract (Classes/Methods).
    - Powered by \`blueprint.json\`.
- **View 3: Inspector (Verification)**:
    - **Visual Mode**: UI Match (Figma vs Mock).
    - **Data Mode**: Execution trace and input/output flow.
    - **Drift Mode**: Architecture vs Code conflict resolution UI.
- **View 4: Mission Control (Management)**:
    - Hierarchical **Task Tree** with status rings.
    - **Approval Gates**: Command buttons to promote tasks between stages.
- **View 5: History (Timeline)**: Git-linked timeline to roll back design and code simultaneously.
- **EXPANSION: Feature Explorer**: A dedicated navigation pane for **Feature -> Class -> Method** exploration.

#### [NEW] [widgets.py](file:///Users/wonseongbae/Documents/GoogleAG/Manifest/widgets.py)
- `RequirementMap`: Visualizes high-level feature dependencies and goal hierarchies.
- `ArchitectureGraph`: Node-edge visualization with status overlays.
- `FeatureTree`: AST-aware code navigation.
- `TaskTree`: Status-aware mission tracker.
- `GateController`: Approval buttons (Approve/Reject/Feedback).

---

### 3. Multi-Agent Communication (Squad System)
Layered chat context for focused collaboration.

#### [MODIFY] [app.py](file:///Users/wonseongbae/Documents/GoogleAG/Manifest/app.py)
- **Orchestrator Chat (#manifest-ai)**: Main control for high-level directives.
- **Agent Squad Channels**: Dynamic tabs (e.g., `#squad-payment`) for mission-specific logs and talk-to-agent interactions.
- **Thought Streaming**: Agents push their "Internal Checklists" and "Mental State" into these channels.

---

### 4. Agent & Spec Integration
Tuning agent system to work within the Manifest "Visual Truth" framework.

#### [MODIFY] [runtime/](file:///Users/wonseongbae/Documents/GoogleAG/Manifest/runtime/)
- **Custom Hook: Post-Action Audit**: Trigger Drift Auditor after every agent tool use.
- **Checkpoint Hook**: Force agents to report internal to-dos before every action.
- **Structured Testing Skill**: Report shadow test results in Manifest-readable JSON.
- **Planner Policy**: Restrict agents to "Blueprint-first" modifications.

## Verification Plan

### Automated Tests
- `pytest tests/test_bridge.py`: Verify IPC stability and state serialization.
- `pytest tests/test_drift_auditor.py`: Test conflict detection logic with mocked AST data.

### Manual Verification (The Conductor's Walkthrough)
1. **Ideation**: Run a planning session; verify both **Requirement Map** and `blueprint.md` generation.
2. **Visual Truth**: Change a class name in the code; verify the Blueprint node turns red and the Inspector shows the conflict.
3. **Shadow Sandbox**: Trigger a mission; verify code builds in `.manifest/shadow/` and shows green rings in the TUI.
4. **Resumption**: Force-quit Manifest mid-mission; verify it restarts exactly at the same task step.
