"""
Task scoping system for managing task boundaries and context.

This module provides the TaskScoper class which determines what context
worker agents should receive for a specific task. It analyzes the blueprint
and intent to identify relevant components, files, and requirements, ensuring
agents only see what's necessary for their task.

This scoping prevents agents from modifying unrelated code and helps maintain
code boundaries and separation of concerns.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set


class TaskScoper:
    """Manages task boundaries and context scoping."""

    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE
        self.blueprint_file = self.manifest_dir / BLUEPRINT_DESIGN_FILE
        self.intent_file = self.manifest_dir / "intent.json"
        self._blueprint_data = {}
        self._intent_data = {}
        self._load_data()

    def _load_data(self):
        """Load blueprint and intent data."""
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        # Load blueprint with metadata
        self._blueprint_data = BlueprintLoader.load_blueprint(
            self.manifest_dir, with_metadata=True
        )

        # Load intent
        if self.intent_file.exists():
            try:
                with open(self.intent_file, "r") as f:
                    self._intent_data = json.load(f)
            except Exception:
                self._intent_data = {"version": "1.0", "sprint": "", "features": []}
        else:
            self._intent_data = {"version": "1.0", "sprint": "", "features": []}

    def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """Get scoped context for a specific task.

        Analyzes the blueprint and intent to determine which components,
        files, and requirements are relevant to this task. This creates
        a boundary that limits what the agent can see and modify.

        Args:
            task_id: ID of the task to get context for.

        Returns:
            Dictionary containing:
            - components: List of blueprint components relevant to the task
            - files: List of file paths the task can access
            - requirements: List of requirements relevant to the task
            - allowed_modifications: List of files/components that can be modified
        """
        # Find components related to task
        components = self._get_task_components(task_id)

        # Find files related to task based on components
        files = self._get_task_files(task_id, components)

        # Get task-specific requirements from intent
        requirements = self._get_task_requirements(task_id)

        # Determine which files/components can be modified
        allowed_modifications = self._get_allowed_modifications(components, files)

        return {
            "components": components,
            "files": files,
            "requirements": requirements,
            "allowed_modifications": allowed_modifications
        }

    def _get_task_components(self, task_id: str) -> List[Dict[str, Any]]:
        """Get blueprint components that are related to a task.

        Filters blueprint components based on task_id. If components have
        a task_id field or tasks list, only matching components are returned.
        If no mapping exists, returns all components (fallback behavior).

        Args:
            task_id: ID of the task to find components for.

        Returns:
            List of component dictionaries from the blueprint.
        """
        # In a real implementation, tasks would be mapped to components
        # For now, return all components (can be refined later)
        components = self._blueprint_data.get("components", [])

        # Filter by task_id if components have task_id field
        task_components = []
        for comp in components:
            if comp.get("task_id") == task_id or task_id in comp.get("tasks", []):
                task_components.append(comp)
            # If no task mapping, include all (will be refined with actual task mapping)

        return task_components if task_components else components

    def _get_task_files(self, task_id: str, components: List[Dict[str, Any]]) -> List[str]:
        """Get files related to task based on components."""
        files = set()

        # Get files from components
        for comp in components:
            comp_files = comp.get("files", [])
            if isinstance(comp_files, list):
                files.update(comp_files)
            elif isinstance(comp_files, str):
                files.add(comp_files)

        # Get files from zones
        zones = self._blueprint_data.get("zones", {})
        for zone_name, zone_components in zones.items():
            for comp in zone_components:
                if comp in components or any(c.get("id") == comp.get("id") for c in components):
                    comp_files = comp.get("files", [])
                    if isinstance(comp_files, list):
                        files.update(comp_files)
                    elif isinstance(comp_files, str):
                        files.add(comp_files)

        return sorted(list(files))

    def _get_task_requirements(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task-specific requirements from intent.json."""
        features = self._intent_data.get("features", [])
        requirements = []

        # Find feature that contains this task
        for feature in features:
            feature_tasks = feature.get("tasks", [])
            if task_id in feature_tasks or any(t.get("id") == task_id for t in feature_tasks if isinstance(t, dict)):
                # Get requirements for this feature
                reqs = feature.get("reqs", [])
                requirements.extend(reqs)

        return requirements

    def _get_allowed_modifications(self, components: List[Dict[str, Any]], files: List[str]) -> List[str]:
        """Determine allowed file modification paths."""
        allowed = set()

        # Add directories from files
        for file_path in files:
            path = Path(file_path)
            if path.parent != Path("."):
                allowed.add(str(path.parent))

        # Add directories from components
        for comp in components:
            comp_dir = comp.get("directory")
            if comp_dir:
                allowed.add(comp_dir)

        return sorted(list(allowed)) if allowed else ["."]  # Default to current directory

    def validate_task_scope(self, task_id: str, file_path: str) -> bool:
        """Check if file is in task scope."""
        task_context = self.get_task_context(task_id)
        allowed_files = task_context.get("files", [])
        allowed_modifications = task_context.get("allowed_modifications", [])

        # Check exact file match
        if file_path in allowed_files:
            return True

        # Check if file is in allowed modification directory
        file_path_obj = Path(file_path)
        for allowed_dir in allowed_modifications:
            allowed_dir_obj = Path(allowed_dir)
            try:
                file_path_obj.relative_to(allowed_dir_obj)
                return True
            except ValueError:
                continue

        return False

    def get_task_scope_summary(self, task_id: str) -> Dict[str, Any]:
        """Get a summary of task scope for display."""
        context = self.get_task_context(task_id)
        return {
            "task_id": task_id,
            "component_count": len(context.get("components", [])),
            "file_count": len(context.get("files", [])),
            "requirement_count": len(context.get("requirements", [])),
            "allowed_directories": context.get("allowed_modifications", [])
        }

    def validate_task_granularity(
        self,
        task_id: str,
        context: Optional[Dict[str, Any]] = None,
        model_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate task granularity against rules and context size.

        Enhanced validation that checks both file/component counts and
        estimated context size against model limits.

        Args:
            task_id: ID of the task to validate.
            context: Optional pre-computed context (to avoid recomputation).
            model_config: Optional model configuration for size validation.

        Returns:
            Dict with validation result:
            {
                "valid": bool,
                "warnings": List[str],
                "errors": List[str],
                "file_count": int,
                "component_count": int,
                "context_size_validation": Optional[Dict]  # If model_config provided
            }
        """
        if context is None:
            context_data = self.get_task_context(task_id)
        else:
            # Extract task context info from provided context
            context_data = {
                "files": context.get("task_scope", {}).get("allowed_files", []),
                "components": context.get("task_scope", {}).get("components", [])
            }

        files = context_data.get("files", [])
        components = context_data.get("components", [])

        file_count = len(files)
        component_count = len(components)

        warnings = []
        errors = []

        # Load granularity rules
        granularity_file = Path(".rules/task-granularity.md")
        if granularity_file.exists():
            rules_content = granularity_file.read_text(encoding="utf-8")

            # Check file count limits
            if file_count > 12:
                errors.append(f"Task modifies {file_count} files (max: 12). Task must be split.")
            elif file_count > 7:
                warnings.append(f"Task modifies {file_count} files (recommended max: 7). Consider splitting.")

            # Check component count
            if component_count > 3:
                warnings.append(f"Task spans {component_count} components. Consider splitting if components are unrelated.")

        result = {
            "valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
            "file_count": file_count,
            "component_count": component_count
        }

        # Add context size validation if model config provided
        if model_config and context:
            from manifest.agents.context_size_calculator import ContextSizeCalculator
            model = model_config.get("model", "")
            provider = model_config.get("provider", "")
            size_validation = ContextSizeCalculator.validate_context_size(context, model, provider)
            result["context_size_validation"] = size_validation

            # Add context size warnings/errors
            if not size_validation.get("valid"):
                excess = size_validation.get("excess_tokens", 0)
                errors.append(
                    f"Context size ({size_validation.get('estimated_tokens')} tokens) "
                    f"exceeds model limit ({size_validation.get('available_tokens')} tokens) "
                    f"by {excess} tokens. Task must be split or context reduced."
                )
                result["valid"] = False
            elif size_validation.get("warnings"):
                for warning in size_validation.get("warnings", []):
                    warnings.append(f"Context size: {warning}")

        return result

    def can_execute_in_parallel(self, task_id_1: str, task_id_2: str) -> bool:
        """
        Check if two tasks can be executed in parallel.

        Returns:
            True if tasks can run in parallel (no file overlap, no dependencies)
        """
        context_1 = self.get_task_context(task_id_1)
        context_2 = self.get_task_context(task_id_2)

        files_1 = set(context_1.get("files", []))
        files_2 = set(context_2.get("files", []))

        # Check file overlap
        if files_1 & files_2:
            return False

        # Check component dependencies
        components_1 = {c.get("id") for c in context_1.get("components", [])}
        components_2 = {c.get("id") for c in context_2.get("components", [])}

        # If tasks share components, they might have dependencies
        if components_1 & components_2:
            # Check if components are tightly coupled (would need more sophisticated analysis)
            # For now, if they share components, assume they can't run in parallel
            return False

        return True

    def validate_parallel_execution(self, task_ids: List[str]) -> Dict[str, Any]:
        """
        Validate if a list of tasks can be executed in parallel.

        Returns:
            Dict with validation result:
            {
                "can_parallelize": bool,
                "conflicts": List[Dict[str, str]],  # [{"task1": "task-1", "task2": "task-2", "reason": "..."}]
                "parallel_groups": List[List[str]]  # Groups of tasks that can run in parallel
            }
        """
        conflicts = []
        parallel_groups = []
        remaining_tasks = task_ids.copy()

        # Build conflict graph
        conflict_pairs = []
        for i, task_id_1 in enumerate(task_ids):
            for task_id_2 in task_ids[i+1:]:
                if not self.can_execute_in_parallel(task_id_1, task_id_2):
                    conflict_pairs.append((task_id_1, task_id_2))
                    conflicts.append({
                        "task1": task_id_1,
                        "task2": task_id_2,
                        "reason": "File overlap or component dependency"
                    })

        # Group tasks that can run in parallel (greedy algorithm)
        while remaining_tasks:
            current_group = [remaining_tasks.pop(0)]

            for task_id in remaining_tasks[:]:
                can_add = True
                for group_task in current_group:
                    if (task_id, group_task) in conflict_pairs or (group_task, task_id) in conflict_pairs:
                        can_add = False
                        break

                if can_add:
                    current_group.append(task_id)
                    remaining_tasks.remove(task_id)

            parallel_groups.append(current_group)

        return {
            "can_parallelize": len(conflicts) == 0,
            "conflicts": conflicts,
            "parallel_groups": parallel_groups
        }
