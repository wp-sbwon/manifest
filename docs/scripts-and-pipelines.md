# Scripts and pipelines

How data in `.manifest/` is created and refreshed. The view app only reads; it does not write these files.

## Bottom-up (code → .manifest)

**Script:** `scripts/run_bottom_up_docs.py`

**When it runs:** On commit. GitManager runs the script after `create_commit()`. For commits made with `git commit` in the terminal, install the post-commit hook so the script runs there too (see README Git hooks).

- **Input:** Project root, manifest dir. Requires `blueprint_design.json` and `opencode` on PATH.
- **Steps:** CodeExtractor (mechanical) → merge with design structure → opencode enricher (intent from code, ground truth). Writes `blueprint_code.json`, then builds and writes `blueprint_view.json` (same keys as design/code; values = plan/actual + deviates). Writes `state.json` → `health_metrics`.
- **Principle:** Same schema and entity ids as design; reality from extraction; intent filled by opencode from the code (not copied from design).

```bash
python scripts/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest
```

## Top-down (design → .manifest)

**Agents / tools** (e.g. Architect) write:

- `prd.json` – product requirements.
- `blueprint_design.json` – blueprint (root intent: mission, goals, interface; entities with id, children, intent, reality, etc.).
- `tasks.json` – task list.

No single “top-down script”; creation is via core APIs or agent workflows that write these files.

## Status (diagram + header)

**Not a file.** The view app computes status when it loads: BlueprintSynchronizer compares design vs code (by entity id) → `component_statuses`. Diagram and header use this. Bottom-up runs on commit; the view refreshes when `.manifest` files change (file watcher).

## Tmp (dev) mock project

The **tmp** project is a small CLI calculator under `tmp/` used for Manifest dev so the view does not load the full manifest codebase.

**Script:** `scripts/create_mock_project_data.py`

- **Writes:** `tmp/.manifest/blueprint_design.json` (fully populated), `tmp/.manifest/blueprint_code.json` (from CodeExtractor + design-id mapping; no opencode), `tmp/.manifest/blueprint_view.json` (comparison output: same keys as design/code, values = plan/actual + deviates), plus `prd.json`, `tasks.json`, `state.json`.
- **Usage:** From repo root: `PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir]`. Default `manifest_dir` is `tmp/.manifest`.

**How the mock code blueprint is built:** The script runs CodeExtractor on `tmp/`, maps extracted components to design entity ids (same schema as design), and merges reality from extraction with intent from design for mapped entities. It does not call the opencode enricher, so tmp works without opencode. Entities present in both design and extracted code get reality from code; others can be omitted so they show as **planned** in the diagram.

**Planned vs done:** The script restricts which design ids appear in the code blueprint (see `implemented_ids` and mapping in the script). Omitted entities show as **planned**; mapped ones show as **healthy** or **deviation**. Keep tmp source under `tmp/` aligned (e.g. cli, arithmetic_engine, add, sub implemented; output/mul as stubs). See `tmp/README.md`.

**Refresh mock data:**

```bash
PYTHONPATH=src python scripts/create_mock_project_data.py tmp/.manifest
```

**Run view with tmp:**

```bash
MANIFEST_DEV=1 PYTHONPATH=src python -m manifest
# or
PYTHONPATH=src python -m manifest.view.app --manifest-dir tmp/.manifest
```
