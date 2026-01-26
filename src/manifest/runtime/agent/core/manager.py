"""
Agent lifecycle management.

This module provides the AgentManager class which creates, manages, and
controls the lifecycle of different agent types. It handles agent creation,
prompt generation, starting/stopping agents, and maintains a registry of
active agents.

The manager creates appropriate agent instances based on agent type and
configures them with the correct prompts and context.
"""
from typing import Dict, Any, Optional, List
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.prompts.coder_prompt import get_coder_prompt, CODER_IDENTITY
from manifest.runtime.agent.prompts.planner_prompt import get_planner_prompt, PLANNER_IDENTITY
from manifest.runtime.agent.prompts.orchestrator_prompt import get_orchestrator_prompt, ORCHESTRATOR_IDENTITY


class AgentManager:
    """Manages agent lifecycle and creation.

    Handles creating agent instances of different types, generating appropriate
    prompts, and managing their lifecycle. Maintains a registry of active
    agents and provides methods to start, stop, and query agents.

    Attributes:
        state_manager: Manages state persistence for agents.
        agents: Dictionary mapping agent IDs to agent instances.
        agent_prompts: Dictionary mapping agent types to their identity prompts.
        executor: AgentExecutor instance for LLM API calls.
    """

    def __init__(
        self,
        state_manager: StateManager,
        executor: Optional["AgentExecutor"] = None
    ):
        """Initialize the agent manager.

        Sets up the agent registry and loads identity prompts for different
        agent types. If no executor is provided, agents will need to be
        created with an executor later.

        Args:
            state_manager: State manager for persisting agent state.
            executor: Optional AgentExecutor instance. If not provided,
                agents must be created with an executor later.
        """
        self.state_manager = state_manager
        self.agents: Dict[str, Any] = {}  # agent_id -> agent instance
        self.agent_prompts: Dict[str, str] = {
            "orchestrator": ORCHESTRATOR_IDENTITY,
            "planner": PLANNER_IDENTITY,
            "coder": CODER_IDENTITY,
            "test": "Test agent",
            "review": "Review agent",
            "debug": "Debug agent",
            "approver": "Approver agent",
            "project_review": "Project Review agent",
            "e2e_test": "E2E Test agent",
            "integration_test": "Integration Test agent"
        }
        self.executor = executor

    async def create_agent(
        self,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        task_id: Optional[str] = None,
        terminal_router: Optional[Any] = None,
        tool_executor: Optional[Any] = None
    ) -> Any:
        """Create a new agent instance of the specified type.

        Generates the appropriate prompt based on agent type and context,
        then creates the corresponding agent class instance. The agent
        is registered in the manager's agent dictionary.

        Args:
            agent_type: Type of agent to create. Valid values: "orchestrator",
                "planner", "coder", "test", "debug", "approver", "project_review",
                "e2e_test", "integration_test".
            context: Tiered context dictionary for the agent (Tier 0-3).
            model_config: Dictionary with provider, model, and api_key.
            task_id: Optional task ID. If not provided, generates a unique ID.

        Returns:
            Agent instance (specific type depends on agent_type). The agent
            is ready to use but not yet started.
        """
        agent_id = task_id or f"agent_{len(self.agents)}"

        # Generate agent prompt based on type
        prompt = self._generate_agent_prompt(agent_type, context, task_id)

        # Create actual agent instance based on type
        agent_instance = None
        if agent_type == "orchestrator" and self.executor:
            from manifest.runtime.agent.agents.orchestrator_agent import OrchestratorAgent
            agent_instance = OrchestratorAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "planner" and self.executor:
            from manifest.runtime.agent.agents.planner_agent import PlannerAgent
            agent_instance = PlannerAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "coder" and self.executor:
            from manifest.runtime.agent.agents.coder_agent import CoderAgent
            agent_instance = CoderAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "test" and self.executor:
            from manifest.runtime.agent.agents.test_agent import TestAgent
            agent_instance = TestAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "debug" and self.executor:
            from manifest.runtime.agent.agents.debug_agent import DebugAgent
            agent_instance = DebugAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "approver" and self.executor:
            from manifest.runtime.agent.agents.approver_agent import ApproverAgent
            agent_instance = ApproverAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "project_review" and self.executor:
            from manifest.runtime.agent.agents.project_review_agent import ProjectReviewAgent
            agent_instance = ProjectReviewAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "e2e_test" and self.executor:
            from manifest.runtime.agent.agents.e2e_test_agent import E2ETestAgent
            agent_instance = E2ETestAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)
        elif agent_type == "integration_test" and self.executor:
            from manifest.runtime.agent.agents.integration_test_agent import IntegrationTestAgent
            agent_instance = IntegrationTestAgent(agent_id, self.executor, self.state_manager, terminal_router=terminal_router, tool_executor=tool_executor)

        # Create agent object
        agent = {
            "id": agent_id,
            "type": agent_type,
            "context": context,
            "model_config": model_config,
            "prompt": prompt,
            "status": "created",
            "system_prompt": self.agent_prompts.get(agent_type, ""),
            "instance": agent_instance  # Actual agent instance
        }

        self.agents[agent_id] = agent
        return agent

    def _generate_agent_prompt(
        self,
        agent_type: str,
        context: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> str:
        """Generate the appropriate prompt for an agent type.

        Uses agent-specific prompt generators (get_coder_prompt, get_planner_prompt,
        etc.) to create prompts tailored to each agent's role and context.

        Args:
            agent_type: Type of agent to generate prompt for.
            context: Tiered context dictionary for the agent.
            task_id: Optional task ID for context in the prompt.

        Returns:
            Complete prompt string ready to send to the LLM.
        """
        if agent_type == "coder":
            # Get task description from context
            task_description = context.get("task_description", "Complete the assigned task")
            task_scope = context.get("task_scope", {})

            return get_coder_prompt(
                task_description=task_description,
                context=context,
                task_scope=task_scope,
                available_tools=context.get("available_tools", [])
            )
        elif agent_type == "planner":
            task_description = context.get("task_description", "Plan the assigned task")
            return get_planner_prompt(
                task_description=task_description,
                context=context,
                available_agents=context.get("available_agents", ["coder", "test", "review"])
            )
        elif agent_type == "orchestrator":
            mission_description = context.get("mission_description", "Coordinate the mission")
            return get_orchestrator_prompt(
                mission_description=mission_description,
                context=context,
                available_agents=context.get("available_agents", ["planner", "coder", "test", "review"])
            )
        elif agent_type == "test":
            # Test agent prompt will be generated by TestAgent itself
            # This is just a placeholder - actual prompt is in test_agent.py
            stage = context.get("stage", "test")
            if stage == "tdd_test":
                return "TDD Test mode: Write tests first based on planner's plan."
            else:
                return "Test execution mode: Run tests after implementation."
        else:
            # Default prompt for other agent types
            return f"""
Agent Type: {agent_type}
Task ID: {task_id}

Context:
{context}

Execute the assigned task following best practices.
"""

    async def start_agent(self, agent_id: str) -> bool:
        """Start an agent."""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "active"
            return True
        return False

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent."""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "stopped"
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information."""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """List all agent IDs."""
        return list(self.agents.keys())

    async def shutdown(self):
        """Shutdown all agents."""
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)
