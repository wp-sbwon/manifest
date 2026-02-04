# View – Data Formats

The view reads from `.manifest/` (e.g. architecture.json, blueprint.json). Core and agents must write these in the right shape.

## architecture.json

Used for: Mission (goals), Inspector, diagram/status. Not used for Project Health metrics.

- **mission** (string): Shown for root in Inspector.
- **global_rules** (list of strings): Shown in Inspector.
- **architecture_style** (string): Shown in Inspector.
- **features** (list of objects): id, name, components, completion_percentage, status, requirements. Used for diagram and status.
- **goals** (list of objects): Each has id, name, description, status. status = Planned | In Progress | Done | Deviation. Drives Mission cards.

Core fixes goals on load/save (ensure_architecture_metadata). Agents should still write this shape.

- **Architect tool**: Writes architecture with goals.
- **Bottom-up** (architecture_code.json): Prompt asks for goals as objects (not strings).

## state.json – Project Health (app state)

Code quality, test coverage, and binary size are **app state** updated when the bottom-up process runs. Stored in **state.json** under **health_metrics** (not in architecture.json).

- **health_metrics** (object): Written by bottom-up via `write_health_to_state()`. Keys: **code_quality** (string), **test_coverage** (number or null), **binary_size** (string or null). View reads this from disk to show Project Health; same logic that produces the data runs in `health_from_code.get_health_from_code()` and is persisted by `write_health_to_state()` when you run `scripts/run_bottom_up_docs.py` or when DeviationMonitor runs.

## blueprint.json (design) – Inspection Planning fields

Used for: Diagram, Inspector (Planning), Differences.

Each **component** must have these so the core inspection panel can show them:

- **description** (string): Goal Intent – one-sentence mission: why does this exist?
- **interface** (string): Interface Contract – formal shape, e.g. `num, num -> num`.
- **logic_style** (string): Logic Style – pattern or approach, e.g. Pure Function, Bitwise Worker, Router.
- **project_rules** (list of strings): Essential Rules – invariants that must never be broken.

Top-down and bottom-up doc agents must produce components in this shape.

## blueprint_code.json (from codebase) – Inspection Code Reality

Used for: Diagram, Inspector (Code Reality), Differences.

Components are **mechanically extracted** from the codebase (CodeExtractor). Each component has:

- **dependencies** (list of strings): Imports / modules used.
- **side_effects** (list of strings): I/O or other effects, e.g. file_write, logging.
- **complexity** (string): Nesting/length or complexity class.
- **detected_interface** (string): Signature or surface from code.

**Do not hand-write.** Create only via Manifest’s pipeline: run `scripts/run_bottom_up_docs.py` (refreshes blueprint_code via CodeWatcher/CodeExtractor), or use CodeWatcher.force_extract() / CodeExtractor in code.

## Bottom-up docs (all): use Manifest’s logic only

- **blueprint_code.json** – From CodeExtractor (run bottom-up script or CodeWatcher.force_extract()).
- **intent_code.json** – From `manifest.audit.code.bottom_up_docs.generate_higher_level_docs_from_code` (LLM step in run_bottom_up_docs.py).
- **architecture_code.json** – Same LLM step.

Do not write these files by hand. Regenerate them by running:

```bash
python scripts/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest
```

Use `--skip-llm` to refresh only blueprint_code.json (no intent_code / architecture_code).

## Inspector panel – Results and Alert

- **Results** (Last Output, Shadow Trace): From state (shadow-* channels). Filled when execution/shadow run writes to state.
- **Alert** (Deviation Alert): Shown when plan and code mismatch; data from blueprint sync (compare_components).

## tasks.json

Used for: Sidebar Tasks. Tasks with status, progress (e.g. percentage), names.

## design_history.json / Git

Used for: Timeline. Design history and Git commits merged by time.
