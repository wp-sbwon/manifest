"""
Agent Coordinator - Coordinates agents through OMOC with task boundaries.
Manages orchestrator and worker agent lifecycle with proper scoping.
"""
from typing import Dict, Any, Optional
from manifest.bridge.omoc_bridge import OMOCBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


class AgentCoordinator:
    """Coordinates agents through OMOC bridge."""
    
    def __init__(
        self,
        omoc_bridge: OMOCBridge,
        context_provider: ContextProvider,
        task_scoper: TaskScoper,
        config_manager: ConfigManager,
        state_manager: StateManager
    ):
        self.omoc_bridge = omoc_bridge
        self.context_provider = context_provider
        self.task_scoper = task_scoper
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.active_agents: Dict[str, Dict[str, Any]] = {}  # task_id -> agent info
    
    async def start_orchestrator(self, mission_description: str) -> bool:
        """Start orchestrator (Prometheus) via OMOC."""
        # Get orchestrator context (Tier 0-1)
        context = self.context_provider.get_orchestrator_context()
        
        # Add mission description to context
        context["mission_description"] = mission_description
        
        # Get model config for orchestrator
        model_config = self.config_manager.get_agent_model_config("prometheus")
        
        # Start via OMOC bridge
        success = await self.omoc_bridge.start_agent_mission(
            task_id="orchestrator",
            agent_type="prometheus",
            context=context,
            model_config=model_config
        )
        
        if success:
            self.active_agents["orchestrator"] = {
                "agent_type": "prometheus",
                "status": "active",
                "channel": "squad-orchestrator-prometheus"
            }
            # Update state
            self.state_manager.set_last_action(f"Started orchestrator: {mission_description}")
            await self.state_manager.save_state()
        
        return success
    
    async def start_worker_agent(
        self,
        task_id: str,
        agent_type: str
    ) -> bool:
        """Start worker agent with task scope."""
        # Validate task exists
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            return False
        
        # Get scoped context (Tier 0, 2, 3)
        context = self.context_provider.get_worker_context(task_id, agent_type)
        
        # Validate scope
        task_scope = context.get("task_scope", {})
        if not task_scope.get("components") and not task_scope.get("allowed_files"):
            # No scope defined - warn but continue
            print(f"Warning: Task {task_id} has no defined scope")
        
        # Get model config for agent type
        model_config = self.config_manager.get_agent_model_config(agent_type)
        
        # Start via OMOC bridge
        success = await self.omoc_bridge.start_agent_mission(
            task_id=task_id,
            agent_type=agent_type,
            context=context,
            model_config=model_config
        )
        
        if success:
            channel = f"squad-{task_id}-{agent_type}"
            self.active_agents[task_id] = {
                "agent_type": agent_type,
                "status": "active",
                "channel": channel
            }
            
            # Update task with agent info
            task["agent"] = {
                "type": agent_type,
                "status": "active",
                "channel": channel
            }
            
            # Update task scope in state
            task["scope"] = {
                "components": task_scope.get("components", []),
                "files": task_scope.get("allowed_files", []),
                "allowed_modifications": task_scope.get("allowed_modifications", [])
            }
            
            self.state_manager.set_task_checklist(tasks)
            self.state_manager.set_last_action(f"Started {agent_type} agent for task {task_id}")
            await self.state_manager.save_state()
        
        return success
    
    async def stop_agent(self, task_id: str) -> bool:
        """Stop agent working on task."""
        if task_id not in self.active_agents:
            return False
        
        success = await self.omoc_bridge.stop_agent(task_id)
        
        if success:
            # Update task status
            tasks = self.state_manager.get_task_checklist()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task and "agent" in task:
                task["agent"]["status"] = "stopped"
                self.state_manager.set_task_checklist(tasks)
                await self.state_manager.save_state()
            
            # Remove from active agents
            del self.active_agents[task_id]
        
        return success
    
    async def get_agent_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of agent working on task."""
        if task_id not in self.active_agents:
            return {"status": "not_active", "data": {}}
        
        status = await self.omoc_bridge.get_agent_status(task_id)
        return status
    
    def get_active_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all active agents."""
        return self.active_agents.copy()
    
    def get_agent_channel(self, task_id: str) -> Optional[str]:
        """Get channel name for agent working on task."""
        agent_info = self.active_agents.get(task_id)
        return agent_info.get("channel") if agent_info else None
    
    async def handle_blueprint_conflict(self, conflict_issue: Dict[str, Any], task_id: str) -> bool:
        """Handle blueprint conflict by resending to worker squad with conflict context."""
        from manifest.audit.blueprint_synchronizer import BlueprintSynchronizer
        
        synchronizer = BlueprintSynchronizer()
        
        # Create resend request
        resend_request = synchronizer.resend_to_worker_squad(task_id, conflict_issue)
        
        # Request planner review
        planner_request = synchronizer.request_planner_review(conflict_issue)
        
        # Send to OMOC for planner review
        # This would integrate with OMOC bridge to send to Prometheus (planner)
        # For now, we'll update the task with conflict information
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["conflict"] = {
                    "issue": conflict_issue,
                    "status": "planner_review",
                    "resend_request": resend_request
                }
                self.state_manager.set_task_checklist(tasks)
                await self.state_manager.save_state()
                break
        
        # TODO: Integrate with OMOC bridge to actually send to planner
        # await self.omoc_bridge.send_to_planner(planner_request)
        
        return True