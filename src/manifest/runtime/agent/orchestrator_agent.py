"""
Orchestrator Agent - Mission coordination and task delegation.
"""
import json
from pathlib import Path
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
    
    async def start_ideation(
        self,
        user_input: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        ideation_history: List[Dict[str, str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Start ideation mode for PRD creation.
        
        Args:
            user_input: Current user input
            context: Tiered context
            model_config: Model configuration
            ideation_history: Previous ideation conversation history
            
        Yields:
            Ideation output chunks
        """
        from manifest.runtime.agent.orchestrator_prompt import get_ideation_prompt
        
        # Generate ideation prompt
        prompt = get_ideation_prompt(user_input, context, ideation_history)
        
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
    
    async def create_sprint_plan(
        self,
        prd_data: Dict[str, Any],
        architecture_data: Dict[str, Any],
        blueprint_data: Dict[str, Any],
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Create Sprint plan based on PRD, Architecture, and Blueprint.
        
        Args:
            prd_data: PRD document data
            architecture_data: Architecture data
            blueprint_data: Blueprint data
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Sprint planning output chunks
        """
        from manifest.runtime.agent.orchestrator_prompt import get_orchestrator_prompt
        
        # Load task granularity rules
        granularity_rules = ""
        granularity_file = Path(".claude/rules/task-granularity.md")
        if granularity_file.exists():
            granularity_rules = granularity_file.read_text(encoding="utf-8")
        
        # Create sprint planning prompt
        mission_description = f"""
Create a Sprint plan based on:
- PRD: {prd_data.get('title', 'N/A')}
- Architecture: {json.dumps(architecture_data, indent=2) if architecture_data else 'N/A'}
- Blueprint: {json.dumps(blueprint_data, indent=2) if blueprint_data else 'N/A'}

Task Granularity Rules:
{granularity_rules}

Requirements:
1. Break down work into tasks following granularity rules
2. Group tasks into Sprint(s)
3. Ensure tasks in a Sprint can be executed in parallel (no file overlap, no dependencies)
4. Present Sprint plan with task list and parallel execution groups
"""
        
        prompt = get_orchestrator_prompt(
            mission_description=mission_description,
            context=context,
            available_agents=context.get("available_agents", ["planner", "coder", "test", "review", "debug", "approver"]),
            mode="sprint_planning"
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