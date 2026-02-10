# Scripts and pipelines

How data in `.manifest/` is created and refreshed. The view app only reads; it does not write these files.

## Bottom-up (code → .manifest)

**Script:** `scripts/run_bottom_up_docs.py`

- **Input:** Project root, manifest dir (e.g. `--project-root <path> --manifest-dir <path>/.manifest`).
- **Writes:**
  - `blueprint_code.json` – always (CodeExtractor from codebase).
- **Also:** Can write `state.json` → `health_metrics` (code quality, test coverage, binary size) when the pipeline runs health collection.

Do not hand-write `blueprint_code.json`. Regenerate with this script or via CodeWatcher/CodeExtractor in code.

```bash
python scripts/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest
python scripts/run_bottom_up_docs.py --project-root <project> --manifest-dir <project>/.manifest
```

## Top-down (design → .manifest)

**Agents / tools** (e.g. Architect) write:

- `prd.json` – product requirements.
- `blueprint_design.json` – blueprint (root intent: mission, goals, interface; entities with id, children, intent, reality, etc.).
- `tasks.json` – task list.

No single “top-down script”; creation is via core APIs or agent workflows that write these files.

## Status (diagram + header)

**Not a file.** The view app computes status when it loads:

- BlueprintSynchronizer compares `blueprint_design.json` vs `blueprint_code.json` → `component_statuses`.
- Diagram and header STATUS use this in-memory result.

So: keep blueprint and blueprint_code in sync (same component ids/names); run bottom-up when code changes; view will show updated status on refresh (S).
