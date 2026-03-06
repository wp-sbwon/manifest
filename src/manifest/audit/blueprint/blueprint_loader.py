"""Load blueprint JSON; normalize."""
from pathlib import Path
from typing import Dict, Any


class BlueprintLoader:
    """Centralized utility for loading blueprint files.

    Delegates to blueprint_io for JSON loading and normalization.
    Optionally attaches metadata fields.
    """

    @staticmethod
    def load_blueprint(
        manifest_dir: Path,
        with_metadata: bool = False,
        default_source: str = "llm_design"
    ) -> Dict[str, Any]:
        """Load blueprint_design.json (from design). Returns version, root_id, entities."""
        from manifest.io.blueprint_io import load_blueprint as _load_bp
        data = _load_bp(manifest_dir)
        if with_metadata:
            from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
            data = ensure_blueprint_metadata(data, default_source, False)
        return data

    @staticmethod
    def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
        """Load blueprint_code.json (from code). Returns version, root_id, entities."""
        from manifest.io.blueprint_io import load_code_blueprint as _load_code_bp
        data = _load_code_bp(manifest_dir)
        from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
        data = ensure_blueprint_metadata(data, "code_extraction", True, "ast_parsing")
        return data
