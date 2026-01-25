"""
Project review agent for requirements compliance verification.

This module provides the ProjectReviewAgent class which reviews completed
Worker Squad work at the project level. It verifies that PRD requirements
are met, checks architecture/blueprint compliance, and ensures project-wide
consistency.

This is a higher-level review than the approver agent, which reviews
individual tasks. The project review agent looks at the big picture.
"""
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.state_manager import StateManager

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


PROJECT_REVIEW_IDENTITY = """
## PROJECT REVIEW AGENT IDENTITY

**YOU ARE A PROJECT REVIEW AGENT. YOU REVIEW PROJECT-LEVEL REQUIREMENTS COMPLIANCE.**

Your role:
- Review completed Worker Squad work at project level
- Verify PRD requirements are met
- Check Architecture/Blueprint compliance
- Ensure project-wide consistency

You do NOT:
- Review individual task implementation details (that's Approver's job)
- Write code or tests

You DO:
- Review against PRD requirements
- Check Architecture/Blueprint alignment
- Verify project-wide consistency
- Identify missing requirements
- Provide feedback to Orchestrator if requirements not met
"""


class ProjectReviewAgent:
    """Project review agent for project-level requirements verification.
    
    Reviews completed Worker Squad work against PRD requirements, architecture
    constraints, and blueprint specifications. This is a higher-level review
    than task-level approval - it ensures the overall project goals are met
    and maintains project-wide consistency.
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting review results.
        message_history: List of conversation messages for context.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"] = None
    ):
        """Initialize the project review agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving review results.
            terminal_router: Optional terminal router for command execution.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.terminal_router = terminal_router
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def review(
        self,
        prd_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
        blueprint_data: Dict[str, Any],
        worker_squad_output: Dict[str, Any],
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Review project-level requirements compliance.
        
        Examines the completed Worker Squad output against PRD requirements,
        architecture guidelines, and blueprint specifications. Identifies
        any missing requirements or inconsistencies at the project level.
        
        Args:
            prd_data: Product Requirements Document containing project goals.
            architecture_data: Architecture document with system design.
            blueprint_data: Blueprint document with component specifications.
            worker_squad_output: Complete output from Worker Squad execution.
            context: Tiered context for additional information.
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains review findings, requirements compliance status,
            and recommendations.
        """
        # Generate review prompt
        prompt = self._generate_review_prompt(
            prd_data, architecture_data, blueprint_data, worker_squad_output, context
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="project_review",
            prompt=prompt,
            model_config=model_config,
            context=context,
            message_history=self.message_history
        ):
            # Save to message history
            if chunk.get("type") == "chunk":
                if not self.message_history or self.message_history[-1]["role"] != "assistant":
                    self.message_history.append({"role": "assistant", "content": ""})
                self.message_history[-1]["content"] += chunk.get("content", "")
            elif chunk.get("type") == "complete":
                # Save complete response
                await self._save_response(chunk.get("content", ""))
            
            yield chunk
    
    def _generate_review_prompt(
        self,
        prd_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
        blueprint_data: Dict[str, Any],
        worker_squad_output: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate project review prompt."""
        import json
        
        prompt = f"""
{PROJECT_REVIEW_IDENTITY}

## PRD REQUIREMENTS

{json.dumps(prd_data, indent=2)}

## ARCHITECTURE

{json.dumps(architecture_data, indent=2) if architecture_data else "No architecture data"}

## BLUEPRINT

{json.dumps(blueprint_data, indent=2) if blueprint_data else "No blueprint data"}

## WORKER SQUAD OUTPUT

{json.dumps(worker_squad_output, indent=2)}

## CONTEXT

{context.get("tier_0", "No policy context")}
{context.get("tier_1", "No architecture context")}

## YOUR TASK

1. Review Worker Squad output against PRD requirements
2. Check Architecture/Blueprint compliance
3. Verify project-wide consistency
4. Identify any missing requirements
5. Provide feedback to Orchestrator if requirements not met

Output your review in this format:
REQUIREMENTS_MET: YES|NO
FINDINGS:
- [finding 1]
- [finding 2]
RECOMMENDATIONS:
- [recommendation 1]
- [recommendation 2]
"""
        return prompt
    
    async def _save_response(self, content: str) -> None:
        """Save project review results to state and chat history.
        
        Writes the review findings and recommendations to the appropriate
        channel so they can be displayed in the UI and used for project
        planning.
        
        Args:
            content: The complete project review content.
        """
        channel = f"squad-{self.agent_id}-project_review"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
