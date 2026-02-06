# Project Information (Manifest View)

**Definition:** The TUI monitors alignment between **Design Plan** (developer intent) and **Actual Code** (implementation). Terminology (UI and internal docs): **Design Plan**, **Actual Code**, **Deviation**. Internal code may use blueprint for file/class names (e.g. blueprint.json).

**See also:** [VIBE_DASHBOARD_SPEC.md](VIBE_DASHBOARD_SPEC.md) for layout, hotkeys, and JSON schemas.

---

## Project information types

| # | Type | Source | Description |
|---|------|--------|-------------|
| 1 | **Architecture – features** | `.manifest/architecture.json` | Features: id, name, components[], completion_percentage, status, requirements[]. Optional root: mission, global_rules, architecture_style. |
| 2 | **Features → components** | architecture.json `features[].components` + Design Plan | Mapping from each feature to component names. |
| 3 | **Design Plan – components** | `.manifest/blueprint.json` | Components, contracts (flow). Optional per component: description, interface, project_rules, logic_style. |
| 4 | **Architecture – user requirements** | `architecture.json` `requirements[]`, `features[].requirements[]` | User/product requirements (what the product needs). Not dependencies. |
| 5 | **Architecture – goals** | `architecture.json` `goals[]` | Project/capability goals. |
| 6 | **Intent** | `.manifest/intent.json` | Sprint, features[] (id, name, description, components). |
| 7 | **PRD** | `.manifest/prd.json` | Product requirements document. |
| 8 | **Design history** | `.manifest/design_history.json` | Versioned design doc saves. |
| 9 | **Actual Code** | `.manifest/blueprint_code.json` | From code extraction: detected_interface, dependencies, side_effects, complexity per component. |
| 10 | **Design Plan vs Actual Code** | Sync layer | Status: Healthy / Planned / Partial / Deviation; deviation %. |

---

## How each type is presented (visual first)

| Type | Presentation rule |
|------|-------------------|
| Architecture – features | **Diagram**: feature boxes in flow, color by status (done/design/partial/drift). |
| Feature → requirements | **Diagram**: each feature box with requirement nodes under it (visual link). No plain text list. |
| Goals & top-level product reqs | **Compact line(s)** in one panel. |
| Features → components | **Diagram**: feature row above, component row below, vertical links. |
| Design Plan structure (components, contracts) | **Diagram**: component boxes in contract order, arrows, color by status. |
| Intent | Not shown in Diagram view (docs omitted). |
| PRD | Not shown in Diagram view (docs omitted). |
| Setup & how it works | Not shown in Diagram view (docs omitted). |
| Component detail (file, line, methods, algorithm, pattern, complexity, notes) | **Inspector Detail (s)** when a component is selected; from blueprint_code.json. |
| Design Plan vs Actual Code | Status colors: Healthy / Planned / Partial / Deviation; right panel D = Differences. |
| Design history | Timeline view (3). |

**Manifest View:** 1=Diagram, 2=Files, 3=Timeline, 4=Mission. Left panel: Project Health (deviation %), Tasks ([X] Done, [>] Active, [ ] Pending). Right panel: Information Hub — Design (Description, Interface, Rules, Actual Code snapshot) or Differences (side-by-side); **D** toggles. **Tab** / **⇧Tab** cycle components; **S** refresh.

---

## Data sources (reference)

| File / store | Contents |
|--------------|----------|
| `.manifest/architecture.json` | features[], requirements[] (top-level), goals[] |
| `.manifest/blueprint.json` | components[], contracts[], zones |
| `.manifest/blueprint_code.json` | Same schema, from code |
| `.manifest/intent.json` | version, sprint, features[] |
| `.manifest/prd.json` | title, sections or requirements |
| `.manifest/design_history.json` | entries (doc, path, timestamp) |

Schema: architecture features have `id`, `name`, `components[]`, `requirements[]` (user requirements for that feature), `status`, `completion_percentage`. **Requirements** = user/product requirements only, not dependencies.
