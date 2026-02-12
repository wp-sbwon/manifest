"""
Minimal View TUI: Diagram, Files, Health, Inspector.
Reads blueprint from manifest_dir via io + schema. No tasks or Edit Design.
"""
import argparse
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label
from textual.binding import Binding

from manifest.io.blueprint_io import load_blueprint, load_code_blueprint
from manifest.view.diagram import build_diagram_spec


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Manifest View TUI")
    p.add_argument("--manifest-dir", type=Path, default=None, help="Path to .manifest")
    return p.parse_args()


class DiagramPane(Static):
    """Shows entity tree from blueprint_design."""

    def __init__(self, manifest_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._manifest_dir = manifest_dir

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        data = load_blueprint(self._manifest_dir)
        lines = build_diagram_spec(data)
        self.update("\n".join(lines) if lines else "(empty)")


class FilesPane(Static):
    """Placeholder: list manifest files."""

    def __init__(self, manifest_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._manifest_dir = manifest_dir

    def on_mount(self) -> None:
        try:
            files = list(self._manifest_dir.iterdir()) if self._manifest_dir.exists() else []
            text = "\n".join(f.name for f in sorted(files)[:20]) if files else "(no files)"
        except Exception:
            text = "(error)"
        self.update(text)


class HealthPane(Static):
    """Placeholder: design vs code status."""

    def __init__(self, manifest_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._manifest_dir = manifest_dir

    def on_mount(self) -> None:
        design = load_blueprint(self._manifest_dir)
        code = load_code_blueprint(self._manifest_dir)
        d_ents = len(design.get("entities") or [])
        c_ents = len(code.get("entities") or [])
        self.update(f"Design: {d_ents} entities\nCode: {c_ents} entities")


class InspectorPane(Static):
    """Placeholder: selected entity details."""

    def on_mount(self) -> None:
        self.update("Select a node in Diagram (future)")


class ViewApp(App[None]):
    """Manifest View: Diagram, Files, Health, Inspector."""

    TITLE = "Manifest View"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, manifest_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._manifest_dir = manifest_dir

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left"):
                yield Label("Diagram")
                yield DiagramPane(self._manifest_dir, id="diagram")
            with Vertical(id="right"):
                yield Label("Files")
                yield FilesPane(self._manifest_dir, id="files")
        with Horizontal():
            yield Label("Health")
            yield HealthPane(self._manifest_dir, id="health")
            yield Label("Inspector")
            yield InspectorPane(id="inspector")
        yield Footer()

    def action_refresh(self) -> None:
        diagram = self.query_one("#diagram", DiagramPane)
        diagram._refresh()
        files = self.query_one("#files", FilesPane)
        files.on_mount()
        health = self.query_one("#health", HealthPane)
        health.on_mount()


def main() -> int:
    args = _parse_args()
    manifest_dir = args.manifest_dir
    if not manifest_dir:
        manifest_dir = Path.cwd() / ".manifest"
    manifest_dir = Path(manifest_dir).resolve()
    if not manifest_dir.exists():
        manifest_dir.mkdir(parents=True, exist_ok=True)
    app = ViewApp(manifest_dir=manifest_dir)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
