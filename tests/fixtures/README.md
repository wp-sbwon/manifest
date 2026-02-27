# Test fixtures

## Bottom-up (code → blueprint)

**Mock project:** `bottom_up_project/`

- **runner.py** – `run(name: str) -> str`; imports and calls `greet` and `format`. Orchestrator.
- **greeter.py** – `greet(name: str) -> str`. Leaf component.
- **formatter.py** – `format(text: str) -> str`. Leaf component.

The project has **depth**: root → runner → [greeter, formatter]. It exercises the full entity shape:

- **Child–parent structure:** root (children: [runner]), runner (children: [greeter, formatter]), greeter/formatter (children: []).
- **Entity fields:** id, children, dependencies, narrative, blueprint, protocol, profile, governance, symbol, traits, topology_actual, preview, outgoing_contracts (unified schema; extraction fills symbol, protocol, profile, dependencies, traits).
- **Outgoing contracts:** runner has contracts to greeter and formatter (from design).

**Golden file:** `bottom_up_expected.json`

100% accurate expected output for running the bottom-up pipeline (CodeExtractor outline + agent (design as guide) that has this tree and runner’s outgoing_contracts) on `bottom_up_project/`. Paths use the placeholder `<PROJECT_ROOT>`.

The test runs the actual bottom-up pipeline and asserts the output matches this file. If they differ, the code is wrong and must be fixed to match the spec.
