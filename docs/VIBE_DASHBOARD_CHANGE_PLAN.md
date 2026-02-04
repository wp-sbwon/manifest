# Manifest View TUI — Change Plan (reference.txt + Image)

This document plans changes to `src/manifest/view/app.py` so the TUI matches the React design in `reference.txt` and the provided screenshot.

---

## 1. Header

**Reference:** Single header bar with left/right sections. No separate Textual `Header()` widget.

| Item | Reference / Image | Current | Change |
|------|-------------------|--------|--------|
| Title | App name only, no version in title (e.g. **Manifest View**) | Textual app title "Manifest View" + subtitle | Header strip: **Manifest View** (no version in title). |
| Mode labels | `[ Planning ]` (active) and `[ Differences ]` (dim); toggle reflects info-hub view | Not present | Add to header strip: **Planning** / **Differences** labels; highlight active (Planning when Design, Differences when Diff). |
| Right side | `STATUS: HEALTHY` or `STATUS: DEVIATION DETECTED` (green/red) + `TIME: <locale time>` | Subtitle shows "Tasks: N" | In header strip: **STATUS** from selected component (healthy vs deviation) + **TIME** (live clock, e.g. 1s interval). |
| Strip style | `border-b border-[#333]`, `bg-[#111]`, `h-8`, compact | `#header-strip` with "Manifest Dashboard \| Metrics" | Redesign `#header-strip` content and `_refresh_header_metrics()` to output: title, Planning/Differences, STATUS, TIME. |

**Implementation notes:**
- App title = "Manifest View" (no version). Version shown only in footer bottom right as "Manifest app 0.0" (effectively 0.0 until release).
- Either hide Textual `Header()` and use only `#header-strip` for the top bar, or set `TITLE = "Manifest View"` and put Planning/Differences + STATUS + TIME in the subtitle/custom strip.
- Add a 1-second timer (e.g. `set_interval(1, ...)`) to update TIME in the header.

---

## 2. Left Sidebar — Project Health

**Reference:** One box, title "Project Health" (uppercase, small, dim), then 4 rows: label + value.

| Row | Reference | Current | Change |
|-----|-----------|--------|--------|
| Title | "Project Health" (9px, #555, uppercase, border-b #222) | "Project Health" + deviation % | Keep title; style as reference (uppercase, dim). |
| 1 | Total Deviation: **12%** (yellow when non-zero) | Total Deviation: pct% (red/green) | Use **yellow** for value when pct &gt; 0; green when 0. |
| 2 | Code Quality: **Excellent** (green) | Code Quality: — | Add placeholder or real value: **Excellent** (green) or "—" until we have data. |
| 3 | Test Coverage: **88%** (blue) | Test Coverage: — | Add placeholder or real value: **88%** (blue) or "—". |
| 4 | Binary Size: **1.2 MB** (text/dim) | Binary Size: — | Add placeholder or real value: **1.2 MB** or "—". |

**Implementation:** Update `_get_sidebar_health()` to output these four rows with Rich markup for colors (yellow/green/blue/dim). Optionally add a "System Core" or project-level health later.

---

## 3. Left Sidebar — Tasks

**Reference:** Title "Tasks" (uppercase, dim); then one block: "SPRINT" + "66%" on one line, thin progress bar (green fill), then task list with `[X]` (done, green), `[>]` (active, yellow), `[ ]` (pending, dim).

| Item | Reference | Current | Change |
|------|-----------|--------|--------|
| Title | "Tasks" (uppercase, dim, border-b) | "My Tasks" / "Tasks (0)" | Use **"Tasks"** as section title only (no count in title). |
| Sprint line | "SPRINT" left, "66%" right (9px, #888, bold) | "SPRINT &lt;pct&gt;%" then bar | Match: one line "SPRINT" / "66%" (or computed %), then bar. |
| Progress bar | Thin (h-1), bg #222, border #333, green (#4ec9b0) fill | ASCII `[====  ]` style | Prefer a thin visual bar if Textual supports it; otherwise keep ASCII bar but match colors (green fill). |
| Task items | **Keep old TUI style** (not React): each task shows icon + number + name, then **status label + progress bar + %** on second line | "N. name" then "Status \| [====] pct%" | **Do not** simplify to React (icon + name only). Keep per-task status and progress. |

**Implementation:** Update `_get_sidebar_tasks()` to:
- Emit "Tasks" as title.
- One "SPRINT" line with percentage.
- One progress bar line (current ASCII or widget).
- Task lines: only icon + name, color by status (completed=green, in_progress=yellow, else dim).

---

## 4. Left Sidebar — Remove "View" Section

**Reference:** No "View" or "View: Diagram" block in the left column.

**Current:** `#sidebar-viz` shows "View: Diagram" (etc.).

**Change:** Remove the "View" sidebar section from compose and from `_refresh_sidebar()` (no more `_get_sidebar_viz()` usage). Optionally remove `_get_sidebar_viz()` or leave unused.

---

## 5. Main Workspace — Tab Bar

**Reference:** Tabs inside main panel: `1:DIAGRAM`, `2:FILES`, `3:TIMELINE`, `4:MISSION`. Selected tab: blue text, blue border, dark blue bg (#1a2b3c, #569cd6, #264f78). Unselected: dim (#555). Right side of tab bar: small "Main Workspace" label (8px, #333).

**Current:** No visible tab bar in main area; view switches via keys 1–4.

**Change:**
- Add a **tab bar** widget or static line at the top of `#main`: four tabs "1:DIAGRAM", "2:FILES", "3:TIMELINE", "4:MISSION".
- Style: selected = blue border + blue text + dark blue background; unselected = dim.
- Right-aligned label: "Main Workspace" (small, dim).
- Tab bar background: #161b22, border-bottom #333.

---

## 6. Main Workspace — Diagram View Content

**Reference:** Exact ASCII from reference (fixed layout):
- Top: `┌──...──┐` / `│  [ARCHITECTURE FLOW] ... │` / `└──...┬──...┘` / `│`
- Then CLI_PARSER (magenta box, green ■)
- Then ARITHMETIC_ENG (blue box, yellow ■), with `└──┬───┬───┬──┘`
- Then three methods (cyan): ADD_METHOD (green ■), SUB_METHOD (green ■), MUL_METHOD (red ■)
- Then FORMATTER (magenta, gray ■)

**Current:** `_render_architecture_flow_diagram()` builds a **generic** vertical list of boxes (one per component from blueprint), not the fixed 5-node layout (CLI_PARSER → ARITHMETIC_ENG → ADD/SUB/MUL → FORMATTER).

**Change:**
- Prefer a **fixed template** diagram that matches reference when we have the right component names/types; otherwise fall back to generic.
- Option A: Add `_render_reference_style_diagram(comp_status)` that outputs the exact reference ASCII with placeholders (CLI_PARSER, ARITHMETIC_ENG, ADD_METHOD, SUB_METHOD, MUL_METHOD, FORMATTER) and colors (magenta/blue/cyan by type, ■ by status from comp_status for those ids).
- Option B: Keep dynamic ordering but change layout to the **same shape** as reference: one gateway → one engine → three methods → one gateway (e.g. detect "parser", "engine", "add/sub/mul", "formatter" by name and assign positions).
- Box widths and spacing must match reference so the diagram looks identical (e.g. `┌──────────────┴──────────────┐`, `│  ■ CLI_PARSER               │`).

---

## 7. Main Workspace — Files View

**Reference:** "Source Tree" title; tree like:
`root/`
`├── ■ cli/` → `parser.py ..... ■`
`├── ■ engine/` → `calculator.py ..... ■` with `add()` / `sub()` / `mul()` (each with ■)
`└── ■ output/` → `formatter.py ..... ■`

**Current:** Flat list "Source (components)" with "■ name  file_path".

**Change:** Replace with a **tree** view: root, then directories (cli, engine, output) and files with status ■. Derive tree from component file paths (e.g. from blueprint_code or llm_design). Color folders by type (magenta/blue/magenta for gateway/module/gateway); files and methods with status ■ (green/yellow/red/gray).

---

## 8. Main Workspace — Timeline View

**Reference:** "Project Changes Timeline"; items: time (e.g. "11:12 AM") left, then vertical line with dot (color), label (DESIGN/CODE in color), message. Design = blue, Code = green.

**Current:** Design history table + Git commits table (separate panels).

**Change:** Single **timeline** list: merge design events and git commits into one chronological list. Each row: time, colored dot, DESIGN or CODE label (blue/green), message. Match reference layout (time column, vertical bar, dot, bold label, dim message).

---

## 9. Main Workspace — Mission View

**Reference:** "Mission Control: Objectives"; cards: each has ID + name (e.g. "M1: High Precision Engine"), status badge (Done / In Progress / Deviation), and body text (italic, left border).

**Current:** Mission view shows Tasks table, Sprints, Worker squad channels, Resources (multiple panels).

**Change:** Replace or add an **Objectives** section that shows **mission/objective cards** from architecture (e.g. from `architecture.json` goals or a new `objectives`/`missions` list). Each card: id+name, status (Done / In Progress / Deviation), body. Styling: border #222, bg #0c0c0c, status badges with color (green/amber/red). If no objectives in data, show placeholder cards or "Mission Control: Objectives" with one placeholder card.

---

## 10. Main Workspace — Panel Title and Border

**Reference:** Diagram is inside main content area with no extra "Design Plan vs Actual Code" panel title around the diagram; tab bar has "Main Workspace" only.

**Current:** Diagram view wrapped in `Panel(..., title="Design Plan vs Actual Code", border_style="blue")`.

**Change:** For Diagram view, **do not** wrap in a Panel (or use a minimal/borderless container) so the diagram is the raw content. Tab bar already says "1:DIAGRAM"; no need for a second title. Same idea for Files/Timeline/Mission: content matches reference; avoid redundant panel titles that are not in the reference.

---

## 11. Right Sidebar — Title and Controls

**Reference:** Top bar: left "**{selected.name} Inspection**" (e.g. "System Core Inspection"), right "[TAB] NEXT" (blue) and, if deviating, "[D] DIFF" / "[D] BACK" (red, toggles Design vs Differences).

**Current:** "Information Hub — Design" / "Information Hub — Differences".

**Change:**
- Title: **"{Component name} Inspection"** (e.g. "System Core" for root, "CLI_PARSER Inspection"). Use display name from design (e.g. "System Core" for PROJECT_ROOT).
- Right: **[TAB] NEXT** (blue) always; **[D] DIFF** / **[D] BACK** only when selected component has deviation, to toggle Design vs Differences.

---

## 12. Right Sidebar — Design View Sections

**Reference:** Four clear sections:
1. **Mission / Description** — small blue uppercase label; then bold white description text.
2. **Interface Planning** — small dim "Interface Planning"; value in green/cyan italic bold (e.g. "Binary Execution -> Console Output"); then "Logical Style:" dim, value blue bold underline.
3. **Actual Code Snapshot** — green-tinted box (border-l #4ec9b0); label "Actual Code Snapshot"; rows: Dependencies, Side Effects, Complexity (value dim or yellow if side effects).
4. **Project Rules** — "Project Rules" (dim, border-b); list with » (blue) and rule text (dim).

**Current:** Single block of lines: "Information Hub — Design", name, Description, Interface, Rules, Logic style, Actual Code (Detected, Deps, Complexity).

**Change:** Restructure `_get_info_hub_content()` for Design view into these **four sections** with the same labels and order. Use Rich markup for: blue labels, green/cyan for interface, blue for logical style, green left border for Actual Code block, » and dim for rules. If selected is a "root" or project-level node, show description/interface/rules from architecture or a virtual "System Core" (like reference `projectData['PROJECT_ROOT']`).

---

## 13. Right Sidebar — Differences View

**Reference:** "Mismatch Comparison" header (red tint); 2-column grid "Design Plan" | "Actual Code" with Interface, Side Effects, Deps compared; then diagnostics paragraph; "Return to Planning" button.

**Current:** Simple table "Design Plan | Actual Code" with a few rows.

**Change:** Keep side-by-side comparison but add: (1) "Mismatch Comparison" header (red styling), (2) column headers "Design Plan" / "Actual Code", (3) rows: Interface (plan vs actual), No Side Effects vs actual side effects, No Deps vs actual deps, (4) short diagnostics line (e.g. "The implementation of X has drifted..."), (5) footer line like "Return to Planning" (or map to key D). Use red for actual values when they deviate.

---

## 14. Right Sidebar — Footer

**Reference:** One line: "[E] Edit Design" left, "[S] Re-Sync Data" right (9px, #555, italic). Border-top #333, bg #050505.

**Current:** No such footer in info-hub.

**Change:** Add a **footer** inside the right sidebar (below info-hub content): "[E] Edit Design" and "[S] Re-Sync Data". E can be no-op or open editor; S already bound to refresh.

---

## 15. Footer (App Footer)

**Reference:** One row: [1] MAP, [2] FILES, [3] HISTORY, [4] MISSION, [TAB] CYCLE, then "Ctrl+C Quit"; right side: "Manifest app 0.0" (and optionally PID). No user-facing version number elsewhere; version is effectively 0.0 until release.

**Current:** Textual Footer with bindings; app version strip at bottom right shows "Manifest app 0.0".

**Change:** When customizing footer text: left — **[1] MAP**, **[2] FILES**, **[3] HISTORY**, **[4] MISSION**, **[TAB] CYCLE**, **Ctrl+C Quit**; right — **Manifest app 0.0** (from APP_VERSION). Use short key labels (MAP not "Diagram", HISTORY not "Timeline"). PID optional.

---

## 16. Colors and Styling

**Reference palette:** bg #0c0c0c, panel #111, border #333/#222, text #ccc, dim #666, blue #569cd6, cyan #4fc1ff, magenta #c586c0, green #4ec9b0, yellow #dcdcaa, red #f44747, gray #444.

**Current:** Textual/CSS uses #0d1117, #161b22, #30363d, #58a6ff, etc.

**Change:** Update CSS and Rich markup to use the **reference palette** where possible (Textual may not support hex in all widgets; use closest named colors: blue, cyan, magenta, green, yellow, red, grey70 for gray). Ensure status ■ and tabs use green/yellow/red/gray as in reference.

---

## 17. Selection Model and "System Core"

**Reference:** Has `PROJECT_ROOT` with name "System Core" (description, interface, rules, actual). Selection can be PROJECT_ROOT, CLI_PARSER, MUL_METHOD, ADD_METHOD; Tab cycles components.

**Current:** Selectable nodes are features then components from architecture + blueprint; no explicit "System Core" / PROJECT_ROOT.

**Change:** Prepend a **virtual root** node (e.g. id `PROJECT_ROOT`, name "System Core") to the selectable list when we have architecture/description. Populate its Design view from architecture.json (goals, global_rules, architecture_style) or a single "project" description. Actual Code Snapshot for root can be project-level (e.g. version, top-level deps). Then Tab/Up/Down cycle: PROJECT_ROOT → first feature → … → components.

---

## 18. Diagram Panel Removal

**Current:** Diagram view returns `Panel(diagram_txt, title="Design Plan vs Actual Code", border_style="blue")`.

**Change:** Return only `diagram_txt` (or a minimal Renderable) so the main area shows the diagram without an extra panel and border. Tab bar already identifies the view.

---

## Summary Checklist

- [ ] **Header:** Manifest View (no version), [ Planning ] / [ Differences ], STATUS (HEALTHY/DEVIATION), TIME (live).
- [ ] **Left – Health:** Project Health with Total Deviation (yellow/green), Code Quality, Test Coverage, Binary Size (placeholders or real).
- [ ] **Left – Tasks:** "Tasks" title, SPRINT + %, one bar, task list [X]/[>]/[ ] + name only.
- [ ] **Left:** Remove "View" section.
- [ ] **Main – Tab bar:** 1:DIAGRAM, 2:FILES, 3:TIMELINE, 4:MISSION + "Main Workspace".
- [ ] **Main – Diagram:** Exact reference ASCII layout and colors (or fixed 5-node template).
- [ ] **Main – Files:** Tree (root, cli/, engine/, output/) with ■.
- [ ] **Main – Timeline:** Single chronological timeline (DESIGN/CODE, time, message).
- [ ] **Main – Mission:** Objectives cards (id+name, status badge, body).
- [ ] **Main:** No Panel title around diagram (and minimal around other views).
- [ ] **Right – Title:** "{Name} Inspection", [TAB] NEXT, [D] when deviation.
- [ ] **Right – Design:** Mission/Description, Interface Planning, Actual Code Snapshot, Project Rules (with reference styling).
- [ ] **Right – Differences:** Mismatch Comparison, 2-column, diagnostics, Return to Planning.
- [ ] **Right – Footer:** [E] Edit Design, [S] Re-Sync Data.
- [ ] **App Footer:** [1] MAP, [2] FILES, [3] HISTORY, [4] MISSION, [TAB] CYCLE, Ctrl+C Quit; right: Manifest app 0.0.
- [ ] **Colors:** Align with reference palette (blue, cyan, magenta, green, yellow, red, gray).
- [ ] **Selection:** Add PROJECT_ROOT "System Core"; Tab cycles all nodes.

Implementing in the order above will align the TUI with `reference.txt` and the provided image.
