"""
Unit tests for OpenCode tools: TaskManagementTool and SprintManagementTool.
"""
import json
import pytest
from pathlib import Path

from manifest.runtime.opencode.tools.task_management import TaskManagementTool
from manifest.runtime.opencode.tools.sprint_management import SprintManagementTool
from manifest.runtime.opencode.tools.worker_squad_spawn import WorkerSquadSpawnTool
from manifest.runtime.opencode.tools.blueprint_sync import BlueprintSyncTool, DriftCheckTool


@pytest.fixture
def manifest_dir(tmp_path):
    """Temporary .manifest directory."""
    d = tmp_path / ".manifest"
    d.mkdir()
    return d


@pytest.fixture
def task_tool(manifest_dir):
    return TaskManagementTool(manifest_dir=manifest_dir)


@pytest.fixture
def sprint_tool(manifest_dir):
    return SprintManagementTool(manifest_dir=manifest_dir)


# --- TaskManagementTool ---


def test_task_tool_create_task(task_tool):
    out = task_tool.create_task(name="Implement auth", sprint_id="sprint_001")
    assert out["ok"] is True
    assert "task_id" in out
    assert out["task"]["name"] == "Implement auth"
    assert out["task"]["sprint_id"] == "sprint_001"
    assert out["task"]["status"] == "pending"
    assert out["task"]["stage"] == "planning"
    assert out["task"]["progress"]["percentage"] == 0


def test_task_tool_update_task_status(task_tool):
    out = task_tool.create_task(name="Task A")
    assert out["ok"] is True
    task_id = out["task_id"]
    out2 = task_tool.update_task_status(task_id, "in_progress")
    assert out2["ok"] is True
    assert out2["task"]["status"] == "in_progress"


def test_task_tool_assign_task(task_tool):
    out = task_tool.create_task(name="Task B")
    task_id = out["task_id"]
    out2 = task_tool.assign_task(task_id, "manifest-coder")
    assert out2["ok"] is True
    assert out2["task"]["assigned_agent"] == "manifest-coder"


def test_task_tool_update_task_progress(task_tool):
    out = task_tool.create_task(name="Task C")
    task_id = out["task_id"]
    out2 = task_tool.update_task_progress(task_id, 45.5)
    assert out2["ok"] is True
    assert out2["task"]["progress"]["percentage"] == 45.5


def test_task_tool_list_tasks(task_tool):
    task_tool.create_task(name="T1", sprint_id="s1")
    task_tool.create_task(name="T2", sprint_id="s1")
    task_tool.create_task(name="T3", sprint_id="s2")
    all_tasks = task_tool.list_tasks()
    assert len(all_tasks) == 3
    s1_tasks = task_tool.list_tasks(sprint_id="s1")
    assert len(s1_tasks) == 2


def test_task_tool_get_task(task_tool):
    out = task_tool.create_task(name="Get me")
    task_id = out["task_id"]
    t = task_tool.get_task(task_id)
    assert t is not None
    assert t["name"] == "Get me"
    assert task_tool.get_task("nonexistent") is None


def test_task_tool_tasks_json_persisted(task_tool, manifest_dir):
    task_tool.create_task(name="Persist")
    path = manifest_dir / "tasks.json"
    assert path.exists()
    with open(path, "r") as f:
        data = json.load(f)
    assert "tasks" in data
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["name"] == "Persist"


# --- SprintManagementTool ---


def test_sprint_tool_create_sprint(sprint_tool):
    out = sprint_tool.create_sprint(
        name="Sprint 1: Auth",
        start_date="2026-01-28",
        end_date="2026-02-04",
    )
    assert out["ok"] is True
    assert "sprint_id" in out
    assert out["sprint"]["name"] == "Sprint 1: Auth"
    assert out["sprint"]["status"] == "active"
    assert out["sprint"]["start_date"] == "2026-01-28"
    assert out["sprint"]["end_date"] == "2026-02-04"


def test_sprint_tool_list_sprints(sprint_tool):
    sprint_tool.create_sprint(name="S1")
    sprint_tool.create_sprint(name="S2")
    sprints = sprint_tool.list_sprints()
    assert len(sprints) == 2


def test_sprint_tool_get_sprint(sprint_tool):
    out = sprint_tool.create_sprint(name="Get Sprint")
    sprint_id = out["sprint_id"]
    s = sprint_tool.get_sprint(sprint_id)
    assert s is not None
    assert s["name"] == "Get Sprint"
    assert sprint_tool.get_sprint("nonexistent") is None


def test_sprint_tool_uses_same_tasks_json(manifest_dir, task_tool, sprint_tool):
    """Sprint and task tools share .manifest/tasks.json."""
    task_tool.create_task(name="Task")
    sprint_tool.create_sprint(name="Sprint")
    path = manifest_dir / "tasks.json"
    with open(path, "r") as f:
        data = json.load(f)
    assert "tasks" in data and "sprints" in data
    assert len(data["tasks"]) == 1
    assert len(data["sprints"]) == 1


# --- WorkerSquadSpawnTool ---


@pytest.fixture
def spawn_tool(manifest_dir):
    return WorkerSquadSpawnTool(manifest_dir=manifest_dir)


def test_spawn_tool_spawn_planner(spawn_tool):
    pid = spawn_tool.spawn_planner("task_001", context={"tier": 1})
    assert pid.startswith("oc-manifest-planner-task_001-")
    assert len(pid) > 30


def test_spawn_tool_spawn_coder(spawn_tool):
    pid = spawn_tool.spawn_coder("task_002", plan={"steps": []})
    assert "manifest-coder" in pid and "task_002" in pid


def test_spawn_tool_spawn_test(spawn_tool):
    pid = spawn_tool.spawn_test("task_003", code_changes=["src/a.py"])
    assert "manifest-test" in pid


def test_spawn_tool_logs_to_manifest(manifest_dir, spawn_tool):
    spawn_tool.spawn_planner("task_001")
    path = manifest_dir / "worker_spawns.json"
    assert path.exists()
    with open(path, "r") as f:
        data = json.load(f)
    assert "spawns" in data
    assert len(data["spawns"]) == 1
    assert data["spawns"][0]["agent_name"] == "manifest-planner"
    assert data["spawns"][0]["task_id"] == "task_001"


# --- BlueprintSyncTool / DriftCheckTool ---


@pytest.fixture
def manifest_with_blueprints(manifest_dir):
    """Minimal .manifest with blueprint and blueprint_code."""
    (manifest_dir / "blueprint.json").write_text(json.dumps({
        "version": "1.0",
        "components": [{"id": "c1", "name": "Comp1", "type": "class"}],
        "contracts": [],
        "zones": {},
    }))
    (manifest_dir / "blueprint_code.json").write_text(json.dumps({
        "version": "1.0",
        "components": [{"id": "c1", "name": "Comp1", "type": "class"}],
        "contracts": [],
        "zones": {},
    }))
    return manifest_dir


def test_blueprint_sync_compare(manifest_with_blueprints):
    tool = BlueprintSyncTool(manifest_dir=manifest_with_blueprints)
    out = tool.compare_blueprints()
    assert out.get("ok") is True
    assert "conflicts" in out
    assert "count" in out


def test_blueprint_sync_detect_drift(manifest_with_blueprints):
    tool = BlueprintSyncTool(manifest_dir=manifest_with_blueprints)
    out = tool.detect_drift()
    assert out.get("ok") is True
    assert "component_statuses" in out


def test_drift_check_tool(manifest_with_blueprints):
    tool = DriftCheckTool(manifest_dir=manifest_with_blueprints)
    out = tool.check()
    assert out.get("ok") is True
    assert "component_statuses" in out
