"""
Agent Manager - Manages agent lifecycle.
"""
from typing import Dict, Any, Optional, List
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.coder_prompt import get_coder_prompt, CODER_IDENTITY
from manifest.runtime.agent.planner_prompt import get_planner_prompt, PLANNER_IDENTITY
from manifest.runtime.agent.orchestrator_prompt import get_orchestrator_prompt, ORCHESTRATOR_IDENTITY


class AgentManager:
    """
    Agent Manager for creating and managing agents.
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        executor: Optional["AgentExecutor"] = None
    ):
        """
        Initialize agent manager.
        
        Args:
            state_manager: State manager for persistence
            executor: Optional agent executor (creates one if not provided)
        """
        self.state_manager = state_manager
        self.agents: Dict[str, Any] = {}  # agent_id -> agent instance
        self.agent_prompts: Dict[str, str] = {
            "orchestrator": ORCHESTRATOR_IDENTITY,
            "planner": PLANNER_IDENTITY,
            "coder": CODER_IDENTITY,
            "test": "Test agent",
            "review": "Review agent"
        }
        self.executor = executor
    
    async def create_agent(
        self,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Any:
        """
        Create a new agent.
        
        Args:
            agent_type: Type of agent (orchestrator, planner, coder, test, review)
            context: Agent context (tiered context)
            model_config: Model configuration
            task_id: Optional task ID
            
        Returns:
            Agent instance with prompt and configuration
        """
        agent_id = task_id or f"agent_{len(self.agents)}"
        
        # Generate agent prompt based on type
        prompt = self._generate_agent_prompt(agent_type, context, task_id)
        
        # Create actual agent instance based on type
        agent_instance = None
        if agent_type == "orchestrator" and self.executor:
            from manifest.runtime.agent.orchestrator_agent import OrchestratorAgent
            agent_instance = OrchestratorAgent(agent_id, self.executor, self.state_manager)
        elif agent_type == "planner" and self.executor:
            from manifest.runtime.agent.planner_agent import PlannerAgent
            agent_instance = PlannerAgent(agent_id, self.executor, self.state_manager)
        elif agent_type == "coder" and self.executor:
            from manifest.runtime.agent.coder_agent import CoderAgent
            agent_instance = CoderAgent(agent_id, self.executor, self.state_manager)
        
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
        """Generate agent prompt."""
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
