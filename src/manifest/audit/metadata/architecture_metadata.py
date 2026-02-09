"""
Load design blueprint from manifest dir.
Consumers use blueprint + entity_schema helpers.
"""
from pathlib import Path
from typing import Dict, Any


def load_blueprint(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint (entity graph) from manifest dir."""
    from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
    return BlueprintLoader.load_blueprint(Path(manifest_dir), with_metadata=False)
