# Bottom-up workflow (code → blueprint_code)

How `blueprint_code.json` is produced from the actual codebase. Design is used only as a guide so that naming and structure can align with top-down; the **source of truth for what exists is the code**.

---

## 1. Overview

- **Goal:** Build a blueprint that describes the **actual** code (entities, dependencies, contracts). No entities that are only in design and not in code.
- **Principle:** Code is the source of truth. Design is a guide for schema, naming, and alignment so top-down and bottom-up documents can be compared.

---

## 2. Steps (in order)

### Step 1: Code extraction (CodeExtractor)

- **Who:** `CodeExtractor` in `src/manifest/audit/code/code_extractor.py`.
- **Input:** Project root (directory of source code).
- **What it does:** Scans Python files, parses AST, identifies components (classes, module-level functions) and relationships (calls, imports, inheritance). Builds an **extraction outline**: a blueprint-shaped dict with `version`, `root_id`, `entities` (each with `id`, `symbol`, `dependencies`, `outgoing_contracts`, `protocol`, `profile`, `traits`, etc.).
- **Output:** `extracted_blueprint` (dict). Entity ids are **extraction-style** (e.g. `comp-{module_path}-{node_name}`). No design knowledge here.

### Step 2: Design-id hints (builder)

- **Who:** `build_code_blueprint` → `_extraction_with_design_id_hints` in `src/manifest/audit/code/code_blueprint_builder.py`.
- **Input:** `design_blueprint`, `extracted_blueprint`.
- **What it does:** For each design entity, finds the best-matching extracted entity (by id, name, path, tokens). Builds a mapping extracted_id → design_id. Adds a **`design_id`** field to each extracted entity that has a design match.
- **Output:** `extraction_with_hints`: same as extraction but with optional `design_id` on entities. This is passed to the agent so it can use design names where they exist.

**How matching works (Step 2):**

We iterate over **design entities** (skip root). For each design entity we look for one **extracted entity** that best corresponds to it.

1. **Exact lookup**
   We build a lookup from extracted entities by **id** and by **display name** (narrative.role, name, symbol, or id). If the design entity’s `id` or its display name equals an extracted id or an extracted display name, we use that extracted entity and stop.

2. **Fuzzy scoring**
   If there’s no exact match, we score every extracted entity and pick the best:
   - **Score 3 (path):** Design id or its path form (e.g. `runner` → `runner` in path) appears in the extracted entity’s **module path** (parsed from `comp-{module}-{name}`), or design id appears in the module path with underscores. Example: design `runner`, extracted `comp-runner-run` → module path `runner` → match.
   - **Score 2 (partial):** The normalized design id (strip spaces/dashes/dots, lowercased) appears as a segment in the extracted entity’s **display name**, **id**, or **symbol**. Example: design `greeter`, extracted display `Greeter` or id containing `greeter`.
   - **Score 1 (tokens):** We tokenize design id, design display name, and design narrative.role, and the extracted id, display name, and symbol. We count **token overlap**. Any overlap gives score 1; we use the overlap count as tie-breaker (higher overlap = better).

3. **Choice and mapping**
   We take the candidate with **highest score**, then **highest tie-break** (e.g. overlap count). One extracted entity is assigned at most one design id: the first design entity that matches it gets to claim it (`if ext_id not in extracted_to_design`). So design entities are processed in iteration order; the first match wins.

### Step 3: Agent run (enricher)

- **Who:** `enrich_code_blueprint` in `src/manifest/opencode/code_blueprint_enricher.py`; invokes the **opencode** agent `enrich-code-blueprint`.
- **Input (to agent):**
  1. **Extraction outline** (with `design_id` hints): what the extractor found and which design entity each matches.
  2. **Actual code:** project root so the agent can read source files.
  3. **Design blueprint:** schema/naming guide only; not the source of what exists.
- **What the agent does:** Reads the three inputs. Produces a **blueprint_code** JSON: same entity-layer schema as design (id, children, dependencies, narrative, protocol, profile, symbol, traits, outgoing_contracts, etc.). Must include **only** entities present in the code. Should use **design_id** as entity id when present (so top-down and bottom-up share names), and use design ids in children, dependencies, and `outgoing_contracts[].to`.
- **Where temp files go:** Enrich inputs (design.json, extraction.json) are written to a **run-unique directory** under the manifest app temp dir (`MANIFEST_TMP_DIR` or `gettempdir()/manifest`), then removed after the run. Nothing is written under the project root or under `.manifest` for this.
- **Output:** Valid blueprint dict; validated (schema + referential integrity), then returned.

### Step 4: Profile normalization (builder)

- **Who:** `build_code_blueprint` after the enricher returns.
- **What it does:** Ensures each entity’s `profile.language` is a list (normalized from string or list).
- **Output:** Final `blueprint_code` dict used to write `blueprint_code.json`.

---

## 3. Data flow (summary)

```
project_root (source code)
       │
       ▼
  CodeExtractor.extract_project_structure()
       │
       ▼
  extracted_blueprint (comp-* ids, no design)
       │
       + design_blueprint
       ▼
  _extraction_with_design_id_hints()  →  extraction_with_hints (adds design_id where matched)
       │
       ▼
  enrich_code_blueprint(design, extraction_with_hints, project_root, manifest_dir)
       │  writes design.json + extraction.json to app temp dir
       │  runs: opencode run … --agent enrich-code-blueprint --dir project_root -f design.json -f extraction.json
       │  parses stdout, validates blueprint
       ▼
  blueprint_code (agent output; only code entities; design ids when design_id was set)
       │
       ▼
  profile normalization  →  final blueprint_code
```

---

## 4. Roles in one sentence

| Step              | Role                                                                 |
|-------------------|----------------------------------------------------------------------|
| CodeExtractor     | Produce a code-only outline (structure + ids from code).             |
| Design-id hints   | Map extraction entities to design entities; add `design_id` for agent. |
| Agent (enricher)  | From outline + code + design (guide), produce full blueprint_code using code as truth and design for naming. |
| Builder           | Orchestrate extraction → hints → enricher → normalize; return blueprint_code. |

---

## 5. What is *not* in this workflow

- **No merge fallback:** There is no path that “merges” design and extraction into blueprint_code without the agent. Only the agent produces blueprint_code.
- **No writing under project root:** Temp files for the agent live in the app temp dir only.
- **No design-only entities in blueprint_code:** If the design has an entity that does not exist in the code, it must not appear in blueprint_code (the agent is instructed to omit it).
