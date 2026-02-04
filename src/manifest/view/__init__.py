"""
Manifest View: visualization-only dashboard.

Chat and terminal are provided by the configured backend (primary: OpenCode). This view shows tasks, status (planned vs code), structure, and history. Textual TUI.
"""
from manifest.view.app import ManifestViewApp

__all__ = ["ManifestViewApp"]
