"""Generated test stubs for entity sub. Assertions from blueprint_design.json."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.calculator import sub

@pytest.mark.manifest_assertion("sub", 0)
def test_sub_assertion_0():
    """Return a - b."""
    assert sub(5, 3) == 2
    assert sub(0, 0) == 0
    assert sub(-1, 1) == -2
