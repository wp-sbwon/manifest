# OpenCode Setup Guide for Manifest

## Problem: "manifest agent not found"

If you see this error when running `manifest`, it means OpenCode doesn't recognize the `manifest-orchestrator` agent.

## Solution Options

### Option 1: Run without --agent flag (Recommended)

The launcher will now run OpenCode without forcing a specific agent. You can:
1. Select the agent in OpenCode UI when it starts
2. Or configure it in OpenCode settings

### Option 2: Create OpenCode Agent Configuration

OpenCode agents are typically configured in one of these ways:

#### A. Using AGENTS.md (OpenCode Convention)

Create or update `AGENTS.md` in your project root:

```markdown
# Manifest Orchestrator Agent

## Description
Manifest orchestrator agent for managing tasks, sprints, and workflows.

## Capabilities
- Task management
- Sprint execution
- Blueprint synchronization
- Drift detection
```

#### B. Using OpenCode Agent Directory

If OpenCode uses an agent directory (check OpenCode docs for your version):

1. Find OpenCode config directory (usually `~/.opencode/` or `.opencode/` in project)
2. Create agent definition file (format depends on OpenCode version)

### Option 3: Use Environment Variable

Set the agent name via environment variable:

```bash
export MANIFEST_OPENCODE_AGENT="your-agent-name"
manifest
```

Or specify in `.manifest/settings.json`:

```json
{
  "opencode": {
    "agent": "your-agent-name"
  }
}
```

## View App

The Manifest View app runs in the background. If you don't see it:

1. Check the log file: `.manifest_view.log` in your project root
2. The View should appear as a separate terminal window
3. If it doesn't appear, check:
   - Python environment is correct
   - Textual is installed: `pip install textual`
   - No errors in `.manifest_view.log`

## Troubleshooting

### View not appearing

```bash
# Check if View process is running
ps aux | grep manifest.view.app

# Check View log
cat .manifest_view.log

# Run View manually to see errors
PYTHONPATH=src python -m manifest.view.app
```

### OpenCode agent issues

```bash
# List available OpenCode agents (if supported)
opencode --list-agents

# Run OpenCode without agent
opencode . -c

# Then select agent in OpenCode UI
```

### Manual View Start

If View doesn't start automatically:

```bash
# In a separate terminal
PYTHONPATH=src python -m manifest.view.app
```

## Current Behavior

When you run `manifest`:

1. **View App**: Starts in background (check `.manifest_view.log` for output)
2. **OpenCode**: Starts with `--agent manifest-orchestrator` (if agent exists) or without agent flag
3. **If agent not found**: OpenCode will start normally, you can select agent in UI

## Next Steps

1. Run `manifest` again
2. If agent not found, select it in OpenCode UI or create the agent config
3. Check `.manifest_view.log` to verify View is running
4. View should appear as a separate window showing blueprint/tasks/drift
