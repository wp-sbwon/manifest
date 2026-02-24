"""Unit tests for launcher."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from manifest.launcher import (
    _is_manifest_repo,
    _get_project_dir,
    _get_manifest_dir,
    DEV_PROJECT_DIR_NAME,
)


@pytest.mark.unit
def test_is_manifest_repo_true_when_src_manifest_exists() -> None:
    """_is_manifest_repo returns True when src/manifest is a dir."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "src" / "manifest").mkdir(parents=True)
        assert _is_manifest_repo(Path(tmp)) is True


@pytest.mark.unit
def test_is_manifest_repo_false_when_missing() -> None:
    """_is_manifest_repo returns False when src/manifest missing."""
    with tempfile.TemporaryDirectory() as tmp:
        assert _is_manifest_repo(Path(tmp)) is False


@pytest.mark.unit
def test_get_project_dir_uses_env_when_set() -> None:
    """_get_project_dir uses MANIFEST_PROJECT_DIR when set."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch.dict(os.environ, {"MANIFEST_PROJECT_DIR": tmp}):
            assert _get_project_dir() == Path(tmp).resolve()


@pytest.mark.unit
def test_get_manifest_dir_appends_manifest() -> None:
    """_get_manifest_dir returns project_dir/.manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch("manifest.launcher._get_project_dir", return_value=Path(tmp)):
            d = _get_manifest_dir()
            assert d.name == ".manifest"
            assert d.parent == Path(tmp)


@pytest.mark.unit
def test_dev_project_dir_name() -> None:
    """DEV_PROJECT_DIR_NAME is 'tmp'."""
    assert DEV_PROJECT_DIR_NAME == "tmp"
