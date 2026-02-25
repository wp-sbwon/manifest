# Doc creation: context management plan (with full examples)

This plan defines what context each doc layer-writer sub-worker receives, using the **mock tmp project** (calculator app from `scripts/create_mock_project_data.py`) as the concrete example. Below, “full context” means the actual payload (or its structure and representative content), not just a description.

---

## Mock tmp project (reference)

- **Blueprint tree** (design):
  - **PROJECT_ROOT** → children: `cli`, `arithmetic_engine`, `output`
  - **cli** → children: `[]`
  - **arithmetic_engine** → children: `add`, `sub`, `mul`
  - **output** → children: `[]`
  - **add**, **sub**, **mul** → children: `[]`

- **PRD** (from mock):
```json
{
  "title": "Calc CLI MVP",
  "sections": [
    {"id": "sec-1", "name": "User can run calculator from terminal"},
    {"id": "sec-2", "name": "Support add, subtract, multiply"},
    {"id": "sec-3", "name": "Unit tests for operations and CLI"}
  ]
}
```

- **Root entity** (abbreviated): id `PROJECT_ROOT`, narrative.role "Calculator", narrative.mission "CLI calculator: parse args → compute → format → print.", goals (CLI entry, Arithmetic, Tests), interface, global_rules, children `["cli", "arithmetic_engine", "output"]`, outgoing_contracts to cli/arithmetic_engine/output.

- **L1 entities**: cli (role "CLI", mission "Parse terminal input into op and two numbers."), arithmetic_engine (role "Arithmetic Engine", mission "Pure arithmetic: add, sub, mul (side-effect free).", children ["add","sub","mul"]), output (role "Output", mission "Format numeric result for console.").

---

## Who receives context (and when)

| Layer | Recipient | Trigger |
|-------|------------|--------|
| 0 | Single layer-writer **task** (parent = PROJECT_ROOT) | `bin/run_doc_layer_writer.py --parent PROJECT_ROOT --layer 0` (or equivalent) |
| 1 | One task per L1 entity: **cli**, **arithmetic_engine**, **output** | After layer-0 task completes, `try_spawn_next_layer` spawns 3 tasks |
| 2 | One task per L2 entity under arithmetic_engine: **add**, **sub**, **mul** | After all three layer-1 tasks complete, `try_spawn_next_layer` spawns 3 tasks |
| 3+ | None in this mock (add/sub/mul have no children; writers return `children: []`) | Branch stops when writer returns no children |

---

## Full context fed to each recipient

Each task’s `context` is a single JSON-like dict stored in `doc_layer_writer_tasks.json` and passed to the runner (and thence to `write_blueprint_layer` / LLM). Below is the **full shape and example content** for each “who”.

---

### 1. Layer-0 writer (parent = PROJECT_ROOT)

**Who:** The single subprocess running `bin/run_doc_layer_writer.py` with a task whose `parent_entity_id` is `PROJECT_ROOT` and `layer_index` is `0`.

**Full context payload:**

```json
{
  "layer_index": 0,
  "max_depth": 10,
  "parent_entity": {
    "id": "PROJECT_ROOT",
    "children": ["cli", "arithmetic_engine", "output"],
    "dependencies": [],
    "narrative": {"role": "Calculator", "mission": "CLI calculator: parse args → compute → format → print."},
    "blueprint": {"type": "FLOW", "topology": {}},
    "protocol": {"input": [{"name": "argv", "type": "string"}], "output": [{"name": "stdout", "type": "string"}]},
    "profile": {"language": "python", "platform": "cli", "io_model": "request_response", "state_model": "stateless"},
    "governance": {"rules": ["Stateless flow.", "No I/O in arithmetic engine."], "assertions": []},
    "symbol": "main",
    "traits": [],
    "topology_actual": {"type": "", "map": []},
    "preview": "main.py: parse → engine → format_result → print.",
    "outgoing_contracts": []
  },
  "prd_excerpt": {
    "title": "Calc CLI MVP",
    "sections": [
      {"id": "sec-1", "name": "User can run calculator from terminal"},
      {"id": "sec-2", "name": "Support add, subtract, multiply"},
      {"id": "sec-3", "name": "Unit tests for operations and CLI"}
    ]
  },
  "blueprint_excerpt": {
    "path_from_root": ["PROJECT_ROOT"],
    "parent_id": "PROJECT_ROOT",
    "sibling_ids": [],
    "root_id": "PROJECT_ROOT"
  }
}
```

**Instruction (conceptual):** Produce direct children of the root (top-level components). In the mock, the writer would output entities for `cli`, `arithmetic_engine`, `output` (or the LLM would derive similar from PRD + parent entity).

---

### 2. Layer-1 writer for entity **cli**

**Who:** One subprocess with task `parent_entity_id` = `"cli"`, `layer_index` = `1`.

**Full context payload:**

```json
{
  "layer_index": 1,
  "max_depth": 10,
  "parent_entity": {
    "id": "cli",
    "children": [],
    "dependencies": [],
    "narrative": {"role": "CLI", "mission": "Parse terminal input into op and two numbers."},
    "blueprint": {"type": "FLOW", "topology": {}},
    "protocol": {
      "input": [{"name": "argv", "type": "list"}],
      "output": [{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}]
    },
    "profile": {"language": "python", "platform": "cli", "io_model": "", "state_model": ""},
    "governance": {"rules": [], "assertions": []},
    "symbol": "cli.parser",
    "traits": ["parser"],
    "topology_actual": {"type": "", "map": []},
    "preview": "",
    "outgoing_contracts": [{"to": "arithmetic_engine", "type": "flow", "file": "cli/parser.py", "symbols": ["parse_args"]}]
  },
  "prd_excerpt": {
    "title": "Calc CLI MVP",
    "sections": [
      {"id": "sec-1", "name": "User can run calculator from terminal"},
      {"id": "sec-2", "name": "Support add, subtract, multiply"},
      {"id": "sec-3", "name": "Unit tests for operations and CLI"}
    ]
  },
  "blueprint_excerpt": {
    "path_from_root": ["PROJECT_ROOT", "cli"],
    "parent_id": "cli",
    "sibling_ids": ["arithmetic_engine", "output"],
    "root_id": "PROJECT_ROOT"
  }
}
```

**Instruction (conceptual):** Produce direct children of `cli`. In the mock, `cli` has no children, so the writer would return `children: []` and this branch stops.

---

### 3. Layer-1 writer for entity **arithmetic_engine**

**Who:** One subprocess with task `parent_entity_id` = `"arithmetic_engine"`, `layer_index` = `1`.

**Full context payload:**

```json
{
  "layer_index": 1,
  "max_depth": 10,
  "parent_entity": {
    "id": "arithmetic_engine",
    "children": ["add", "sub", "mul"],
    "dependencies": [],
    "narrative": {"role": "Arithmetic Engine", "mission": "Pure arithmetic: add, sub, mul (side-effect free)."},
    "blueprint": {"type": "FLOW", "topology": {}},
    "protocol": {
      "input": [{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
      "output": [{"name": "result", "type": "float"}]
    },
    "profile": {"language": "python", "platform": "cli", "io_model": "", "state_model": ""},
    "governance": {"rules": ["No side effects.", "Pure functions only."], "assertions": []},
    "symbol": "engine.calculator",
    "traits": ["orchestrator", "pure"],
    "topology_actual": {"type": "", "map": []},
    "preview": "",
    "outgoing_contracts": [
      {"to": "add", "type": "dependency", "file": "engine/calculator.py", "symbols": ["add"]},
      {"to": "sub", "type": "dependency", "file": "engine/calculator.py", "symbols": ["sub"]},
      {"to": "mul", "type": "dependency", "file": "engine/calculator.py", "symbols": ["mul"]},
      {"to": "output", "type": "flow", "file": "main.py", "symbols": ["format_result"]}
    ]
  },
  "prd_excerpt": {
    "title": "Calc CLI MVP",
    "sections": [
      {"id": "sec-1", "name": "User can run calculator from terminal"},
      {"id": "sec-2", "name": "Support add, subtract, multiply"},
      {"id": "sec-3", "name": "Unit tests for operations and CLI"}
    ]
  },
  "blueprint_excerpt": {
    "path_from_root": ["PROJECT_ROOT", "arithmetic_engine"],
    "parent_id": "arithmetic_engine",
    "sibling_ids": ["cli", "output"],
    "root_id": "PROJECT_ROOT"
  }
}
```

**Instruction (conceptual):** Produce direct children of `arithmetic_engine`. In the mock, the writer would return entities for `add`, `sub`, `mul`.

---

### 4. Layer-1 writer for entity **output**

**Who:** One subprocess with task `parent_entity_id` = `"output"`, `layer_index` = `1`.

**Full context payload:** Same structure as for **cli**, with `parent_entity` = the full output entity (role "Output", mission "Format numeric result for console.", children [], etc.), `path_from_root` = `["PROJECT_ROOT", "output"]`, `sibling_ids` = `["cli", "arithmetic_engine"]`. **prd_excerpt** same as above (full PRD or same excerpt). Writer returns `children: []` for the mock.

---

### 5. Layer-2 writer for entity **add** (and similarly **sub**, **mul**)

**Who:** One subprocess with task `parent_entity_id` = `"add"`, `layer_index` = `2`.

**Full context payload (add):**

```json
{
  "layer_index": 2,
  "max_depth": 10,
  "parent_entity": {
    "id": "add",
    "children": [],
    "dependencies": [],
    "narrative": {"role": "Add", "mission": "Return a + b."},
    "blueprint": {"type": "FLOW", "topology": {}},
    "protocol": {
      "input": [{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
      "output": [{"name": "result", "type": "float"}]
    },
    "profile": {"language": "python", "platform": "cli", "io_model": "", "state_model": ""},
    "governance": {"rules": ["Pure function."], "assertions": []},
    "symbol": "calc.operations.add",
    "traits": ["pure", "O(1)"],
    "topology_actual": {"type": "", "map": []},
    "preview": "",
    "outgoing_contracts": []
  },
  "prd_excerpt": {
    "title": "Calc CLI MVP",
    "sections": [
      {"id": "sec-1", "name": "User can run calculator from terminal"},
      {"id": "sec-2", "name": "Support add, subtract, multiply"},
      {"id": "sec-3", "name": "Unit tests for operations and CLI"}
    ]
  },
  "blueprint_excerpt": {
    "path_from_root": ["PROJECT_ROOT", "arithmetic_engine", "add"],
    "parent_id": "add",
    "sibling_ids": ["sub", "mul"],
    "root_id": "PROJECT_ROOT"
  }
}
```

**Instruction (conceptual):** Produce direct children of `add`. In the mock, add has no further breakdown, so the writer returns `children: []` and this branch stops. Same idea for **sub** and **mul** (same structure, different parent_entity id/role/mission/symbol).

---

## Summary table (who gets what)

| Recipient | parent_entity_id | layer_index | path_from_root | sibling_ids | prd_excerpt |
|-----------|------------------|-------------|----------------|-------------|-------------|
| Layer-0 writer | PROJECT_ROOT | 0 | [PROJECT_ROOT] | [] | Full PRD (title + sections) |
| Layer-1 writer (cli) | cli | 1 | [PROJECT_ROOT, cli] | [arithmetic_engine, output] | Full PRD (or excerpt) |
| Layer-1 writer (arithmetic_engine) | arithmetic_engine | 1 | [PROJECT_ROOT, arithmetic_engine] | [cli, output] | Full PRD (or excerpt) |
| Layer-1 writer (output) | output | 1 | [PROJECT_ROOT, output] | [cli, arithmetic_engine] | Full PRD (or excerpt) |
| Layer-2 writer (add) | add | 2 | [PROJECT_ROOT, arithmetic_engine, add] | [sub, mul] | Full PRD (or excerpt) |
| Layer-2 writer (sub) | sub | 2 | [PROJECT_ROOT, arithmetic_engine, sub] | [add, mul] | Full PRD (or excerpt) |
| Layer-2 writer (mul) | mul | 2 | [PROJECT_ROOT, arithmetic_engine, mul] | [add, sub] | Full PRD (or excerpt) |

---

## Implementation notes (unchanged from prior plan)

- **Single helper** `build_layer_writer_context(manifest_dir, parent_entity_id, layer_index, max_depth=None, max_context_tokens=12000)` builds this dict: load blueprint → parent entity, path from root, sibling ids; load PRD → full or excerpt; optionally cap size by trimming prd_excerpt then blueprint_excerpt.
- **Wire spawn:** `try_spawn_next_layer` and the layer-0 entry point (e.g. `bin/run_doc_layer_writer.py`) call the helper and pass the result as `context` for each task (no more `context={}`).
- **Runner:** Uses `task["context"]` as the full structured payload; when adding an LLM, pass `context["parent_entity"]`, `context["prd_excerpt"]`, etc. explicitly. **Stopping:** When the writer returns `children: []`, merge as-is and do not add a placeholder; that branch stops. Optional `max_depth` cap in `try_spawn_next_layer` to avoid spawning beyond layer N.

This document is the plan: the mock tmp project examples above are the **full context** (shape and example content) fed to each “who” in the doc layer-writer pipeline.
