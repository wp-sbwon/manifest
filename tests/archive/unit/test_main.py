"""
Unit tests for __main__ module.

Tests the main entry point: launcher (View + OpenCode).
"""
from unittest.mock import patch

from manifest import __main__


def test_main_exists_and_returns_int():
    """__main__.main exists and returns an int (exit code)."""
    assert hasattr(__main__, "main")
    assert callable(__main__.main)
    with patch("manifest.launcher.main", return_value=0):
        result = __main__.main()
        assert result == 0
        assert isinstance(result, int)
    with patch("manifest.launcher._is_opencode_available", return_value=False), \
         patch("manifest.launcher._start_view"), \
         patch("sys.stderr"):
        result = __main__.main()
        assert result == 1
        assert isinstance(result, int)


def test_main_calls_launcher():
    """main() delegates to launcher.main and returns its exit code."""
    with patch("manifest.launcher.main", return_value=0) as m:
        # __main__.main() does: from manifest.launcher import main as launcher_main; return launcher_main()
        # So we patch manifest.launcher.main and call __main__.main(); __main__.main will call the real launcher.main
        # unless we patch it at import time. So we patch manifest.launcher.main before __main__.main runs.
        result = __main__.main()
        assert result == 0
        m.assert_called_once()
