# Scripts and pipelines

How data in `.manifest/` is created and refreshed. The view app only reads; it does not write these files.

## Bottom-up (code → .manifest)

**Script:** `scripts/run_bottom_up_docs.py`

- **Input:** Project root, manifest dir (e.g. `--project-root <path> --manifest-dir <path>/.manifest`).
- **Writes:**
  - `blueprint_code.json` – always (CodeExtractor from codebase).
  - Optionally `intent_code.json`, `architecture_code.json` (LLM step); use `--skip-llm` to refresh only blueprint_code.
- **Also:** Can write `state.json` → `health_metrics` (code quality, test coverage, binary size) when the pipeline runs health collection.

Do not hand-write `blueprint_code.json`. Regenerate with this script or via CodeWatcher/CodeExtractor in code.

```bash
python scripts/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest
# Only blueprint_code + health, no LLM:
python scripts/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest --skip-llm
```

## Top-down (design → .manifest)

**Agents / tools** (e.g. Architect) write:

- `architecture.json` – mission, interface, architecture_style, global_rules, features, goals.
- `blueprint.json` – components with id, name, description, interface, logic_style, project_rules; optional zones/contracts.
- `tasks.json` – task list.
- `intent.json` – intent (optional).

No single “top-down script”; creation is via core APIs or agent workflows that write these files.

## Status (diagram + header)

**Not a file.** The view app computes status when it loads:

- BlueprintSynchronizer compares `blueprint.json` vs `blueprint_code.json` (and architecture) → `component_statuses`.
- Diagram and header STATUS use this in-memory result.

So: keep blueprint and blueprint_code in sync (same component ids/names); run bottom-up when code changes; view will show updated status on refresh (S).
