"""Pytest setup. Skip slow health checks (ruff/pytest) in view tests."""
import os

os.environ.setdefault("MANIFEST_VIEW_SKIP_SLOW_METRICS", "1")
