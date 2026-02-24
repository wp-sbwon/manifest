"""Unit tests for ConflictReportStorage."""
import tempfile
from pathlib import Path

import pytest

from manifest.audit.blueprint.conflict_report_storage import ConflictReportStorage


@pytest.mark.unit
def test_save_and_load_roundtrip() -> None:
    """save and load roundtrip preserves data."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ConflictReportStorage(Path(tmp))
        data = {"task_id": "t1", "timestamp": "2025-01-01T00:00:00", "conflicts": [], "status": "pending"}
        path = storage.save(data)
        assert path.exists()
        loaded = storage.load(path)
        assert loaded is not None
        assert loaded["task_id"] == "t1"
        assert loaded["status"] == "pending"


@pytest.mark.unit
def test_load_missing_returns_none() -> None:
    """load returns None for non-existent path."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = ConflictReportStorage(Path(tmp))
        assert storage.load(Path(tmp) / "missing.json") is None
