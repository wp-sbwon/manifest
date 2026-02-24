import json
import tempfile
from pathlib import Path

import pytest

from manifest.core.design_history import get_design_history
from manifest.core.constants import DESIGN_HISTORY_FILE


@pytest.mark.unit
def test_get_design_history_missing_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert get_design_history(Path(tmp)) == []


@pytest.mark.unit
def test_get_design_history_loads_entries() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / DESIGN_HISTORY_FILE
        path.write_text(json.dumps({"entries": [{"ts": "1", "msg": "a"}, {"ts": "2", "msg": "b"}]}))
        result = get_design_history(Path(tmp))
        assert len(result) == 2
        assert result[0]["msg"] == "b"
        assert result[1]["msg"] == "a"
