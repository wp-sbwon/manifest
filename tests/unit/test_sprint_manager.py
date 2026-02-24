"""Unit tests for SprintManager."""
import tempfile
from pathlib import Path

import pytest

from manifest.core.sprint_manager import SprintManager, _ensure_sprint_test_structure


@pytest.mark.unit
def test_save_sprint_creates_file() -> None:
    """save_sprint writes sprint-{id}.json."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SprintManager(Path(tmp))
        ok = mgr.save_sprint({"id": "s1", "name": "Sprint 1"})
        assert ok is True
        path = Path(tmp) / "sprints" / "sprint-s1.json"
        assert path.exists()
        data = path.read_text()
        assert "s1" in data
        assert "integration_tests" in data
        assert "e2e_tests" in data


@pytest.mark.unit
def test_load_sprint_returns_none_when_missing() -> None:
    """load_sprint returns None for missing sprint."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SprintManager(Path(tmp))
        assert mgr.load_sprint("missing") is None


@pytest.mark.unit
def test_load_sprint_roundtrip() -> None:
    """load_sprint returns saved data with normalized structure."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SprintManager(Path(tmp))
        mgr.save_sprint({"id": "s2", "name": "S2"})
        loaded = mgr.load_sprint("s2")
        assert loaded is not None
        assert loaded["id"] == "s2"
        assert "integration_tests" in loaded
        assert "e2e_tests" in loaded


@pytest.mark.unit
def test_list_sprints() -> None:
    """list_sprints returns sorted sprint IDs."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SprintManager(Path(tmp))
        mgr.save_sprint({"id": "b"})
        mgr.save_sprint({"id": "a"})
        assert mgr.list_sprints() == ["a", "b"]


@pytest.mark.unit
def test_ensure_sprint_test_structure_fills_missing() -> None:
    """_ensure_sprint_test_structure adds integration_tests and e2e_tests."""
    data = {}
    _ensure_sprint_test_structure(data)
    assert "integration_tests" in data
    assert data["integration_tests"]["status"] == "pending"
    assert "e2e_tests" in data
