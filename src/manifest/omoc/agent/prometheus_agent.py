"""
Prometheus Agent - Planner/Orchestrator agent implementation.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.omoc.agent.executor import AgentExecutor
from manifest.omoc.agent.prometheus_prompt import get_prometheus_prompt
from manifest.core.state_manager import StateManager


class PrometheusAgent:
    """
    Prometheus agent - Strategic planning consultant.
    Plans work but does not implement.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Prometheus agent.
        
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
        mission_description: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Create a work plan for the mission.
        
        Args:
            mission_description: Mission description
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Planning output chunks
        """
        # Generate prompt
        prompt = get_prometheus_prompt(
            mission_description=mission_description,
            context=context,
            available_agents=context.get("available_agents", ["sisyphus", "test", "review"])
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="prometheus",
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
        channel = f"squad-{self.agent_id}-prometheus"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
