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

from manifest.core.logger import get_logger

logger = get_logger(__name__)


class TaskScoper:
    """Manages task boundaries and context scoping."""

    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE
        self.blueprint_file = self.manifest_dir / BLUEPRINT_DESIGN_FILE
        self._blueprint_data = {}
        self._load_data()

    def _load_data(self):
        """Load blueprint data."""
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        self._blueprint_data = BlueprintLoader.load_blueprint(
            self.manifest_dir, with_metadata=True
        )

    def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """Get scoped context for a task.

        Args:
            task_id: Task ID.

        Returns:
            Dict with entities, files, requirements, allowed_modifications.
        """
        entities = self._get_task_entities(task_id)
        files = self._get_task_files(task_id, entities)
        requirements = self._get_task_requirements(task_id)
        allowed_modifications = self._get_allowed_modifications(entities, files)

        return {
            "entities": entities,
            "files": files,
            "requirements": requirements,
            "allowed_modifications": allowed_modifications
        }

    def _get_task_entities(self, task_id: str) -> List[Dict[str, Any]]:
        """Return entities related to a task."""
        from manifest.audit.entity_schema import PROJECT_ROOT_ID
        entities = self._blueprint_data.get("entities") or []
        nodes = [e for e in entities if (e.get("id") or "") != PROJECT_ROOT_ID]
        task_nodes = [e for e in nodes if e.get("task_id") == task_id or task_id in (e.get("tasks") or [])]
        return task_nodes if task_nodes else nodes

    def _get_task_files(self, task_id: str, entities: List[Dict[str, Any]]) -> List[str]:
        """Return file paths for task from entity reality or file."""
        files = set()
        for ent in entities:
            ent_files = ent.get("files", [])
            if isinstance(ent_files, list):
                files.update(ent_files)
            elif isinstance(ent_files, str):
                files.add(ent_files)
            else:
                symbol = (ent.get("reality") or {}).get("symbol") or ent.get("file")
                if symbol:
                    files.add(symbol)
        return sorted(list(files))

    def _get_task_requirements(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task-specific requirements from blueprint (entity governance/assertions)."""
        requirements = []
        for e in self._blueprint_data.get("entities") or []:
            if e.get("task_id") == task_id or task_id in (e.get("tasks") or []):
                gov = (e.get("intent") or {}).get("governance") or {}
                for a in gov.get("assertions") or []:
                    if isinstance(a, str):
                        requirements.append({"description": a})
                for r in gov.get("rules") or []:
                    if isinstance(r, str):
                        requirements.append({"description": r})
        return requirements

    def _get_allowed_modifications(self, entities: List[Dict[str, Any]], files: List[str]) -> List[str]:
        """Determine allowed file modification paths."""
        allowed = set()

        for file_path in files:
            path = Path(file_path)
            if path.parent != Path("."):
                allowed.add(str(path.parent))

        for ent in entities:
            ent_dir = ent.get("directory")
            if ent_dir:
                allowed.add(ent_dir)

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
            "entity_count": len(context.get("entities", [])),
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
        """Validate task granularity; return valid, warnings, errors, counts.

        Args:
            task_id: Task ID.
            context: Pre-computed context (optional).
            model_config: Model config for size validation (optional).

        Returns:
            Dict with valid, warnings, errors, file_count, entity_count, context_size_validation.
        """
        if context is None:
            context_data = self.get_task_context(task_id)
        else:
            context_data = {
                "files": context.get("task_scope", {}).get("allowed_files", []),
                "entities": context.get("task_scope", {}).get("entities", [])
            }

        files = context_data.get("files", [])
        entities = context_data.get("entities", [])

        file_count = len(files)
        entity_count = len(entities)

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

            if entity_count > 3:
                warnings.append(f"Task spans {entity_count} entities. Consider splitting if entities are unrelated.")

        result = {
            "valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
            "file_count": file_count,
            "entity_count": entity_count
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
        """Return True if two tasks can run in parallel (no file or entity overlap)."""
        context_1 = self.get_task_context(task_id_1)
        context_2 = self.get_task_context(task_id_2)

        files_1 = set(context_1.get("files", []))
        files_2 = set(context_2.get("files", []))

        # Check file overlap
        if files_1 & files_2:
            return False

        ids_1 = {e.get("id") for e in context_1.get("entities", [])}
        ids_2 = {e.get("id") for e in context_2.get("entities", [])}

        if ids_1 & ids_2:
            return False

        return True

    def validate_parallel_execution(self, task_ids: List[str]) -> Dict[str, Any]:
        """Validate parallel execution; return can_parallelize, conflicts, parallel_groups."""
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
