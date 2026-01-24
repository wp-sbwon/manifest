"""
Main entry point for Manifest application.
Allows running with: python -m manifest
"""
from manifest.ui.app import ManifestApp
from manifest.ui.bootstrap_ui import run_bootstrap
from manifest.core.config import get_config_manager

if __name__ == "__main__":
    # Check if API keys are configured
    config = get_config_manager()
    if not config.has_all_keys():
        # Run bootstrap UI to configure keys
        # This runs in its own event loop and finishes before ManifestApp starts
        run_bootstrap()
    
    # Start the main application
    app = ManifestApp()
    app.run()
