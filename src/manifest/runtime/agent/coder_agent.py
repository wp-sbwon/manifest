"""
Coder Agent - Code implementation agent.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.agent.coder_prompt import get_coder_prompt
from manifest.core.state_manager import StateManager


class CoderAgent:
    """
    Coder agent - Code implementer.
    Implements code following plans and best practices.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Coder agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
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
        """
        Implement the task.
        
        Args:
            task_description: Task description
            context: Tiered context
            task_scope: Task scope (components, files, allowed modifications)
            model_config: Model configuration
            
        Yields:
            Implementation output chunks
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
        """Generate self-review prompt."""
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
