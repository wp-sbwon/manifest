"""Load blueprint JSON; normalize."""
from pathlib import Path
from typing import Dict, Any

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE
from manifest.audit.entity_schema import empty_blueprint_root
from manifest.audit.entity_validation import normalize_for_schema
from manifest.core.logger import get_logger
from manifest.io.json_io import read_json_or_default

logger = get_logger(__name__)


def _load_and_normalize(path: Path) -> Dict[str, Any]:
    """Load JSON, normalize; log on error."""
    return read_json_or_default(
        path, empty_blueprint_root(), normalize=normalize_for_schema, logger=logger
    )


class BlueprintLoader:
    """Centralized utility for loading blueprint files.

    Provides static methods for loading blueprint_design.json and blueprint_code.json.
    Handles file existence checks, error handling, and optional metadata loading.
    """

    @staticmethod
    def load_blueprint(
        manifest_dir: Path,
        with_metadata: bool = False,
        default_source: str = "llm_design"
    ) -> Dict[str, Any]:
        """Load blueprint_design.json (from design). Returns version, root_id, entities."""
        manifest_dir = Path(manifest_dir)
        blueprint_file = manifest_dir / BLUEPRINT_DESIGN_FILE
        data = _load_and_normalize(blueprint_file)
        if with_metadata:
            from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
            data = ensure_blueprint_metadata(data, default_source, False)
        return data

    @staticmethod
    def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
        """Load blueprint_code.json (from code). Returns version, root_id, entities."""
        manifest_dir = Path(manifest_dir)
        code_blueprint_file = manifest_dir / BLUEPRINT_CODE_FILE
        data = _load_and_normalize(code_blueprint_file)
        from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
        data = ensure_blueprint_metadata(data, "code_extraction", True, "ast_parsing")
        return data
