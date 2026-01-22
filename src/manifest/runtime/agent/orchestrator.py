"""
Orchestrator - Agent orchestration system.
"""
from typing import Dict, Any, Optional, List
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.orchestrator_prompt import get_orchestrator_prompt, ORCHESTRATOR_SYSTEM_PROMPT


class Orchestrator:
    """
    Orchestrator for managing agent missions.
    """
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize orchestrator.
        
        Args:
            state_manager: State manager for persistence
        """
        self.state_manager = state_manager
        self.active_missions: Dict[str, Dict[str, Any]] = {}
        self.system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
    
    async def start_mission(self, task_id: str, mission_description: str) -> bool:
        """
        Start a new mission.
        
        Args:
            task_id: Task identifier
            mission_description: Description of the mission
            
        Returns:
            True if mission started successfully
        """
        # Get context for orchestrator (Tier 0, Tier 1)
        state = self.state_manager.get_state()
        
        context = {
            "tier_0": self._get_tier_0_context(),
            "tier_1": self._get_tier_1_context(state)
        }
        
        # Generate prompt using orchestrator prompt
        prompt = get_orchestrator_prompt(
            mission_description=mission_description,
            context=context,
            available_agents=["planner", "coder", "test", "review"]
        )
        
        self.active_missions[task_id] = {
            "description": mission_description,
            "status": "active",
            "prompt": prompt,
            "context": context
        }
        
        return True
    
    def _get_tier_0_context(self) -> str:
        """Get Tier 0 context (Policy & Principles)."""
        # Load from .claude/rules/manifest-policy.md
        try:
            from pathlib import Path
            policy_path = Path(".claude/rules/manifest-policy.md")
            if policy_path.exists():
                return policy_path.read_text(encoding="utf-8")
        except Exception:
            pass
        return "Blueprint-First Development: All code must align with blueprint.json"
    
    def _get_tier_1_context(self, state: Dict[str, Any]) -> str:
        """Get Tier 1 context (Architecture & Blueprint)."""
        # Get architecture and blueprint from state
        architecture = state.get("architecture", {})
        blueprint = state.get("blueprint", {})
        
        context_parts = []
        if architecture:
            context_parts.append(f"Architecture: {architecture}")
        if blueprint:
            context_parts.append(f"Blueprint: {blueprint}")
        
        return "\n".join(context_parts) if context_parts else "No architecture/blueprint available"
    
    async def stop_mission(self, task_id: str) -> bool:
        """Stop a mission."""
        if task_id in self.active_missions:
            del self.active_missions[task_id]
            return True
        return False
    
    def get_mission_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get mission status."""
        return self.active_missions.get(task_id)
