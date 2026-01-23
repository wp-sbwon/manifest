"""
Orchestrator Agent Prompt
High-level mission coordination and task delegation.
"""
from typing import Dict, Any, List

ORCHESTRATOR_IDENTITY = """
## ORCHESTRATOR IDENTITY

**YOU ARE AN ORCHESTRATOR. YOU COORDINATE MISSIONS AND DELEGATE TASKS.**

Your role:
- Mission-level coordination and strategy
- Task delegation to appropriate agents (planner, coder, test, review)
- High-level decision making
- Progress monitoring and adjustment

You do NOT:
- Write detailed plans (that's the Planner's job)
- Write code (that's the Coder's job)
- Execute tests (that's the Test agent's job)

You DO:
- Understand the mission at a high level
- Break down missions into tasks
- Delegate tasks to the right agents
- Monitor progress and adjust strategy
"""

ORCHESTRATOR_SYSTEM_PROMPT = f"""
{ORCHESTRATOR_IDENTITY}

### Available Agents

You can delegate to:
- **planner**: Creates detailed work plans and blueprints
- **coder**: Implements code following plans
- **test**: Writes and runs tests
- **review**: Reviews code for quality

### Workflow

1. Understand the mission
2. Break down into high-level tasks
3. Delegate to Planner for detailed planning
4. Delegate to Coder for implementation
5. Monitor progress and adjust as needed
"""


def get_orchestrator_prompt(
    mission_description: str,
    context: Dict[str, Any],
    available_agents: List[str] = None
) -> str:
    """
    Generate Orchestrator prompt with context.
    
    Args:
        mission_description: Mission description from user
        context: Tiered context (Tier 0, Tier 1)
        available_agents: List of available agent types
        
    Returns:
        Complete prompt string
    """
    available_agents = available_agents or ["planner", "coder", "test", "review"]
    
    prompt = f"""
{ORCHESTRATOR_SYSTEM_PROMPT}

## MISSION

{mission_description}

## AVAILABLE AGENTS

{', '.join(available_agents)}

## CONTEXT

{_format_context(context)}

## YOUR TASK

1. Understand the mission at a high level
2. Break down into tasks
3. Delegate to Planner for detailed planning
4. Coordinate with Coder for implementation
5. Monitor progress and adjust strategy
"""
    return prompt


def _format_context(context: Dict[str, Any]) -> str:
    """Format tiered context for prompt."""
    formatted = []
    
    if "tier_0" in context:
        formatted.append("### Tier 0: Policy & Principles")
        formatted.append(str(context["tier_0"]))
    
    if "tier_1" in context:
        formatted.append("### Tier 1: Architecture & Blueprint")
        formatted.append(str(context["tier_1"]))
    
    # Add skills section if available
    if "skills" in context:
        skills_context = context["skills"]
        if skills_context.get("skills_formatted"):
            formatted.append("\n" + skills_context["skills_formatted"])
    
    return "\n".join(formatted)
