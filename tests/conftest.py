"""Pytest setup. Skip slow health checks (ruff/pytest) in view tests."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("MANIFEST_VIEW_SKIP_SLOW_METRICS", "1")


@pytest.fixture
def manifest_dir(tmp_path: Path) -> Path:
    """Directory for .manifest (design/code/view files). Created under tmp_path."""
    d = tmp_path / ".manifest"
    d.mkdir(parents=True, exist_ok=True)
    return d
