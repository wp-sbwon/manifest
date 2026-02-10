"""
Orchestrator for high-level mission management.

This module provides the Orchestrator class which manages top-level missions.
The orchestrator receives mission descriptions and breaks them down into
tasks. It operates at Tier 0-1 context level (policies and blueprint),
not at the code level.

The orchestrator is the entry point for new missions and coordinates the
overall workflow.
"""
from typing import Dict, Any, Optional, List
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.prompts.orchestrator_prompt import get_orchestrator_prompt, ORCHESTRATOR_SYSTEM_PROMPT


class Orchestrator:
    """Orchestrates high-level missions and breaks them into tasks.

    The orchestrator is the top-level agent that receives mission descriptions
    and plans how to accomplish them. It works with Tier 0-1 context (policies
    and blueprint) and delegates actual implementation to worker agents.

    Attributes:
        state_manager: Manages state persistence for missions.
        active_missions: Dictionary tracking currently active missions.
        system_prompt: System prompt that defines orchestrator behavior.
    """

    def __init__(self, state_manager: StateManager):
        """Initialize the orchestrator.

        Args:
            state_manager: State manager for persisting mission data.
        """
        self.state_manager = state_manager
        self.active_missions: Dict[str, Dict[str, Any]] = {}
        self.system_prompt = ORCHESTRATOR_SYSTEM_PROMPT

    async def start_mission(self, task_id: str, mission_description: str) -> bool:
        """Start a new mission with the given description.

        Loads Tier 0 (policies) and Tier 1 (blueprint) context, generates
        an orchestrator prompt, and registers the mission as active. The
        orchestrator will then work on breaking down the mission into tasks.

        Args:
            task_id: Unique identifier for this mission/task.
            mission_description: High-level description of what needs to
                be accomplished. The orchestrator will break this down.

        Returns:
            True if mission was registered successfully, False otherwise.
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
        """Load Tier 0 context: Policies and principles.

        Tier 0 contains the "law" - project policies, rules, and constraints
        that all agents must follow. This is loaded from manifest-policy.md.

        Returns:
            String containing policy content, or default policy message if
            file doesn't exist or can't be read.
        """
        # Load from .rules/manifest-policy.md
        try:
            from pathlib import Path
            policy_path = Path(".rules/manifest-policy.md")
            if policy_path.exists():
                return policy_path.read_text(encoding="utf-8")
        except Exception:
            pass
        return "Blueprint-First Development: All code must align with blueprint_design.json"

    def _get_tier_1_context(self, state: Dict[str, Any]) -> str:
        """Load Tier 1 context: Blueprint (design).

        Tier 1 contains high-level blueprint information that guides the
        orchestrator's planning decisions.

        Args:
            state: Current application state dictionary.

        Returns:
            String containing blueprint information, or a message if not available.
        """
        blueprint = state.get("blueprint", {})
        if blueprint:
            return f"Blueprint: {blueprint}"
        return "No blueprint available"

    async def stop_mission(self, task_id: str) -> bool:
        """Stop an active mission.

        Removes the mission from the active missions registry. This doesn't
        stop any worker agents that may have been started for the mission's
        tasks - those must be stopped separately.

        Args:
            task_id: ID of the mission to stop.

        Returns:
            True if mission was found and stopped, False if it wasn't active.
        """
        if task_id in self.active_missions:
            del self.active_missions[task_id]
            return True
        return False

    def get_mission_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a mission.

        Args:
            task_id: ID of the mission to query.

        Returns:
            Dictionary containing mission information (description, status,
            prompt, context) if mission is active, None otherwise.
        """
        return self.active_missions.get(task_id)
