"""
Coder agent for code implementation.

This module provides the CoderAgent class which implements code based on
planner plans and task requirements. The coder agent receives scoped context
(Tier 0, 2-3) and implements code within the allowed boundaries.

The coder can also perform self-review to verify its implementation complies
with the original plan.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.agent.coder_prompt import get_coder_prompt
from manifest.core.state_manager import StateManager


class CoderAgent:
    """Coder agent for implementing code based on plans.
    
    The coder agent receives a task description, planner's plan, and scoped
    context, then implements the code to fulfill the requirements. It works
    within task boundaries to ensure it only modifies allowed files and
    components.
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting agent output.
        message_history: List of conversation messages for context.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """Initialize the coder agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving agent output to channels.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def implement(
        self,
        task_description: str,
        context: Dict[str, Any],
        task_scope: Optional[Dict[str, Any]],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Implement code for a task based on the planner's plan.
        
        Generates a coder-specific prompt with task description, context,
        and scope boundaries, then executes the agent to produce implementation
        code. Output is streamed in real-time and saved to the agent's channel.
        
        Args:
            task_description: Description of what needs to be implemented.
            context: Tiered context dictionary (Tier 0, 2-3 for workers).
            task_scope: Dictionary defining what files/components can be
                modified. Includes allowed_files, allowed_components, etc.
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains the implementation code and explanations.
        """
        # Generate prompt
        prompt = get_coder_prompt(
            task_description=task_description,
            context=context,
            task_scope=task_scope,
            available_tools=context.get("available_tools", [])
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="coder",
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
    
    async def _save_response(self, content: str):
        """Save agent response to state."""
        channel = f"squad-{self.agent_id}-coder"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
    
    async def self_review(
        self,
        planner_plan: str,
        implementation_summary: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Self-review implementation against plan.
        
        Args:
            planner_plan: Planner's plan
            implementation_summary: Summary of implementation
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Self-review output chunks
        """
        # Generate self-review prompt
        prompt = self._generate_self_review_prompt(planner_plan, implementation_summary, context)
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="coder",
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
    
    def _generate_self_review_prompt(
        self,
        planner_plan: str,
        implementation_summary: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate a prompt for self-review mode.
        
        Creates a prompt that asks the coder to compare its implementation
        against the planner's plan and identify any discrepancies.
        
        Args:
            planner_plan: The original plan to compare against.
            implementation_summary: Summary of what was implemented.
            context: Tiered context for additional information.
        
        Returns:
            Complete prompt string for self-review.
        """
        prompt = f"""
## SELF REVIEW MODE

You are reviewing your own implementation against the Planner's plan.

## PLANNER'S PLAN

{planner_plan}

## YOUR IMPLEMENTATION

{implementation_summary}

## CONTEXT

{context.get("tier_2", "No task-specific context")}

## YOUR TASK

1. Compare your implementation with the Planner's plan
2. Identify any differences or deviations
3. Verify all plan requirements are met
4. Check for any missing features or functionality
5. Assess plan compliance

Output your review in this format:
PLAN_COMPLIANCE: COMPLIANT|NON_COMPLIANT
DIFFERENCES:
- [difference 1]
- [difference 2]
MISSING_FEATURES:
- [missing feature 1]
- [missing feature 2]
FINDINGS:
- [finding 1]
- [finding 2]
"""
        return prompt
