"""
Unit tests for task_scoper.py
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from manifest.agents.task_scoper import TaskScoper


@pytest.fixture
def temp_manifest_dir(tmp_path):
    """Create temporary manifest directory with test data."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    # Create blueprint.json
    blueprint = {
        "version": "1.0",
        "zones": {
            "client": [],
            "server": [
                {
                    "id": "comp-1",
                    "name": "AuthService",
                    "files": ["src/auth/service.py", "src/auth/models.py"]
                }
            ],
            "data": []
        },
        "components": [
            {
                "id": "comp-1",
                "name": "AuthService",
                "files": ["src/auth/service.py", "src/auth/models.py"],
                "directory": "src/auth"
            }
        ],
        "contracts": []
    }
    with open(manifest_dir / "blueprint.json", "w") as f:
        json.dump(blueprint, f)

    # Create intent.json
    intent = {
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": [
            {
                "id": "feature-1",
                "name": "Auth Feature",
                "tasks": ["task-1"],
                "reqs": [
                    {"id": "REQ-1", "desc": "Login functionality"}
                ]
            }
        ]
    }
    with open(manifest_dir / "intent.json", "w") as f:
        json.dump(intent, f)

    return manifest_dir


def test_task_scoper_init(temp_manifest_dir):
    """Test TaskScoper initialization."""
    scoper = TaskScoper(temp_manifest_dir)
    assert scoper.manifest_dir == temp_manifest_dir
    assert scoper._blueprint_data is not None
    assert scoper._intent_data is not None


def test_get_task_context(temp_manifest_dir):
    """Test getting task context."""
    scoper = TaskScoper(temp_manifest_dir)
    context = scoper.get_task_context("task-1")

    assert "components" in context
    assert "files" in context
    assert "requirements" in context
    assert "allowed_modifications" in context


def test_validate_task_scope(temp_manifest_dir):
    """Test task scope validation."""
    scoper = TaskScoper(temp_manifest_dir)

    # File in scope
    assert scoper.validate_task_scope("task-1", "src/auth/service.py") == True

    # File not in scope
    assert scoper.validate_task_scope("task-1", "src/other/file.py") == False


def test_get_task_scope_summary(temp_manifest_dir):
    """Test getting task scope summary."""
    scoper = TaskScoper(temp_manifest_dir)
    summary = scoper.get_task_scope_summary("task-1")

    assert "task_id" in summary
    assert "component_count" in summary
    assert "file_count" in summary
    assert summary["task_id"] == "task-1"


# ========== TDL: Task Scoper Tests ==========

def test_task_granularity_validation(temp_manifest_dir):
    """Test task granularity validation."""
    scoper = TaskScoper(temp_manifest_dir)

    # Create granularity rules file
    rules_file = Path(".rules/task-granularity.md")
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Task Granularity Rules\n\nMax files: 12\nRecommended: 7")

    # Test with valid task (few files)
    context = {
        "task_scope": {
            "allowed_files": ["file1.py", "file2.py"],
            "components": [{"id": "comp-1"}]
        }
    }
    result = scoper.validate_task_granularity("task-1", context=context)
    assert result["valid"] is True
    assert result["file_count"] == 2
    assert result["component_count"] == 1

    # Test with too many files (warning)
    context_warning = {
        "task_scope": {
            "allowed_files": [f"file{i}.py" for i in range(8)],
            "components": [{"id": "comp-1"}]
        }
    }
    result_warning = scoper.validate_task_granularity("task-1", context=context_warning)
    assert result_warning["valid"] is True  # Warnings don't invalidate
    assert len(result_warning["warnings"]) > 0

    # Test with too many files (error)
    context_error = {
        "task_scope": {
            "allowed_files": [f"file{i}.py" for i in range(15)],
            "components": [{"id": "comp-1"}]
        }
    }
    result_error = scoper.validate_task_granularity("task-1", context=context_error)
    assert result_error["valid"] is False
    assert len(result_error["errors"]) > 0


def test_task_granularity_with_model_config(temp_manifest_dir):
    """Test task granularity validation with model config (context size)."""
    scoper = TaskScoper(temp_manifest_dir)

    context = {
        "task_scope": {
            "allowed_files": ["file1.py"],
            "components": [{"id": "comp-1"}]
        }
    }

    model_config = {"provider": "anthropic", "model": "claude-3-opus"}

    # Mock context size calculator (imported inside method)
    with patch('manifest.agents.context_size_calculator.ContextSizeCalculator') as mock_calc_class:
        mock_calc_class.validate_context_size = Mock(return_value={
            "valid": True,
            "estimated_tokens": 1000,
            "available_tokens": 200000
        })

        result = scoper.validate_task_granularity("task-1", context=context, model_config=model_config)
        assert "context_size_validation" in result
        assert result["context_size_validation"]["valid"] is True


def test_task_granularity_context_size_exceeds_limit(temp_manifest_dir):
    """Test task granularity validation when context size exceeds limit."""
    scoper = TaskScoper(temp_manifest_dir)

    context = {
        "task_scope": {
            "allowed_files": ["file1.py"],
            "components": [{"id": "comp-1"}]
        }
    }

    model_config = {"provider": "anthropic", "model": "claude-3-opus"}

    # Mock context size calculator (imported inside method)
    with patch('manifest.agents.context_size_calculator.ContextSizeCalculator') as mock_calc_class:
        mock_calc_class.validate_context_size = Mock(return_value={
            "valid": False,
            "estimated_tokens": 250000,
            "available_tokens": 200000,
            "excess_tokens": 50000
        })

        result = scoper.validate_task_granularity("task-1", context=context, model_config=model_config)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("exceeds model limit" in err for err in result["errors"])


def test_component_scope_extraction(temp_manifest_dir):
    """Test component scope extraction."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with task-specific components
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "Component 1", "task_id": "task-1", "files": ["file1.py"]},
            {"id": "comp-2", "name": "Component 2", "task_id": "task-2", "files": ["file2.py"]},
            {"id": "comp-3", "name": "Component 3", "tasks": ["task-1"], "files": ["file3.py"]}
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    # Reload data
    scoper._load_data()

    # Test component extraction for task-1
    components = scoper._get_task_components("task-1")
    assert len(components) == 2  # comp-1 and comp-3
    assert any(c["id"] == "comp-1" for c in components)
    assert any(c["id"] == "comp-3" for c in components)
    assert not any(c["id"] == "comp-2" for c in components)


def test_component_scope_extraction_no_mapping(temp_manifest_dir):
    """Test component scope extraction when no task mapping exists (fallback to all)."""
    scoper = TaskScoper(temp_manifest_dir)

    # Components without task_id or tasks field
    components = scoper._get_task_components("task-unknown")
    # Should return all components as fallback
    assert len(components) >= 1  # At least the default comp-1


def test_file_scope_determination(temp_manifest_dir):
    """Test file scope determination from components."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with files
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["src/auth/service.py", "src/auth/models.py", "src/auth/utils.py"]
            }
        ],
        "zones": {
            "server": [
                {
                    "id": "comp-1",
                    "files": ["src/auth/service.py"]
                }
            ]
        },
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    # Get task context
    context = scoper.get_task_context("task-1")
    files = context["files"]

    # Should include files from components
    assert "src/auth/service.py" in files
    assert "src/auth/models.py" in files
    assert "src/auth/utils.py" in files


def test_file_scope_from_zones(temp_manifest_dir):
    """Test file scope determination from zones."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with zone files
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "Component 1", "task_id": "task-1"}
        ],
        "zones": {
            "server": [
                {
                    "id": "comp-1",
                    "files": ["src/server/api.py", "src/server/handlers.py"]
                }
            ]
        },
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    context = scoper.get_task_context("task-1")
    files = context["files"]

    # Should include files from zones
    assert "src/server/api.py" in files or len(files) > 0


def test_dependency_analysis_parallel_execution(temp_manifest_dir):
    """Test dependency analysis via parallel execution check."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with overlapping components
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["src/auth/service.py"]
            },
            {
                "id": "comp-2",
                "name": "Component 2",
                "task_id": "task-2",
                "files": ["src/user/service.py"]
            },
            {
                "id": "comp-3",
                "name": "Component 3",
                "task_id": "task-3",
                "files": ["src/auth/service.py"]  # Overlaps with task-1
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    # Test parallel execution check
    # task-1 and task-2 should be able to run in parallel (no overlap)
    can_parallel = scoper.can_execute_in_parallel("task-1", "task-2")
    assert can_parallel is True

    # task-1 and task-3 should NOT be able to run in parallel (file overlap)
    cannot_parallel = scoper.can_execute_in_parallel("task-1", "task-3")
    assert cannot_parallel is False


def test_dependency_analysis_component_overlap(temp_manifest_dir):
    """Test dependency analysis when tasks share components."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with shared components
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-shared",
                "name": "Shared Component",
                "task_id": "task-1",
                "files": ["src/shared/service.py"]
            },
            {
                "id": "comp-shared",
                "name": "Shared Component",
                "task_id": "task-2",
                "files": ["src/shared/service.py"]
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    # Both tasks reference the same component, so they can't run in parallel
    can_parallel = scoper.can_execute_in_parallel("task-1", "task-2")
    # Should be False because they share the same component
    assert can_parallel is False


def test_validate_parallel_execution(temp_manifest_dir):
    """Test parallel execution validation for multiple tasks."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with multiple tasks
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["src/task1/file1.py"]
            },
            {
                "id": "comp-2",
                "name": "Component 2",
                "task_id": "task-2",
                "files": ["src/task2/file2.py"]
            },
            {
                "id": "comp-3",
                "name": "Component 3",
                "task_id": "task-3",
                "files": ["src/task3/file3.py"]
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    # Validate parallel execution
    result = scoper.validate_parallel_execution(["task-1", "task-2", "task-3"])
    assert "can_parallelize" in result
    assert "conflicts" in result
    assert "parallel_groups" in result
    # All tasks should be able to run in parallel (no overlaps)
    assert result["can_parallelize"] is True
    assert len(result["conflicts"]) == 0


def test_validate_parallel_execution_with_conflicts(temp_manifest_dir):
    """Test parallel execution validation with file conflicts."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with overlapping files
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["src/shared/file.py"]
            },
            {
                "id": "comp-2",
                "name": "Component 2",
                "task_id": "task-2",
                "files": ["src/shared/file.py"]  # Same file!
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    result = scoper.validate_parallel_execution(["task-1", "task-2"])
    assert result["can_parallelize"] is False
    assert len(result["conflicts"]) > 0
    assert any(c["task1"] == "task-1" and c["task2"] == "task-2" for c in result["conflicts"])


def test_scope_boundary_enforcement_file_validation(temp_manifest_dir):
    """Test scope boundary enforcement via file validation."""
    scoper = TaskScoper(temp_manifest_dir)

    # Get task context
    context = scoper.get_task_context("task-1")
    allowed_files = context.get("files", [])
    allowed_modifications = context.get("allowed_modifications", [])

    # Test exact file match
    if allowed_files:
        assert scoper.validate_task_scope("task-1", allowed_files[0]) is True

    # Test file not in scope
    assert scoper.validate_task_scope("task-1", "src/unauthorized/file.py") is False


def test_scope_boundary_enforcement_directory_validation(temp_manifest_dir):
    """Test scope boundary enforcement via directory validation."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with directory
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["src/auth/service.py"],
                "directory": "src/auth"
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    # Get task context
    context = scoper.get_task_context("task-1")
    allowed_modifications = context.get("allowed_modifications", [])

    # Test file in allowed directory
    if "src/auth" in allowed_modifications:
        assert scoper.validate_task_scope("task-1", "src/auth/other_file.py") is True

    # Test file outside allowed directory
    assert scoper.validate_task_scope("task-1", "src/other/service.py") is False


def test_get_task_requirements(temp_manifest_dir):
    """Test getting task-specific requirements from intent."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update intent with requirements
    intent_file = temp_manifest_dir / "intent.json"
    intent = {
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": [
            {
                "id": "feature-1",
                "name": "Auth Feature",
                "tasks": ["task-1"],
                "reqs": [
                    {"id": "REQ-1", "desc": "Login functionality"},
                    {"id": "REQ-2", "desc": "Logout functionality"}
                ]
            }
        ]
    }
    with open(intent_file, "w") as f:
        json.dump(intent, f)

    scoper._load_data()

    # Get requirements for task-1
    requirements = scoper._get_task_requirements("task-1")
    assert len(requirements) == 2
    assert any(r.get("id") == "REQ-1" for r in requirements)
    assert any(r.get("id") == "REQ-2" for r in requirements)


def test_get_task_requirements_no_match(temp_manifest_dir):
    """Test getting requirements for task not in any feature."""
    scoper = TaskScoper(temp_manifest_dir)

    # Get requirements for non-existent task
    requirements = scoper._get_task_requirements("task-unknown")
    assert len(requirements) == 0


def test_get_allowed_modifications(temp_manifest_dir):
    """Test getting allowed modification directories."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with files and directories
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["src/auth/service.py", "src/auth/models.py"],
                "directory": "src/auth"
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    context = scoper.get_task_context("task-1")
    allowed_modifications = context.get("allowed_modifications", [])

    # Should include directory from component
    assert "src/auth" in allowed_modifications or len(allowed_modifications) > 0


def test_get_allowed_modifications_default(temp_manifest_dir):
    """Test default allowed modifications when no directories specified."""
    scoper = TaskScoper(temp_manifest_dir)

    # Update blueprint with no directory
    blueprint_file = temp_manifest_dir / "blueprint.json"
    blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component 1",
                "task_id": "task-1",
                "files": ["file1.py"]  # No directory
            }
        ],
        "zones": {},
        "contracts": []
    }
    with open(blueprint_file, "w") as f:
        json.dump(blueprint, f)

    scoper._load_data()

    context = scoper.get_task_context("task-1")
    allowed_modifications = context.get("allowed_modifications", [])

    # Should default to ["."] if no directories
    assert len(allowed_modifications) > 0
