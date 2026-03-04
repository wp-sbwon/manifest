# View data: three sources

The view app uses **three sources of data** and builds the comparison and status on refresh.

## Three sources

| Source | Role | Persisted as (optional) |
|-------|------|-------------------------|
| **Blueprint (design)** | Entity layers: intent (assertions), contracts, structure. Single source of truth for "plan." | `blueprint_design.json` |
| **Code (extracted contents)** | What the extractor produced from the repo: symbols, protocol, dependencies. Used for "actual" and contract matching. | e.g. `blueprint_code.json` or `code_extracted.json` |
| **Test results** | Per-assertion or per-entity pass/fail. Used to show **intent** status (assertions → stub tests). | TBD (e.g. pytest output, manifest assertion report) |

On refresh, the view loads these three (or two if test results are not yet wired), builds plan/actual and per-field status in memory, and renders. The view does not depend on a pre-written view file; the pipeline may write one for tooling.

## Inspector: intent vs contract status

- **Intent** (narrative, assertions, governance): status comes from **test results**. Assertions map to generated stub tests; pass/fail of those tests drives the intent status in the Inspector.
- **Contracts** (protocol, symbol, dependencies, outgoing_contracts): status comes from **code-extracted contents**. The extractor output is compared to the design; match → healthy, mismatch → deviation.

Each field in the Inspector can show a status indicator (e.g. ✓ / ⚠) according to whether it is intent (test) or contract (extractor).

## Stray code (code with no design)

**How the bottom-up process picks it up:** The extractor walks the codebase and produces entities for what it finds (files, symbols, protocols). It does *not* filter by "is this in the design?" So:

- A **stray function** appears as one extracted entity with no design entity matching it (by id/symbol). It is treated as **code-only** (orphan).
- A **whole unused module or feature** (e.g. `unused/old_feature/`) is still on disk, so the extractor sees it. It produces one or more entities (e.g. per file or per symbol). None of them have a design counterpart, so they all appear as **code-only**.

**How it is displayed:** Code-only entities are included in the computed view with status **extra**. They appear in the diagram (e.g. in a "Code only" or orphan list, or alongside design entities with a distinct style) and in the Inspector when selected. So "stray code" is exactly "extracted but not in the blueprint": the view shows it so the team can remove it or add it to the design.

**Summary:** Stray code is not special-cased; the extractor picks up all code it can, and anything with no matching design entity is shown as extra. A whole unused module is just one or more of those extra entities.
