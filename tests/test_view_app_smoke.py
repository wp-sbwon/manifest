"""
Smoke test: ManifestViewApp instantiates and all views load without crashing.

Run: pytest tests/test_view_app_smoke.py -v
"""
from pathlib import Path

from manifest.view.app import ManifestViewApp, ViewType, InspectorMode

ROOT = Path(__file__).resolve().parent.parent


def test_view_app_smoke():
    """App instantiates and all view types and inspector modes load."""
    manifest_dir = ROOT / ".manifest"
    if not manifest_dir.exists():
        manifest_dir = Path.cwd() / ".manifest"
    app = ManifestViewApp(manifest_dir=manifest_dir if manifest_dir.exists() else None)

    for view_type in ViewType:
        app.current_view = view_type
        content = app._get_current_view_content()
        assert content is not None

    app.current_view = ViewType.INSPECTOR
    for mode in InspectorMode:
        app.inspector_mode = mode
        content = app._load_inspector_view()
        assert isinstance(content, str)

    view_map = {
        "Diagram": ViewType.DIAGRAM,
        "Files": ViewType.FILES,
        "Timeline": ViewType.TIMELINE,
        "History": ViewType.HISTORY,
        "Inspector": ViewType.INSPECTOR,
    }
    for view_name, view_type in view_map.items():
        app.action_switch_view(view_name)
        assert app.current_view == view_type
