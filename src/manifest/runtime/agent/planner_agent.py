"""
Planner Agent - Detailed task planning and blueprint creation.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.agent.planner_prompt import get_planner_prompt
from manifest.core.state_manager import StateManager


class PlannerAgent:
    """
    Planner agent - Detailed planning consultant.
    Creates detailed work plans and blueprints but does not implement.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Planner agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
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
        """
        Create a detailed work plan for the task.
        
        Args:
            task_description: Task description
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Planning output chunks
        """
        # Generate prompt
        prompt = get_planner_prompt(
            task_description=task_description,
            context=context,
            available_agents=context.get("available_agents", ["coder", "test", "review"])
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
    
    async def _save_response(self, content: str):
        """Save agent response to state and extract methodology information."""
        channel = f"squad-{self.agent_id}-planner"
        self.state_manager.add_chat_message(channel, "assistant", content)
        
        # Extract methodology/algorithm information from planner output
        methodology_info = self._extract_methodology_info(content)
        
        # Update Blueprint with methodology metadata if available
        if methodology_info:
            await self._update_blueprint_metadata(methodology_info)
        
        await self.state_manager.save_state()
    
    def _extract_methodology_info(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract methodology, algorithm, and design pattern information from planner output.
        
        Args:
            content: Planner output content
            
        Returns:
            Dict with methodology information or None
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
    
    async def _update_blueprint_metadata(self, methodology_info: Dict[str, Any]):
        """
        Update Blueprint with metadata (algorithm, design_pattern, complexity).
        Note: methodology is excluded as it's a development methodology, not product logic.
        
        Args:
            methodology_info: Metadata information dict (algorithm, design_pattern, complexity)
        """
        from manifest.audit.blueprint_metadata import load_blueprint_with_metadata, save_blueprint_with_metadata
        
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