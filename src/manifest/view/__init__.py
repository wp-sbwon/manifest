"""
Manifest View: visualization-only dashboard.

Chat and terminal are provided by the configured backend (primary: OpenCode). This view shows tasks, blueprint, structure, drift, and history. Textual TUI.
"""
from manifest.view.app import ManifestViewApp

__all__ = ["ManifestViewApp"]
