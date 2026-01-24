"""
Planner agent for detailed task planning.

This module provides the PlannerAgent class which creates detailed work plans
for tasks. The planner analyzes requirements, considers architecture and
blueprint constraints, and creates a step-by-step plan that the coder will
follow.

The planner also extracts methodology, algorithm, and design pattern information
from its output and updates the blueprint metadata accordingly.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.runtime.agent.prompts.planner_prompt import get_planner_prompt
from manifest.core.state_manager import StateManager


class PlannerAgent:
    """Planner agent for creating detailed work plans.
    
    The planner agent receives a task description and creates a comprehensive
    plan that breaks down the work into steps. It considers architecture,
    blueprint constraints, and available tools/agents. The plan guides the
    coder's implementation.
    
    The planner also extracts product logic information (algorithms, design
    patterns, complexity) from its output and updates blueprint metadata.
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting plans and output.
        message_history: List of conversation messages for context.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """Initialize the planner agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving plans and output.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def plan(
        self,
        task_description: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Create a detailed work plan for a task.
        
        Analyzes the task description and context to create a step-by-step
        plan. The plan should be detailed enough for the coder to follow
        and implement. Output is streamed in real-time.
        
        Args:
            task_description: Description of what needs to be accomplished.
            context: Tiered context dictionary (Tier 0-1 for planning).
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains the detailed plan with steps, considerations,
            and implementation guidance.
        """
        # Check if this is a conflict review (from context or stage)
        stage = context.get("stage")  # Stage might be passed in context
        is_conflict_review = (
            context.get("conflict_review") is not None or
            stage == "conflict_review"
        )
        
        # Generate prompt (will handle conflict review mode internally)
        prompt = get_planner_prompt(
            task_description=task_description,
            context=context,
            available_agents=context.get("available_agents", ["coder", "test", "review"]),
            stage=stage or ("conflict_review" if is_conflict_review else None)
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="planner",
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
        """Save planner response and extract product logic metadata.
        
        Saves the planner's output to state and extracts information about
        algorithms, design patterns, and complexity from the plan. This
        metadata is then added to the blueprint to document the design decisions.
        
        Args:
            content: The complete planner output content.
        """
        channel = f"squad-{self.agent_id}-planner"
        self.state_manager.add_chat_message(channel, "assistant", content)
        
        # Extract product logic information (algorithms, patterns, complexity)
        methodology_info = self._extract_methodology_info(content)
        
        # Update blueprint with metadata if found
        if methodology_info:
            await self._update_blueprint_metadata(methodology_info)
        
        await self.state_manager.save_state()
    
    def _extract_methodology_info(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract algorithm, design pattern, and complexity information from planner output.
        
        Uses regex patterns to find mentions of algorithms (e.g., "Dijkstra"),
        design patterns (e.g., "Strategy"), and complexity notation (e.g., "O(n log n)").
        Note: Development methodologies (TDD, BDD) are excluded as they're not
        product logic.
        
        Args:
            content: Planner output text to analyze.
        
        Returns:
            Dictionary with algorithm, design_pattern, and/or complexity keys
            if found, None if no product logic information is detected.
        """
        methodology_info = {}
        
        # Look for methodology mentions (TDD, BDD, etc.)
        methodology_patterns = [
            r"methodology[:\s]+([A-Z]+)",
            r"TDD|BDD|DDD|ATDD",
            r"test[-\s]?driven|behavior[-\s]?driven"
        ]
        for pattern in methodology_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                methodology = match.group(1) if match.groups() else match.group(0)
                methodology_info["methodology"] = methodology.upper() if len(methodology) <= 5 else methodology
                break
        
        # Look for algorithm mentions
        algorithm_patterns = [
            r"algorithm[:\s]+([A-Za-z]+)",
            r"(?:using|implementing)\s+([A-Z][a-z]+)\s+algorithm",
            r"Dijkstra|BFS|DFS|A\*|quicksort|mergesort"
        ]
        for pattern in algorithm_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                algorithm = match.group(1) if match.groups() else match.group(0)
                methodology_info["algorithm"] = algorithm
                break
        
        # Look for design pattern mentions
        pattern_patterns = [
            r"design[-\s]?pattern[:\s]+([A-Za-z]+)",
            r"(?:using|implementing)\s+([A-Z][a-z]+)\s+pattern",
            r"Strategy|Factory|Singleton|Observer|Decorator|Adapter"
        ]
        for pattern in pattern_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                design_pattern = match.group(1) if match.groups() else match.group(0)
                methodology_info["design_pattern"] = design_pattern
                break
        
        # Look for complexity mentions
        complexity_patterns = [
            r"complexity[:\s]+([O\(][^)]+\))",
            r"O\([^)]+\)",
            r"time[-\s]?complexity[:\s]+([O\(][^)]+\))"
        ]
        for pattern in complexity_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                complexity = match.group(1) if match.groups() else match.group(0)
                methodology_info["complexity"] = complexity
                break
        
        return methodology_info if methodology_info else None
    
    async def _update_blueprint_metadata(self, methodology_info: Dict[str, Any]) -> None:
        """Update blueprint with extracted product logic metadata.
        
        Adds algorithm, design pattern, and complexity information to the
        blueprint components. This documents the design decisions made during
        planning. Development methodologies are excluded as they're not
        product logic.
        
        Args:
            methodology_info: Dictionary containing algorithm, design_pattern,
                and/or complexity information extracted from planner output.
        """
        from manifest.audit.blueprint.blueprint_metadata import load_blueprint_with_metadata, save_blueprint_with_metadata
        
        manifest_dir = Path(".manifest")
        blueprint_file = manifest_dir / "blueprint.json"
        
        if not blueprint_file.exists():
            return
        
        try:
            blueprint = load_blueprint_with_metadata(blueprint_file, "llm_design", False)
            
            # Update components with metadata (excluding methodology)
            # For now, update the first component or create a metadata section
            if "components" in blueprint and blueprint["components"]:
                # Update the first component (or we could match by task_id)
                # This is a simplified approach - in production, we'd match components by task
                comp = blueprint["components"][0]
                # Only update algorithm, design_pattern, complexity (not methodology)
                if "algorithm" in methodology_info:
                    comp["algorithm"] = methodology_info["algorithm"]
                    comp["algorithm_reasoning"] = methodology_info.get("algorithm_reasoning", "")
                if "design_pattern" in methodology_info:
                    comp["design_pattern"] = methodology_info["design_pattern"]
                    comp["design_pattern_reasoning"] = methodology_info.get("design_pattern_reasoning", "")
                if "complexity" in methodology_info:
                    comp["complexity"] = methodology_info["complexity"]
                    comp["complexity_reasoning"] = methodology_info.get("complexity_reasoning", "")
            
            # Save updated blueprint with metadata
            save_blueprint_with_metadata(blueprint, blueprint_file, "llm_design", False, "llm_inference")
        except Exception as e:
            # Silently fail - blueprint update is optional
            pass