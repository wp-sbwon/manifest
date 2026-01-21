"""
Sisyphus Agent - Coder/Implementer agent implementation.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.omoc.agent.executor import AgentExecutor
from manifest.omoc.agent.sisyphus_prompt import get_sisyphus_prompt
from manifest.core.state_manager import StateManager


class SisyphusAgent:
    """
    Sisyphus agent - SF Bay Area engineer.
    Implements code following plans and best practices.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Sisyphus agent.
        
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
        prompt = get_sisyphus_prompt(
            task_description=task_description,
            context=context,
            task_scope=task_scope,
            available_tools=context.get("available_tools", [])
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="sisyphus",
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
        channel = f"squad-{self.agent_id}-sisyphus"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
