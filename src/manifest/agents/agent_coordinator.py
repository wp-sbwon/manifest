"""
Agent Coordinator - Coordinates agents with task boundaries.
Manages orchestrator and worker agent lifecycle with proper scoping.
Supports both direct execution and Docker container execution.
"""
import asyncio
from typing import Dict, Any, Optional, List
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.agents.container_manager import ContainerManager
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


class AgentCoordinator:
    """Coordinates agents through agent bridge."""
    
    def __init__(
        self,
        agent_bridge: AgentBridge,
        context_provider: ContextProvider,
        task_scoper: TaskScoper,
        config_manager: ConfigManager,
        state_manager: StateManager
    ):
        self.agent_bridge = agent_bridge
        self.context_provider = context_provider
        self.task_scoper = task_scoper
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.active_agents: Dict[str, Dict[str, Any]] = {}  # task_id -> agent info
        
        # Access to agent components
        self.terminal_router = agent_bridge.terminal_router
        self.orchestrator = agent_bridge.orchestrator
        self.agent_manager = agent_bridge.agent_manager
        
        # Container manager for Docker-based agent execution
        self.container_manager = ContainerManager()
        self.use_containers = self.container_manager.is_docker_available()
        
        # Container communication (if using containers)
        if self.use_containers:
            from manifest.agents.container_communication import ContainerStateSync
            self.state_sync = ContainerStateSync(state_manager, self.container_manager.message_bus)
        else:
            self.state_sync = None
    
    async def start_orchestrator(self, mission_description: str) -> bool:
        """Start orchestrator via agent bridge."""
        # Get orchestrator context (Tier 0-1)
        context = self.context_provider.get_orchestrator_context()
        
        # Add mission description to context
        context["mission_description"] = mission_description
        
        # Get model config for orchestrator
        model_config = self.config_manager.get_agent_model_config("orchestrator")
        
        # Start via agent bridge
        success = await self.agent_bridge.start_agent_mission(
            task_id="orchestrator",
            agent_type="orchestrator",
            context=context,
            model_config=model_config
        )
        
        if success:
            self.active_agents["orchestrator"] = {
                "agent_type": "orchestrator",
                "status": "active",
                "channel": "squad-orchestrator-orchestrator"
            }
            # Update state
            self.state_manager.set_last_action(f"Started orchestrator: {mission_description}")
            await self.state_manager.save_state()
        
        return success
    
    async def start_worker_agent(
        self,
        task_id: str,
        agent_type: str,
        use_container: Optional[bool] = None
    ) -> bool:
        """
        Start worker agent with task scope.
        
        Args:
            task_id: Task identifier
            agent_type: Type of agent (orchestrator, planner, coder, test, review)
            use_container: Whether to use Docker container (None = auto-detect)
        """
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
        
        # Determine execution mode
        should_use_container = use_container if use_container is not None else self.use_containers
        
        if should_use_container and self.container_manager.is_docker_available():
            # Start agent in Docker container
            container_id = await self.container_manager.start_agent_container(
                task_id=task_id,
                agent_type=agent_type,
                environment={
                    "TASK_ID": task_id,
                    "AGENT_TYPE": agent_type,
                    **{f"CONTEXT_{k.upper()}": str(v) for k, v in context.items()}
                }
            )
            
            if container_id:
                channel = f"squad-{task_id}-{agent_type}"
                self.active_agents[task_id] = {
                    "agent_type": agent_type,
                    "status": "active",
                    "channel": channel,
                    "container_id": container_id,
                    "execution_mode": "container"
                }
                
                # Update task with agent info
                task["agent"] = {
                    "type": agent_type,
                    "status": "active",
                    "channel": channel,
                    "container_id": container_id
                }
                
                # Update task scope in state
                task["scope"] = {
                    "components": task_scope.get("components", []),
                    "files": task_scope.get("allowed_files", []),
                    "allowed_modifications": task_scope.get("allowed_modifications", [])
                }
                
                self.state_manager.set_task_checklist(tasks)
                self.state_manager.set_last_action(f"Started {agent_type} agent in container for task {task_id}")
                await self.state_manager.save_state()
                return True
            else:
                # Fall back to direct execution if container fails
                print(f"Failed to start container, falling back to direct execution")
        
        # Start via agent bridge (direct execution)
        success = await self.agent_bridge.start_agent_mission(
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
                "channel": channel,
                "execution_mode": "direct"
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
        
        agent_info = self.active_agents[task_id]
        execution_mode = agent_info.get("execution_mode", "direct")
        
        success = False
        
        if execution_mode == "container":
            # Stop container
            success = await self.container_manager.stop_agent_container(task_id)
        else:
            # Stop via agent bridge
            success = await self.agent_bridge.stop_agent(task_id)
        
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
        
        agent_info = self.active_agents[task_id]
        execution_mode = agent_info.get("execution_mode", "direct")
        
        if execution_mode == "container":
            # Get container status
            container_status = await self.container_manager.get_container_status(task_id)
            if container_status:
                return {
                    "status": container_status.get("status", "unknown"),
                    "data": {
                        "execution_mode": "container",
                        "container_id": container_status.get("container_id"),
                        "cpu_usage": container_status.get("cpu_usage"),
                        "memory_usage": container_status.get("memory_usage"),
                        "memory_limit": container_status.get("memory_limit"),
                        **container_status.get("metadata", {})
                    }
                }
            else:
                return {"status": "not_active", "data": {}}
        else:
            # Get status via agent bridge
            status = await self.agent_bridge.get_agent_status(task_id)
            if status:
                status["data"]["execution_mode"] = "direct"
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
        
        # Send to agent bridge for planner review
        # This would integrate with agent bridge to send to planner
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
        
        # TODO: Integrate with agent bridge to actually send to planner
        # await self.agent_bridge.send_to_planner(planner_request)
        
        return True
    
    async def start_sprint(self, sprint_id: str, max_parallel: int = 10) -> Dict[str, Any]:
        """
        Start a Sprint by executing all tasks in parallel.
        
        Args:
            sprint_id: Sprint ID
            max_parallel: Maximum number of tasks to run in parallel
            
        Returns:
            Dict with execution results:
            {
                "success": bool,
                "started_tasks": List[str],
                "failed_tasks": List[str],
                "parallel_groups": List[List[str]]
            }
        """
        # Get Sprint tasks
        tasks = self.state_manager.get_task_checklist()
        sprint_tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
        
        if not sprint_tasks:
            return {
                "success": False,
                "error": f"No tasks found for sprint {sprint_id}",
                "started_tasks": [],
                "failed_tasks": [],
                "parallel_groups": []
            }
        
        # Validate parallel execution
        task_ids = [t.get("id") for t in sprint_tasks]
        validation = self.task_scoper.validate_parallel_execution(task_ids)
        
        if not validation["can_parallelize"]:
            # Log conflicts but continue (user/Orchestrator should have validated)
            print(f"Warning: Parallel execution conflicts detected: {validation['conflicts']}")
        
        # Group tasks for parallel execution
        parallel_groups = validation.get("parallel_groups", [task_ids])
        
        # Start tasks in parallel (respecting max_parallel limit)
        started_tasks = []
        failed_tasks = []
        
        for group in parallel_groups:
            # Limit parallel execution
            limited_group = group[:max_parallel]
            
            # Start all tasks in this group in parallel
            results = await asyncio.gather(
                *[self._start_task_worker_squad(task_id) for task_id in limited_group],
                return_exceptions=True
            )
            
            for task_id, result in zip(limited_group, results):
                if isinstance(result, Exception):
                    failed_tasks.append(task_id)
                    print(f"Failed to start task {task_id}: {result}")
                elif result:
                    started_tasks.append(task_id)
                else:
                    failed_tasks.append(task_id)
        
        return {
            "success": len(failed_tasks) == 0,
            "started_tasks": started_tasks,
            "failed_tasks": failed_tasks,
            "parallel_groups": parallel_groups
        }
    
    async def _start_task_worker_squad(self, task_id: str) -> bool:
        """Start Worker Squad for a task (internal helper)."""
        # This will be called by execute_worker_squad
        # For now, just start the first agent (planner)
        return await self.start_worker_agent(task_id, "planner")
    
    async def execute_worker_squad(self, task_id: str) -> Dict[str, Any]:
        """
        Execute Worker Squad workflow for a task.
        
        Worker Squad flow:
        1. Planner: Create plan
        2. Coder: Implement code
        3. Test: Write and run tests
        4. Debug: Fix bugs if tests fail (iterative)
        5. Self Review: Verify plan compliance
        6. Approver: Final approval
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict with execution results:
            {
                "success": bool,
                "stages": {
                    "planner": {...},
                    "coder": {...},
                    "test": {...},
                    "debug": {...},
                    "self_review": {...},
                    "approver": {...}
                }
            }
        """
        stages = {}
        
        # 1. Planner
        planner_success = await self._execute_planner_stage(task_id)
        stages["planner"] = {
            "status": "completed" if planner_success else "failed",
            "output": ""
        }
        if not planner_success:
            return {"success": False, "stages": stages}
        
        # 2. Coder
        coder_success = await self._execute_coder_stage(task_id)
        stages["coder"] = {
            "status": "completed" if coder_success else "failed",
            "output": ""
        }
        if not coder_success:
            return {"success": False, "stages": stages}
        
        # 3. Test
        test_result = await self._execute_test_stage(task_id)
        stages["test"] = test_result
        
        # 4. Debug (iterative if tests fail)
        debug_iterations = 0
        max_debug_iterations = 5
        while test_result.get("status") == "failed" and debug_iterations < max_debug_iterations:
            debug_result = await self._execute_debug_stage(task_id, test_result)
            stages["debug"] = debug_result
            debug_iterations += 1
            
            if debug_result.get("status") == "completed":
                # Re-run tests after debug
                test_result = await self._execute_test_stage(task_id)
                stages["test"] = test_result
            else:
                break
        
        if test_result.get("status") == "failed":
            return {"success": False, "stages": stages, "error": "Tests failed after max debug iterations"}
        
        # 5. Self Review
        self_review_result = await self._execute_self_review_stage(task_id)
        stages["self_review"] = self_review_result
        
        # 6. Approver
        approver_result = await self._execute_approver_stage(task_id, self_review_result)
        stages["approver"] = approver_result
        
        # If approver rejects, go back to coder
        max_approver_iterations = 3
        approver_iterations = 0
        while approver_result.get("decision") == "rejected" and approver_iterations < max_approver_iterations:
            # Go back to coder
            coder_success = await self._execute_coder_stage(task_id, approver_result.get("feedback", ""))
            stages["coder"] = {
                "status": "completed" if coder_success else "failed",
                "output": "",
                "iteration": approver_iterations + 1
            }
            
            if not coder_success:
                return {"success": False, "stages": stages, "error": "Coder failed after approver rejection"}
            
            # Re-run self review and approver
            self_review_result = await self._execute_self_review_stage(task_id)
            stages["self_review"] = self_review_result
            
            approver_result = await self._execute_approver_stage(task_id, self_review_result)
            stages["approver"] = approver_result
            approver_iterations += 1
        
        if approver_result.get("decision") != "approved":
            return {"success": False, "stages": stages, "error": "Approver did not approve after max iterations"}
        
        return {
            "success": True,
            "stages": stages
        }
    
    async def _execute_planner_stage(self, task_id: str) -> bool:
        """Execute Planner stage."""
        return await self.start_worker_agent(task_id, "planner")
    
    async def _execute_coder_stage(self, task_id: str, feedback: str = "") -> bool:
        """Execute Coder stage."""
        # If feedback provided, add it to context
        if feedback:
            # Update task with feedback
            tasks = self.state_manager.get_task_checklist()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task:
                if "worker_squad" not in task:
                    task["worker_squad"] = {}
                task["worker_squad"]["approver_feedback"] = feedback
                self.state_manager.set_task_checklist(tasks)
        
        return await self.start_worker_agent(task_id, "coder")
    
    async def _execute_test_stage(self, task_id: str) -> Dict[str, Any]:
        """Execute Test stage."""
        success = await self.start_worker_agent(task_id, "test")
        return {
            "status": "completed" if success else "failed",
            "test_results": {}
        }
    
    async def _execute_debug_stage(self, task_id: str, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Debug stage."""
        success = await self.start_worker_agent(task_id, "debug")
        return {
            "status": "completed" if success else "failed",
            "issues_fixed": []
        }
    
    async def _execute_self_review_stage(self, task_id: str) -> Dict[str, Any]:
        """Execute Self Review stage (Coder self-review)."""
        # Self review is done by Coder agent
        # This is a placeholder - actual implementation would call coder's self_review method
        return {
            "status": "completed",
            "plan_compliance": True,
            "findings": []
        }
    
    async def _execute_approver_stage(self, task_id: str, self_review_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Approver stage."""
        success = await self.start_worker_agent(task_id, "approver")
        return {
            "status": "completed" if success else "failed",
            "decision": "approved" if success else "pending",
            "feedback": ""
        }
    
    async def review_project_requirements(self, task_id: str) -> Dict[str, Any]:
        """
        Review project-level requirements compliance.
        
        Args:
            task_id: Task ID that completed Worker Squad
            
        Returns:
            Dict with review results:
            {
                "requirements_met": bool,
                "findings": List[str],
                "recommendations": List[str]
            }
        """
        # Start Project Review Agent
        success = await self.start_worker_agent(task_id, "project_review")
        
        if success:
            # Get review results (would be from agent output)
            return {
                "requirements_met": True,
                "findings": [],
                "recommendations": []
            }
        
        return {
            "requirements_met": False,
            "findings": ["Project review agent failed to start"],
            "recommendations": []
        }