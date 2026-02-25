# Scripts and pipelines

How data in `.manifest/` is created and refreshed. The view app only reads; it does not write these files.

**Layout:** App runnables (bottom-up pipeline, layer writer, OpenCode agent setup) live in `bin/`. Dev/CI/setup helpers (tests, pre-push, post-commit hook driver, setup scripts) live in `scripts/`.

## Bottom-up (code → .manifest)

**Script:** `bin/run_bottom_up_docs.py`

**When it runs:** On commit. GitManager runs the script after `create_commit()`. For commits made with `git commit` in the terminal, install the post-commit hook so the script runs there too (see README Git hooks).

- **Input:** Project root, manifest dir. Requires `blueprint_design.json` and `opencode` on PATH.
- **Steps:** CodeExtractor (mechanical) → merge with design structure → opencode enricher (narrative, governance, etc. from code; design as context). Writes `blueprint_code.json`, then builds and writes `blueprint_view.json` (same keys as design/code; values = plan/actual + deviates). Writes `state.json` → `health_metrics`.
- **Principle:** Same schema and entity ids as design; mechanical fields from extraction; narrative and governance filled by enricher from code (design as context).

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

**How the mock code blueprint is built:** The script runs CodeExtractor on the project root (e.g. `tmp/calculator/`), merges with design via `merge_design_and_extraction` (same schema and entity ids), then applies overrides so some entities match design (healthy) and one (e.g. output) differs for deviation. It does not call the opencode enricher. Run the script to refresh `tmp/<name>/.manifest` JSON files.

**Planned vs done:** The script restricts which design ids appear in the code blueprint (see `implemented_ids` and mapping in the script). Omitted entities show as **planned**; mapped ones show as **healthy** or **deviation**. Keep source under the mock project dir aligned (e.g. cli, arithmetic_engine, add, sub implemented; output/mul as stubs). See `tmp/calculator/README.md`.

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
