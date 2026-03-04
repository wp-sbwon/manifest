"""Generated test stubs for entity output. Assertions from blueprint_design.json."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from output.formatter import format_result

@pytest.mark.manifest_assertion("output", 0)
def test_output_assertion_0():
    """Format numeric result for console."""
    assert format_result(42.0) == "42.0"
    assert format_result(0.0) == "0.0"
    assert isinstance(format_result(3.14), str)
