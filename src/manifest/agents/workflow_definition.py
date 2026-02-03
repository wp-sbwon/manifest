"""
Workflow definition system for dynamic workflow composition.

This module provides a flexible system for defining and executing workflows
dynamically. Workflows can be defined in JSON/YAML format and modified at
runtime, allowing for different workflow patterns based on task requirements.

Canonical stage order and sets are defined here so coordinator and executor
use a single source of truth.
"""
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from dataclasses import dataclass, field
from manifest.core.logger import get_logger

logger = get_logger(__name__)

# Default Worker Squad stage order (canonical source; used by coordinator and executor)
DEFAULT_STAGE_ORDER: List[str] = [
    "planner",
    "tdd_test",
    "coder",
    "test",
    "debug",
    "self_review",
    "approver",
]

# Stages required for workflow completion (debug is conditional)
DEFAULT_REQUIRED_STAGES: Set[str] = {"planner", "tdd_test", "coder", "test", "self_review", "approver"}

# Stages whose failure terminates the workflow
DEFAULT_CRITICAL_STAGES: Set[str] = {"planner", "tdd_test"}


def get_next_stage_in_order(
    current_stage: Optional[str],
    stage_order: Optional[List[str]] = None,
) -> Optional[str]:
    """Return the next stage in the given order, or None if current is last.

    Uses DEFAULT_STAGE_ORDER if stage_order is not given.
    """
    order = stage_order or DEFAULT_STAGE_ORDER
    if not current_stage:
        return order[0] if order else None
    try:
        idx = order.index(current_stage)
        if idx < len(order) - 1:
            return order[idx + 1]
    except ValueError:
        pass
    return None


class StageCondition(Enum):
    """Conditions for stage execution."""
    ALWAYS = "always"  # Always execute
    ON_SUCCESS = "on_success"  # Execute if previous stage succeeded
    ON_FAILURE = "on_failure"  # Execute if previous stage failed
    CONDITIONAL = "conditional"  # Execute based on custom condition


@dataclass
class StageDefinition:
    """Definition of a workflow stage.

    Attributes:
        name: Stage name (e.g., "planner", "coder").
        agent_type: Type of agent to use for this stage.
        condition: Condition for executing this stage.
        dependencies: List of stage names that must complete before this stage.
        timeout: Timeout in seconds for this stage.
        retry_on_failure: Whether to retry on failure.
        max_retries: Maximum number of retries.
        parallel: Whether this stage can run in parallel with others.
        required: Whether this stage is required for workflow completion.
        metadata: Additional metadata for the stage.
    """
    name: str
    agent_type: str
    condition: StageCondition = StageCondition.ALWAYS
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 300.0
    retry_on_failure: bool = True
    max_retries: int = 3
    parallel: bool = False
    required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageDefinition":
        """Create StageDefinition from dictionary."""
        condition_str = data.get("condition", "always")
        condition = StageCondition(condition_str) if isinstance(condition_str, str) else condition_str

        return cls(
            name=data["name"],
            agent_type=data["agent_type"],
            condition=condition,
            dependencies=data.get("dependencies", []),
            timeout=data.get("timeout", 300.0),
            retry_on_failure=data.get("retry_on_failure", True),
            max_retries=data.get("max_retries", 3),
            parallel=data.get("parallel", False),
            required=data.get("required", True),
            metadata=data.get("metadata", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "condition": self.condition.value,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "retry_on_failure": self.retry_on_failure,
            "max_retries": self.max_retries,
            "parallel": self.parallel,
            "required": self.required,
            "metadata": self.metadata
        }


@dataclass
class WorkflowDefinition:
    """Definition of a complete workflow.

    Attributes:
        name: Workflow name.
        description: Workflow description.
        stages: List of stage definitions in execution order.
        entry_points: List of stage names that can be entry points.
        exit_points: List of stage names that are exit points.
        metadata: Additional metadata for the workflow.
    """
    name: str
    description: str = ""
    stages: List[StageDefinition] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    exit_points: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create WorkflowDefinition from dictionary."""
        stages = [
            StageDefinition.from_dict(stage_data)
            for stage_data in data.get("stages", [])
        ]

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            stages=stages,
            entry_points=data.get("entry_points", []),
            exit_points=data.get("exit_points", []),
            metadata=data.get("metadata", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "stages": [stage.to_dict() for stage in self.stages],
            "entry_points": self.entry_points,
            "exit_points": self.exit_points,
            "metadata": self.metadata
        }

    def get_stage(self, name: str) -> Optional[StageDefinition]:
        """Get stage definition by name."""
        return next((s for s in self.stages if s.name == name), None)

    def get_dependencies(self, stage_name: str) -> List[str]:
        """Get dependencies for a stage."""
        stage = self.get_stage(stage_name)
        return stage.dependencies if stage else []

    def get_dependents(self, stage_name: str) -> List[str]:
        """Get stages that depend on this stage."""
        return [
            s.name for s in self.stages
            if stage_name in s.dependencies
        ]

    def validate(self) -> tuple[bool, List[str]]:
        """Validate workflow definition.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []

        # Check for duplicate stage names
        stage_names = [s.name for s in self.stages]
        if len(stage_names) != len(set(stage_names)):
            errors.append("Duplicate stage names found")

        # Check dependencies exist
        all_stage_names = set(stage_names)
        for stage in self.stages:
            for dep in stage.dependencies:
                if dep not in all_stage_names:
                    errors.append(f"Stage {stage.name} depends on non-existent stage: {dep}")

        # Check entry points exist
        for entry in self.entry_points:
            if entry not in all_stage_names:
                errors.append(f"Entry point {entry} does not exist")

        # Check exit points exist
        for exit_point in self.exit_points:
            if exit_point not in all_stage_names:
                errors.append(f"Exit point {exit_point} does not exist")

        # Check for cycles in dependencies
        if self._has_cycle():
            errors.append("Circular dependency detected in workflow")

        return len(errors) == 0, errors

    def _has_cycle(self) -> bool:
        """Check if workflow has circular dependencies."""
        visited = set()
        rec_stack = set()

        def has_cycle_util(stage_name: str) -> bool:
            visited.add(stage_name)
            rec_stack.add(stage_name)

            stage = self.get_stage(stage_name)
            if stage:
                for dep in stage.dependencies:
                    if dep not in visited:
                        if has_cycle_util(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(stage_name)
            return False

        for stage in self.stages:
            if stage.name not in visited:
                if has_cycle_util(stage.name):
                    return True

        return False

    def get_execution_order(self) -> List[List[str]]:
        """Get execution order as levels (stages that can run in parallel).

        Returns:
            List of lists, where each inner list contains stage names that
            can run in parallel (same dependency level).
        """
        # Build dependency graph
        remaining = {s.name for s in self.stages}
        levels = []

        while remaining:
            # Find stages with no remaining dependencies
            ready = []
            for stage_name in remaining:
                stage = self.get_stage(stage_name)
                if stage:
                    deps = set(stage.dependencies)
                    if not deps or all(dep not in remaining for dep in deps):
                        ready.append(stage_name)

            if not ready:
                # Circular dependency or error
                logger.warning(f"Could not resolve execution order, remaining stages: {remaining}")
                break

            levels.append(ready)
            remaining -= set(ready)

        return levels


class WorkflowRegistry:
    """Registry for workflow definitions.

    Manages multiple workflow definitions and provides lookup and validation.
    """

    def __init__(self):
        """Initialize the workflow registry."""
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._load_default_workflows()

    def _load_default_workflows(self):
        """Load default workflow definitions."""
        # Default Worker Squad workflow
        worker_squad = WorkflowDefinition(
            name="worker_squad",
            description="Standard TDD-based Worker Squad workflow",
            stages=[
                StageDefinition(
                    name="planner",
                    agent_type="planner",
                    condition=StageCondition.ALWAYS,
                    dependencies=[],
                    timeout=300.0,
                    required=True
                ),
                StageDefinition(
                    name="tdd_test",
                    agent_type="test",
                    condition=StageCondition.ON_SUCCESS,
                    dependencies=["planner"],
                    timeout=300.0,
                    required=True
                ),
                StageDefinition(
                    name="coder",
                    agent_type="coder",
                    condition=StageCondition.ON_SUCCESS,
                    dependencies=["tdd_test"],
                    timeout=900.0,
                    required=True
                ),
                StageDefinition(
                    name="test",
                    agent_type="test",
                    condition=StageCondition.ON_SUCCESS,
                    dependencies=["coder"],
                    timeout=300.0,
                    required=True
                ),
                StageDefinition(
                    name="debug",
                    agent_type="debug",
                    condition=StageCondition.ON_FAILURE,
                    dependencies=["test"],
                    timeout=600.0,
                    required=False,
                    max_retries=5
                ),
                StageDefinition(
                    name="self_review",
                    agent_type="coder",
                    condition=StageCondition.ON_SUCCESS,
                    dependencies=["test"],
                    timeout=300.0,
                    required=True
                ),
                StageDefinition(
                    name="approver",
                    agent_type="approver",
                    condition=StageCondition.ON_SUCCESS,
                    dependencies=["self_review"],
                    timeout=300.0,
                    required=True
                )
            ],
            entry_points=["planner"],
            exit_points=["approver"]
        )
        self.register(worker_squad)

    def register(self, workflow: WorkflowDefinition) -> bool:
        """Register a workflow definition.

        Args:
            workflow: Workflow definition to register.

        Returns:
            True if registration successful, False if validation failed.
        """
        is_valid, errors = workflow.validate()
        if not is_valid:
            logger.error(f"Workflow {workflow.name} validation failed: {errors}")
            return False

        self._workflows[workflow.name] = workflow
        logger.info(f"Workflow {workflow.name} registered")
        return True

    def get(self, name: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by name.

        Args:
            name: Workflow name.

        Returns:
            Workflow definition or None if not found.
        """
        return self._workflows.get(name)

    def list(self) -> List[str]:
        """List all registered workflow names.

        Returns:
            List of workflow names.
        """
        return list(self._workflows.keys())

    def unregister(self, name: str) -> bool:
        """Unregister a workflow.

        Args:
            name: Workflow name.

        Returns:
            True if unregistered, False if not found.
        """
        if name in self._workflows:
            del self._workflows[name]
            logger.info(f"Workflow {name} unregistered")
            return True
        return False

    def load_from_dict(self, data: Dict[str, Any]) -> bool:
        """Load workflow from dictionary.

        Args:
            data: Dictionary containing workflow definition.

        Returns:
            True if loaded successfully.
        """
        try:
            workflow = WorkflowDefinition.from_dict(data)
            return self.register(workflow)
        except Exception as e:
            logger.error(f"Error loading workflow from dict: {e}", exc_info=True)
            return False

    def load_from_file(self, file_path: str) -> bool:
        """Load workflow from JSON/YAML file.

        Args:
            file_path: Path to workflow definition file.

        Returns:
            True if loaded successfully.
        """
        from pathlib import Path
        import json
        import yaml

        path = Path(file_path)
        if not path.exists():
            logger.error(f"Workflow file not found: {file_path}")
            return False

        try:
            with open(path, 'r') as f:
                if path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            return self.load_from_dict(data)
        except Exception as e:
            logger.error(f"Error loading workflow from file {file_path}: {e}", exc_info=True)
            return False
