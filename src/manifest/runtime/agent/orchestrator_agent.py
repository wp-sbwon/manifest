"""
Orchestrator Agent - Mission coordination and task delegation.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.agent.orchestrator_prompt import get_orchestrator_prompt
from manifest.core.state_manager import StateManager


class OrchestratorAgent:
    """
    Orchestrator agent - Mission-level coordination.
    Coordinates missions and delegates tasks to appropriate agents.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Orchestrator agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def coordinate(
        self,
        mission_description: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Coordinate a mission by delegating tasks.
        
        Args:
            mission_description: Mission description
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Coordination output chunks
        """
        # Generate prompt
        prompt = get_orchestrator_prompt(
            mission_description=mission_description,
            context=context,
            available_agents=context.get("available_agents", ["planner", "coder", "test", "review"])
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="orchestrator",
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
        channel = f"squad-{self.agent_id}-orchestrator"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
