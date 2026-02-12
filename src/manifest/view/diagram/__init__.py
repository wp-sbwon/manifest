"""Diagram spec builder and renderer (config from diagram_config.json)."""

from manifest.view.diagram.config_loader import load_diagram_config
from manifest.view.diagram.builder import (
    build_diagram_spec,
    build_flat_diagram_spec,
    is_app_component,
)
from manifest.view.diagram.render import render_diagram

__all__ = [
    "load_diagram_config",
    "build_diagram_spec",
    "build_flat_diagram_spec",
    "is_app_component",
    "render_diagram",
]
