"""Generated test stubs for entity add. Assertions from blueprint_design.json."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.calculator import add

@pytest.mark.manifest_assertion("add", 0)
def test_add_assertion_0():
    """Return a + b."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
