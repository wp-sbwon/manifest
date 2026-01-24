"""
Orchestrator agent for mission coordination and task delegation.

This module provides the OrchestratorAgent class which coordinates high-level
missions by breaking them down into tasks. The orchestrator operates at Tier
0-1 context level and delegates actual implementation to worker agents.

The orchestrator can also handle ideation mode for PRD creation and sprint
planning based on PRD, architecture, and blueprint data.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.agent.orchestrator_prompt import get_orchestrator_prompt
from manifest.core.state_manager import StateManager


class OrchestratorAgent:
    """Orchestrator agent for mission-level coordination.
    
    The orchestrator is the top-level agent that receives mission descriptions
    and breaks them down into tasks. It works with Tier 0-1 context (policies
    and architecture) and creates a plan for worker agents to execute.
    
    The orchestrator can also handle ideation (PRD creation) and sprint planning
    based on project documentation.
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting orchestrator output.
        message_history: List of conversation messages for context.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """Initialize the orchestrator agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving coordination output.
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
        """Coordinate a mission by breaking it down into tasks.
        
        Analyzes the mission description and creates a plan that breaks the
        work into manageable tasks. The plan is then used to create tasks that
        worker agents can execute.
        
        Args:
            mission_description: High-level description of what needs to be
                accomplished. The orchestrator will break this into tasks.
            context: Tiered context dictionary (Tier 0-1 for orchestrator).
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains the mission breakdown and task plan.
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
    
    async def _save_response(self, content: str) -> None:
        """Save orchestrator response to state and chat history.
        
        Writes the orchestrator's output to the appropriate channel so it
        can be displayed in the UI and used for task creation.
        
        Args:
            content: The complete orchestrator output content.
        """
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
        """Start ideation mode for collaborative PRD creation.
        
        In ideation mode, the orchestrator works with the user to create
        a Product Requirements Document (PRD) through conversation. This
        is an interactive process where the orchestrator asks clarifying
        questions and refines requirements.
        
        Args:
            user_input: Current user input in the ideation conversation.
            context: Tiered context for the ideation session.
            model_config: Dictionary with provider, model, and api_key.
            ideation_history: Previous conversation messages in this
                ideation session. Used to maintain context.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains the orchestrator's response, questions, or
            PRD suggestions.
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
        """Create a sprint plan based on PRD, architecture, and blueprint.
        
        Analyzes the PRD, architecture, and blueprint to break down work
        into tasks and organize them into sprints. Tasks are grouped to
        allow parallel execution (no file overlap, no dependencies).
        
        The plan follows task granularity rules and ensures tasks in a
        sprint can be executed simultaneously.
        
        Args:
            prd_data: Product Requirements Document data.
            architecture_data: Architecture document data.
            blueprint_data: Blueprint document data.
            context: Tiered context for planning.
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains the sprint plan with task list and parallel
            execution groups.
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