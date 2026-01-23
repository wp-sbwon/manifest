# Skills System

Manifest supports a hierarchical skills system following OpenCode conventions, allowing users to configure skills at two levels:

1. **Agent Default Skills**: Per-agent type skills in `.manifest/agent_config.json`
2. **Project Scope Skills**: Project-wide skills in `AGENTS.md` and `.claude/rules/`

## Skills Hierarchy (Priority Order)

1. **Project Scope Skills** (`AGENTS.md`, `.claude/rules/*.md`) - Highest priority
2. **Agent Default Skills** (`.manifest/agent_config.json`) - Fallback
3. **Global Skills** (future: user-level skills) - Lowest priority

## Configuration

### Agent Default Skills

Edit `.manifest/agent_config.json`:

```json
{
  "agent_skills": {
    "orchestrator": ["skill1", "skill2"],
    "planner": ["skill3"],
    "coder": ["skill1", "skill4"],
    "test": [],
    "review": []
  }
}
```

### Project Scope Skills

#### Option 1: AGENTS.md (OpenCode Convention)

Create `AGENTS.md` in your project root:

```markdown
# AGENTS.md

## Skills

### Skill: code_review
Automatically review code changes for quality.

**Triggers**: review, code review, check code

**Agents**: coder, review
```

#### Option 2: .claude/rules/ (OpenCode Convention)

Create skill files in `.claude/rules/` directory:

```markdown
# .claude/rules/code-style.md

# Code Style Guidelines

## Description
Project-specific code style rules.

## Trigger Keywords
- code style
- formatting
- lint

## Agents
- coder
- review
```

## Skill File Format

Skills follow markdown format with metadata:

```markdown
# Skill Name

## Description
What this skill does

## Trigger Keywords
- keyword1
- keyword2

## Agents
- coder
- planner
```

## Usage

Skills are automatically loaded and injected into agent prompts. When a request matches a skill trigger, the agent will invoke the skill immediately.

### Example

If you have a skill with trigger "code review" and the user says "review this code", the agent will:
1. Detect the trigger match
2. Load the skill content
3. Execute the skill workflow
4. Return results

## Integration with OpenCode

Manifest's skills system follows OpenCode conventions:
- `AGENTS.md` file support
- `.claude/rules/` directory structure
- Compatible with OpenCode skill definitions

This allows you to use the same skills configuration across both Manifest and OpenCode.
