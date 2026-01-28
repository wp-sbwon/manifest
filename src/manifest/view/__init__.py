"""
Manifest View: visualization-only dashboard.

Chat and terminal are handled by OpenCode. This view shows tasks, blueprint,
structure, drift, and history. Implemented as a Textual TUI.
"""
from manifest.view.app import ManifestViewApp

__all__ = ["ManifestViewApp"]
