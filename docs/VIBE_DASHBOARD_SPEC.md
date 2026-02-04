# Manifest View — TUI Architecture Monitor (Spec)

## 1. Core Vision

The TUI monitors alignment between **Design Plan** (developer intent) and **Actual Code** (implementation reality). It gives a visual map so development stays grounded in the project's architecture.

**Terminology (same in UI and internal docs):**
- **Design Plan** — the intended design (user-facing; internal files may still be named blueprint.json).
- **Actual Code** — what is in the source (user-facing; internal may use from_actual_code / ground_truth in JSON).
- **Deviation** — when Actual Code does not match the Design Plan (not "Drift" in user-facing text).

---

## 2. Information Fields

### A. Design Planning (The Intent)

**Root / global (e.g. in `architecture.json`):**
- **Mission** — high-level goal of the project.
- **Global Rules** — system-wide constraints (e.g. "No external network access").
- **Architecture Style** — overarching design pattern (e.g. "Monolithic Core").

**Component / module (e.g. in `blueprint.json` or architecture):**
- **Description** — purpose of the unit.
- **Interface** — expected inputs and outputs.
- **Project Rules** — behavioral rules (e.g. "Must be pure / side-effect free").
- **Logic Style** — specific pattern used (e.g. "Strategy Router").

### B. Actual Code (The Reality)

**From code extraction (e.g. `blueprint_code.json`):**
- **Detected Interface** — function/class signature found in source.
- **Dependencies** — modules actually imported.
- **Side Effects** — detected I/O (e.g. file write, logging).
- **Complexity** — score from logic depth and size (e.g. lines of code).

---

## 3. JSON Schemas (Design Plan vs Actual Code)

### Design Plan sources

| Source | Root/global fields | Component/module fields |
|--------|--------------------|--------------------------|
| `architecture.json` | `mission`, `global_rules`, `architecture_style` | (features reference components) |
| `blueprint.json` (design) | — | `description`, `interface`, `project_rules`, `logic_style` |

**architecture.json** (optional additions):
- `mission` (string)
- `global_rules` (array of strings)
- `architecture_style` (string)

**blueprint.json** components (optional additions):
- `description` (string)
- `interface` (string or object: expected inputs/outputs)
- `project_rules` (array of strings)
- `logic_style` (string)

### Actual Code source: `blueprint_code.json`

**Per component (from code extraction):**
- `detected_interface` (string) — signature or class + methods.
- `dependencies` (array of strings) — imported modules used.
- `side_effects` (array of strings) — e.g. "file_write", "logging".
- `complexity` (string or number) — e.g. "O(n)", or LOC-based score.

Existing fields (`methods`, `algorithm`, `design_pattern`, etc.) remain; these are additive.

---

## 4. Terminal Interface Layout

### Persistent sidebars

**Left panel — Vitals & Progress**
- **Project Health** — deviation % (mismatch count) and optional binary size.
- **My Tasks** — sprint progress bar and task list with status: `[X]` Done, `[>]` Active, `[ ]` Pending.

**Right panel — Information Hub**
- **View 1 (Design)** — Description, Interface, Rules, and a summary of Actual Code stats.
- **View 2 (Differences)** — Side-by-side Design Plan vs Actual Code; mismatches in red.
- Hotkey **D** toggles Design vs Differences.

### Main workspace (swappable center views)

| Key | View | Content |
|-----|------|--------|
| **1** | Diagram | Vertical ASCII flow; box color = type (Module / Method / I/O); status color = Healthy / Partial / Deviation / Planned. Flow: top-down (e.g. CLI_PARSER → Engine → FORMATTER). |
| **2** | Files | Hierarchical tree of source code with status indicators. |
| **3** | Timeline | Vertical node map: Design updates vs Code updates in time order. |
| **4** | Mission | Full-screen objective: mission, goals, task descriptions. |

### Visual standards

- **Symbols:** Terminal box-drawing (┌, ┐, │, ─) and solid block **■** for status.
- **Status indicator:** **■** next to names; color = state.
- **Status colors:** Green = Healthy, Yellow = Partial, Red = Deviation, Gray = Planned.
- **Box type colors:** Blue = Module, Cyan = Method, Magenta = Input/Output gateway.

**Deviation (red) when:**
- Actual interface ≠ Planned interface.
- Unplanned dependencies in code.
- Side effects in a component marked "side-effect free" in the Design Plan.

### Hotkeys

- **1–4** — Switch main workspace view (Diagram, Files, Timeline, Mission).
- **Tab** — Cycle to next component for inspection.
- **Shift+Tab** — Previous component.
- **D** — Toggle right panel: Design vs Differences.
- **S** — Manual refresh / sync.
- **q** — Quit.

---

## 5. Agent / Writer Compliance

- **Architect (top-down)** — When writing `architecture.json`, can set `mission`, `global_rules`, `architecture_style`. When writing design components (e.g. in blueprint or architecture), can set `description`, `interface`, `project_rules`, `logic_style`.
- **Code extractor (bottom-up)** — Populates `blueprint_code.json` with `detected_interface`, `dependencies`, `side_effects`, `complexity` per component.
- **View / sync** — Uses "Design Plan" and "Actual Code" in all UI labels; reports "Deviation" and shows Healthy / Partial / Deviation / Planned. App title: "Manifest View"; version (e.g. 0.0) on bottom right as "Manifest app 0.0" until release.

---

## 6. Data Flow

- **Design Plan** = `architecture.json` (global intent) + `blueprint.json` (component intent).
- **Actual Code** = `blueprint_code.json` (from AST/code extraction).
- **Comparison** = Sync layer compares Design Plan vs Actual Code and sets status (Healthy / Partial / Deviation / Planned) and deviation %.
