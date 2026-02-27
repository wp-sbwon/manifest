# Scripts and pipelines

How data in `.manifest/` is created and refreshed. The view app only reads; it does not write these files.

**Layout:** App runnables (bottom-up pipeline, layer writer, OpenCode agent setup) live in `bin/`. Dev/CI/setup helpers (tests, pre-push, post-commit hook driver, setup scripts) live in `scripts/`.

## Bottom-up (code → .manifest)

**Script:** `bin/run_bottom_up_docs.py`

**When it runs:** On commit. GitManager runs the script after `create_commit()`. For commits made with `git commit` in the terminal, install the post-commit hook so the script runs there too (see README Git hooks).

- **Input:** Project root, manifest dir. Requires `blueprint_design.json`.
- **Steps:** CodeExtractor produces an outline of the code; a deterministic merge with design (exact ID, symbol-based mapping) produces `blueprint_code.json`. Then the pipeline builds and writes `blueprint_view.json` (plan/actual + deviates) and `state.json` (health_metrics).
- **Principle:** blueprint_code combines design (narrative, governance) with extraction (symbol, protocol, dependencies). Design-only entities stay as planned; extraction-only entities appear as orphans.

```bash
python bin/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest
```

## Top-down (design → .manifest)

**Agents / tools** (e.g. Architect) write:

- `prd.json` – product requirements.
- `blueprint_design.json` – blueprint (entities with id, children, dependencies, narrative, blueprint, protocol, profile, governance, symbol, traits, topology_actual, preview, outgoing_contracts).
- `tasks.json` – task list.

No single “top-down script”; creation is via core APIs or agent workflows that write these files.

## Status (diagram + header)

**Not a file.** The view app builds the blueprint view from design and code (by entity id) and reads status from it. Diagram and header use that. Bottom-up runs on commit; the view refreshes when `.manifest` files change (file watcher).

## Tmp (dev) mock projects

Mock projects live under `tmp/<name>/` (e.g. `tmp/calculator/`). The **calculator** mock is a small CLI calculator used for Manifest dev so the view does not load the full manifest codebase.

**Script:** `scripts/create_mock_project_data.py`

- **Writes:** `tmp/<name>/.manifest/blueprint_design.json`, `blueprint_code.json`, `blueprint_view.json`, plus `prd.json`, `tasks.json`, `state.json`. Default name is `calculator`.
- **Usage:** From repo root: `PYTHONPATH=src python scripts/create_mock_project_data.py [name_or_path]`. Omit for `tmp/calculator/.manifest`; pass a name (e.g. `myproject`) for `tmp/myproject/.manifest`; or pass a path to another `.manifest` dir.

**How the mock code blueprint is built:** The script runs CodeExtractor, then `build_code_blueprint` (deterministic merge with design, same as the bottom-up pipeline). Merge maps extraction to design by symbol and combines design (narrative, governance) with extraction (mechanical fields). Run the script to refresh `tmp/<name>/.manifest` JSON files and stub tests.

**Planned vs done:** Entities present only in design (no extraction match) appear in blueprint_code and show as **planned**; entities in the code show as **healthy** or **deviation** per contract comparison; code-only entities show as **orphaned**.

**Refresh mock data:**

```bash
PYTHONPATH=src python scripts/create_mock_project_data.py
# or: scripts/create_mock_project_data.py calculator
```

**Run view with default mock:**

```bash
MANIFEST_DEV=1 PYTHONPATH=src python -m manifest
# or
PYTHONPATH=src python -m manifest.view.app --manifest-dir tmp/calculator/.manifest
```

**Wire launcher to a mock:** Set `MANIFEST_DEV=1`; optional `MANIFEST_DEV_PROJECT=calculator` (default). The launcher uses `tmp/<MANIFEST_DEV_PROJECT>/` as the project dir.
