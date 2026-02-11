"""Tests for fixed PRD schema and validation (timestamp versioning only)."""
import pytest
from pathlib import Path

from manifest.core.prd_schema import validate_prd, normalize_prd, REQUIRED_KEYS
from manifest.core.state_manager import StateManager
from manifest.core.prd_manager import PRDManager


def _valid_prd() -> dict:
    return {
        "title": "Test Product",
        "overview": {"product_name": "Test", "primary_goal": "Goal", "target_users": "Users", "success_metrics": "OK"},
        "user_flows": [],
        "technical_constraints": {},
        "success_criteria": {},
        "architecture_requirements": {},
        "dependencies": [],
        "created_at": "2025-02-05T12:00:00.000Z",
        "updated_at": "2025-02-05T12:00:00.000Z",
    }


def test_validate_prd_valid():
    valid, errors = validate_prd(_valid_prd())
    assert valid is True
    assert errors == []


def test_validate_prd_missing_keys():
    valid, errors = validate_prd({"title": "Only title"})
    assert valid is False
    for key in ("overview", "user_flows", "created_at", "updated_at"):
        assert any(key in e for e in errors)


def test_validate_prd_rejects_numeric_version():
    prd = _valid_prd()
    prd["version"] = "1.0"
    valid, errors = validate_prd(prd)
    assert valid is False
    assert any("version" in e for e in errors)


def test_validate_prd_wrong_types():
    prd = _valid_prd()
    prd["user_flows"] = "not an array"
    valid, errors = validate_prd(prd)
    assert valid is False
    assert any("user_flows" in e for e in errors)


def test_validate_prd_invalid_timestamp():
    prd = _valid_prd()
    prd["created_at"] = "not-a-date"
    valid, errors = validate_prd(prd)
    assert valid is False
    assert any("created_at" in e for e in errors)


def test_normalize_prd_fills_missing():
    prd = {"title": "Minimal"}
    out = normalize_prd(prd)
    for key in REQUIRED_KEYS:
        assert key in out
    assert "version" not in out
    assert out["title"] == "Minimal"
    assert isinstance(out["created_at"], str)
    assert isinstance(out["updated_at"], str)


def test_normalize_prd_removes_version():
    prd = _valid_prd()
    prd["version"] = "1.0"
    out = normalize_prd(prd)
    assert "version" not in out


def test_save_prd_rejects_invalid_prd(tmp_path: Path) -> None:
    """PRDManager.save_prd does not write file and returns (False, errors) for invalid PRD."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    state_manager = StateManager(manifest_dir)
    prd_manager = PRDManager(state_manager)
    invalid = {"title": "Only title"}
    ok, errors = prd_manager.save_prd(invalid)
    assert ok is False
    assert isinstance(errors, list) and len(errors) > 0
    assert not (manifest_dir / "prd.json").exists()


def test_save_prd_accepts_valid_prd(tmp_path: Path) -> None:
    """PRDManager.save_prd writes file and returns (True, []) for valid PRD."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    state_manager = StateManager(manifest_dir)
    prd_manager = PRDManager(state_manager)
    ok, errors = prd_manager.save_prd(_valid_prd())
    assert ok is True
    assert errors == []
    assert (manifest_dir / "prd.json").exists()
