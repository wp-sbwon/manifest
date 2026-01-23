"""
Project Review Agent - Reviews project-level requirements compliance.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.core.state_manager import StateManager


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
    """
    Project Review agent - Project-level requirements reviewer.
    Reviews Worker Squad work against PRD and Architecture.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Project Review agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
        """
        self.agent_id = agent_id
        self.executor = executor
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
        """
        Review project-level requirements compliance.
        
        Args:
            prd_data: PRD document
            architecture_data: Architecture document
            blueprint_data: Blueprint document
            worker_squad_output: Worker Squad execution output
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Review output chunks
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
    
    async def _save_response(self, content: str):
        """Save agent response to state."""
        channel = f"squad-{self.agent_id}-project_review"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
