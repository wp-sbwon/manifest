"""
Main entry point for Manifest application.
Allows running with: python -m manifest
"""
from manifest.ui.app import ManifestApp

if __name__ == "__main__":
    app = ManifestApp()
    app.run()
