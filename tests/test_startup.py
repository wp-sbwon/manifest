"""
Single smoke test: ensures the app starts up okay.

Run: pytest tests/test_startup.py -v
"""
import sys
from pathlib import Path

# Ensure src is on path (same as running from repo root with PYTHONPATH=src)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_app_starts_up():
    """App package imports and exposes runnable entry point (python -m manifest)."""
    import manifest  # noqa: F401
    import manifest.__main__ as main_module
    assert hasattr(main_module, "main")
    assert callable(main_module.main)
