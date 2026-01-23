"""
Prompt Hooks - Intercept and modify agent prompts.
Allows injection of Visual Reality and other context modifications.
"""
from typing import Dict, Any, Optional, List, Callable, Awaitable
from abc import ABC, abstractmethod


class PromptHook(ABC):
    """
    Base class for prompt hooks.
    Hooks can intercept and modify prompts before they are sent to LLMs.
    """
    
    @abstractmethod
    async def intercept_prompt(
        self,
        agent_id: str,
        agent_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Intercept and modify a prompt before execution.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent (orchestrator, planner, coder, etc.)
            prompt: Original prompt
            context: Agent context
            message_history: Previous message history
            
        Returns:
            Modified prompt
        """
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """
        Get hook priority (lower = executed first).
        
        Returns:
            Priority value (0-100, lower is higher priority)
        """
        pass


class VisualRealityHook(PromptHook):
    """
    Visual Reality Hook - Injects current project state into prompts.
    
    Visual Reality includes:
    - Current Blueprint state
    - Architecture status
    - Implementation progress
    - Drift information
    """
    
    def __init__(self, state_manager, blueprint_synchronizer=None):
        """
        Initialize Visual Reality Hook.
        
        Args:
            state_manager: StateManager instance
            blueprint_synchronizer: BlueprintSynchronizer instance (optional)
        """
        self.state_manager = state_manager
        self.blueprint_synchronizer = blueprint_synchronizer
    
    async def intercept_prompt(
        self,
        agent_id: str,
        agent_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Inject Visual Reality into prompt.
        """
        visual_reality = await self._generate_visual_reality(agent_type, context)
        
        if visual_reality:
            # Inject Visual Reality section before the main prompt
            visual_section = f"""
## VISUAL REALITY (Current Project State)

{visual_reality}

---
"""
            # Insert after system prompt but before task description
            if "## TASK" in prompt or "## MISSION" in prompt:
                # Insert before TASK/MISSION section
                prompt = prompt.replace("## TASK", f"{visual_section}## TASK")
                prompt = prompt.replace("## MISSION", f"{visual_section}## MISSION")
            else:
                # Append at the end if no clear insertion point
                prompt = f"{prompt}\n\n{visual_section}"
        
        return prompt
    
    async def _generate_visual_reality(
        self,
        agent_type: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate Visual Reality content based on agent type and context.
        
        Args:
            agent_type: Type of agent
            context: Agent context
            
        Returns:
            Visual Reality string
        """
        visual_reality_parts = []
        
        # Load architecture and blueprint data
        from pathlib import Path
        manifest_dir = Path(".manifest")
        architecture_file = manifest_dir / "architecture.json"
        blueprint_file = manifest_dir / "blueprint.json"
        blueprint_code_file = manifest_dir / "blueprint_code.json"
        
        # Architecture status
        if architecture_file.exists():
            import json
            try:
                with open(architecture_file, "r") as f:
                    architecture = json.load(f)
                
                features = architecture.get("features", [])
                if features:
                    visual_reality_parts.append("### Architecture Status")
                    for feature in features[:5]:  # Limit to first 5
                        name = feature.get("name", "Unknown")
                        status = feature.get("status", "unknown")
                        completion = feature.get("completion_percentage", 0)
                        visual_reality_parts.append(f"- **{name}**: {status} ({completion}% complete)")
            except Exception:
                pass
        
        # Blueprint comparison (if synchronizer available)
        if self.blueprint_synchronizer:
            try:
                status = self.blueprint_synchronizer.calculate_implementation_status()
                if status:
                    visual_reality_parts.append("\n### Implementation Status")
                    implemented = status.get("implemented", 0)
                    ghost = status.get("ghost", 0)
                    drift = status.get("drift", 0)
                    visual_reality_parts.append(f"- Implemented: {implemented} components")
                    visual_reality_parts.append(f"- Ghost (unimplemented): {ghost} components")
                    visual_reality_parts.append(f"- Drift (inconsistent): {drift} components")
            except Exception:
                pass
        
        # Task status (if task_id in context)
        if context:
            task_id = context.get("task_id")
            if task_id:
                tasks = self.state_manager.get_task_checklist()
                task = next((t for t in tasks if t.get("id") == task_id), None)
                if task:
                    visual_reality_parts.append("\n### Current Task Status")
                    visual_reality_parts.append(f"- Task: {task.get('name', 'Unknown')}")
                    visual_reality_parts.append(f"- Status: {task.get('status', 'unknown')}")
                    visual_reality_parts.append(f"- Stage: {task.get('stage', 'unknown')}")
        
        return "\n".join(visual_reality_parts) if visual_reality_parts else ""
    
    def get_priority(self) -> int:
        """Visual Reality should be injected early (high priority)."""
        return 10


class HookManager:
    """
    Manages prompt hooks and executes them in priority order.
    """
    
    def __init__(self):
        self.hooks: List[PromptHook] = []
    
    def register_hook(self, hook: PromptHook):
        """
        Register a prompt hook.
        
        Args:
            hook: PromptHook instance
        """
        self.hooks.append(hook)
        # Sort by priority (lower = higher priority)
        self.hooks.sort(key=lambda h: h.get_priority())
    
    def unregister_hook(self, hook: PromptHook):
        """
        Unregister a prompt hook.
        
        Args:
            hook: PromptHook instance
        """
        if hook in self.hooks:
            self.hooks.remove(hook)
    
    async def apply_hooks(
        self,
        agent_id: str,
        agent_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Apply all registered hooks to a prompt.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent
            prompt: Original prompt
            context: Agent context
            message_history: Previous message history
            
        Returns:
            Modified prompt after all hooks
        """
        modified_prompt = prompt
        
        for hook in self.hooks:
            try:
                modified_prompt = await hook.intercept_prompt(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    prompt=modified_prompt,
                    context=context,
                    message_history=message_history
                )
            except Exception as e:
                # Log error but continue with other hooks
                print(f"Error in hook {hook.__class__.__name__}: {e}")
                continue
        
        return modified_prompt
