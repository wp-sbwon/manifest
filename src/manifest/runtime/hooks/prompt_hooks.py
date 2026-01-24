"""
Prompt hooks for intercepting and modifying agent prompts.

This module provides a hook system that allows intercepting prompts before
they're sent to LLMs. Hooks can inject additional context, modify prompts,
or add constraints. This enables features like Visual Reality (injecting
current project state) and other dynamic prompt modifications.

Hooks are executed in priority order (lower priority number = executed first),
allowing multiple hooks to modify prompts in sequence.
"""
from typing import Dict, Any, Optional, List, Callable, Awaitable
from abc import ABC, abstractmethod
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class PromptHook(ABC):
    """Base class for prompt hooks that intercept and modify prompts.
    
    Hooks allow modifying prompts before they're sent to LLMs. This enables
    dynamic injection of context, constraints, or other modifications based
    on current project state or agent type.
    
    Hooks are executed in priority order, with lower priority numbers
    executing first. This allows multiple hooks to modify prompts in sequence.
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
        """Intercept and modify a prompt before it's sent to the LLM.
        
        This method is called for every agent execution, allowing the hook
        to inspect and modify the prompt. The modified prompt is then used
        for the LLM call.
        
        Args:
            agent_id: Unique identifier of the agent making the call.
            agent_type: Type of agent (e.g., "orchestrator", "coder", "planner").
            prompt: The original prompt that would be sent to the LLM.
            context: Optional tiered context dictionary for the agent.
            message_history: Optional previous conversation messages.
        
        Returns:
            The modified prompt string. Can be the same as the original
            if no modifications are needed.
        """
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get the execution priority of this hook.
        
        Hooks with lower priority numbers are executed first. This allows
        multiple hooks to modify prompts in a specific order.
        
        Returns:
            Priority value between 0-100. Lower numbers mean higher priority
            (executed first).
        """
        pass


class VisualRealityHook(PromptHook):
    """Visual Reality hook that injects current project state into prompts.
    
    Visual Reality provides agents with awareness of the current project
    state, including blueprint status, architecture state, implementation
    progress, and any drift issues. This helps agents make decisions based
    on what actually exists, not just what's planned.
    
    Attributes:
        state_manager: StateManager for accessing current project state.
        blueprint_synchronizer: Optional BlueprintSynchronizer for drift
            information.
    """
    
    def __init__(self, state_manager, blueprint_synchronizer=None):
        """Initialize the Visual Reality hook.
        
        Args:
            state_manager: StateManager instance for accessing project state.
            blueprint_synchronizer: Optional BlueprintSynchronizer for drift
                detection and conflict information.
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
        """Inject Visual Reality section into the prompt.
        
        Generates a Visual Reality section containing current project state
        and inserts it into the prompt before the task/mission description.
        This gives agents awareness of the actual codebase state.
        
        Args:
            agent_id: ID of the agent making the call.
            agent_type: Type of agent.
            prompt: Original prompt to modify.
            context: Optional tiered context.
            message_history: Optional conversation history.
        
        Returns:
            Modified prompt with Visual Reality section inserted.
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
        
        # 1. Architecture status
        if architecture_file.exists():
            import json
            try:
                with open(architecture_file, "r") as f:
                    architecture = json.load(f)
                
                features = architecture.get("features", [])
                if features:
                    visual_reality_parts.append("### Architecture Status")
                    for feature in features:
                        name = feature.get("name", "Unknown")
                        status = feature.get("status", "unknown")
                        completion = feature.get("completion_percentage", 0)
                        visual_reality_parts.append(f"- **{name}**: {status} ({completion}% complete)")
            except Exception:
                pass
        
        # 2. Implementation Status & Drift
        if self.blueprint_synchronizer and blueprint_file.exists():
            try:
                from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
                top_down = BlueprintLoader.load_blueprint(manifest_dir)
                bottom_up = BlueprintLoader.load_code_blueprint(manifest_dir)
                
                status_info = self.blueprint_synchronizer.calculate_implementation_status(top_down, bottom_up)
                
                if status_info:
                    visual_reality_parts.append("\n### Implementation Status")
                    component_statuses = status_info.get("component_statuses", {})
                    
                    counts = {"implemented": 0, "ghost": 0, "drift": 0, "extra": 0}
                    for s in component_statuses.values():
                        if s in counts:
                            counts[s] += 1
                    
                    visual_reality_parts.append(f"- Implemented: {counts['implemented']} components")
                    visual_reality_parts.append(f"- Ghost (unimplemented): {counts['ghost']} components")
                    visual_reality_parts.append(f"- Drift (inconsistent): {counts['drift']} components")
                    
                    # Add specific drift details
                    drifts = status_info.get("component_drifts", {})
                    if drifts:
                        visual_reality_parts.append("\n#### Active Drift Details:")
                        for comp_id, messages in drifts.items():
                            visual_reality_parts.append(f"- **{comp_id}**:")
                            for msg in messages:
                                visual_reality_parts.append(f"  - {msg}")
            except Exception as e:
                logger.error(f"Error generating implementation status for Visual Reality: {e}")
        
        # 3. Task status (if task_id in context)
        if context:
            task_id = context.get("task_id")
            if task_id:
                tasks = self.state_manager.get_task_checklist()
                task = next((t for t in tasks if t.get("id") == task_id), None)
                if task:
                    visual_reality_parts.append("\n### Current Task Context")
                    visual_reality_parts.append(f"- **Task ID**: {task_id}")
                    visual_reality_parts.append(f"- **Name**: {task.get('name', 'Unknown')}")
                    visual_reality_parts.append(f"- **Status**: {task.get('status', 'unknown')}")
                    visual_reality_parts.append(f"- **Stage**: {task.get('stage', 'unknown')}")
                    
                    # Add allowed modifications if available
                    scope = task.get("scope", {})
                    allowed_files = scope.get("allowed_files", [])
                    if allowed_files:
                        visual_reality_parts.append("- **Allowed Files**:")
                        for f in allowed_files:
                            visual_reality_parts.append(f"  - {f}")
        
        return "\n".join(visual_reality_parts) if visual_reality_parts else ""
    
    def get_priority(self) -> int:
        """Get the execution priority for this hook.
        
        Visual Reality should be injected early so other hooks can see
        the current state. Lower numbers mean higher priority.
        
        Returns:
            Priority value of 10 (high priority, executed early).
        """
        return 10


class PolicyInjectionHook(PromptHook):
    """Hook that ensures Tier 0 policy is injected into every prompt.
    
    Tier 0 policy represents the fundamental principles and constraints
    that all agents must follow. This hook ensures they are always present.
    """
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    async def intercept_prompt(
        self,
        agent_id: str,
        agent_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Inject Tier 0 policy if not already present."""
        if "## Tier 0: Policy" in prompt or "## POLICY" in prompt:
            return prompt
            
        # Load policy from file
        from pathlib import Path
        policy_file = Path(".claude/rules/manifest-policy.md")
        if policy_file.exists():
            try:
                with open(policy_file, "r") as f:
                    policy = f.read()
                
                policy_section = f"""
## TIER 0: GLOBAL POLICY & PRINCIPLES

{policy}

---
"""
                # Inject at the very beginning
                return f"{policy_section}{prompt}"
            except Exception:
                pass
                
        return prompt
    
    def get_priority(self) -> int:
        """Policy should be injected first.
        
        Returns:
            Priority value of 0 (highest priority).
        """
        return 0


class HookManager:
    """Manages prompt hooks and executes them in priority order.
    
    Maintains a registry of prompt hooks and applies them to prompts before
    they're sent to LLMs. Hooks are executed in priority order (lower priority
    number = executed first), allowing multiple hooks to modify prompts sequentially.
    
    Attributes:
        hooks: List of registered PromptHook instances, sorted by priority.
    """
    
    def __init__(self):
        """Initialize the hook manager.
        
        Creates an empty hook registry. Hooks can be registered later using
        register_hook().
        """
        self.hooks: List[PromptHook] = []
    
    def register_hook(self, hook: PromptHook) -> None:
        """Register a prompt hook.
        
        Adds the hook to the registry and re-sorts hooks by priority.
        Hooks with lower priority numbers will be executed first.
        
        Args:
            hook: PromptHook instance to register.
        """
        self.hooks.append(hook)
        # Sort by priority (lower = higher priority, executed first)
        self.hooks.sort(key=lambda h: h.get_priority())
    
    def unregister_hook(self, hook: PromptHook) -> None:
        """Unregister a prompt hook.
        
        Removes the hook from the registry. The hook will no longer be
        applied to prompts.
        
        Args:
            hook: PromptHook instance to unregister.
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
        """Apply all registered hooks to a prompt.
        
        Executes each registered hook in priority order. Each hook
        receives the prompt as modified by previous hooks, allowing
        hooks to build on each other's modifications.
        
        Args:
            agent_id: ID of the agent making the call.
            agent_type: Type of agent (e.g., "orchestrator", "coder").
            prompt: Original prompt before any hook modifications.
            context: Optional tiered context dictionary.
            message_history: Optional previous conversation messages.
        
        Returns:
            Prompt string after all hooks have been applied. If no hooks
            are registered, returns the original prompt unchanged.
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
                logger.error(f"Error in hook {hook.__class__.__name__}: {e}", exc_info=True)
                continue
        
        return modified_prompt
