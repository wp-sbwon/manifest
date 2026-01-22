"""
Planner Agent - Detailed task planning and blueprint creation.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.agent.planner_prompt import get_planner_prompt
from manifest.core.state_manager import StateManager


class PlannerAgent:
    """
    Planner agent - Detailed planning consultant.
    Creates detailed work plans and blueprints but does not implement.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Planner agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def plan(
        self,
        task_description: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Create a detailed work plan for the task.
        
        Args:
            task_description: Task description
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Planning output chunks
        """
        # Generate prompt
        prompt = get_planner_prompt(
            task_description=task_description,
            context=context,
            available_agents=context.get("available_agents", ["coder", "test", "review"])
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="planner",
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
        channel = f"squad-{self.agent_id}-planner"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
