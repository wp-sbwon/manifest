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
    with tempfile.TemporaryDirectory() as tmp:
        storage = ConflictReportStorage(Path(tmp))
        assert storage.load(Path(tmp) / "missing.json") is None


@pytest.mark.unit
def test_prune_removes_old_resolved() -> None:
    import os
    import time

    with tempfile.TemporaryDirectory() as tmp:
        storage = ConflictReportStorage(Path(tmp))
        old = {"task_id": "t1", "timestamp": "2020-01-01T00:00:00", "conflicts": [], "status": "resolved"}
        path = storage.save(old)
        old_mtime = time.time() - 40 * 86400
        os.utime(str(path), (old_mtime, old_mtime))
        n = storage.prune(max_age_days=30)
        assert n == 1
        assert not path.exists()
