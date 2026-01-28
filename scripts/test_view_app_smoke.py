#!/usr/bin/env python3
"""
Smoke test script for ManifestViewApp.

This script verifies that the app can actually start and load all views
without crashing. Run this to verify the app works before deploying.

Usage:
    PYTHONPATH=src python scripts/test_view_app_smoke.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from manifest.view.app import ManifestViewApp, ViewType, InspectorMode
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def test_app_smoke():
    """Test that app can be instantiated and all views load."""
    print("Testing ManifestViewApp smoke test...")

    # Use current directory's .manifest if it exists
    manifest_dir = Path.cwd() / ".manifest"
    if not manifest_dir.exists():
        print(f"WARNING: {manifest_dir} does not exist. Some views may show 'no data'.")

    try:
        # Instantiate app
        print("1. Instantiating app...")
        app = ManifestViewApp(manifest_dir=manifest_dir if manifest_dir.exists() else None)
        print("   ✓ App instantiated successfully")

        # Test all views can load
        print("\n2. Testing all views can load data...")
        for view_type in ViewType:
            app.current_view = view_type
            try:
                content = app._get_current_view_content()
                assert isinstance(content, str)
                print(f"   ✓ {view_type.value} view loaded ({len(content)} chars)")
            except Exception as e:
                print(f"   ✗ {view_type.value} view failed: {e}")
                return False

        # Test Inspector modes
        print("\n3. Testing Inspector modes...")
        app.current_view = ViewType.INSPECTOR
        for mode in InspectorMode:
            app.inspector_mode = mode
            try:
                content = app._load_inspector_view()
                assert isinstance(content, str)
                print(f"   ✓ Inspector {mode.value} mode loaded")
            except Exception as e:
                print(f"   ✗ Inspector {mode.value} mode failed: {e}")
                return False

        # Test view switching
        print("\n4. Testing view switching...")
        view_map = {
            ViewType.ARCHITECT: "Architect",
            ViewType.BLUEPRINT: "Blueprint",
            ViewType.HISTORY: "History",
            ViewType.INSPECTOR: "Inspector",
            ViewType.MISSION_CONTROL: "Mission",
        }
        for view_type, view_name in view_map.items():
            app.action_switch_view(view_name)
            assert app.current_view == view_type, f"Expected {view_type}, got {app.current_view}"
        print("   ✓ View switching works")

        print("\n✅ All smoke tests passed! App should work correctly.")
        return True

    except Exception as e:
        print(f"\n❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_app_smoke()
    sys.exit(0 if success else 1)
