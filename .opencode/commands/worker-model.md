---
description: "Worker squad model: /worker-model [agent] [provider] [model]. Agents: planner, coder, test, review. No args = list; agent only = use default. Example: /worker-model coder anthropic claude-sonnet-4-5"
---
Set or list Manifest worker squad models. The command below runs in your project; use no arguments to list, or --help for full usage.

!`manifest config worker-model $ARGUMENTS`

Quick reference:
- /worker-model — list current models
- /worker-model coder — clear coder (use backend default)
- /worker-model coder anthropic claude-sonnet-4-5 — set coder model
- /worker-model coder anthropic/claude-sonnet-4-5 — same (provider/model in one arg)
