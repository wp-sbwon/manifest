# Bottom-up workflow (code → blueprint_code)

How `blueprint_code.json` is produced from the actual codebase. Design provides narrative and governance; extraction provides mechanical fields (symbol, protocol, dependencies). Merge is deterministic (exact ID and symbol-based mapping).

---

## 1. Overview

- **Goal:** Build a blueprint that describes the **actual** code (entities, dependencies, contracts). Design entities without extraction match remain as planned; extracted entities without design id appear as orphans.
- **Principle:** Code is the source of truth for mechanical structure. Design supplies narrative and governance. Merge uses exact ID matching after mapping extraction ids to design ids by symbol equality.

---

## 2. Steps (in order)

### Step 1: Code extraction (CodeExtractor)

- **Who:** `CodeExtractor` in `src/manifest/audit/code/code_extractor.py`.
- **Input:** Project root (directory of source code).
- **What it does:** Scans Python files, parses AST, identifies components (classes, module-level functions) and relationships (calls, imports, inheritance). Builds an **extraction outline**: a blueprint-shaped dict with `version`, `root_id`, `entities` (each with `id`, `symbol`, `dependencies`, `outgoing_contracts`, `protocol`, `profile`, `traits`, etc.).
- **Output:** `extracted_blueprint` (dict). Entity ids are extraction-style (e.g. `comp-{module_path}-{node_name}`).

### Step 2: Map extraction ids to design ids (builder)

- **Who:** `build_code_blueprint` → `_extraction_with_design_ids` in `src/manifest/audit/code/code_blueprint_builder.py`.
- **Input:** `design_blueprint`, `extracted_blueprint`.
- **What it does:** For each design entity, normalized symbol (path to dots, no `.py`) is recorded. For each extracted entity, normalized symbol is compared; when it matches exactly one design entity’s symbol, that extracted entity’s id is rewritten to the design id (one-to-one). Root and unmatched extracted entities keep their ids.
- **Output:** Extraction dict with entities whose ids may now be design ids where symbol matched.

### Step 3: Merge (builder)

- **Who:** `merge_design_and_extraction` in `src/manifest/audit/code/code_blueprint_builder.py`.
- **Input:** `design_blueprint`, extracted blueprint from Step 2.
- **What it does:** For each design entity id, if an extracted entity has the same id: entity gets narrative, blueprint, governance from design and symbol, protocol, profile, dependencies, traits, topology_actual, preview from extraction. If no extracted match: design entity is included as-is (planned). All extracted entities whose id is not in design are appended as orphans. Referential integrity: children, dependencies, outgoing_contracts are filtered to valid entity ids.
- **Output:** Normalized blueprint (version, root_id, entities) with profile.language aggregated and normalized.

### Step 4: Profile normalization (builder)

- **Who:** `build_code_blueprint` after merge returns.
- **What it does:** Ensures each entity’s `profile.language` is a list.
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
  extracted_blueprint (comp-* ids)
       │
       + design_blueprint
       ▼
  _extraction_with_design_ids()  →  extraction with design ids where symbol matches
       │
       ▼
  merge_design_and_extraction(design, extraction_mapped)
       │  exact ID only; narrative/governance from design, mechanical from extraction; orphans appended
       ▼
  blueprint_code
       │
       ▼
  profile normalization  →  final blueprint_code
```

---

## 4. Roles in one sentence

| Step                    | Role                                                                 |
|-------------------------|----------------------------------------------------------------------|
| CodeExtractor           | Produce a code-only outline (structure + ids from code).             |
| Design-id mapping       | Rewrite extracted entity ids to design ids when symbol matches.      |
| Merge                   | Combine design (narrative, governance) and extraction (mechanical) by exact ID; add orphans. |
| Builder                 | Orchestrate extraction → mapping → merge → normalize; return blueprint_code. |

---

## 5. What is *not* in this workflow

- **No agent run:** blueprint_code is produced by deterministic merge only.
- **No writing under project root:** All output is under `.manifest` or app temp as needed.
- **Orphans:** Extracted entities that do not match any design id by symbol are included with their extraction id and empty narrative/governance so the view can show Orphaned status.
