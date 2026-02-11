# Doc creation process: user journey and hierarchical blueprint

This document describes the intended flow from ideation to PRD to blueprint, and the multi-agent, layer-by-layer blueprint creation so that no single agent has to author the entire entity model at once.

## User journey

1. **Ideation** – User talks to the ideation agent (OpenCode/ClaudeCode terminal) about the project: goals, users, flows, constraints. Conversation continues until the idea is sufficiently clear.
2. **PRD first** – Once the idea is finalized, the first written artifact is the **PRD** (`.manifest/prd.json`). The ideation agent (or orchestrator in ideation mode) should call the architect tool with `write_prd` to persist the PRD. No blueprint yet.
3. **Blueprint from PRD** – After PRD exists, the user (or the same agent) triggers **blueprint creation**. The blueprint is the entity model (root, features, components, intent per entity). This step is done **hierarchically** by multiple agents, not by one agent in a single pass.

## Why hierarchical blueprint creation

A single agent writing the whole blueprint (all layers and all intent) in one go is error-prone and context-heavy. Splitting by layer and by subtree:

- Keeps each agent’s context focused (one layer, one parent entity, PRD excerpt).
- Allows parallel work on sibling entities (e.g. one agent per top-level feature).
- Produces better intent and structure per entity because each agent specializes in “this entity and its children” rather than “the whole tree.”

## Hierarchical flow (recursive)

The same layer-writer process runs for every layer, including layer 0: one runner (`run_doc_layer_writer.py`) handles all layers. `run_layer_0` spawns one task (parent = root, layer_index = 0); that process produces the root's children (top-level entities), merges, then `try_spawn_next_layer` spawns layer 1. No separate layer-0 script.

- **Layer 0 (root + top level)**
  One **planner / doc-writing agent** (e.g. “blueprint root planner”) is started with:
  - PRD (full or summary)
  - Entity schema (root_id, entities with id, children, intent, reality)
  - Instruction: produce the **root** entity and **top-level entities only** (e.g. features). For each top-level entity, fill: id, name, intent (narrative.role, mission, high-level interface), and `children: []` (to be filled later). No deeper subtree yet.

- **Layer 1 (one agent per top-level entity)**
  For **each** top-level entity produced in layer 0, the system spawns a **sub-agent** (layer writer) with:
  - PRD (or excerpt relevant to that feature)
  - That entity’s intent and id (from layer 0)
  - Parent path (e.g. root_id → feature_id)
  - Schema and rules (e.g. id naming, no cycles)
  - Instruction: produce **only the direct children** of this entity (components or sub-features), with full entity dicts (id, intent, children=[]). Do not recurse deeper.

- **Layer 2+**
  Same pattern: for each entity that has `children: []` and is marked to be expanded (e.g. by depth limit or by “expand_children” flag), spawn a **layer writer** for that entity. Each writer receives:
  - Parent entity’s intent and id
  - PRD excerpt
  - Existing partial blueprint (so the writer can see siblings and avoid id clashes)
  - Instruction: produce only direct children of that parent.

- **Merge**
  Each layer writer returns a **fragment**: a list of entity dicts (the new children). The **coordinator** (or a merge step) updates the single blueprint:
  - By `entity_id`: add new entities; for the parent entity, set `children` to the list of child ids from the fragment.
  - Persist to `.manifest/blueprint_design.json` (e.g. via `BlueprintLoader.save_blueprint` or a dedicated merge API).

So: **one planner for layer 0**, then **one agent per entity at each layer** for the next layer, with context scoped to that entity and PRD; merge after each layer (or after each entity) into one blueprint.

## Agent roles (proposed)

- **Ideation agent** – Converses with user; when idea is finalized, calls architect `write_prd`; then may trigger “start blueprint from PRD” (e.g. via a doc_creation or hierarchical_blueprint tool).
- **Blueprint root planner (layer 0)** – Single agent run with PRD + schema; outputs root + top-level entities (with intent, empty children). Triggers spawn of one **layer writer** per top-level entity.
- **Blueprint layer writer (layer N, per entity)** – Receives parent entity + PRD excerpt + partial blueprint. Outputs direct children only. Calls merge to attach children to parent; optionally triggers spawn of layer writers for each new child if depth limit not reached.

Spawning can be implemented like worker_squad_spawn: record a “doc_layer_writer” task with context (parent_entity_id, prd_excerpt, depth); when that agent runs, it loads context, produces the fragment, calls merge, and optionally spawns child layer writers.

## Wiring (implementation)

When OpenCode is configured (`agent.execution_backend` = `opencode`), `write_blueprint_layer` calls OpenCode **via the backend agent** (not raw LLM): sync HTTP session create + session message with `agent` set (config: `opencode.layer_writer_agent`, default `architect`). The OpenCode server runs that agent (context, tools, model from opencode.json); we send a layer-writer task as the message and parse the agent’s reply for a JSON array of child entities. This matches worker agents: agent actions go through the backend so we don’t manage context or tools directly. The prompt is built from PRD, parent entity, and blueprint scope; response is parsed and normalized to entity dicts. On empty or parse failure, no children are returned; we accept that (expansion stops at that layer; the user can re-run or refine ideation/PRD if needed).

## Order of operations (summary)

1. User ideates → ideation agent.
2. Idea finalized → architect tool `write_prd` → `.manifest/prd.json`.
3. User or agent triggers “create blueprint from PRD.”
4. Layer 0: one agent writes root + top-level entities → partial blueprint saved; spawn one layer writer per top-level entity.
5. Each layer writer: load context (parent, PRD) → write direct children → merge into blueprint → spawn layer writers for each child (if needed).
6. When no more “expand” is requested or depth limit is reached, blueprint is complete.

## Tool / API surface (for implementation)

- **architect** (existing): `write_prd`, `write_architecture`. Use `write_prd` after ideation; use `write_architecture` only for the **final** merged blueprint or for manual single-pass writes.
- **doc_creation** (or **hierarchical_blueprint**) (new):
  - `start_blueprint_from_prd` – Input: PRD path or content. Runs or enqueues layer-0 writer; returns partial blueprint + list of spawn tasks (one per top-level entity).
  - `write_blueprint_layer` – Input: parent_entity_id, prd_excerpt, current_blueprint (or manifest_dir). Output: list of child entity dicts. Used by a layer writer agent.
  - `merge_blueprint_fragment` – Input: current blueprint, parent_entity_id, list of child entity dicts. Merges (add entities, set parent’s children), validates, saves `blueprint_design.json`.
  - `spawn_layer_writer` – Input: parent_entity_id, context (PRD excerpt, parent intent, depth). Records a doc_layer_writer task; returns task_id. When that agent runs, it calls `write_blueprint_layer` then `merge_blueprint_fragment`, then optionally `spawn_layer_writer` for each new child.

This keeps the data schema (blueprint_design.json, entity schema) unchanged; only the **creation process** is multi-agent and layer-by-layer.
