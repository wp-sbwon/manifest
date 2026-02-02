# Project rules (.rules)

This directory holds **project rules** that agents (orchestrator and workers) are instructed to read and follow. It is provider-agnostic (not tied to any specific AI vendor).

## Contents

- **task-granularity.md** – Max files per task, recommended scope (e.g. 7 recommended, 12 max)
- **prd-template.md** – PRD structure and required sections for ideation
- **code-style.md.example** – Code style and formatting (copy to `code-style.md` to enable)
- **manifest-policy.md** (optional) – Tier 0 policy; create if you want a global policy file

## Usage

Skills and policy loaders in this repo read from `.rules/` (see `src/manifest/agents/skills_manager.py`, `context_provider.py`, `task_scoper.py`).
